import os
import hashlib
import logging
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import ManifestEntry

logger = logging.getLogger(__name__)

import asyncio

class ManifestManager:
    """
    Manages document change detection via database manifest entries.
    Reference: Phase 1 & Appendix A (Table 13).
    """
    _lock = asyncio.Lock()

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Compute SHA-256 content hash in 64KB streaming blocks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    async def should_process(cls, file_path: str, session: AsyncSession) -> Tuple[bool, Optional[str], float, str]:
        """
        Check if a file is new, modified, unchanged, or duplicate.
        Returns: (should_process, content_hash, mtime, reason)
        where reason is one of: 'new_file', 'modified', 'retry_failed', 'unchanged', 'duplicate_skipped', 'file_not_found'.
        """
        async with cls._lock:
            if not os.path.exists(file_path):
                return False, None, 0.0, "file_not_found"

            mtime = os.path.getmtime(file_path)
            stmt = select(ManifestEntry).where(ManifestEntry.path == file_path)
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()

            if entry is not None and entry.status == "processing":
                return False, entry.content_hash, mtime, "processing"

            if entry is None:
                content_hash = ManifestManager.compute_sha256(file_path)
                dup_stmt = select(ManifestEntry).where(
                    ManifestEntry.content_hash == content_hash,
                    ManifestEntry.status == "done"
                )
                dup_res = await session.execute(dup_stmt)
                dup_entry = dup_res.scalars().first()

                if dup_entry is not None:
                    logger.info(
                        f"Duplicate file content detected for '{os.path.basename(file_path)}' "
                        f"(matches '{os.path.basename(dup_entry.path)}'). Bypassing."
                    )
                    await ManifestManager.record_entry(
                        session,
                        file_path=file_path,
                        content_hash=content_hash,
                        mtime=mtime,
                        status="skipped_duplicate",
                        error=f"Duplicate content matches {os.path.basename(dup_entry.path)}"
                    )
                    return False, content_hash, mtime, "duplicate_skipped"

                await ManifestManager.record_entry(session, file_path, content_hash, mtime, status="processing")
                return True, content_hash, mtime, "new_file"

            if entry.status == "skipped_duplicate" and abs(entry.mtime - mtime) <= 1e-3:
                return False, entry.content_hash, mtime, "duplicate_skipped"

            if abs(entry.mtime - mtime) > 1e-3 or entry.status == "failed":
                content_hash = ManifestManager.compute_sha256(file_path)
                if content_hash != entry.content_hash or entry.status == "failed":
                    dup_stmt = select(ManifestEntry).where(
                        ManifestEntry.content_hash == content_hash,
                        ManifestEntry.status == "done",
                        ManifestEntry.path != file_path
                    )
                    dup_res = await session.execute(dup_stmt)
                    dup_entry = dup_res.scalars().first()
                    if dup_entry is not None:
                        logger.info(f"Updated content matches existing file '{dup_entry.path}'. Bypassing.")
                        await ManifestManager.record_entry(
                            session,
                            file_path=file_path,
                            content_hash=content_hash,
                            mtime=mtime,
                            status="skipped_duplicate",
                            error=f"Duplicate content matches {os.path.basename(dup_entry.path)}"
                        )
                        return False, content_hash, mtime, "duplicate_skipped"

                    reason = "retry_failed" if entry.status == "failed" else "modified"
                    await ManifestManager.record_entry(session, file_path, content_hash, mtime, status="processing")
                    return True, content_hash, mtime, reason

            return False, entry.content_hash, mtime, "unchanged"

    @staticmethod
    async def record_entry(
        session: AsyncSession,
        file_path: str,
        content_hash: str,
        mtime: float,
        status: str = "pending",
        error: Optional[str] = None
    ) -> ManifestEntry:
        """Upsert a manifest entry for change detection."""
        stmt = select(ManifestEntry).where(ManifestEntry.path == file_path)
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry is None:
            entry = ManifestEntry(
                path=file_path,
                content_hash=content_hash,
                mtime=mtime,
                status=status,
                error=error,
                updated_at=datetime.utcnow(),
            )
            session.add(entry)
        else:
            entry.content_hash = content_hash
            entry.mtime = mtime
            entry.status = status
            entry.error = error
            entry.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(entry)
        return entry
