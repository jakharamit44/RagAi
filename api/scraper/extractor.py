import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Set
from bs4 import BeautifulSoup
import trafilatura
from .url_normalizer import UrlNormalizer

from .banner_ocr import banner_ocr_pipeline
import httpx

logger = logging.getLogger(__name__)

class PageExtractor:
    """
    Extracts high-fidelity academic content, Markdown tables, banner image announcements via OCR,
    and document links from HTML web pages.
    Combines Trafilatura (boilerplate stripping) with BeautifulSoup (fallback, link harvesting, and banner OCR).
    """

    @staticmethod
    async def extract_html_content(
        html_bytes: bytes,
        page_url: str,
        content_type: str = "text/html",
        allowed_domains: Optional[List[str]] = None,
        ocr_banners: bool = True,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """
        Extracts clean text/markdown, metadata, and banner OCR announcements from raw HTML.
        Handles BOM, UTF-8, fallback encodings, and visual announcements.
        """
        # 1. Decode HTML handling possible UTF-8 BOM
        try:
            html_text = html_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                html_text = html_bytes.decode("latin-1")
            except Exception:
                html_text = html_bytes.decode("utf-8", errors="replace")

        # 2. Extract title
        title = ""
        soup = None
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
        except Exception as e:
            logger.debug(f"Soup title parse note: {e}")

        # 3. Trafilatura boilerplate-free extraction
        clean_markdown = None
        try:
            clean_markdown = trafilatura.extract(
                html_text,
                url=page_url,
                include_tables=True,
                include_links=True,
                include_images=False,
                output_format="markdown",
                favor_recall=True,
                deduplicate=True
            )
        except Exception as e:
            logger.warning(f"Trafilatura extraction warning for {page_url}: {e}")

        # 4. Fallback to BeautifulSoup if Trafilatura yields sparse text
        if not clean_markdown or len(clean_markdown.strip()) < 80:
            if soup is None:
                soup = BeautifulSoup(html_text, "html.parser")
            
            # Remove script, style, nav, footer
            for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                element.decompose()

            # Find main content container if available
            main_elem = soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"content|main|body", re.I)) or soup.body
            if main_elem:
                clean_markdown = main_elem.get_text(separator="\n", strip=True)
            else:
                clean_markdown = soup.get_text(separator="\n", strip=True)

        if not title:
            # Fallback title from first H1 or URL
            if soup:
                h1 = soup.find("h1")
                if h1 and h1.text:
                    title = h1.text.strip()
            if not title:
                title = page_url.split("/")[-1].split("?")[0] or "University Web Page"

        # 5. Banner and Slider Image Announcement OCR
        banner_announcements = []
        if ocr_banners:
            try:
                domains = allowed_domains or [UrlNormalizer.extract_root_domain(page_url) or "mdu.ac.in"]
                banner_announcements = await banner_ocr_pipeline.extract_banner_announcements(
                    html_text=html_text,
                    page_url=page_url,
                    allowed_domains=domains,
                    client=client
                )
                if banner_announcements:
                    banner_md = banner_ocr_pipeline.format_announcements_markdown(banner_announcements)
                    clean_markdown = (clean_markdown or "") + banner_md
            except Exception as ocr_err:
                logger.warning(f"Banner OCR processing note for {page_url}: {ocr_err}")

        return {
            "title": title,
            "text": clean_markdown or "",
            "char_count": len(clean_markdown or ""),
            "page_url": page_url,
            "banner_announcements": banner_announcements
        }

    @staticmethod
    def harvest_links(
        html_bytes: bytes,
        page_url: str,
        allowed_domains: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Discovers all valid internal web page links (including subdomains) and downloadable academic documents.
        Returns:
            (valid_page_links, downloadable_doc_links)
        """
        page_links: Set[str] = set()
        doc_links: Set[str] = set()

        try:
            try:
                html_text = html_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                html_text = html_bytes.decode("latin-1", errors="replace")

            soup = BeautifulSoup(html_text, "html.parser")

            # 1. Harvest from <a> tags
            for a_tag in soup.find_all("a", href=True):
                raw_href = a_tag["href"]
                normalized = UrlNormalizer.normalize(raw_href, base_url=page_url)
                if not normalized:
                    continue

                link_text = (a_tag.get_text() or "").strip()
                has_download_attr = a_tag.has_attr("download")

                # Detect if anchor text or attribute strongly signals a document
                is_doc = UrlNormalizer.is_document_url(normalized)
                if not is_doc and (has_download_attr or re.search(r"\b(?:pdf|download|syllabus|datesheet|circular|notice)\b", link_text, re.I)):
                    # Check if target URL has document keywords
                    if re.search(r"\.(?:pdf|docx?|xlsx?|pptx?)(?:[?#]|$)", raw_href, re.I):
                        is_doc = True

                if is_doc:
                    if UrlNormalizer.is_allowed_domain(normalized, allowed_domains):
                        doc_links.add(normalized)
                else:
                    if UrlNormalizer.is_skippable_url(normalized):
                        continue
                    if UrlNormalizer.is_allowed_domain(normalized, allowed_domains):
                        page_links.add(normalized)

            # 2. Harvest from onclick attributes (e.g. window.open('...pdf') or location.href='...pdf')
            for tag in soup.find_all(attrs={"onclick": True}):
                onclick_val = tag["onclick"]
                matches = re.findall(r"(?:window\.open|location\.href)\s*=\s*['\"]([^'\"]+)['\"]", onclick_val)
                matches += re.findall(r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]", onclick_val)
                for raw_link in matches:
                    norm = UrlNormalizer.normalize(raw_link, base_url=page_url)
                    if norm and UrlNormalizer.is_document_url(norm) and UrlNormalizer.is_allowed_domain(norm, allowed_domains):
                        doc_links.add(norm)

            # 3. Inspect iframe src or embed src for PDFs
            for frame in soup.find_all(["iframe", "embed", "object"], src=True):
                norm = UrlNormalizer.normalize(frame["src"], base_url=page_url)
                if norm and UrlNormalizer.is_document_url(norm) and UrlNormalizer.is_allowed_domain(norm, allowed_domains):
                    doc_links.add(norm)

            # Also check <object data="...">
            for obj in soup.find_all("object", data=True):
                norm = UrlNormalizer.normalize(obj["data"], base_url=page_url)
                if norm and UrlNormalizer.is_document_url(norm) and UrlNormalizer.is_allowed_domain(norm, allowed_domains):
                    doc_links.add(norm)

        except Exception as e:
            logger.error(f"Error harvesting links from {page_url}: {e}")

        return sorted(list(page_links)), sorted(list(doc_links))
