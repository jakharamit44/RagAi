import os
import io
import asyncio
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from api.scraper.url_normalizer import UrlNormalizer
from api.scraper.banner_ocr import BannerOCRPipeline, banner_ocr_pipeline
from api.scraper.extractor import PageExtractor
from ingestion.ocr_printed import printed_ocr


def test_root_domain_extraction():
    """Verify canonical academic root domain extraction for Indian and global domains."""
    assert UrlNormalizer.extract_root_domain("https://admission.mdu.ac.in/Apply.aspx") == "mdu.ac.in"
    assert UrlNormalizer.extract_root_domain("https://www.mdu.ac.in/Default.aspx") == "mdu.ac.in"
    assert UrlNormalizer.extract_root_domain("results.mdu.ac.in") == "mdu.ac.in"
    assert UrlNormalizer.extract_root_domain("https://iqac.mdu.ac.in") == "mdu.ac.in"
    assert UrlNormalizer.extract_root_domain("https://iitd.ac.in/news") == "iitd.ac.in"
    assert UrlNormalizer.extract_root_domain("https://cs.stanford.edu/courses") == "stanford.edu"
    assert UrlNormalizer.extract_root_domain("mdu.ac.in") == "mdu.ac.in"
    assert UrlNormalizer.extract_root_domain("*.mdu.ac.in") == "mdu.ac.in"


def test_wildcard_subdomain_matching():
    """Verify that allowing mdu.ac.in automatically matches all university subdomains."""
    allowed = ["mdu.ac.in"]
    assert UrlNormalizer.is_allowed_domain("https://mdu.ac.in/default.aspx", allowed) is True
    assert UrlNormalizer.is_allowed_domain("https://admission.mdu.ac.in/registration", allowed) is True
    assert UrlNormalizer.is_allowed_domain("https://results.mdu.ac.in/odd_semester", allowed) is True
    assert UrlNormalizer.is_allowed_domain("https://iqac.mdu.ac.in/reports", allowed) is True
    assert UrlNormalizer.is_allowed_domain("http://www.mdu.ac.in/", allowed) is True

    # External domains must be rejected
    assert UrlNormalizer.is_allowed_domain("https://google.com", allowed) is False
    assert UrlNormalizer.is_allowed_domain("https://fake-mdu.ac.in.attacker.com", allowed) is False
    assert UrlNormalizer.is_allowed_domain("https://mdu.attacker.com", allowed) is False


def test_document_url_detection():
    """Verify detection of direct and query-based academic documents (.pdf, .docx, .xlsx)."""
    assert UrlNormalizer.is_document_url("https://mdu.ac.in/UpFiles/Datesheet_May2026.pdf") is True
    assert UrlNormalizer.is_document_url("https://mdu.ac.in/syllabus/CS_2026.docx") is True
    assert UrlNormalizer.is_document_url("https://mdu.ac.in/merit_list.xlsx") is True
    assert UrlNormalizer.is_document_url("https://mdu.ac.in/Download.aspx?file=notice.pdf") is True
    assert UrlNormalizer.is_document_url("https://mdu.ac.in/get_file.php?type=pdf&id=101") is True
    assert UrlNormalizer.is_document_url("https://mdu.ac.in/default.aspx") is False
    assert UrlNormalizer.is_document_url("https://mdu.ac.in/about-us") is False


