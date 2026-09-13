import logging
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Document, Chunk, WebScrapeManifest
from ingestion.chunker import chunker
from ingestion.dedup import ContentDeduplicator
from api.rag.embedder import embedder
from api.rag.qdrant_store import qdrant_store
from api.rag.bm25_index import bm25_index
from workers.ingest_tasks import _run_pipeline_async
from .storage_cleaner import StorageCleaner

logger = logging.getLogger(__name__)

class ScraperIngestBridge:
    """
    Bridges scraped web pages and downloaded academic documents directly into the RagAi vector pipeline.
    """

    @staticmethod
    async def ingest_document_file(
        local_file_path: str,
        manifest_entry: WebScrapeManifest,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Ingests a downloaded PDF/DOCX using the core document ingestion pipeline.
        """
        try:
            res = await _run_pipeline_async(
                file_path=local_file_path,
                department="University Portal",
                course="Official Document",
                semester="All"
            )

            if res.get("status") == "success":
                manifest_entry.document_id = res.get("document_id")
                manifest_entry.status = "ingested"
                manifest_entry.local_file_path = None
                await session.commit()
                logger.info(f"Successfully indexed document {local_file_path} into vector store.")
                StorageCleaner.cleanup_file(local_file_path)
            elif res.get("status") == "skipped":
                manifest_entry.status = "skipped_unchanged"
                await session.commit()
                StorageCleaner.cleanup_file(local_file_path)
            else:
                manifest_entry.status = "failed"
                manifest_entry.error_message = str(res.get("message") or "Pipeline processing failed")
                await session.commit()
                StorageCleaner.cleanup_file(local_file_path)

            return res
        except Exception as e:
            logger.error(f"Error ingesting file {local_file_path}: {e}")
            manifest_entry.status = "failed"
            manifest_entry.error_message = str(e)
            await session.commit()
            StorageCleaner.cleanup_file(local_file_path)
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def ingest_web_page(
        page_url: str,
        title: str,
        markdown_text: str,
        manifest_entry: WebScrapeManifest,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Ingests clean Markdown text of a crawled web page into the RAG pipeline.
        """
        if not markdown_text or len(markdown_text.strip()) < 50:
            manifest_entry.status = "skipped_empty"
            await session.commit()
            return {"status": "skipped", "reason": "insufficient_text"}

        try:
            clean_title = title.strip() or page_url.split("/")[-1] or "MDU Web Notice"

            # Check if document already exists for this URL
            existing_doc = None
            if manifest_entry.document_id:
                stmt = select(Document).where(Document.id == manifest_entry.document_id)
                existing_doc = (await session.execute(stmt)).scalars().first()

            if existing_doc:
                doc_record = existing_doc
                doc_record.title = clean_title
                # Remove previous chunks to refresh
                del_chunks = delete(Chunk).where(Chunk.document_id == doc_record.id)
                await session.execute(del_chunks)
            else:
                doc_record = Document(
                    source_path=page_url,
                    title=clean_title,
                    department="University Portal",
                    course="Web Announcement",
                    semester="All",
                    doc_type="web_page",
                    ocr_confidence=1.0,
                )
                session.add(doc_record)
                await session.flush()

            manifest_entry.document_id = doc_record.id

            # Chunk document
            pages_data = [{"page_number": 1, "section": clean_title, "text": markdown_text}]
            raw_chunks = chunker.chunk_document(pages_data)
            unique_chunks = ContentDeduplicator.deduplicate_in_memory(raw_chunks)

            if not unique_chunks:
                manifest_entry.status = "ingested"
                await session.commit()
                return {"status": "success", "chunks": 0}

            # Embed chunks using CPU embedder FIRST (offloaded to thread, zero SQLite lock time)
            texts = [c.get("text", "") for c in unique_chunks]
            vectors = await asyncio.to_thread(embedder.embed_texts, texts)

            chunk_models = []
            for c in unique_chunks:
                chunk_record = Chunk(
                    document_id=doc_record.id,
                    page_number=c.get("page_number", 1),
                    section=c.get("section", clean_title),
                    text=c.get("text"),
                    content_hash=c.get("content_hash"),
                )
                chunk_models.append(chunk_record)

            session.add_all(chunk_models)
            await session.flush()

            points_to_upsert = []
            bm25_items = []

            for chunk, vec in zip(chunk_models, vectors):
                pid = str(chunk.id)
                payload = {
                    "chunk_id": str(chunk.id),
                    "document_id": str(doc_record.id),
                    "title": doc_record.title,
                    "department": doc_record.department,
                    "semester": doc_record.semester,
                    "course": doc_record.course,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "text": chunk.text,
                    "content_hash": chunk.content_hash,
                }
                points_to_upsert.append({
                    "id": pid,
                    "vector": vec,
                    "payload": payload
                })
                bm25_items.append(payload)
                chunk.embedding_ref = pid

            manifest_entry.status = "ingested"
            manifest_entry.title = clean_title
            await session.commit()

            # Upsert into Qdrant (offloaded to thread to avoid blocking loop)
            await asyncio.to_thread(qdrant_store.upsert_chunks, points_to_upsert)
            bm25_index.corpus.extend(bm25_items)

            logger.info(f"Ingested web page: {clean_title} ({len(chunk_models)} chunks)")

            # Synchronize OpenViking tiered context (debounced)
            try:
                from api.context.tiered_engine import tiered_engine
                tiered_engine.trigger_debounced_sync(delay=3.0)
            except Exception as e:
                logger.warning(f"Could not trigger tiered engine sync after web ingestion: {e}")

            return {
                "status": "success",
                "document_id": str(doc_record.id),
                "title": clean_title,
                "chunks_count": len(chunk_models)
            }

        except Exception as e:
            logger.error(f"Failed to ingest web page {page_url}: {e}")
            manifest_entry.status = "failed"
            manifest_entry.error_message = str(e)
            await session.commit()
            return {"status": "error", "message": str(e)}
