import os
import sys
import asyncio
import logging
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath("."))
from api.main import app
from api.core.auth import create_access_token
from db.session import async_session_factory
from db.models import Document, Chunk, ManifestEntry
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_admin_governance")

async def run_governance_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        admin_jwt = create_access_token({"sub": "admin_super", "role": "admin"})
        admin_headers = {"Authorization": f"Bearer {admin_jwt}"}

        # -------------------------------------------------------------
        # 1. Test GET /api/v1/folders/tree (Universal Directory & Drive Selector)
        # -------------------------------------------------------------
        logger.info("\n--- 1. Testing GET /api/v1/folders/tree (Universal Access) ---")
        
        # Test 1a: Inspect project data directory
        res1 = await client.get("/api/v1/folders/tree?path=data/sample_courses", headers=admin_headers)
        assert res1.status_code == 200, f"Failed tree: {res1.text}"
        data1 = res1.json()
        logger.info(f"Tree for '{data1['current_path']}': {len(data1['directories'])} dirs, {len(data1['files'])} files")
        dir_names = [d["name"] for d in data1["directories"]]
        assert "CS401" in dir_names or "CS402" in dir_names, f"Expected CS courses in tree: {dir_names}"
        assert len(data1["available_drives"]) > 0, "Expected system drives to be listed"
        logger.info(f"[PASS] Directory tree explorer verified. System drives: {data1['available_drives']}")

        # Test 1b: System DRIVES root view
        res_drives = await client.get("/api/v1/folders/tree?path=DRIVES", headers=admin_headers)
        assert res_drives.status_code == 200, f"Failed drives view: {res_drives.text}"
        data_drives = res_drives.json()
        assert data_drives["current_path"] == "Computer (System Drives)"
        assert len(data_drives["directories"]) > 0
        logger.info(f"[PASS] DRIVES root selector verified: {[d['name'] for d in data_drives['directories']]}")

        # Test 1c: Universal filesystem access (parent and arbitrary drives accessible)
        res_parent = await client.get("/api/v1/folders/tree?path=..", headers=admin_headers)
        assert res_parent.status_code == 200, "Universal access should allow browsing parent directories"
        logger.info(f"[PASS] Universal access confirmed for parent directory: {res_parent.json()['current_path']}")

        # Test 1d: Non-existent directory returns 404
        res_nonexistent = await client.get("/api/v1/folders/tree?path=Z:/NonExistentPath98765", headers=admin_headers)
        assert res_nonexistent.status_code == 404
        logger.info("[PASS] Non-existent path cleanly returns HTTP 404")

        # Test 1e: Non-admin access rejected with 403
        student_jwt = create_access_token({"sub": "student_test", "role": "student"})
        res_unauth = await client.get("/api/v1/folders/tree?path=data", headers={"Authorization": f"Bearer {student_jwt}"})
        assert res_unauth.status_code == 403
        logger.info("[PASS] Role check verified: non-admin users forbidden from browsing filesystem")

        # -------------------------------------------------------------
        # 2. Test Multi-Tenant API Key Management
        # -------------------------------------------------------------
        logger.info("\n--- 2. Testing API Key Management (Create, Auth, Disable, Delete) ---")
        create_payload = {
            "name": "Automated Test Bot",
            "role": "student",
            "department": "ComputerScience",
            "rate_limit": 100
        }
        res2 = await client.post("/api/v1/admin/api-keys", json=create_payload, headers=admin_headers)
        assert res2.status_code == 201, f"Failed create API key: {res2.text}"
        key_data = res2.json()
        api_key_id = key_data["id"]
        raw_secret_key = key_data["raw_api_key"]
        assert raw_secret_key.startswith("rag_live_")
        logger.info(f"Created API Key: id={api_key_id}, prefix={key_data['key_prefix']}")

        # Test authenticating with the new dynamic API Key on /api/v1/ask
        key_headers = {"X-API-Key": raw_secret_key}
        ask_payload = {
            "question": "What is an AVL tree?",
            "department": "ComputerScience",
            "course": "CS401"
        }
        res_ask = await client.post("/api/v1/ask", json=ask_payload, headers=key_headers)
        assert res_ask.status_code == 200, f"Auth with new API key failed: {res_ask.text}"
        logger.info(f"[PASS] Successfully authenticated with dynamic API Key '{raw_secret_key[:16]}...'")

        # Disable the API Key
        logger.info("--> Disabling API Key...")
        res_disable = await client.patch(
            f"/api/v1/admin/api-keys/{api_key_id}/status",
            json={"is_active": False},
            headers=admin_headers
        )
        assert res_disable.status_code == 200
        assert res_disable.json()["is_active"] is False

        # Attempt query with disabled key -> expect 403 Forbidden
        res_ask_blocked = await client.post("/api/v1/ask", json=ask_payload, headers=key_headers)
        assert res_ask_blocked.status_code == 403, f"Expected 403 for disabled key, got: {res_ask_blocked.status_code}"
        logger.info("[PASS] Disabled API Key properly rejected with HTTP 403 Forbidden")

        # Re-enable the API Key
        logger.info("--> Re-enabling API Key...")
        await client.patch(
            f"/api/v1/admin/api-keys/{api_key_id}/status",
            json={"is_active": True},
            headers=admin_headers
        )
        res_ask_re = await client.post("/api/v1/ask", json=ask_payload, headers=key_headers)
        assert res_ask_re.status_code == 200
        logger.info("[PASS] Re-enabled API Key successfully authorized")

        # Delete the API Key
        logger.info("--> Deleting API Key...")
        res_del = await client.delete(f"/api/v1/admin/api-keys/{api_key_id}", headers=admin_headers)
        assert res_del.status_code == 200

        # Query with deleted key -> expect 401 Unauthorized
        res_ask_deleted = await client.post("/api/v1/ask", json=ask_payload, headers=key_headers)
        assert res_ask_deleted.status_code == 401
        logger.info("[PASS] Deleted API Key revoked permanently (HTTP 401)")

        # -------------------------------------------------------------
        # 3. Test URL Governance (Allow / Disallow)
        # -------------------------------------------------------------
        logger.info("\n--- 3. Testing External URL Governance ---")
        rule_allow = {
            "url_pattern": "https://catalog.university.edu/*",
            "action": "allow",
            "description": "Official Course Catalog"
        }
        res_r1 = await client.post("/api/v1/admin/url-rules", json=rule_allow, headers=admin_headers)
        assert res_r1.status_code == 201
        rule1_id = res_r1.json()["id"]

        rule_disallow = {
            "url_pattern": "https://*.cheating-site.org/*",
            "action": "disallow",
            "description": "Disallowed academic violation domain"
        }
        res_r2 = await client.post("/api/v1/admin/url-rules", json=rule_disallow, headers=admin_headers)
        assert res_r2.status_code == 201
        rule2_id = res_r2.json()["id"]

        # Evaluate candidate URLs against rules
        test_eval_1 = await client.post(
            "/api/v1/admin/url-rules/test",
            json={"url": "https://catalog.university.edu/courses/cs401"},
            headers=admin_headers
        )
        assert test_eval_1.status_code == 200
        assert test_eval_1.json()["is_allowed"] is True
        logger.info(f"[PASS] Evaluated Allowed URL: {test_eval_1.json()['reason']}")

        test_eval_2 = await client.post(
            "/api/v1/admin/url-rules/test",
            json={"url": "https://sub.cheating-site.org/exam-leaks"},
            headers=admin_headers
        )
        assert test_eval_2.status_code == 200
        assert test_eval_2.json()["is_allowed"] is False
        logger.info(f"[PASS] Evaluated Disallowed URL: {test_eval_2.json()['reason']}")

        # Clean up test rules
        await client.delete(f"/api/v1/admin/url-rules/{rule1_id}", headers=admin_headers)
        await client.delete(f"/api/v1/admin/url-rules/{rule2_id}", headers=admin_headers)
        logger.info("[PASS] URL rules lifecycle verified cleanly")

        # -------------------------------------------------------------
        # 4. Test Complete RAG Cascade Deletion
        # -------------------------------------------------------------
        logger.info("\n--- 4. Testing Complete Document Cascade Purge ---")
        # Ingest a temporary dummy document directly
        async with async_session_factory() as session:
            test_doc = Document(
                source_path="data/uploads/temp_to_delete.txt",
                title="temp_to_delete.txt",
                department="ComputerScience",
                course="CS401",
                doc_type="born_digital"
            )
            session.add(test_doc)
            await session.commit()
            await session.refresh(test_doc)

            test_chunk = Chunk(
                document_id=test_doc.id,
                page_number=1,
                section="Test Section",
                text="This is temporary text that must be purged completely.",
                content_hash="hash_purge_test_12345"
            )
            test_manifest = ManifestEntry(
                path="data/uploads/temp_to_delete.txt",
                content_hash="hash_purge_test_12345",
                mtime=123456.0,
                status="done"
            )
            session.add(test_chunk)
            session.add(test_manifest)
            await session.commit()
            doc_id_to_purge = str(test_doc.id)

        # Execute Cascade Deletion API
        res_purge = await client.delete(f"/api/v1/documents/{doc_id_to_purge}", headers=admin_headers)
        assert res_purge.status_code == 200, f"Failed purge: {res_purge.text}"
        purge_data = res_purge.json()
        assert purge_data["status"] == "deleted"
        assert purge_data["deleted_chunks"] == 1
        logger.info(f"Purge Response: {purge_data['message']}")

        # Verify DB is completely clean of this document, chunk, and manifest
        async with async_session_factory() as session:
            doc_check = (await session.execute(select(Document).where(Document.id == doc_id_to_purge))).scalar_one_or_none()
            chunk_check = (await session.execute(select(Chunk).where(Chunk.document_id == doc_id_to_purge))).scalars().all()
            manifest_check = (await session.execute(select(ManifestEntry).where(ManifestEntry.path == "data/uploads/temp_to_delete.txt"))).scalar_one_or_none()

            assert doc_check is None, "Document still exists in DB!"
            assert len(chunk_check) == 0, "Chunks still exist in DB!"
            assert manifest_check is None, "Manifest still exists in DB!"

        logger.info("[PASS] Complete RAG cascade deletion verified: Document, Chunks, and Manifest purged!")

    logger.info("\n" + "=" * 65)
    logger.info("ALL ADMIN GOVERNANCE & PURGE SUITES PASSED SUCCESSFULLY!")
    logger.info("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_governance_tests())