def test_subdomain_and_document_link_harvesting():
    """Verify PageExtractor harvests subdomain page links and document links across diverse HTML structures."""
    sample_html = b"""
    <!DOCTYPE html>
    <html>
    <head><title>MDU Rohtak Portal</title></head>
    <body>
        <div class="nav">
            <a href="https://admission.mdu.ac.in/apply">Online Admissions 2026</a>
            <a href="https://results.mdu.ac.in/results.aspx">Examination Results</a>
            <a href="/about-university.aspx">About University</a>
        </div>
        <div class="notices">
            <a href="/UpFiles/PdfFiles/2026/May/Datesheet_BTech.pdf">Download B.Tech Date Sheet</a>
            <a href="/download_notice.aspx?file=circular_postponed.pdf">Exam Postponement Notice</a>
            <button onclick="window.open('/Documents/Tender_2026.docx')">View Tender Details</button>
        </div>
        <div class="external">
            <a href="https://google.com">Google External</a>
        </div>
    </body>
    </html>
    """

    page_links, doc_links = PageExtractor.harvest_links(
        sample_html,
        page_url="https://mdu.ac.in/default.aspx",
        allowed_domains=["mdu.ac.in"]
    )

    # Subdomain links must be harvested
    assert "https://admission.mdu.ac.in/apply" in page_links
    assert "https://results.mdu.ac.in/results.aspx" in page_links
    assert "https://mdu.ac.in/about-university.aspx" in page_links
    assert "https://google.com" not in page_links

    # Document links must be harvested
    assert "https://mdu.ac.in/UpFiles/PdfFiles/2026/May/Datesheet_BTech.pdf" in doc_links
    assert "https://mdu.ac.in/download_notice.aspx?file=circular_postponed.pdf" in doc_links
    assert "https://mdu.ac.in/Documents/Tender_2026.docx" in doc_links


def test_banner_image_discovery():
    """Verify BannerOCRPipeline discovers carousel and banner announcement images."""
    pipeline = BannerOCRPipeline()
    html_text = """
    <html>
    <body>
        <div class="owl-carousel hero-slider">
            <img src="/Images/Banners/banner_admissions_open_2026.jpg" alt="Admissions Open 2026-27">
            <img src="/Images/Banners/convocation_date_sheet.png" alt="18th Convocation Ceremony">
        </div>
        <div class="content">
            <img src="/assets/icons/logo.png" alt="MDU Logo">
        </div>
    </body>
    </html>
    """
    discovered = pipeline.harvest_banner_image_urls(
        html_text=html_text,
        page_url="https://mdu.ac.in",
        allowed_domains=["mdu.ac.in"]
    )

    assert "https://mdu.ac.in/Images/Banners/banner_admissions_open_2026.jpg" in discovered
    assert "https://mdu.ac.in/Images/Banners/convocation_date_sheet.png" in discovered
    # Logo is decorative and not inside banner keywords
    assert "https://mdu.ac.in/assets/icons/logo.png" not in discovered


def test_banner_ocr_extraction_and_markdown():
    """Verify synthetic graphic OCR extraction and markdown synthesis."""
    # Generate synthetic announcement graphic using PIL
    img = Image.new("RGB", (600, 160), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (590, 150)], outline=(180, 20, 20), width=4)
    # Render legible block text
    draw.text((30, 40), "MDU ADMISSIONS 2026-27", fill=(0, 0, 0))
    draw.text((30, 80), "LAST DATE TO APPLY: 30 JUNE", fill=(0, 0, 0))

    ocr_res = printed_ocr.extract_text(img)
    extracted_text = (ocr_res.get("text") or "").upper()

    assert "ADMISSIONS" in extracted_text or "2026" in extracted_text or "JUNE" in extracted_text

    # Test Markdown formatting
    announcements = [{
        "image_url": "https://mdu.ac.in/Images/Banners/admission_2026.jpg",
        "image_name": "admission_2026.jpg",
        "ocr_text": "ADMISSIONS OPEN 2026-27\nLAST DATE 30 JUNE",
        "confidence": 0.95
    }]
    md = BannerOCRPipeline.format_announcements_markdown(announcements)
    assert "📢 Visual Banner Announcements" in md
    assert "admission_2026.jpg" in md
    assert "ADMISSIONS OPEN 2026-27" in md


