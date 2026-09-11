import os
import asyncio
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Document, Chunk
from .manifest import ManifestManager
from .path_tagger import PathTagger
from .extractors import DocumentExtractorRouter
from .chunker import chunker
from .dedup import ContentDeduplicator

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Unified Ingestion Pipeline:
    Change Detection -> Metadata Inference -> Text Extraction -> Semantic Chunking -> DB Persistence.
    Reference: Phase 1 & Phase 2 of technical plan.
    """

    @staticmethod
    async def process_file(
        file_path: str,
        session: AsyncSession,
        watched_root: Optional[str] = None,
        force_reprocess: bool = False,
        department: Optional[str] = None,
        course: Optional[str] = None,
        semester: Optional[str] = None,
    ) -> Dict[str, Any]:
        abs_path = os.path.abspath(file_path)
        filename = os.path.basename(abs_path)

        # 1. Change detection via Manifest (with duplicate SHA-256 bypass)
        should_process, content_hash, mtime, reason = await ManifestManager.should_process(abs_path, session)
        if not should_process and not force_reprocess:
            if reason == "duplicate_skipped":
                logger.info(f"Bypassing duplicate file: {filename} (hash: {str(content_hash)[:8]}...)")
                return {
                    "status": "skipped",
                    "reason": "duplicate_skipped",
                    "path": abs_path,
                    "content_hash": content_hash,
                    "message": "Duplicate file content already indexed. Zero compute wasted."
                }
            logger.info(f"Skipping unchanged file: {filename}")
            return {
                "status": "skipped",
                "reason": "unchanged",
                "path": abs_path,
                "content_hash": content_hash,
                "message": "File unchanged since last scan."
            }

        logger.info(f"Ingesting: {filename} (hash: {str(content_hash)[:8]}..., reason: {reason})")
        # Mark manifest as processing
        await ManifestManager.record_entry(session, abs_path, content_hash, mtime, status="processing")

        try:
            # 2. Metadata tagging from folder path or manual override (supports mixed files)
            tags = PathTagger.infer_tags(abs_path, watched_root=watched_root)
            folder_basename = os.path.basename(os.path.dirname(abs_path))
            if folder_basename.upper() in ["", "/", "\\", "C:", "D:", "E:", "DATA", "UPLOADS"]:
                folder_basename = "General"

            final_dept = department or tags.get("department") or "General"
            final_course = course or tags.get("course") or folder_basename
            final_sem = semester or tags.get("semester") or "All"

            # 3. Document text extraction (offloaded to thread for OCR/PDF compute)
            pages_data, doc_type, ocr_confidence = await asyncio.to_thread(DocumentExtractorRouter.extract, abs_path)

            # 4. Save Document record (Table 14)
            doc_record = Document(
                source_path=abs_path,
                title=filename,
                department=final_dept,
                semester=final_sem,
                course=final_course,
                doc_type=doc_type,
                ocr_confidence=ocr_confidence,
            )
            session.add(doc_record)
            await session.flush()  # populate doc_record.id

            # 5. Semantic layout-aware chunking (Phase 2 & Table 15)
            raw_chunks = chunker.chunk_document(pages_data)

            # Deduplicate chunks
            unique_chunks = ContentDeduplicator.deduplicate_in_memory(raw_chunks)

            # 6. Save Chunk records
            chunk_models = []
            for c in unique_chunks:
                chunk_record = Chunk(
                    document_id=doc_record.id,
                    page_number=c.get("page_number"),
                    section=c.get("section"),
                    text=c.get("text"),
                    content_hash=c.get("content_hash"),
                    embedding_ref=None  # will be populated in Phase 3 by embedder
                )
                chunk_models.append(chunk_record)

            session.add_all(chunk_models)
            await session.commit()

            # 7. Mark Manifest as done
            await ManifestManager.record_entry(session, abs_path, content_hash, mtime, status="done")

            logger.info(
                f"Successfully ingested {filename}: {len(chunk_models)} chunks created, "
                f"dept={tags.get('department')}, course={tags.get('course')}"
            )

            return {
                "status": "success",
                "document_id": str(doc_record.id),
                "title": filename,
                "chunks_count": len(chunk_models),
                "tags": tags,
                "doc_type": doc_type
            }

        except Exception as e:
            logger.error(f"Failed to ingest {filename}: {e}", exc_info=True)
            await session.rollback()
            await ManifestManager.record_entry(
                session, abs_path, content_hash, mtime, status="failed", error=str(e)
            )
            return {"status": "failed", "path": abs_path, "error": str(e)}
