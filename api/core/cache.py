import time
import json
import hashlib
import logging
from collections import OrderedDict
from typing import Optional, Dict, Any, List
import numpy as np
from api.core.config import settings

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Authorization and scope-aware cache layer.
    Tier 1: High-speed SHA-256 exact-match key cache (Redis / in-memory LRU).
    Tier 2: In-memory cosine-similarity semantic cache for query embeddings (threshold >= 0.94).
    Reference: Phase 7 & Phase 19 of technical plan.
    """

    MAX_MEMORY_CACHE_ENTRIES = 5000

    def __init__(self):
        self.redis_client = None
        self._memory_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._semantic_vectors: List[Dict[str, Any]] = []
        self._max_semantic_entries = 1000
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
        """Purges expired items from memory cache safely without mutation during iteration."""
        now = time.time()
        keys = list(self._memory_cache.keys())
        for k in keys:
            item = self._memory_cache.get(k)
            if item and item.get("expires_at", 0) <= now:
                self._memory_cache.pop(k, None)

    async def set(self, key: str, data: Dict[str, Any], ttl: int = None):
        ttl = ttl or settings.CACHE_TTL_VOLATILE_SECONDS
        client = await self._get_redis()
        if client:
            try:
                await client.set(key, json.dumps(data), ex=ttl)
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

    def get_semantic(
        self,
        query_vector: List[float],
        scope: str = "all|all",
        threshold: float = 0.94
    ) -> Optional[Dict[str, Any]]:
        """
        Tier-2 Semantic Cache: Evaluates cosine similarity of query embedding against cached queries.
        Returns cached response if similarity >= threshold (default 0.94).
        Runs in <1ms in memory without hitting disk or LLM.
        """
        if not self._semantic_vectors or not query_vector:
            return None

        now = time.time()
        try:
            q_arr = np.array(query_vector, dtype=np.float32)
            norm_q = np.linalg.norm(q_arr)
            if norm_q == 0:
                return None
            q_arr = q_arr / norm_q

            best_sim = 0.0
            best_entry = None
            valid_entries = []

            for entry in self._semantic_vectors:
                if entry["expires_at"] <= now:
                    continue
                valid_entries.append(entry)
                if entry["scope"] != scope:
                    continue
                sim = float(np.dot(q_arr, entry["norm_vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_entry = entry

            self._semantic_vectors = valid_entries

            if best_entry and best_sim >= threshold:
                logger.info(f"Tier-2 Semantic Cache HIT! (Cosine sim: {best_sim:.3f} >= {threshold})")
                return best_entry["data"]
        except Exception as e:
            logger.warning(f"Tier-2 semantic cache evaluation note: {e}")

        return None

    async def set_semantic(
        self,
        key: str,
        query_vector: Optional[List[float]],
        scope: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Sets both Tier-1 exact key and Tier-2 semantic vector cache."""
        await self.set(key, data, ttl=ttl)
        if query_vector:
            try:
                q_arr = np.array(query_vector, dtype=np.float32)
                norm_q = np.linalg.norm(q_arr)
                if norm_q > 0:
                    ttl_val = ttl or settings.CACHE_TTL_VOLATILE_SECONDS
                    if len(self._semantic_vectors) >= self._max_semantic_entries:
                        self._semantic_vectors.pop(0)
                    self._semantic_vectors.append({
                        "norm_vector": q_arr / norm_q,
                        "scope": scope,
                        "data": data,
                        "expires_at": time.time() + ttl_val,
                    })
            except Exception as e:
                logger.warning(f"Tier-2 semantic cache store note: {e}")

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
        self._semantic_vectors.clear()
        if self.redis_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.redis_client.flushdb())
            except Exception as e:
                logger.warning(f"Redis clear note: {e}")

cache = SemanticCache()