async def test_scraped_rag_purge_preserves_courses():
    """
    Simulates Scraped RAG purge cascade and strictly verifies that:
    1. Documents tagged with department='University Portal' are purged.
    2. Academic course documents (e.g. Computer Science, CS101) remain 100% intact.
    """
    from db.session import init_db, async_session_factory
    from db.models import Document, Chunk, WebScrapeManifest, ContextTier
    from sqlalchemy import select

    await init_db()

    async with async_session_factory() as session:
        # Create course document (MUST NOT BE DELETED)
        course_doc = Document(
            title="Operating Systems Notes",
            department="ComputerScience",
            course="CS101",
            semester="4",
            source_path="data/sample_courses/CS101_OS.pdf",
            doc_type="born_digital",
            ocr_confidence=1.0
        )
        session.add(course_doc)
        await session.flush()

        course_chunk = Chunk(
            document_id=course_doc.id,
            page_number=1,
            section="Process Scheduling",
            text="Round robin scheduling algorithms in OS.",
            content_hash="hash_course_cs101_mock"
        )
        session.add(course_chunk)

        # Create scraped document (MUST BE PURGED)
        import uuid
        test_uid = uuid.uuid4().hex[:8]
        test_url = f"https://mdu.ac.in/notice_admission_{test_uid}.aspx"
        scraped_doc = Document(
            title=f"MDU Admission Notice {test_uid}",
            department="University Portal",
            course="General",
            semester="All",
            source_path=test_url,
            doc_type="web_page",
            ocr_confidence=1.0
        )
        session.add(scraped_doc)
        await session.flush()

        scraped_chunk = Chunk(
            document_id=scraped_doc.id,
            page_number=1,
            section="Online Admissions",
            text="Admissions are open for B.Tech and MCA courses.",
            content_hash=f"hash_scraped_admission_{test_uid}"
        )
        session.add(scraped_chunk)

        manifest_entry = WebScrapeManifest(
            url=test_url,
            url_hash=f"hash_url_{test_uid}",
            document_id=scraped_doc.id,
            status="ingested",
            title="Admission Notification 2026"
        )
        session.add(manifest_entry)
        await session.commit()

        course_doc_id = course_doc.id
        scraped_doc_id = scraped_doc.id

    # Now execute the purge logic
    import httpx
    from api.core.auth import create_access_token
    admin_token = create_access_token({"sub": "admin", "role": "admin"})

    # Check if server is running on 8000
    is_live = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://127.0.0.1:8000/health")
            if resp.status_code == 200:
                is_live = True
    except Exception:
        is_live = False

    if is_live:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                "http://127.0.0.1:8000/api/v1/admin/scraper/purge-rag-data",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp.status_code == 200, f"Purge returned status {resp.status_code}: {resp.text}"
            purge_res = resp.json()
    else:
        from api.routers.scraper import purge_scraped_rag_data
        purge_res = await purge_scraped_rag_data()

    assert purge_res["status"] == "success"
    assert purge_res["metrics"]["documents_purged"] >= 1

    # Verify database state after purge
    async with async_session_factory() as session:
        # Scraped document must be gone
        scraped_lookup = (await session.execute(select(Document).where(Document.id == scraped_doc_id))).scalar_one_or_none()
        assert scraped_lookup is None

        # Course document must be completely intact
        course_lookup = (await session.execute(select(Document).where(Document.id == course_doc_id))).scalar_one_or_none()
        assert course_lookup is not None
        assert course_lookup.department == "ComputerScience"
        assert course_lookup.course == "CS101"

        # Cleanup test course document
        from sqlalchemy import delete
        await session.execute(delete(Chunk).where(Chunk.document_id == course_doc_id))
        await session.execute(delete(Document).where(Document.id == course_doc_id))
        await session.commit()


if __name__ == "__main__":
    print("Running test_root_domain_extraction...")
    test_root_domain_extraction()
    print("PASS: test_root_domain_extraction")

    print("Running test_wildcard_subdomain_matching...")
    test_wildcard_subdomain_matching()
    print("PASS: test_wildcard_subdomain_matching")

    print("Running test_document_url_detection...")
    test_document_url_detection()
    print("PASS: test_document_url_detection")

    print("Running test_subdomain_and_document_link_harvesting...")
    test_subdomain_and_document_link_harvesting()
    print("PASS: test_subdomain_and_document_link_harvesting")

    print("Running test_banner_image_discovery...")
    test_banner_image_discovery()
    print("PASS: test_banner_image_discovery")

    print("Running test_banner_ocr_extraction_and_markdown...")
    test_banner_ocr_extraction_and_markdown()
    print("PASS: test_banner_ocr_extraction_and_markdown")

    print("Running test_scraped_rag_purge_preserves_courses...")
    asyncio.run(test_scraped_rag_purge_preserves_courses())
    print("PASS: test_scraped_rag_purge_preserves_courses")

    print("\nALL 7 SCRAPER ENHANCEMENT TESTS PASSED!")
