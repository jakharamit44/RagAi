import os
import sys
import asyncio
import logging
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_ui")

async def run_ui_tests():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test Admin Dashboard HTML
        logger.info("\n--- 1. Testing GET /admin ---")
        res1 = await client.get("/admin")
        assert res1.status_code == 200
        assert "Admin Console" in res1.text
        assert "Register & Scan Watched Folder" in res1.text
        logger.info(f"✓ GET /admin PASSED (Length: {len(res1.text)} chars)")

        # 2. Test Student Chat Widget HTML
        logger.info("\n--- 2. Testing GET /chat ---")
        res2 = await client.get("/chat")
        assert res2.status_code == 200
        assert "University Academic Assistant" in res2.text
        assert "Verified citations from syllabus" in res2.text
        logger.info(f"✓ GET /chat PASSED (Length: {len(res2.text)} chars)")

        # 3. Test Root Redirect
        logger.info("\n--- 3. Testing GET / ---")
        res3 = await client.get("/")
        assert res3.status_code in [302, 307]
        assert res3.headers.get("location") == "/chat"
        logger.info("✓ GET / Redirect PASSED")

        # 4. Test GET /api/v1/documents
        logger.info("\n--- 4. Testing GET /api/v1/documents ---")
        res4 = await client.get("/api/v1/documents")
        assert res4.status_code == 200
        docs = res4.json()
        logger.info(f"Retrieved {len(docs)} documents:")
        for d in docs:
            logger.info(f"  - {d['title']} (chunks: {d['chunk_count']}, type: {d['doc_type']})")
        assert len(docs) >= 3
        logger.info("✓ GET /api/v1/documents PASSED")

        # 5. Test GET /api/v1/manifest
        logger.info("\n--- 5. Testing GET /api/v1/manifest ---")
        res5 = await client.get("/api/v1/manifest")
        assert res5.status_code == 200
        manifest = res5.json()
        logger.info(f"Retrieved {len(manifest)} manifest entries:")
        for m in manifest:
            logger.info(f"  - {os.path.basename(m['path'])} | {m['content_hash'][:10]}... | status: {m['status']}")
        assert len(manifest) >= 3
        logger.info("✓ GET /api/v1/manifest PASSED")

        # 6. Test POST /api/v1/folders/scan
        logger.info("\n--- 6. Testing POST /api/v1/folders/scan ---")
        from api.core.auth import create_access_token
        admin_token = create_access_token({"sub": "admin_ui", "role": "admin"})
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        scan_payload = {
            "path": "data/sample_courses",
            "department": "ComputerScience",
            "course": "CS401"
        }
        res6 = await client.post("/api/v1/folders/scan", headers=headers_admin, json=scan_payload)
        assert res6.status_code == 200
        scan_data = res6.json()
        logger.info(f"Scan response: status='{scan_data['status']}', files_evaluated={scan_data['processed_files']}")
        assert scan_data["status"] == "ok"
        logger.info("✓ POST /api/v1/folders/scan PASSED")

    logger.info("\n=======================================================")
    logger.info("ALL PHASE 10 UI ENDPOINTS TESTED AND VERIFIED!")
    logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_ui_tests())
