import time
import json
import hashlib
import logging
from collections import OrderedDict
from typing import Optional, Dict, Any
from api.core.config import settings

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Authorization and scope-aware cache layer.
    Uses Redis when available, falls back to persistent in-memory bounded LRU TTL store.
    Reference: Phase 7 & Phase 19 of technical plan.
    """

    MAX_MEMORY_CACHE_ENTRIES = 5000

    def __init__(self):
        self.redis_client = None
        self._memory_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._init_attempted = False
        self._op_counter = 0

    async def _get_redis(self):
        if not self._init_attempted:
            self._init_attempted = True
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
                await client.ping()
                self.redis_client = client
                logger.info(f"Connected to Redis cache at: {settings.REDIS_URL}")
            except Exception as e:
                logger.info(f"Redis cache offline ({e}). Using in-memory TTL cache fallback.")
                self.redis_client = None
        return self.redis_client

    @staticmethod
    def make_cache_key(question: str, department: Optional[str] = None, course: Optional[str] = None) -> str:
        """
        Builds authorization-aware cache key.
        Same question in different departments or courses produces separate cache slots.
        """
        raw_str = f"dept:{department or 'all'}|course:{course or 'all'}|q:{question.strip().lower()}"
        return f"rag_cache:{hashlib.sha256(raw_str.encode('utf-8')).hexdigest()}"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        client = await self._get_redis()
        if client:
            try:
                val = await client.get(key)
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # In-memory LRU fallback
        item = self._memory_cache.get(key)
        if item:
            if item["expires_at"] > time.time():
                self._memory_cache.move_to_end(key)
                return item["data"]
            else:
                del self._memory_cache[key]
        return None

    def _purge_expired_memory(self):
        """Purges expired items from memory cache to keep memory consumption low."""
        now = time.time()
        expired_keys = [k for k, v in self._memory_cache.items() if v["expires_at"] <= now]
        for k in expired_keys:
            self._memory_cache.pop(k, None)

    async def set(self, key: str, data: Dict[str, Any], ttl: int = None):
        ttl = ttl or settings.CACHE_TTL_VOLATILE_SECONDS
        client = await self._get_redis()
        if client:
            try:
                await client.setex(key, ttl, json.dumps(data))
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # In-memory bounded LRU fallback
        self._op_counter += 1
        if self._op_counter % 100 == 0:
            self._purge_expired_memory()

        if key in self._memory_cache:
            self._memory_cache.move_to_end(key)
        elif len(self._memory_cache) >= self.MAX_MEMORY_CACHE_ENTRIES:
            # Evict oldest LRU entry
            self._memory_cache.popitem(last=False)

        self._memory_cache[key] = {
            "data": data,
            "expires_at": time.time() + ttl
        }

    async def get_diagnostics(self) -> Dict[str, Any]:
        """
        Returns live connection diagnostics for Redis and in-memory fallback.
        """
        redis_connected = False
        redis_error = None
        ping_ms = None
        redis_keys = 0
        redis_memory_human = None

        try:
            import redis.asyncio as aioredis
            client = self.redis_client
            if not client:
                client = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.5)
            
            p_start = time.time()
            await client.ping()
            ping_ms = round((time.time() - p_start) * 1000, 2)
            self.redis_client = client
            redis_connected = True
            
            try:
                redis_keys = await client.dbsize()
                info = await client.info("memory")
                redis_memory_human = info.get("used_memory_human", "N/A")
            except Exception:
                pass
        except Exception as e:
            redis_connected = False
            redis_error = str(e)
            self.redis_client = None

        now = time.time()
        active_memory_entries = sum(1 for v in self._memory_cache.values() if v.get("expires_at", 0) > now)

        return {
            "is_connected": redis_connected,
            "status": "connected" if redis_connected else "fallback_in_memory",
            "mode": "Redis Server" if redis_connected else "In-Memory LRU Cache",
            "url": settings.REDIS_URL,
            "ping_ms": ping_ms,
            "redis_keys": redis_keys if redis_connected else 0,
            "redis_memory": redis_memory_human,
            "in_memory_entries": active_memory_entries,
            "in_memory_max": self.MAX_MEMORY_CACHE_ENTRIES,
            "error": redis_error if not redis_connected else None,
        }

    def clear(self):
        """Clears in-memory cache and attempts to flush Redis keys."""
        self._memory_cache.clear()
        if self.redis_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.redis_client.flushdb())
            except Exception as e:
                logger.warning(f"Redis clear note: {e}")

cache = SemanticCache()

