import os
import sys
import asyncio
import logging
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_metrics")

async def test_metrics_pipeline():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Initial Scrape of /metrics
        logger.info("\n--- 1. Initial Scrape of /metrics ---")
        res1 = await client.get("/metrics")
        assert res1.status_code == 200
        assert "rag_documents_total" in res1.text
        assert "rag_chunks_total" in res1.text
        logger.info(f"✓ GET /metrics PASSED (Scrape size: {len(res1.text)} bytes)")

        # 2. Trigger a Cache Miss Query
        logger.info("\n--- 2. Sending Query to Trigger Cache Miss & Retrieval Metrics ---")
        q1 = {"question": "What is an AVL tree balancing factor?", "department": "ComputerScience", "course": "CS401"}
        res_q1 = await client.post("/api/v1/ask", json=q1)
        assert res_q1.status_code == 200

        # 3. Trigger a Cache Hit Query
        logger.info("\n--- 3. Sending Identical Query to Trigger Cache Hit Metric ---")
        res_q2 = await client.post("/api/v1/ask", json=q1)
        assert res_q2.status_code == 200

        # 4. Scrape /metrics again and assert telemetry was updated
        logger.info("\n--- 4. Scraping /metrics to verify metric counters & histograms ---")
        res2 = await client.get("/metrics")
        assert res2.status_code == 200
        metrics_body = res2.text

        logger.info("Verifying metric keys in scrape output:")
        for metric_name in [
            "rag_query_total",
            "rag_query_duration_seconds",
            "rag_retrieval_duration_seconds",
            "rag_cache_hits_total",
            "rag_cache_misses_total",
            "rag_documents_total",
            "rag_chunks_total"
        ]:
            assert metric_name in metrics_body, f"Missing metric {metric_name} in /metrics output!"
            logger.info(f"  ✓ Found {metric_name}")

        # Extract specific counters
        assert "rag_cache_hits_total 1.0" in metrics_body or "rag_cache_hits_total 2.0" in metrics_body
        logger.info("✓ Cache Hit Counter verified in Prometheus export")

    logger.info("\n=======================================================")
    logger.info("ALL PHASE 12 PROMETHEUS METRICS TESTS PASSED!")
    logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(test_metrics_pipeline())
