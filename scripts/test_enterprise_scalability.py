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
from ingestion.extractors import DocumentExtractorRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_enterprise_scalability")

async def run_scalability_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        admin_jwt = create_access_token({"sub": "admin_scale", "role": "admin"})
        admin_headers = {"Authorization": f"Bearer {admin_jwt}"}

        logger.info("\n--- 1. Testing Server-Side Document Pagination (Scalable to 100k+ docs) ---")
        res_p1 = await client.get("/api/v1/documents?page=1&page_size=2")
        assert res_p1.status_code == 200, f"Failed paginated docs: {res_p1.text}"
        data_p1 = res_p1.json()
        assert "items" in data_p1
        assert "total" in data_p1
        assert "total_pages" in data_p1
        assert data_p1["page"] == 1
        assert data_p1["page_size"] == 2
        assert len(data_p1["items"]) <= 2
        logger.info(f"[PASS] Page 1: returned {len(data_p1['items'])} items of total {data_p1['total']}")

        if data_p1["total"] > 2:
            res_p2 = await client.get("/api/v1/documents?page=2&page_size=2")
            assert res_p2.status_code == 200
            data_p2 = res_p2.json()
            assert data_p2["page"] == 2
            p1_ids = [d["id"] for d in data_p1["items"]]
            p2_ids = [d["id"] for d in data_p2["items"]]
            assert not any(i in p1_ids for i in p2_ids), "Page 2 should have distinct items from Page 1"
            logger.info("[PASS] Page 2 returned non-overlapping slice correctly")

        res_search = await client.get("/api/v1/documents?page=1&page_size=10&search=syllabus")
        assert res_search.status_code == 200
        data_search = res_search.json()
        assert all("syllabus" in d["title"].lower() or "syllabus" in (d["department"] or "").lower() for d in data_search["items"])
        logger.info(f"[PASS] Search filter returned {len(data_search['items'])} matches for syllabus")

        res_legacy = await client.get("/api/v1/documents")
        assert res_legacy.status_code == 200
        data_legacy = res_legacy.json()
        assert isinstance(data_legacy, list)
        logger.info(f"[PASS] Backward compatibility verified: unpaginated call returns List of {len(data_legacy)} items")

        logger.info("\n--- 2. Testing Server-Side Manifest Pagination ---")
        res_m1 = await client.get("/api/v1/manifest?page=1&page_size=3")
        assert res_m1.status_code == 200
        data_m1 = res_m1.json()
        assert "items" in data_m1
        assert "total" in data_m1
        assert data_m1["page"] == 1
        logger.info(f"[PASS] Manifest pagination verified: {len(data_m1['items'])} items, total: {data_m1['total']}")

        res_m_done = await client.get("/api/v1/manifest?page=1&page_size=10&status=done")
        assert res_m_done.status_code == 200
        data_m_done = res_m_done.json()
        assert all(m["status"] == "done" for m in data_m_done["items"])
        logger.info(f"[PASS] Manifest status filter verified ({len(data_m_done['items'])} done items)")

        logger.info("\n--- 3. Testing Batch Document Deletion ---")
        async with async_session_factory() as session:
            doc_a = Document(source_path="data/temp/batch_a.txt", title="batch_a.txt", doc_type="born_digital")
            doc_b = Document(source_path="data/temp/batch_b.txt", title="batch_b.txt", doc_type="scanned")
            session.add_all([doc_a, doc_b])
            await session.commit()
            await session.refresh(doc_a)
            await session.refresh(doc_b)

            c_a = Chunk(document_id=doc_a.id, text="Chunk A", content_hash="hash_a_123")
            c_b = Chunk(document_id=doc_b.id, text="Chunk B", content_hash="hash_b_123")
            session.add_all([c_a, c_b])
            await session.commit()
            ids_to_batch_delete = [str(doc_a.id), str(doc_b.id)]

        res_batch = await client.post(
            "/api/v1/admin/documents/batch-delete",
            json={"document_ids": ids_to_batch_delete},
            headers=admin_headers
        )
        assert res_batch.status_code == 200
        data_batch = res_batch.json()
        assert data_batch["deleted_documents_count"] == 2
        assert data_batch["purged_chunks_count"] == 2
        logger.info(f"[PASS] Batch deletion verified: {data_batch['message']}")

        logger.info("\n--- 4. Testing Scanned & Image File Extractor Routing ---")
        test_img_path = "data/sample_courses/scan_test.png"
        with open(test_img_path, "w") as f:
            f.write("mock image data")

        try:
            pages, doc_type, conf = DocumentExtractorRouter.extract(test_img_path)
            assert doc_type == "scanned"
            assert len(pages) > 0
            assert conf is not None
            logger.info(f"[PASS] Scanned image extraction routed correctly: type={doc_type}, confidence={conf}")
        finally:
            if os.path.exists(test_img_path):
                os.remove(test_img_path)

    logger.info("\n========================================================")
    logger.info("ALL ENTERPRISE SCALABILITY & EXTRACTION TESTS PASSED!")
    logger.info("========================================================")

if __name__ == "__main__":
    asyncio.run(run_scalability_tests())
