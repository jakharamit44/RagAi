import io
import re
import os
import hashlib
import logging
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx

from .url_normalizer import UrlNormalizer
from ingestion.ocr_printed import printed_ocr

logger = logging.getLogger(__name__)

BANNER_CONTAINER_KEYWORDS = re.compile(
    r"banner|slider|carousel|owl-carousel|swiper|marquee|announcement|notice|circular|hero|flyer|popup",
    re.I
)

BANNER_IMG_KEYWORDS = re.compile(
    r"banner|slider|slide|carousel|announcement|notice|circular|admission|exam|postpone|datesheet|schedule|convocation|tender|flyer",
    re.I
)

class BannerOCRPipeline:
    """
    Identifies, retrieves, and extracts textual announcements from university banner graphics,
    homepage carousels, and image-based circulars using local PP-OCRv4 (RapidOCR).
    Caches results via SHA-256 hash to eliminate redundant OCR computation.
    """

    def __init__(self, max_images_per_page: int = 5, max_image_bytes: int = 8 * 1024 * 1024):
        self.max_images_per_page = max_images_per_page
        self.max_image_bytes = max_image_bytes
        # In-memory cache: sha256 -> {"text": str, "confidence": float}
        self._cache: Dict[str, Dict[str, Any]] = {}

    def harvest_banner_image_urls(self, html_text: str, page_url: str, allowed_domains: List[str]) -> List[str]:
        """
        Scans HTML DOM to identify prominent banner, slider, and announcement graphic URLs.
        """
        candidate_urls: Set[str] = set()

        try:
            soup = BeautifulSoup(html_text, "html.parser")

            # 1. Images inside banner/slider/carousel/announcement containers
            containers = soup.find_all(lambda tag: (
                tag.name in ["div", "section", "header", "ul", "marquee"] and (
                    BANNER_CONTAINER_KEYWORDS.search(str(tag.get("class", []))) or
                    BANNER_CONTAINER_KEYWORDS.search(tag.get("id", ""))
                )
            ))

            for container in containers:
                for img in container.find_all("img"):
                    src = img.get("src") or img.get("data-src") or img.get("data-lazy")
                    if src:
                        candidate_urls.add(src)

            # 2. Standalone images with banner-like filenames, alt text, or titles
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy")
                if not src:
                    continue

                alt = img.get("alt", "")
                title = img.get("title", "")
                img_class = " ".join(img.get("class", []))

                if (
                    BANNER_IMG_KEYWORDS.search(src) or
                    BANNER_IMG_KEYWORDS.search(alt) or
                    BANNER_IMG_KEYWORDS.search(title) or
                    BANNER_IMG_KEYWORDS.search(img_class)
                ):
                    candidate_urls.add(src)

            # 3. Resolve URLs, check SSRF safety, and deduplicate
            valid_urls: List[str] = []
            for raw_src in candidate_urls:
                full_url = urljoin(page_url, raw_src.strip())
                norm_url = UrlNormalizer.normalize(full_url, base_url=page_url)
                if not norm_url:
                    continue

                is_safe, _ = UrlNormalizer.is_safe_url(norm_url, allowed_domains)
                if is_safe and norm_url not in valid_urls:
                    valid_urls.append(norm_url)

                if len(valid_urls) >= self.max_images_per_page:
                    break

            return valid_urls

        except Exception as e:
            logger.warning(f"Error harvesting banner image URLs from {page_url}: {e}")
            return []

    async def extract_banner_announcements(
        self,
        html_text: str,
        page_url: str,
        allowed_domains: List[str],
        client: Optional[httpx.AsyncClient] = None
    ) -> List[Dict[str, Any]]:
        """
        Finds banner images, downloads them safely, runs RapidOCR, and returns structured announcement data.
        """
        image_urls = self.harvest_banner_image_urls(html_text, page_url, allowed_domains)
        if not image_urls:
            return []

        results: List[Dict[str, Any]] = []
        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0, verify=True, follow_redirects=False)
            should_close_client = True

        try:
            for img_url in image_urls:
                try:
                    announcement = await self._process_single_image(client, img_url, allowed_domains=allowed_domains)
                    if announcement:
                        results.append(announcement)
                except Exception as ex:
                    logger.debug(f"Banner OCR note for {img_url}: {ex}")
        finally:
            if should_close_client:
                await client.aclose()

        return results

    async def _process_single_image(
        self,
        client: httpx.AsyncClient,
        img_url: str,
        allowed_domains: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Downloads single image with redirect SSRF validation, runs OCR in thread with cache lookup, and validates textual relevance."""
        curr_url = img_url
        domains = allowed_domains or ["mdu.ac.in"]

        # Safe fetch with manual redirect resolution and per-hop SSRF validation
        resp = None
        for _ in range(3):
            is_safe, _ = UrlNormalizer.is_safe_url(curr_url, allowed_domains=domains)
            if not is_safe:
                return None

            try:
                resp = await client.get(curr_url)
            except Exception:
                return None

            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                if not loc:
                    return None
                curr_url = urljoin(curr_url, loc)
                continue
            break
        else:
            return None

        if not resp or resp.status_code != 200 or len(resp.content) > self.max_image_bytes or len(resp.content) < 500:
            return None

        content_type = resp.headers.get("content-type", "").lower()
        if "image" not in content_type and not any(curr_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            return None

        img_bytes = resp.content
        img_hash = hashlib.sha256(img_bytes).hexdigest()

        # Cache lookup
        if img_hash in self._cache:
            cached_data = self._cache[img_hash]
            if not cached_data.get("text"):
                return None
            return {
                "image_url": curr_url,
                "image_name": os.path.basename(urlparse(curr_url).path) or "banner.jpg",
                "ocr_text": cached_data["text"],
                "confidence": cached_data.get("confidence", 0.9),
                "cached": True
            }

        # Perform OCR in worker thread to prevent event loop blocking
        try:
            from PIL import Image
            import asyncio
            Image.MAX_IMAGE_PIXELS = 16_000_000

            def _decode_and_ocr(b: bytes) -> Dict[str, Any]:
                with Image.open(io.BytesIO(b)) as raw_img:
                    if raw_img.width * raw_img.height > 16_000_000:
                        return {"text": "", "confidence": 0.0}
                    converted = raw_img.convert("RGB")
                    return printed_ocr.extract_text(converted)

            ocr_res = await asyncio.to_thread(_decode_and_ocr, img_bytes)
            text = (ocr_res.get("text") or "").strip()
            confidence = ocr_res.get("confidence", 0.0)

            # Bound cache size to prevent memory bloat
            if len(self._cache) > 500:
                for k in list(self._cache.keys())[:100]:
                    self._cache.pop(k, None)

            # Informative threshold filter: require >= 15 chars and meaningful alphanumeric words
            clean_words = [w for w in re.findall(r"\w+", text) if len(w) > 1]
            if len(text) < 15 or len(clean_words) < 2:
                self._cache[img_hash] = {"text": "", "confidence": 0.0}
                return None

            self._cache[img_hash] = {"text": text, "confidence": confidence}

            return {
                "image_url": curr_url,
                "image_name": os.path.basename(urlparse(curr_url).path) or "banner.jpg",
                "ocr_text": text,
                "confidence": confidence,
                "cached": False
            }
        except Exception as e:
            logger.debug(f"Failed to OCR image {curr_url}: {e}")
            self._cache[img_hash] = {"text": "", "confidence": 0.0}
            return None

    @staticmethod
    def format_announcements_markdown(announcements: List[Dict[str, Any]]) -> str:
        """Formats extracted banner announcements into structured Markdown."""
        if not announcements:
            return ""

        sections = ["\n\n## 📢 Visual Banner Announcements (Extracted via OCR)\n"]
        for item in announcements:
            img_name = item.get("image_name", "banner.jpg")
            img_url = item.get("image_url", "")
            ocr_text = item.get("ocr_text", "")
            conf = int(item.get("confidence", 0.9) * 100)

            sections.append(
                f"### Announcement Graphic: {img_name}\n"
                f"- **Image Source**: {img_url}\n"
                f"- **OCR Confidence**: {conf}%\n"
                f"- **Extracted Text Content**:\n"
                f"```text\n{ocr_text}\n```\n"
            )

        return "\n".join(sections)

# Global singleton
banner_ocr_pipeline = BannerOCRPipeline()
