"""
RagAi Unified Python Client SDK
Authoritative client library to integrate RagAi into Student Portals, Employee Intranets,
Faculty Systems, HR Dashboards, and Administrative Services.
"""

from typing import Dict, Any, List, Optional
import time
import requests


class RagAiError(Exception):
    """Base exception for all RagAi client errors."""
    pass


class AuthenticationError(RagAiError):
    """Raised when an invalid or revoked API key is supplied (HTTP 401/403)."""
    pass


class RateLimitError(RagAiError):
    """Raised when API rate limits are exceeded (HTTP 429)."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(RagAiError):
    """Raised when the RagAi server encounters an internal error (HTTP 500/503)."""
    pass


class RagAiClient:
    """
    Unified client for interacting with the RagAi REST API.
    Supports students, employees, faculty, and administrative personas.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "ragai_student_default",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "RagAi-Integration-SDK/2.4.0"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        retries = 0

        while True:
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                
                if response.status_code in (200, 201):
                    return response.json()
                
                if response.status_code in (401, 403):
                    raise AuthenticationError(
                        f"Authentication failed ({response.status_code}): {response.text}"
                    )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    if retries < self.max_retries:
                        time.sleep(retry_after)
                        retries += 1
                        continue
                    raise RateLimitError(
                        f"Rate limit exceeded. Try again after {retry_after}s.",
                        retry_after=retry_after
                    )
                
                if response.status_code >= 500:
                    if retries < self.max_retries:
                        time.sleep(1.5 ** retries)
                        retries += 1
                        continue
                    raise ServerError(f"Server error ({response.status_code}): {response.text}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if retries < self.max_retries:
                    time.sleep(1.5 ** retries)
                    retries += 1
                    continue
                raise RagAiError(f"Network request to RagAi failed: {e}") from e

    def ask(
        self,
        query: str,
        department: Optional[str] = None,
        course: Optional[str] = None,
        role: str = "general",
        top_k: int = 5,
        temperature: float = 0.20,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ask an academic, employee, or administrative question with verified RAG grounding.
        """
        payload = {
            "query": query,
            "department": department,
            "course": course,
            "role": role,
            "top_k": top_k,
            "temperature": temperature,
            "session_id": session_id
        }
        return self._request("POST", "/api/v1/ask", json=payload)

    def submit_feedback(
        self,
        query_id: str,
        feedback_type: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit user feedback ('up' or 'down') to feed the Corrective RAG self-tuning engine.
        """
        if feedback_type not in ("up", "down"):
            raise ValueError("feedback_type must be 'up' or 'down'")

        payload = {
            "query_id": query_id,
            "feedback": feedback_type,
            "reason": reason
        }
        return self._request("POST", "/api/v1/feedback", json=payload)

    def get_cortex(self, department: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch the current Cognitive AI Brain knowledge graph nodes, edges, and coherence metrics.
        Requires admin privileges (e.g. 'ragai_master_admin_key').
        """
        headers = {"X-API-Key": api_key} if api_key else None
        params = {"department": department} if department else {}
        try:
            return self._request("GET", "/api/v1/admin/brain/graph", params=params, headers=headers)
        except RagAiError as e:
            if "404" in str(e):
                dept_params = {"dept": department} if department else {}
                return self._request("GET", "/api/v1/brain/cortex", params=dept_params, headers=headers)
            raise

    def fire_synapse(self, query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger an on-demand cognitive probe to test neural activation and view the Thought Pathway.
        Requires admin privileges (e.g. 'ragai_master_admin_key').
        """
        headers = {"X-API-Key": api_key} if api_key else None
        try:
            return self._request("POST", "/api/v1/admin/brain/fire-synapse", json={"query": query}, headers=headers)
        except RagAiError as e:
            if "404" in str(e):
                return self._request("POST", "/api/v1/brain/fire", json={"query": query}, headers=headers)
            raise

    def check_health(self) -> Dict[str, Any]:
        """
        Probe cluster health (Redis, Qdrant, SQLite, Embedder, LLM Router).
        """
        return self._request("GET", "/api/v1/health")

    # =========================================================================
    # OpenViking Virtual Context Filesystem & Tiered Storage (ragai://)
    # =========================================================================

    def get_context_tree(self, department: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve the full hierarchical context tree (OpenViking `ov tree`).
        Returns nested root -> department -> course -> document structure.
        """
        params = {"department": department} if department else {}
        return self._request("GET", "/api/v1/context/tree", params=params)

    def list_context_dir(self, uri: str = "ragai://knowledge") -> Dict[str, Any]:
        """
        List immediate directory children for a virtual `ragai://` URI (OpenViking `ov ls`).
        Returns entries with L0 abstracts, chunk counts, and token footprints.
        """
        return self._request("GET", "/api/v1/context/ls", params={"uri": uri})

    def resolve_context(self, uri: str, tier: str = "l1") -> Dict[str, Any]:
        """
        Resolve context content at a specific tier (OpenViking `ov read`).
        Tiers:
          - 'l0': Dense 1-sentence abstract (~50-100 tokens)
          - 'l1': Structured curricular synopsis (~400-800 tokens, 85% savings)
          - 'l2': Deep verbatim chunks with source citations
          - 'all': Complete multi-tier package
        """
        return self._request("GET", "/api/v1/context/resolve", params={"uri": uri, "tier": tier})

    def find_context(
        self,
        query: str,
        base_uri: str = "ragai://knowledge",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Execute directory-guided semantic search (OpenViking `ov find`).
        Discovers relevant branches without dumping raw chunks into LLM context.
        """
        payload = {
            "query": query,
            "base_uri": base_uri,
            "top_k": top_k
        }
        return self._request("POST", "/api/v1/context/find", json=payload)

    def get_context_stats(self) -> Dict[str, Any]:
        """
        Retrieve telemetry on context nodes, average token budgets, and LLM token savings.
        """
        return self._request("GET", "/api/v1/context/stats")

    def sync_context_tiers(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger an administrative sync of all document tiers and virtual directories.
        Requires admin privileges (e.g. 'ragai_master_admin_key').
        """
        headers = {"X-API-Key": api_key} if api_key else None
        return self._request("POST", "/api/v1/context/sync", headers=headers)

