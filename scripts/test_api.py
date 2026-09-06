import os
import sys
import asyncio
import logging
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from api.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_api")

async def run_api_tests():
    logger.info("Initializing in-memory ASGI test client...")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test /health
        logger.info("\n--- 1. Testing GET /health ---")
        res = await client.get("/health")
        logger.info(f"Health Response ({res.status_code}): {res.json()}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["database"] is True
        assert data["vector_store"] is True
        assert data["documents_indexed"] >= 3
        logger.info("✓ GET /health PASSED")

        # 2. Test POST /api/v1/ask (Course Scoped Query)
        logger.info("\n--- 2. Testing POST /api/v1/ask (AVL Trees) ---")
        req_body = {
            "question": "What is an AVL tree and what is its rebalancing rule?",
            "department": "ComputerScience",
            "course": "CS401",
        }
        res = await client.post("/api/v1/ask", json=req_body)
        logger.info(f"Ask Response Status: {res.status_code}")
        data = res.json()
        logger.info(f"Answer: {data['answer'][:150]}...")
        logger.info(f"Served by: {data['served_by']}")
        logger.info(f"Citations ({len(data['citations'])}):")
        for c in data["citations"]:
            logger.info(f"  - [{c['title']} p.{c['page_number']} {c['section']}]: {c['snippet'][:80]}...")

        assert res.status_code == 200
        assert len(data["citations"]) > 0
        assert any("lecture1_notes.docx" in c["title"] for c in data["citations"])
        assert "avl" in data["answer"].lower()
        logger.info("✓ POST /api/v1/ask (Course Query) PASSED")

        # 3. Test POST /api/v1/ask (Technical Plan Query)
        logger.info("\n--- 3. Testing POST /api/v1/ask (Five Design Principles) ---")
        req_body2 = {
            "question": "What are the five design principles behind every phase?",
        }
        res2 = await client.post("/api/v1/ask", json=req_body2)
        assert res2.status_code == 200
        data2 = res2.json()
        logger.info(f"Answer: {data2['answer'][:150]}...")
        logger.info(f"Citations count: {len(data2['citations'])}")
        assert any("Enterprise_RAG_University_Plan" in c["title"] for c in data2["citations"])
        logger.info("✓ POST /api/v1/ask (Plan Query) PASSED")

        # 4. Test Explicit Abstention
        logger.info("\n--- 4. Testing Explicit Abstention (Unrelated Query) ---")
        req_body3 = {
            "question": "What is the capital city of ancient Atlantis in 5000 BC?",
            "department": "ComputerScience",
            "course": "CS401"
        }
        res3 = await client.post("/api/v1/ask", json=req_body3)
        assert res3.status_code == 200
        data3 = res3.json()
        logger.info(f"Abstention Answer: {data3['answer']}")
        logger.info(f"Citations count: {len(data3['citations'])}")
        assert "not have sufficient verified" in data3["answer"].lower()
        assert len(data3["citations"]) == 0
        logger.info("✓ Explicit Abstention PASSED")

        # 5. Test OpenAI-Compatible /v1/chat/completions
        logger.info("\n--- 5. Testing POST /v1/chat/completions ---")
        chat_body = {
            "model": "university-rag",
            "messages": [
                {"role": "user", "content": "When are the instructor office hours?"}
            ]
        }
        res4 = await client.post("/v1/chat/completions", json=chat_body)
        assert res4.status_code == 200
        data4 = res4.json()
        logger.info(f"OpenAI completion id: {data4['id']}")
        logger.info(f"Model: {data4['model']}")
        logger.info(f"Message: {data4['choices'][0]['message']['content'][:120]}...")
        assert data4["object"] == "chat.completion"
        logger.info("✓ POST /v1/chat/completions PASSED")

        # 6. Test POST /api/v1/folders/register
        logger.info("\n--- 6. Testing POST /api/v1/folders/register ---")
        from api.core.auth import create_access_token
        admin_token = create_access_token({"sub": "admin_test", "role": "admin"})
        folder_body = {
            "path": "data/sample_courses",
            "department": "ComputerScience",
            "course": "CS401"
        }
        res5 = await client.post(
            "/api/v1/folders/register",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=folder_body
        )
        assert res5.status_code == 201
        data5 = res5.json()
        logger.info(f"Registered folder id: {data5['id']}")
        logger.info("✓ POST /api/v1/folders/register PASSED")

        # 7. Test Auth Token Endpoint
        logger.info("\n--- 7. Testing POST /auth/token ---")
        res6 = await client.post("/auth/token", headers={"X-API-Key": settings.API_KEY})
        assert res6.status_code == 200
        data6 = res6.json()
        logger.info(f"Issued token: {data6['access_token'][:20]}...")
        logger.info("✓ POST /auth/token PASSED")

    logger.info("\n=======================================================")
    logger.info("ALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")
    logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_api_tests())
