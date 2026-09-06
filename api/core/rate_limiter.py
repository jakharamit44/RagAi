import time
import logging
from typing import Dict, List
from fastapi import HTTPException, status
from api.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Sliding-window rate limiter for unauthenticated IPs and student tokens.
    Reference: Phase 7 & Phase 19 (Abuse prevention).
    """

    def __init__(self):
        # Maps client_id -> list of unix timestamps
        self._windows: Dict[str, List[float]] = {}

    def check_rate_limit(self, client_id: str, limit: int = None, window_seconds: int = 60):
        limit = limit or settings.RATE_LIMIT_PER_IP_PER_MINUTE
        now = time.time()
        window_start = now - window_seconds

        # Clean old timestamps
        history = self._windows.get(client_id, [])
        valid_history = [t for t in history if t > window_start]

        if len(valid_history) >= limit:
            logger.warning(f"Rate limit exceeded for client: {client_id} ({len(valid_history)}/{limit})")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "rate_limited",
                        "message": f"Query rate limit exceeded ({limit} requests per minute). Please wait."
                    }
                }
            )

        valid_history.append(now)
        self._windows[client_id] = valid_history

rate_limiter = RateLimiter()
