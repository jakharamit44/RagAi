import os
import sys
import asyncio
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.session import init_db, async_session_factory
from db.models import Chunk, Document
from sqlalchemy import select
from api.rag.retriever import retriever
from api.rag.bm25_index import bm25_index

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_retrieval")

async def test_all_queries():
    await init_db()

    # Ensure BM25 has loaded corpus from DB
    async with async_session_factory() as session:
        stmt = select(Chunk, Document).join(Document, Chunk.document_id == Document.id)
        rows = (await session.execute(stmt)).all()
        corpus = []
        for c, d in rows:
            corpus.append({
                "chunk_id": str(c.id),
                "document_id": str(d.id),
                "title": d.title,
                "department": d.department,
                "semester": d.semester,
                "course": d.course,
                "page_number": c.page_number,
                "section": c.section,
                "text": c.text,
            })
        bm25_index.build_index(corpus)

    test_queries = [
        {
            "q": "What is an AVL tree and how does it rebalance?",
            "scope": {"course": "CS401"},
            "expected_term": "AVL"
        },
        {
            "q": "When are the instructor office hours?",
            "scope": {"course": "CS401"},
            "expected_term": "Office Hours"
        },
        {
            "q": "Five design principles behind every phase",
            "scope": None,
            "expected_term": "principles"
        }
    ]

    for item in test_queries:
        q = item["q"]
        scope = item["scope"] or {}
        logger.info(f"\n==========================================")
        logger.info(f"Query: '{q}' (Scope: {scope})")

        results = await retriever.retrieve(
            query=q,
            department=scope.get("department"),
            course=scope.get("course"),
            semester=scope.get("semester")
        )

        logger.info(f"Top {len(results)} chunks retrieved:")
        for idx, r in enumerate(results):
            logger.info(f"  [{idx+1}] Doc: '{r.get('title')}' | Sec: '{r.get('section')}' | Page: {r.get('page_number')}")
            logger.info(f"      Score: {r.get('rerank_score', 0):.4f} | RRF: {r.get('rrf_score', 0):.4f}")
            logger.info(f"      Snippet: {r.get('text', '')[:120].strip()}...\n")

        assert len(results) > 0, f"No results for query: {q}"
        assert any(item["expected_term"].lower() in r.get("text", "").lower() for r in results), (
            f"Expected term '{item['expected_term']}' not found in top results."
        )

    logger.info("ALL RETRIEVAL TESTS PASSED! Hybrid search & citation linking operational.")

if __name__ == "__main__":
    asyncio.run(test_all_queries())
