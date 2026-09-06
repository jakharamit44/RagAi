import os
import sys
import time
import asyncio
import logging
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from api.core.config import settings
from db.session import init_db, async_session_factory
from db.models import QueryAuditLog

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_cache")

async def run_cache_and_ratelimit_tests():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        query_payload = {
            "question": "What is an AVL tree and what is its rebalancing rule?",
            "department": "ComputerScience",
            "course": "CS401",
        }

        # 1. Query 1: Initial Cache Miss
        logger.info("\n--- 1. First Query: Expect Cache MISS ---")
        t0 = time.time()
        res1 = await client.post("/api/v1/ask", json=query_payload)
        t1 = time.time()
        latency1 = (t1 - t0) * 1000

        assert res1.status_code == 200
        data1 = res1.json()
        logger.info(f"Response 1: served_by='{data1['served_by']}', latency={latency1:.2f}ms")
        assert data1["served_by"] == "local"
        logger.info("✓ Query 1 (Cache MISS) PASSED")

        # 2. Query 2: Cache Hit
        logger.info("\n--- 2. Second Query: Expect Cache HIT ---")
        t2 = time.time()
        res2 = await client.post("/api/v1/ask", json=query_payload)
        t3 = time.time()
        latency2 = (t3 - t2) * 1000

        assert res2.status_code == 200
        data2 = res2.json()
        logger.info(f"Response 2: served_by='{data2['served_by']}', latency={latency2:.2f}ms")
        assert data2["served_by"] == "cache"
        assert len(data2["citations"]) == len(data1["citations"])
        logger.info("✓ Query 2 (Cache HIT) PASSED")

        # 3. Verify Query Audit Log in Database
        logger.info("\n--- 3. Verifying Query Audit Log in Database ---")
        async with async_session_factory() as session:
            stmt = select(QueryAuditLog).order_by(QueryAuditLog.timestamp.desc()).limit(2)
            audit_records = (await session.execute(stmt)).scalars().all()
            logger.info(f"Retrieved {len(audit_records)} recent audit log records:")
            for rec in audit_records:
                logger.info(f"  - Hash: {rec.question_hash[:10]}... | served_by={rec.served_by} | latency={rec.latency_ms:.2f}ms | tokens={rec.tokens_used}")

            assert len(audit_records) >= 2
            served_by_set = {r.served_by for r in audit_records}
            assert "cache" in served_by_set
            logger.info("✓ Query Audit Logging PASSED")

        # 4. Test Rate Limiting
        logger.info("\n--- 4. Testing Rate Limiting (Burst Requests) ---")
        # Send rapid burst of 65 requests from same IP (limit is 60/min)
        exceeded_429 = False
        for i in range(65):
            res = await client.post(
                "/api/v1/ask",
                json={"question": f"Spam question {i}", "department": "ComputerScience", "course": "CS401"}
            )
            if res.status_code == 429:
                exceeded_429 = True
                logger.info(f"Triggered 429 on request #{i + 1}: {res.json()}")
                break

        assert exceeded_429, "Rate limiter did not trigger HTTP 429 on burst traffic!"
        logger.info("✓ Rate Limiter HTTP 429 Trigger PASSED")

    logger.info("\n===========================================================")
    logger.info("ALL PHASE 7 CACHING & RATE LIMITING TESTS PASSED!")
    logger.info("===========================================================")

if __name__ == "__main__":
    asyncio.run(run_cache_and_ratelimit_tests())
