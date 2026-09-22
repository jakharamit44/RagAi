import os
import asyncio
import logging
import concurrent.futures
from typing import Dict, Any, Optional
from sqlalchemy import select

from .celery_app import celery_app
from db.session import init_db, async_session_factory
from db.models import Chunk, Document
from ingestion.pipeline import IngestionPipeline
from api.rag.embedder import embedder
from api.rag.qdrant_store import qdrant_store
from api.rag.bm25_index import bm25_index

logger = logging.getLogger(__name__)

async def _run_pipeline_async(file_path: str, department: Optional[str], course: Optional[str], semester: Optional[str]) -> Dict[str, Any]:
    await init_db()
    abs_path = os.path.abspath(file_path)

    async with async_session_factory() as session:
        # 1. Process document through ingestion pipeline
        ingest_res = await IngestionPipeline.process_file(abs_path, session)

        if ingest_res.get("status") != "success":
            return ingest_res

        doc_id = ingest_res["document_id"]

        # Override tags if explicitly supplied
        if department or course or semester:
            doc_stmt = select(Document).where(Document.id == doc_id)
            doc = (await session.execute(doc_stmt)).scalar_one()
            if department:
                doc.department = department
            if course:
                doc.course = course
            if semester:
                doc.semester = semester
            await session.commit()

        # 2. Fetch newly created chunks
        chunk_stmt = (
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.document_id == doc_id)
        )
        rows = (await session.execute(chunk_stmt)).all()

        if rows:
            texts = [c.text for c, _ in rows]
            vectors = await asyncio.to_thread(embedder.embed_texts, texts)

            points_to_upsert = []
            bm25_items = []

            for i, ((chunk, doc), vec) in enumerate(zip(rows, vectors)):
                pid = str(chunk.id)
                payload = {
                    "chunk_id": str(chunk.id),
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "department": doc.department,
                    "semester": doc.semester,
                    "course": doc.course,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "text": chunk.text[:350],
                    "content_hash": chunk.content_hash,
                }
                points_to_upsert.append({
                    "id": pid,
                    "vector": vec,
                    "payload": payload
                })
                bm25_items.append(payload)
                chunk.embedding_ref = str(pid)

            await session.commit()

            # 3. Upsert into Qdrant in worker thread
            await asyncio.to_thread(qdrant_store.upsert_chunks, points_to_upsert)

            # 4. Sync in-memory BM25 index safely without blocking server
            bm25_index.add_chunks(bm25_items)

        return {
            "status": "success",
            "document_id": doc_id,
            "title": ingest_res.get("title"),
            "chunks_count": len(rows),
            "department": department or ingest_res.get("tags", {}).get("department"),
            "course": course or ingest_res.get("tags", {}).get("course"),
        }

@celery_app.task(
    name="tasks.process_document_pipeline", 
    bind=True, 
    acks_late=True, 
    max_retries=3, 
    autoretry_for=(Exception,), 
    retry_backoff=True
)
def process_document_pipeline(self, file_path: str, department: Optional[str] = None, course: Optional[str] = None, semester: Optional[str] = None):
    """
    Asynchronous Celery task processing complete ingestion, chunking,
    embedding, and Qdrant indexing pipeline.
    Reference: Phase 8 of technical plan.
    """
    logger.info(f"Worker task {self.request.id} started for: {file_path}")

    # Safely execute async pipeline from either separate Celery worker or eager FastAPI loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                _run_pipeline_async(file_path, department, course, semester)
            )
            result = future.result()
    else:
        result = asyncio.run(_run_pipeline_async(file_path, department, course, semester))

    logger.info(f"Worker task {self.request.id} completed: {result.get('status')}")
    return result
