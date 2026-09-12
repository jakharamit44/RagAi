import re
import socket
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
    re.compile(r"\.(?:png|jpg|jpeg|gif|svg|ico|bmp|tif|tiff|jfif|webp|psd|ai|eps|raw|cr2|nef|css|js|woff|woff2|ttf|eot|mp4|webm|avi|mp3|wav|ogg|rar|zip|7z|tar|gz|bz2|xz|iso|bin|exe|msi|dmg|apk|dat|xlsm|xltx|xltm|dotx|dotm|potx|potm)(?:$|[?#])", re.I),
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
    def extract_root_domain(url_or_host: str) -> str:
        """
        Extracts the canonical root domain from a hostname or URL.
        Correctly handles Indian and academic multi-part ccTLDs (.ac.in, .edu.in, etc.).
        e.g. 'admission.mdu.ac.in' -> 'mdu.ac.in'
             'https://www.mdu.ac.in/portal' -> 'mdu.ac.in'
             'mdu.ac.in' -> 'mdu.ac.in'
        """
        if not url_or_host or not isinstance(url_or_host, str):
            return ""

        clean = url_or_host.strip().lower()
        if "://" in clean:
            try:
                clean = urlparse(clean).hostname or clean
            except Exception:
                pass

        # Strip port and path if still present
        clean = clean.split("/")[0].split(":")[0]
        if clean.startswith("*."):
            clean = clean[2:]

        parts = clean.split(".")
        if len(parts) <= 2:
            return clean

        two_level_tlds = {
            "ac.in", "edu.in", "res.in", "gov.in", "org.in", "co.in", "nic.in",
            "ac.uk", "edu.au", "gov.uk", "co.uk", "org.uk", "ernet.in"
        }

        last_two = f"{parts[-2]}.{parts[-1]}"
        if last_two in two_level_tlds and len(parts) >= 3:
            return f"{parts[-3]}.{last_two}"

        return f"{parts[-2]}.{parts[-1]}"

    @staticmethod
    def is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
        """
        Checks if the URL's domain is in the allowed domain list (supports wildcard subdomains).
        e.g. 'mdu.ac.in' automatically allows 'mdu.ac.in', 'admission.mdu.ac.in', 'results.mdu.ac.in', etc.
        """
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower().strip()
            if not host:
                return False

            host_root = UrlNormalizer.extract_root_domain(host)

            for allowed in allowed_domains:
                clean_allowed = allowed.strip().lower()
                if not clean_allowed:
                    continue
                if clean_allowed.startswith("*."):
                    clean_allowed = clean_allowed[2:]

                # Direct match or subdomain of allowed domain
                if host == clean_allowed or host.endswith("." + clean_allowed):
                    return True

                # Match against root domain of allowed domain
                allowed_root = UrlNormalizer.extract_root_domain(clean_allowed)
                if allowed_root and (host == allowed_root or host.endswith("." + allowed_root) or host_root == allowed_root):
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

            # Parse literal IP or resolve domain names via DNS to prevent SSRF
            try:
                ip = ipaddress.ip_address(host)
                resolved_ips = [ip]
            except ValueError:
                # Host is a domain: resolve via DNS to inspect underlying IPs
                try:
                    addr_info = socket.getaddrinfo(host, None)
                    resolved_ips = [ipaddress.ip_address(addr[4][0]) for addr in addr_info if addr[4]]
                except Exception:
                    return False, f"Could not resolve domain '{host}' via DNS"

            if not resolved_ips:
                return False, f"Could not resolve any IP address for host '{host}'"

            for ip_obj in resolved_ips:
                if ip_obj.is_loopback:
                    return False, f"Access to loopback IP {ip_obj} for host '{host}' is blocked"
                if str(ip_obj) in ("169.254.169.254", "0.0.0.0") or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
                    return False, "Cloud metadata, link-local, or unroutable service access is blocked"
                if ip_obj.is_private:
                    # Allow private IP ONLY if host is in an explicitly configured allowed_domains list (e.g. campus intranet)
                    if allowed_domains and UrlNormalizer.is_allowed_domain(url, allowed_domains):
                        pass
                    else:
                        return False, f"Access to private/internal IP {ip_obj} for host '{host}' is blocked"

            if allowed_domains:
                if not UrlNormalizer.is_allowed_domain(url, allowed_domains):
                    return False, f"Domain '{host}' is not in allowed domain whitelist: {allowed_domains}"

            return True, "OK"
        except Exception as e:
            return False, f"URL safety check error: {str(e)}"

    @staticmethod
    def is_document_url(url: str) -> bool:
        """
        Returns True if the URL points to a downloadable academic document (.pdf, .docx, .xlsx, etc.).
        Handles direct extensions and ASP.NET/PHP query-based download routes.
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in DOCUMENT_EXTENSIONS):
                return True

            # Query string document detection (e.g. ?file=notice.pdf, ?doc_type=pdf, ?filename=results.xlsx)
            query = parsed.query.lower()
            if query:
                for ext in DOCUMENT_EXTENSIONS:
                    clean_ext = ext.lstrip(".")
                    if f".{clean_ext}" in query or f"type={clean_ext}" in query or f"format={clean_ext}" in query:
                        return True

            return False
        except Exception:
            return False

    @staticmethod
    def is_skippable_url(url: str) -> bool:
        """
        Checks if the URL is an asset or sensitive URL (images, styles, logout).
        """
        try:
            parsed = urlparse(url)
            path = parsed.path
            for pat in DISALLOWED_PATH_PATTERNS:
                if pat.search(path) or pat.search(url):
                    return True
            return False
        except Exception:
            return True
