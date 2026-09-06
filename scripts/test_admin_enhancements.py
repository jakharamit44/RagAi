import asyncio
import os
import sys

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath("."))

from httpx import AsyncClient, ASGITransport
from api.main import app
from api.core.config import settings

async def run_tests():
    print("=== Testing Enterprise Admin Portal Enhancements ===")
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": "dev-secret-key-rag-university"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health & Storage Telemetry
        print("\n--- 1. Testing Storage Telemetry in /health & /api/v1/admin/rag/status ---")
        res = await client.get("/health")
        assert res.status_code == 200, f"/health returned {res.status_code}"
        data = res.json()
        assert "storage" in data, "storage key missing in /health response"
        st = data["storage"]
        print(f"  Storage Telemetry from /health:")
        print(f"    - SQLite DB Size: {st['db_size_mb']} MB")
        print(f"    - Qdrant Vector Store Size: {st['vector_store_size_mb']} MB")
        print(f"    - Total RAG Storage: {st['total_rag_storage_mb']} MB")
        print(f"    - Host Drive ({st['host_drive']}): {st['host_disk_free_gb']} GB Free / {st['host_disk_total_gb']} GB Total ({st['host_disk_free_pct']}%)")
        assert st["total_rag_storage_mb"] >= 0
        assert st["host_disk_free_gb"] > 0

        res_full = await client.get("/api/v1/admin/rag/status", headers=headers)
        assert res_full.status_code == 200
        full_st = res_full.json()["storage"]
        assert full_st["db_size_mb"] == st["db_size_mb"]
        print("  [PASS] Storage Telemetry verified across /health and /admin/rag/status")

        # 2. Watched Folder Registration & Persistence
        print("\n--- 2. Testing Watched Folders Persistence & Listing ---")
        # Register a test course folder
        reg_res = await client.post(
            "/api/v1/folders/scan",
            json={"path": "data/sample_courses/CS401", "department": "ComputerScience", "course": "CS401"},
            headers=headers
        )
        assert reg_res.status_code == 200, f"Register folder failed: {reg_res.text}"
        folder_id = reg_res.json().get("folder_id")
        print(f"  Folder registered. Response folder_id: {folder_id}")

        # List folders
        list_res = await client.get("/api/v1/folders", headers=headers)
        assert list_res.status_code == 200
        folders = list_res.json()["folders"]
        assert len(folders) >= 1, "Expected at least 1 registered watched folder"
        target_folder = next((f for f in folders if "CS401" in f["path"]), None)
        assert target_folder is not None, "CS401 watched folder not found in list"
        print(f"  Found persisted watched folder: id={target_folder['id']}, path={target_folder['path']}, files_indexed={target_folder['files_indexed']}")
        print("  [PASS] Watched Folders persistence verified")

        # 3. Incremental Refetch
        print("\n--- 3. Testing Incremental Refetch ---")
        scan_res = await client.post(f"/api/v1/folders/{target_folder['id']}/scan", headers=headers)
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        print(f"  Incremental Refetch Output: total={scan_data['total_files']}, ingested={scan_data['files_ingested']}, skipped_dup={scan_data['files_skipped_duplicate']}, unchanged={scan_data['files_unchanged']}")
        assert scan_data["action"] == "refetch_incremental"
        print("  [PASS] Incremental Refetch verified")

        # 4. Force Refetch Safety (Requires confirm: true)
        print("\n--- 4. Testing Force Refetch Safety Guard ---")
        # Attempt without confirm -> must be rejected 400
        rej_res = await client.post(f"/api/v1/folders/{target_folder['id']}/force-refetch", json={"confirm": False}, headers=headers)
        assert rej_res.status_code == 400, f"Expected 400 rejection for confirm=False, got {rej_res.status_code}"
        print(f"  Safeguard triggered: Rejected unconfirmed force-refetch with 400: {rej_res.json()['detail']}")

        # Now execute with confirm: true
        force_res = await client.post(f"/api/v1/folders/{target_folder['id']}/force-refetch", json={"confirm": True}, headers=headers)
        assert force_res.status_code == 200, f"Force refetch failed: {force_res.text}"
        force_data = force_res.json()
        print(f"  Force Refetch Executed: purged_docs={force_data['purged_documents_count']}, reindexed={force_data['files_reindexed']}")
        assert force_data["action"] == "force_refetch"
        print("  [PASS] Force Refetch safety and execution verified")

        # 5. Retry Failed Files
        print("\n--- 5. Testing Retry Failed Files Endpoint ---")
        retry_res = await client.post("/api/v1/admin/rag/retry-failed", headers=headers)
        assert retry_res.status_code == 200
        retry_data = retry_res.json()
        print(f"  Retry Failed Result: retried={retry_data['retried_count']}, succeeded={retry_data['succeeded']}, still_failed={retry_data['still_failed']}")
        assert retry_data["status"] == "ok"
        print("  [PASS] Retry Failed Files endpoint verified")

        # 6. Hugging Face Models Status & Token Management
        print("\n--- 6. Testing Hugging Face Models Governance & Status ---")
        models_res = await client.get("/api/v1/admin/models/status", headers=headers)
        assert models_res.status_code == 200
        m_data = models_res.json()
        print(f"  Embedding Model: {m_data['embedding_model']['name']} (Cached: {m_data['embedding_model']['cached']})")
        print(f"  Reranker Model: {m_data['reranker_model']['name']} (Cached: {m_data['reranker_model']['cached']})")
        print(f"  Hub Cache Size: {m_data['cache_size_mb']} MB")
        print(f"  HF Token Configured: {m_data['hf_token_configured']} ({m_data['hf_token_masked']})")
        assert "embedding_model" in m_data
        assert "reranker_model" in m_data
        print("  [PASS] Model status & token inspection verified")

        # Set token
        token_res = await client.post("/api/v1/admin/settings/hf-token", json={"token": "hf_test_token_for_verification_only_12345"}, headers=headers)
        assert token_res.status_code == 200
        assert token_res.json()["status"] == "ok"

        # Verify token was updated
        models_res2 = await client.get("/api/v1/admin/models/status", headers=headers)
        m_data2 = models_res2.json()
        assert m_data2["hf_token_configured"] is True
        print(f"  Token successfully set and active: {m_data2['hf_token_masked']}")
        print("  [PASS] HF token save and reload verified")

    print("\n========================================================")
    print("   ALL ADMIN ENHANCEMENTS VERIFIED SUCCESSFULLY (100%)")
    print("========================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
