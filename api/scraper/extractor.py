import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Set
from bs4 import BeautifulSoup
import trafilatura
from .url_normalizer import UrlNormalizer

logger = logging.getLogger(__name__)

class PageExtractor:
    """
    Extracts high-fidelity academic content, Markdown tables, and document links from HTML web pages.
    Combines Trafilatura (boilerplate stripping) with BeautifulSoup (fallback & link harvesting).
    """

    @staticmethod
    def extract_html_content(
        html_bytes: bytes,
        page_url: str,
        content_type: str = "text/html"
    ) -> Dict[str, Any]:
        """
        Extracts clean text/markdown and metadata from raw HTML.
        Handles BOM, UTF-8, and fallback encodings.
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

        return {
            "title": title,
            "text": clean_markdown or "",
            "char_count": len(clean_markdown or ""),
            "page_url": page_url
        }

    @staticmethod
    def harvest_links(
        html_bytes: bytes,
        page_url: str,
        allowed_domains: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Discovers all valid internal web page links and downloadable academic documents.
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

            for a_tag in soup.find_all("a", href=True):
                raw_href = a_tag["href"]
                normalized = UrlNormalizer.normalize(raw_href, base_url=page_url)
                if not normalized:
                    continue

                if UrlNormalizer.is_document_url(normalized):
                    # Only accept document if within allowed domain or direct link
                    if UrlNormalizer.is_allowed_domain(normalized, allowed_domains):
                        doc_links.add(normalized)
                else:
                    if UrlNormalizer.is_skippable_url(normalized):
                        continue
                    if UrlNormalizer.is_allowed_domain(normalized, allowed_domains):
                        page_links.add(normalized)

            # Also inspect iframe src or embed src for PDFs
            for frame in soup.find_all(["iframe", "embed"], src=True):
                norm = UrlNormalizer.normalize(frame["src"], base_url=page_url)
                if norm and UrlNormalizer.is_document_url(norm) and UrlNormalizer.is_allowed_domain(norm, allowed_domains):
                    doc_links.add(norm)

        except Exception as e:
            logger.error(f"Error harvesting links from {page_url}: {e}")

        return sorted(list(page_links)), sorted(list(doc_links))
