import os
import sys
import time
import asyncio
import logging
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from db.session import init_db, async_session_factory
from db.models import ManifestEntry
from api.core.cache import cache
from api.core.llm_router import llm_router
from api.rag.qdrant_store import qdrant_store
from ingestion.pipeline import IngestionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("chaos_runner")

async def run_chaos_experiments():
    await init_db()

    transport = ASGITransport(app=app)
    results = []

    logger.info("=================================================================")
    logger.info("   STARTING PHASE 14: CHAOS & FAULT INJECTION EXPERIMENTS        ")
    logger.info("=================================================================\n")

    # -------------------------------------------------------------
    # Experiment 1: Redis Severance & In-Memory Fallback
    # -------------------------------------------------------------
    logger.info("--- Experiment 1: Redis Crash / Severance Simulation ---")
    mock_bad_redis = MagicMock()
    async def broken_call(*args, **kwargs):
        raise ConnectionError("Simulated Redis socket failure (SIGKILL)")
    mock_bad_redis.get = broken_call
    mock_bad_redis.setex = broken_call

    with patch.object(cache, "_get_redis", return_value=mock_bad_redis):
        # Set and get with Redis offline
        test_key = "chaos_test_key_1"
        test_data = {"answer": "Resilient response", "citations": []}
        await cache.set(test_key, test_data, ttl=60)
        retrieved_data = await cache.get(test_key)

        assert retrieved_data is not None
        assert retrieved_data["answer"] == "Resilient response"
        logger.info("✓ Experiment 1 PASSED: Redis severance absorbed by in-memory TTL fallback without query failure.")
        results.append(("Redis Crash / Socket Drop", "In-memory TTL fallback engaged", "PASSED"))

    # -------------------------------------------------------------
    # Experiment 2: Qdrant Vector Store Outage (Degrade to BM25)
    # -------------------------------------------------------------
    logger.info("\n--- Experiment 2: Vector Database Outage Simulation ---")
    def simulate_qdrant_timeout(*args, **kwargs):
        raise TimeoutError("Simulated Qdrant ANN network partition / timeout")

    with patch.object(qdrant_store, "search_dense", side_effect=simulate_qdrant_timeout):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.post("/api/v1/ask", json={
                "question": "When are the instructor office hours for CS401?",
                "department": "ComputerScience",
                "course": "CS401"
            })
            assert res.status_code == 200
            data = res.json()
            assert len(data["citations"]) > 0
            assert any("course_syllabus.txt" in c["title"] for c in data["citations"])
            logger.info(f"✓ Experiment 2 PASSED: Vector outage absorbed. Retrieved via sparse BM25: '{data['citations'][0]['title']}'.")
            results.append(("Vector Store Outage", "Degraded to sparse BM25 search", "PASSED"))

    # -------------------------------------------------------------
    # Experiment 3: Local LLM Backend Dropout
    # -------------------------------------------------------------
    logger.info("\n--- Experiment 3: LLM Inference Engine Dropout ---")
    async def simulate_vllm_crash(*args, **kwargs):
        import httpx
        raise httpx.ConnectError("Simulated vLLM inference backend connection reset")

    with patch.object(llm_router, "_call_local", side_effect=simulate_vllm_crash):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.post("/api/v1/ask", json={
                "question": "What is an AVL tree and what is its rebalancing rule?",
                "department": "ComputerScience",
                "course": "CS401"
            })
            assert res.status_code == 200
            data = res.json()
            assert "Based on verified course material" in data["answer"]
            assert data["served_by"] == "local"
            logger.info("✓ Experiment 3 PASSED: LLM failure absorbed by deterministic local synthesizer.")
            results.append(("LLM Daemon Crash", "Resilient local synthesizer activated", "PASSED"))

    # -------------------------------------------------------------
    # Experiment 4: Corrupted / Malformed File Ingestion
    # -------------------------------------------------------------
    logger.info("\n--- Experiment 4: Corrupted File Ingestion Injected ---")
    corrupt_file = os.path.abspath("data/uploads/corrupt_test_file.docx")
    os.makedirs(os.path.dirname(corrupt_file), exist_ok=True)
    with open(corrupt_file, "wb") as f:
        # Write corrupted header bytes that will fail docx parsing
        f.write(b"CORRUPTED_BINARY_TRASH_DATA_NOT_A_ZIP_CONTAINER")

    async with async_session_factory() as session:
        ingest_result = await IngestionPipeline.process_file(corrupt_file, session)
        assert ingest_result["status"] == "failed"
        logger.info(f"Ingestion result: {ingest_result}")

        # Check manifest recorded the error
        stmt = select(ManifestEntry).where(ManifestEntry.path == corrupt_file)
        entry = (await session.execute(stmt)).scalar_one_or_none()
        assert entry is not None
        assert entry.status == "failed"
        assert entry.error is not None
        logger.info(f"✓ Experiment 4 PASSED: Corrupted file safely isolated in manifest (error: {entry.error[:40]}...).")
        results.append(("Corrupted File Injection", "Manifest isolated error without crashing pipeline", "PASSED"))

    if os.path.exists(corrupt_file):
        os.remove(corrupt_file)

    # -------------------------------------------------------------
    # Experiment 5: Health Check Telemetry Under Degradation
    # -------------------------------------------------------------
    logger.info("\n--- Experiment 5: Health Check Probe Degradation ---")
    def broken_collections():
        raise Exception("Qdrant service down")

    with patch.object(qdrant_store.client, "get_collections", side_effect=broken_collections):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            health_res = await client.get("/health")
            assert health_res.status_code == 200
            h_data = health_res.json()
            assert h_data["status"] == "degraded"
            assert h_data["vector_store"] is False
            logger.info(f"✓ Experiment 5 PASSED: /health correctly reported status='degraded' (data: {h_data}).")
            results.append(("Subsystem Degradation", "Health probe reported status='degraded'", "PASSED"))

    # -------------------------------------------------------------
    # Generate Chaos Scorecard Report
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("      ENTERPRISE UNIVERSITY RAG - CHAOS EXPERIMENTS SCORECARD")
    print("=" * 65)
    for exp_name, fallback_action, status in results:
        print(f"[{status}] {exp_name:<28} -> {fallback_action}")
    print("=" * 65)

    os.makedirs("reports", exist_ok=True)
    report_path = "reports/chaos_test_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Enterprise University RAG - Chaos & Resilience Report\n\n")
        f.write(f"**Execution Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        f.write("## 1. Fault Injection Experiments\n\n")
        f.write("| Experiment | Fault Injected | Self-Healing Fallback Behavior | Result |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for exp_name, fallback_action, status in results:
            f.write(f"| **{exp_name}** | Simulated subsystem failure | {fallback_action} | 🟢 {status} |\n")
        f.write("\n## 2. Verdict\n\nAll 5 chaos injection experiments demonstrated zero uncaught 500 exceptions, automatic graceful degradation, and seamless recovery.\n")

    logger.info(f"Chaos report exported to: {report_path}")
    return results

if __name__ == "__main__":
    asyncio.run(run_chaos_experiments())
