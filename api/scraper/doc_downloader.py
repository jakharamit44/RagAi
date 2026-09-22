import os
import hashlib
import logging
from typing import Optional, Tuple
import httpx
from .url_normalizer import UrlNormalizer

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "downloads", "mdu_scraped"))
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB

class DocumentDownloader:
    """
    Asynchronous document streamer for downloading academic PDFs, circulars, and syllabi.
    """

    @staticmethod
    def get_storage_path(url: str) -> str:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        url_hash_prefix = UrlNormalizer.get_url_hash(url)[:12]
        raw_name = url.split("/")[-1].split("?")[0]
        # Sanitize filename
        safe_name = "".join(c for c in raw_name if c.isalnum() or c in "._- ").strip()
        # Protect against Windows device reserved names (CON, PRN, AUX, NUL, COM1..9, LPT1..9)
        base_no_ext = os.path.splitext(safe_name)[0].upper()
        if base_no_ext in {"CON", "PRN", "AUX", "NUL"} or (len(base_no_ext) == 4 and base_no_ext[:3] in {"COM", "LPT"} and base_no_ext[3].isdigit()):
            safe_name = f"safe_{safe_name}"

        if not safe_name or not UrlNormalizer.is_document_url(safe_name):
            filename = f"{url_hash_prefix}_doc.pdf"
        else:
            filename = f"{url_hash_prefix}_{safe_name}"
        return os.path.join(DOWNLOAD_DIR, filename)

    @staticmethod
    async def download_file(
        client: httpx.AsyncClient,
        url: str,
        conditional_headers: Optional[dict] = None,
        allowed_domains: Optional[List[str]] = None
    ) -> Tuple[bool, int, Optional[str], Optional[str], dict]:
        """
        Streams document to disk.
        Returns:
            (success, http_status, local_path, sha256_hash, response_headers)
        """
        target_path = DocumentDownloader.get_storage_path(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UnivRAG-Scraper/1.1",
            "Accept": "application/pdf,*/*",
        }
        if conditional_headers:
            headers.update(conditional_headers)

        hasher = hashlib.sha256()

        try:
            async with client.stream("GET", url, headers=headers, follow_redirects=True, timeout=30.0) as resp:
                resp_headers = dict(resp.headers)
                # Re-validate final redirected URL against SSRF with allowed_domains
                eff_allowed = allowed_domains if allowed_domains is not None else ["mdu.ac.in"]
                is_safe_target, target_reason = UrlNormalizer.is_safe_url(str(resp.url), allowed_domains=eff_allowed)
                if not is_safe_target:
                    logger.warning(f"Download redirect target {resp.url} failed SSRF check: {target_reason}")
                    return False, 400, None, None, resp_headers

                if resp.status_code == 304:
                    return False, 304, None, None, resp_headers

                if resp.status_code != 200:
                    logger.warning(f"Download returned {resp.status_code} for {url}")
                    return False, resp.status_code, None, None, resp_headers

                # Check Content-Length header if present
                content_length = resp.headers.get("content-length")
                if content_length and content_length.isdigit() and int(content_length) > MAX_DOCUMENT_SIZE:
                    logger.warning(f"Document exceeds max size limit ({content_length} bytes): {url}")
                    return False, 413, None, None, resp_headers

                # Stream to temporary file first with size limit enforcement
                temp_path = f"{target_path}.tmp"
                total_bytes = 0
                with open(temp_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        if chunk:
                            total_bytes += len(chunk)
                            if total_bytes > MAX_DOCUMENT_SIZE:
                                logger.warning(f"Streaming exceeded max size limit ({MAX_DOCUMENT_SIZE} bytes): {url}")
                                f.close()
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                                return False, 413, None, None, resp_headers
                            f.write(chunk)
                            hasher.update(chunk)

                # Move temp to final
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.replace(temp_path, target_path)

                content_hash = hasher.hexdigest()
                logger.info(f"Downloaded document: {os.path.basename(target_path)} ({content_hash[:8]}...)")
                return True, 200, target_path, content_hash, resp_headers

        except Exception as e:
            logger.error(f"Failed to stream document {url}: {e}")
            temp_path = f"{target_path}.tmp"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            return False, 500, None, None, {}
