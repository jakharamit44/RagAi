import re
import hashlib
import ipaddress
from typing import Optional, List, Set, Tuple
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode

DOCUMENT_EXTENSIONS: Set[str] = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"
}

IGNORED_SCHEMES: Set[str] = {
    "mailto", "tel", "javascript", "data", "whatsapp", "callto"
}

DISALLOWED_PATH_PATTERNS = [
    re.compile(r"/logout", re.I),
    re.compile(r"/logoff", re.I),
    re.compile(r"/login", re.I),
    re.compile(r"/signin", re.I),
    re.compile(r"\.(?:png|jpg|jpeg|gif|svg|ico|css|js|woff|woff2|ttf|eot|mp4|webm|avi|mp3)$", re.I),
]

class UrlNormalizer:
    """
    Standardizes and filters URLs for academic web crawling.
    Ensures safe domain boundary enforcement and reliable delta tracking.
    """

    @staticmethod
    def normalize(raw_url: str, base_url: str = "https://mdu.ac.in") -> Optional[str]:
        """
        Normalizes a URL by stripping fragments, tracking queries, and resolving relative links.
        """
        if not raw_url or not isinstance(raw_url, str):
            return None

        raw_url = raw_url.strip()
        if not raw_url:
            return None

        # Ignore scheme shortcuts
        lower_raw = raw_url.lower()
        for scheme in IGNORED_SCHEMES:
            if lower_raw.startswith(f"{scheme}:"):
                return None

        try:
            # Resolve relative URLs against base_url
            joined = urljoin(base_url, raw_url)
            parsed = urlparse(joined)

            if parsed.scheme not in ("http", "https"):
                return None

            if not parsed.netloc:
                return None

            netloc = parsed.netloc.lower()
            # Remove standard default ports
            if netloc.endswith(":80"):
                netloc = netloc[:-3]
            elif netloc.endswith(":443"):
                netloc = netloc[:-4]

            # Filter out tracking query params while keeping critical ASPX / server query parameters
            query_params = []
            for k, v in parse_qsl(parsed.query, keep_blank_values=True):
                if k.lower() not in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"):
                    query_params.append((k, v))

            clean_query = urlencode(query_params)

            # Reconstruct URL without fragment
            clean_url = urlunparse((
                parsed.scheme.lower(),
                netloc,
                parsed.path,
                parsed.params,
                clean_query,
                ""  # Strip fragment
            ))

            return clean_url
        except Exception:
            return None

    @staticmethod
    def get_url_hash(url: str) -> str:
        """Returns 64-character SHA-256 hex digest of normalized URL."""
        return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
        """
        Checks if the URL's domain is in the allowed domain list (supports subdomains).
        e.g. 'mdu.ac.in' matches 'mdu.ac.in', 'admission.mdu.ac.in', 'www.mdu.ac.in'.
        """
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower().strip()
            if not host:
                return False

            for allowed in allowed_domains:
                clean_allowed = allowed.strip().lower()
                if not clean_allowed:
                    continue
                if clean_allowed.startswith("*."):
                    clean_allowed = clean_allowed[2:]
                
                if host == clean_allowed or host.endswith("." + clean_allowed):
                    return True

            return False
        except Exception:
            return False

    @staticmethod
    def is_safe_url(url: str, allowed_domains: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        SSRF defense: Validates scheme, blocks private/loopback/metadata IP ranges,
        and enforces domain whitelisting.
        """
        if not url or not isinstance(url, str):
            return False, "Empty or invalid URL"
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ("http", "https"):
                return False, f"Unsupported scheme '{parsed.scheme}'"

            host = (parsed.hostname or "").lower().strip()
            if not host:
                return False, "Missing hostname"

            # Check loopback hostnames
            if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
                return False, "Access to localhost or loopback is blocked"

            # Check IP address targets
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False, f"Access to private/internal IP {host} is blocked"
                if str(ip) == "169.254.169.254":
                    return False, "Cloud metadata service access is blocked"
            except ValueError:
                pass

            if allowed_domains:
                if not UrlNormalizer.is_allowed_domain(url, allowed_domains):
                    return False, f"Domain '{host}' is not in allowed domain whitelist: {allowed_domains}"

            return True, "OK"
        except Exception as e:
            return False, f"URL safety check error: {str(e)}"

    @staticmethod
    def is_document_url(url: str) -> bool:
        """
        Returns True if the URL points to a downloadable document (.pdf, .docx, etc.).
        """
        try:
            path = urlparse(url).path.lower()
            return any(path.endswith(ext) for ext in DOCUMENT_EXTENSIONS)
        except Exception:
            return False

    @staticmethod
    def is_skippable_url(url: str) -> bool:
        """
        Checks if the URL is an asset or sensitive URL (images, styles, logout).
        """
        try:
            path = urlparse(url).path
            for pat in DISALLOWED_PATH_PATTERNS:
                if pat.search(path):
                    return True
            return False
        except Exception:
            return True
