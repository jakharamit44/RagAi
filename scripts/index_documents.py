import os
import sys
import asyncio
import logging
from uuid import uuid4
from sqlalchemy import select, update

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.session import init_db, async_session_factory
from db.models import Document, Chunk
from api.rag.embedder import embedder
from api.rag.qdrant_store import qdrant_store
from api.rag.bm25_index import bm25_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("index_documents")

async def index_all_chunks(batch_size: int = 50):
    await init_db()

    async with async_session_factory() as session:
        # Fetch chunks with their document metadata
        stmt = (
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.embedding_ref == None)  # unindexed chunks
        )
        result = await session.execute(stmt)
        rows = result.all()

        if not rows:
            # If all are already indexed, fetch all for verification/BM25
            logger.info("No unindexed chunks found. Fetching all chunks for BM25 sync...")
            all_stmt = select(Chunk, Document).join(Document, Chunk.document_id == Document.id)
            rows = (await session.execute(all_stmt)).all()

        logger.info(f"Total chunks to process: {len(rows)}")

        bm25_corpus = []
        points_to_upsert = []
        point_id_counter = 1

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            texts = [chunk.text for chunk, _ in batch]
            vectors = embedder.embed_texts(texts)

            for (chunk, doc), vec in zip(batch, vectors):
                point_id = point_id_counter
                point_id_counter += 1

                payload = {
                    "chunk_id": str(chunk.id),
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "department": doc.department,
                    "semester": doc.semester,
                    "course": doc.course,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "text": chunk.text,
                    "content_hash": chunk.content_hash,
                }

                points_to_upsert.append({
                    "id": point_id,
                    "vector": vec,
                    "payload": payload
                })

                bm25_corpus.append(payload)

                # Update database embedding_ref
                chunk.embedding_ref = str(point_id)

            await session.commit()
            logger.info(f"Embedded batch {i // batch_size + 1}: {len(batch)} chunks.")

        # Upsert into Qdrant
        if points_to_upsert:
            qdrant_store.upsert_chunks(points_to_upsert)
            logger.info(f"Upserted {len(points_to_upsert)} points into Qdrant collection.")

        # Build in-memory BM25 index
        bm25_index.build_index(bm25_corpus)
        logger.info(f"BM25 index built with {len(bm25_corpus)} documents.")

    logger.info("Indexing process completed successfully!")

if __name__ == "__main__":
    asyncio.run(index_all_chunks())
