import os
import io
import time
import json
import asyncio
import hashlib
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont
import httpx

from api.core.auth import create_access_token
from api.scraper.banner_ocr import BannerOCRPipeline
from db.session import async_session_factory, init_db
from db.models import Document, Chunk, WebScrapeManifest, ContextTier
from sqlalchemy import select, func, delete

BASE_URL = "http://127.0.0.1:8000"

async def run_live_verification():
    results = {}

    print("=" * 70)
    print("STEP 1: Database Pre-Inspection & Data Setup")
    print("=" * 70)

    # 1. Inspect existing documents and sample courses
    course_files = []
    sample_courses_dir = os.path.abspath("data/sample_courses")
    for root, dirs, files in os.walk(sample_courses_dir):
        for f in files:
            full_path = os.path.join(root, f)
            course_files.append({
                "path": full_path,
                "size": os.path.getsize(full_path),
                "mtime": os.path.getmtime(full_path)
            })

    print(f"Discovered {len(course_files)} course asset files in {sample_courses_dir}:")
    for cf in course_files:
        print(f"  - {os.path.relpath(cf['path'])} ({cf['size']} bytes)")

    # Inspect Document table
    async with async_session_factory() as session:
        dept_counts_stmt = select(Document.department, func.count(Document.id)).group_by(Document.department)
        dept_counts_before = dict((await session.execute(dept_counts_stmt)).all())
        cs_docs_stmt = select(Document.id, Document.title, Document.course).where(Document.department == "ComputerScience")
        cs_docs_before = [(str(row[0]), row[1], row[2]) for row in (await session.execute(cs_docs_stmt)).all()]

    print(f"Document counts before test by department: {dept_counts_before}")
    print(f"ComputerScience documents count: {len(cs_docs_before)}")

    # 2. Insert test Scraped Document and Manifest entry for purge testing
    test_url = "https://mdu.ac.in/admissions/btech_merit_list_2026.aspx"
    test_url_hash = hashlib.sha256(test_url.encode("utf-8")).hexdigest()
    
    async with async_session_factory() as session:
        portal_doc = Document(
            title="MDU B.Tech Merit List 2026",
            department="University Portal",
            course="General",
            semester="All",
            source_path=test_url,
            doc_type="web_page",
            ocr_confidence=0.98
        )
        session.add(portal_doc)
        await session.flush()

        portal_chunk = Chunk(
            document_id=portal_doc.id,
            page_number=1,
            section="Merit List",
            text="Provisional Merit List for B.Tech CSE Admissions 2026-27 announced.",
            content_hash=hashlib.sha256(b"merit_list_cse_2026").hexdigest()
        )
        session.add(portal_chunk)

        manifest = WebScrapeManifest(
            url=test_url,
            url_hash=test_url_hash,
            document_id=portal_doc.id,
            status="ingested",
            title="MDU B.Tech Merit List 2026"
        )
        session.add(manifest)
        await session.commit()
        test_portal_doc_id = str(portal_doc.id)

    print(f"Inserted test 'University Portal' doc: ID={test_portal_doc_id}")

    # Also stage a temporary file in data/downloads/mdu_scraped/ for cleanup test
    mdu_download_dir = os.path.abspath("data/downloads/mdu_scraped")
    os.makedirs(mdu_download_dir, exist_ok=True)
    temp_test_file = os.path.join(mdu_download_dir, "test_scraped_notice_temp.tmp")
    with open(temp_test_file, "wb") as f:
        f.write(b"SAMPLE TEMP DOWNLOAD CONTENT FOR RECLAMATION TEST " * 1000)
    print(f"Staged test temp file in scraper downloads: {temp_test_file} ({os.path.getsize(temp_test_file)} bytes)")

    # Generate JWT tokens
    admin_token = create_access_token({"sub": "admin_qa_verifier", "role": "admin"})
    student_token = create_access_token({"sub": "student_qa_verifier", "role": "student"})

    print("\n" + "=" * 70)
    print("STEP 2: Live HTTP API Verification & RBAC Testing")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # A. RBAC on DELETE /api/v1/admin/scraper/purge-rag-data
        # 1. Unauthenticated
        t0 = time.perf_counter()
        resp_unauth = await client.delete("/api/v1/admin/scraper/purge-rag-data")
        lat_unauth = (time.perf_counter() - t0) * 1000
        print(f"[RBAC 1] Unauthenticated DELETE: Status {resp_unauth.status_code} ({lat_unauth:.2f} ms)")
        assert resp_unauth.status_code == 401, f"Expected 401, got {resp_unauth.status_code}"

        # 2. Student Role JWT
        t0 = time.perf_counter()
        resp_student = await client.delete(
            "/api/v1/admin/scraper/purge-rag-data",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        lat_student = (time.perf_counter() - t0) * 1000
        print(f"[RBAC 2] Student JWT DELETE: Status {resp_student.status_code} ({lat_student:.2f} ms)")
        assert resp_student.status_code == 403, f"Expected 403, got {resp_student.status_code}"

        # 3. Admin Role JWT
        t0 = time.perf_counter()
        resp_admin = await client.delete(
            "/api/v1/admin/scraper/purge-rag-data",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lat_admin = (time.perf_counter() - t0) * 1000
        print(f"[RBAC 3] Admin JWT DELETE: Status {resp_admin.status_code} ({lat_admin:.2f} ms)")
        assert resp_admin.status_code == 200, f"Expected 200, got {resp_admin.status_code}"
        admin_purge_json = resp_admin.json()
        print(f"Admin purge response metrics: {json.dumps(admin_purge_json.get('metrics', {}), indent=2)}")

        results["purge_rbac"] = {
            "unauthenticated": {"status": resp_unauth.status_code, "latency_ms": round(lat_unauth, 2)},
            "student": {"status": resp_student.status_code, "latency_ms": round(lat_student, 2)},
            "admin": {"status": resp_admin.status_code, "latency_ms": round(lat_admin, 2), "metrics": admin_purge_json.get("metrics")}
        }

        # B. GET /api/v1/admin/scraper/status
        t0 = time.perf_counter()
        resp_status = await client.get(
            "/api/v1/admin/scraper/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lat_status = (time.perf_counter() - t0) * 1000
        print(f"\n[Status] GET /status: Status {resp_status.status_code} ({lat_status:.2f} ms)")
        assert resp_status.status_code == 200, f"Expected 200, got {resp_status.status_code}"
        status_json = resp_status.json()
        print(f"Crawler Status: is_running={status_json.get('is_running')}, stats={status_json.get('stats')}")
        results["status_endpoint"] = {
            "status": resp_status.status_code,
            "latency_ms": round(lat_status, 2),
            "payload": status_json
        }

        # C. POST /api/v1/admin/scraper/cleanup
        # Stage another temp file to verify reclamation
        temp_cleanup_file = os.path.join(mdu_download_dir, "test_cleanup_verify.tmp")
        with open(temp_cleanup_file, "wb") as f:
            f.write(b"CLEANUP RECLAMATION TEST DATA" * 2000)

        t0 = time.perf_counter()
        resp_cleanup = await client.post(
            "/api/v1/admin/scraper/cleanup",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        lat_cleanup = (time.perf_counter() - t0) * 1000
        print(f"\n[Cleanup] POST /cleanup: Status {resp_cleanup.status_code} ({lat_cleanup:.2f} ms)")
        assert resp_cleanup.status_code == 200, f"Expected 200, got {resp_cleanup.status_code}"
        cleanup_json = resp_cleanup.json()
        print(f"Cleanup Response: {json.dumps(cleanup_json.get('metrics', {}), indent=2)}")
        assert not os.path.exists(temp_cleanup_file), "Temp cleanup file was not removed!"
        results["cleanup_endpoint"] = {
            "status": resp_cleanup.status_code,
            "latency_ms": round(lat_cleanup, 2),
            "metrics": cleanup_json.get("metrics")
        }

    print("\n" + "=" * 70)
    print("STEP 3: Data Isolation Verification Post-Purge")
    print("=" * 70)

    # Verify SQLite Document table
    async with async_session_factory() as session:
        dept_counts_after = dict((await session.execute(dept_counts_stmt)).all())
        cs_docs_after = [(str(row[0]), row[1], row[2]) for row in (await session.execute(cs_docs_stmt)).all()]
        
        # Verify purged portal doc is gone
        portal_lookup = (await session.execute(select(Document).where(Document.id == test_portal_doc_id))).scalar_one_or_none()
        assert portal_lookup is None, f"Error: Portal document {test_portal_doc_id} was NOT purged!"

        # Verify manifest count
        manifest_count = (await session.execute(select(func.count(WebScrapeManifest.id)))).scalar() or 0
        assert manifest_count == 0, f"Error: Scrape manifest entries remain: {manifest_count}"

    print(f"Document counts after purge: {dept_counts_after}")
    print(f"ComputerScience docs count after purge: {len(cs_docs_after)}")
    assert len(cs_docs_after) == len(cs_docs_before), f"Course docs changed: {len(cs_docs_before)} -> {len(cs_docs_after)}"
    assert set(cs_docs_after) == set(cs_docs_before), "Course doc IDs or metadata changed!"
    print("PASS: Academic course documents in ComputerScience remain 100% intact!")

    # Verify sample_courses directory files on disk
    for cf in course_files:
        assert os.path.exists(cf["path"]), f"Missing course file: {cf['path']}"
        cur_size = os.path.getsize(cf["path"])
        assert cur_size == cf["size"], f"File size changed for {cf['path']}: {cur_size} vs {cf['size']}"
    print("PASS: All sample course files on disk remain completely untouched!")

    results["data_isolation"] = {
        "portal_purged": True,
        "manifest_purged": True,
        "manifest_count_after": manifest_count,
        "cs_docs_count_before": len(cs_docs_before),
        "cs_docs_count_after": len(cs_docs_after),
        "sample_courses_files_verified": len(course_files),
        "sample_courses_intact": True
    }

    print("\n" + "=" * 70)
    print("STEP 4: Banner OCR Pipeline Verification")
    print("=" * 70)

    pipeline = BannerOCRPipeline(max_images_per_page=5, max_image_bytes=8 * 1024 * 1024)

    # 4A. Test HTML Snippets
    # Snippet 1: owl-carousel
    html_carousel = """
    <div class="owl-carousel hero-slider">
        <img src="/Images/Banners/banner_convocation_2026.jpg" alt="18th Convocation">
    </div>
    """
    urls_carousel = pipeline.harvest_banner_image_urls(html_carousel, "https://mdu.ac.in", ["mdu.ac.in"])
    print(f"[Snippet 1 - owl-carousel] Harvested: {urls_carousel}")
    assert "https://mdu.ac.in/Images/Banners/banner_convocation_2026.jpg" in urls_carousel

    # Snippet 2: hero banner
    html_hero = """
    <div class="hero-banner-wrap">
        <img src="/assets/slider/admissions_open_btech.png" alt="Admissions Open">
    </div>
    """
    urls_hero = pipeline.harvest_banner_image_urls(html_hero, "https://mdu.ac.in", ["mdu.ac.in"])
    print(f"[Snippet 2 - hero banner] Harvested: {urls_hero}")
    assert "https://mdu.ac.in/assets/slider/admissions_open_btech.png" in urls_hero

    # Snippet 3: marquee
    html_marquee = """
    <marquee direction="left">
        <img src="/circulars/exam_postponed_circular.jpg" alt="Urgent Notice">
    </marquee>
    """
    urls_marquee = pipeline.harvest_banner_image_urls(html_marquee, "https://mdu.ac.in", ["mdu.ac.in"])
    print(f"[Snippet 3 - marquee] Harvested: {urls_marquee}")
    assert "https://mdu.ac.in/circulars/exam_postponed_circular.jpg" in urls_marquee

    # Snippet 4: standard img with keyword
    html_std_img = """
    <div class="col-md-12">
        <img src="/uploads/tender_notice_2026.jpg" alt="Tender Notice">
        <img src="/icons/social_twitter.png" alt="Twitter">
    </div>
    """
    urls_std_img = pipeline.harvest_banner_image_urls(html_std_img, "https://mdu.ac.in", ["mdu.ac.in"])
    print(f"[Snippet 4 - standard img with keyword] Harvested: {urls_std_img}")
    assert "https://mdu.ac.in/uploads/tender_notice_2026.jpg" in urls_std_img
    assert "https://mdu.ac.in/icons/social_twitter.png" not in urls_std_img

    results["banner_snippets"] = {
        "owl_carousel": urls_carousel,
        "hero_banner": urls_hero,
        "marquee": urls_marquee,
        "standard_img": urls_std_img
    }

    # 4B. Test Image Download Size Limits
    print("\nTesting image download size limits...")
    # Create synthetic test image
    img_valid = Image.new("RGB", (640, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img_valid)
    draw.rectangle([(10, 10), (630, 190)], outline=(200, 30, 30), width=5)
    draw.text((30, 50), "MDU ADMISSION COUNSELING 2026-27", fill=(0, 0, 0))
    draw.text((30, 100), "MERIT LIST REPORTING DATE: 15 JULY", fill=(0, 0, 0))
    valid_buf = io.BytesIO()
    img_valid.save(valid_buf, format="PNG")
    valid_bytes = valid_buf.getvalue()
    print(f"Generated synthetic banner: {len(valid_bytes)} bytes")

    # Generate oversized bytes (>8MB)
    oversized_bytes = valid_bytes + (b"\x00" * (9 * 1024 * 1024))
    print(f"Generated oversized dummy image payload: {len(oversized_bytes)} bytes (~{len(oversized_bytes)/(1024*1024):.2f} MB)")

    # Undersized payload (<500 bytes)
    undersized_bytes = b"tiny"

    # Mock HTTP transport
    def mock_handler(request: httpx.Request):
        url = str(request.url)
        if "oversized" in url:
            return httpx.Response(200, content=oversized_bytes, headers={"Content-Type": "image/png"})
        elif "undersized" in url:
            return httpx.Response(200, content=undersized_bytes, headers={"Content-Type": "image/png"})
        elif "valid" in url:
            return httpx.Response(200, content=valid_bytes, headers={"Content-Type": "image/png"})
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

    # Test oversized rejection
    res_oversized = await pipeline._process_single_image(mock_client, "https://mdu.ac.in/Images/Banners/oversized_image.png")
    assert res_oversized is None, "Oversized image was NOT rejected!"
    print("PASS: Oversized image (>8MB) rejected cleanly by size guard.")

    # Test undersized rejection
    res_undersized = await pipeline._process_single_image(mock_client, "https://mdu.ac.in/Images/Banners/undersized_image.png")
    assert res_undersized is None, "Undersized image was NOT rejected!"
    print("PASS: Undersized image (<500 bytes) rejected cleanly by size guard.")

    # 4C. Test SHA-256 Caching
    print("\nTesting SHA-256 OCR caching...")
    valid_url = "https://mdu.ac.in/Images/Banners/valid_admission_notice.png"
    
    # First call: cache miss, runs RapidOCR
    t0 = time.perf_counter()
    announcement_call1 = await pipeline._process_single_image(mock_client, valid_url)
    lat_call1 = (time.perf_counter() - t0) * 1000
    assert announcement_call1 is not None, "Failed to process valid banner image!"
    assert announcement_call1["cached"] is False, "Call 1 should have cached == False"
    print(f"Call 1 (Cache Miss / First OCR Run): {lat_call1:.2f} ms")
    print(f"  Extracted text: {announcement_call1['ocr_text']!r}")
    print(f"  Confidence: {announcement_call1['confidence']:.2f}")

    # Second call with exact same image: cache hit
    t0 = time.perf_counter()
    announcement_call2 = await pipeline._process_single_image(mock_client, valid_url)
    lat_call2 = (time.perf_counter() - t0) * 1000
    assert announcement_call2 is not None
    assert announcement_call2["cached"] is True, "Call 2 should have cached == True"
    assert announcement_call2["ocr_text"] == announcement_call1["ocr_text"]
    print(f"Call 2 (Cache Hit via SHA-256): {lat_call2:.2f} ms")
    print(f"  Cached flag: {announcement_call2['cached']}")
    print(f"  Speedup factor: {lat_call1 / max(lat_call2, 0.001):.1f}x faster")
    assert lat_call2 < lat_call1, "Cache hit must be significantly faster than initial OCR!"

    results["ocr_caching"] = {
        "call_1_latency_ms": round(lat_call1, 2),
        "call_1_cached": announcement_call1["cached"],
        "call_2_latency_ms": round(lat_call2, 2),
        "call_2_cached": announcement_call2["cached"],
        "speedup_factor": round(lat_call1 / max(lat_call2, 0.001), 1),
        "extracted_text_preview": announcement_call1["ocr_text"][:60]
    }

    await mock_client.aclose()

    # Save summary results to JSON
    with open("tests/verification_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_live_verification())
