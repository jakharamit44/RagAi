import re
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import WebScrapeManifest
from .url_normalizer import UrlNormalizer

logger = logging.getLogger(__name__)

class DeltaDetector:
    """
    Intelligent 3-tier delta change detection engine.
    Eliminates redundant network transfers and vector indexing for unchanged content.
    """

    @staticmethod
    def normalize_academic_text(text: str) -> str:
        """
        Strips dynamic server noise such as live visitor counters, timestamps,
        and volatile whitespace so content hashing is robust and deterministic.
        """
        if not text:
            return ""
        # Remove live visitor / user counters commonly present on university portals
        cleaned = re.sub(r'(?:Online Users|Total Visitors?|Visitor Counter|Page Hits?|Hit Count)\s*:\s*\**\d+\**', '', text, flags=re.I)
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned


    @staticmethod
    async def get_conditional_headers(url: str, session: AsyncSession) -> Dict[str, str]:
        """
        Retrieves If-None-Match (ETag) and If-Modified-Since headers from previous crawl manifest.
        """
        url_hash = UrlNormalizer.get_url_hash(url)
        stmt = select(WebScrapeManifest).where(WebScrapeManifest.url_hash == url_hash)
        entry = (await session.execute(stmt)).scalars().first()

        headers = {}
        if entry:
            if entry.etag:
                headers["If-None-Match"] = entry.etag
            if entry.last_modified_header:
                headers["If-Modified-Since"] = entry.last_modified_header

        return headers

    @staticmethod
    async def evaluate_change(
        url: str,
        http_status: int,
        response_headers: Dict[str, str],
        raw_body: bytes = b"",
        extracted_text: Optional[str] = None,
        session: AsyncSession = None,
        computed_hash: Optional[str] = None
    ) -> Tuple[bool, str, Optional[WebScrapeManifest]]:
        """
        Evaluates whether a web page or document has changed and needs ingestion.
        Returns:
            (should_ingest, reason, manifest_entry)
        """
        url_hash = UrlNormalizer.get_url_hash(url)
        stmt = select(WebScrapeManifest).where(WebScrapeManifest.url_hash == url_hash)
        manifest_entry = (await session.execute(stmt)).scalars().first()

        # Tier 1: Server returned 304 Not Modified
        if http_status == 304:
            if manifest_entry:
                manifest_entry.last_checked_at = datetime.utcnow()
                manifest_entry.status = "skipped_unchanged"
                await session.commit()
            return False, "304_not_modified", manifest_entry

        # Extract headers from response
        etag = response_headers.get("etag") or response_headers.get("ETag")
        last_modified = response_headers.get("last-modified") or response_headers.get("Last-Modified")

        # Tier 2: Determine content hash (from pre-computed stream hash, normalized text, or raw body)
        if computed_hash:
            new_content_hash = computed_hash
        elif extracted_text is not None:
            normalized_str = DeltaDetector.normalize_academic_text(extracted_text)
            target_bytes = normalized_str.encode("utf-8")
            new_content_hash = hashlib.sha256(target_bytes).hexdigest()
        else:
            target_bytes = raw_body
            new_content_hash = hashlib.sha256(target_bytes).hexdigest()


        if manifest_entry:
            # Check if content matches previous run
            if manifest_entry.content_hash == new_content_hash:
                manifest_entry.last_checked_at = datetime.utcnow()
                manifest_entry.status = "skipped_unchanged"
                if etag:
                    manifest_entry.etag = etag
                if last_modified:
                    manifest_entry.last_modified_header = last_modified
                await session.commit()
                return False, "content_hash_unchanged", manifest_entry
            else:
                # Content has changed
                manifest_entry.last_checked_at = datetime.utcnow()
                manifest_entry.last_changed_at = datetime.utcnow()
                manifest_entry.content_hash = new_content_hash
                if etag:
                    manifest_entry.etag = etag
                if last_modified:
                    manifest_entry.last_modified_header = last_modified
                manifest_entry.status = "modified"
                await session.commit()
                return True, "content_modified", manifest_entry

        # Tier 3: Brand new URL never seen before
        new_entry = WebScrapeManifest(
            url=url,
            url_hash=url_hash,
            content_type=response_headers.get("content-type", "text/html").split(";")[0],
            etag=etag,
            last_modified_header=last_modified,
            content_hash=new_content_hash,
            http_status=http_status,
            status="discovered",
            last_checked_at=datetime.utcnow(),
            last_changed_at=datetime.utcnow(),
        )
        session.add(new_entry)
        await session.commit()
        return True, "new_resource", new_entry
