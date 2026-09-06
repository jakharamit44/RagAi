import os
import sys
import asyncio
import logging
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_workers")

async def test_async_worker_flow():
    await init_db()

    # 1. Create a sample upload document
    test_upload_file = os.path.abspath("data/test_lecture_nlp.txt")
    os.makedirs(os.path.dirname(test_upload_file), exist_ok=True)
    with open(test_upload_file, "w", encoding="utf-8") as f:
        f.write(
            "# CS402: Natural Language Processing\n\n"
            "Instructor: Dr. Noam Chomsky\n\n"
            "## Lecture 1: Reciprocal Rank Fusion\n"
            "Reciprocal Rank Fusion (RRF) is a method that combines multiple retrieval score lists. "
            "It computes the reciprocal rank 1 / (k + rank) for each candidate document across sparse and dense search.\n\n"
            "## Lecture 2: Transformer Attention\n"
            "Self-attention calculates Query, Key, and Value vectors to allow all tokens to attend to each other simultaneously."
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        logger.info("\n--- 1. Testing POST /api/v1/documents/upload (Multipart) ---")

        from api.core.auth import create_access_token
        faculty_token = create_access_token({"sub": "faculty_uploader", "role": "faculty"})
        headers = {"Authorization": f"Bearer {faculty_token}"}

        with open(test_upload_file, "rb") as file_stream:
            files = {"file": ("lecture_nlp.txt", file_stream, "text/plain")}
            data = {"department": "ComputerScience", "course": "CS402"}

            res = await client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)

        logger.info(f"Upload Response ({res.status_code}): {res.json()}")
        assert res.status_code == 202
        upload_data = res.json()
        assert upload_data["status"] == "queued"
        task_id = upload_data.get("task_id")
        assert task_id is not None
        logger.info(f"✓ Upload accepted with task ID: {task_id}")

        # 2. Poll Task Status
        logger.info("\n--- 2. Polling GET /api/v1/documents/tasks/{task_id} ---")
        status_res = await client.get(f"/api/v1/documents/tasks/{task_id}")
        assert status_res.status_code == 200
        task_status = status_res.json()
        logger.info(f"Task status: {task_status}")
        assert task_status["state"] in ["SUCCESS", "PENDING"]
        logger.info("✓ Task Status Query PASSED")

        # 3. Test Asking a Question from the newly uploaded document!
        logger.info("\n--- 3. Testing /api/v1/ask from asynchronously indexed document ---")
        ask_payload = {
            "question": "How does Reciprocal Rank Fusion work in retrieval?",
            "department": "ComputerScience",
            "course": "CS402",
        }
        ask_res = await client.post("/api/v1/ask", json=ask_payload)
        assert ask_res.status_code == 200
        ask_data = ask_res.json()
        logger.info(f"Answer: {ask_data['answer']}")
        logger.info(f"Citations count: {len(ask_data['citations'])}")
        assert len(ask_data["citations"]) > 0
        assert any("lecture_nlp.txt" in c["title"] for c in ask_data["citations"])
        logger.info("✓ Async-indexed document Q&A Verified!")

    logger.info("\n=======================================================")
    logger.info("ALL PHASE 8 CELERY WORKER TESTS PASSED!")
    logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(test_async_worker_flow())
