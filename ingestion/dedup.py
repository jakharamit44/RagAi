from typing import List, Dict, Any, Set
from sqlalchemy import select
from db.models import Chunk

class ContentDeduplicator:
    """
    Performs cross-document and within-document deduplication via chunk content hashes.
    Reference: Phase 2 of technical plan.
    """

    @staticmethod
    def deduplicate_in_memory(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_hashes: Set[str] = set()
        unique_chunks = []
        for c in chunks:
            h = c["content_hash"]
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_chunks.append(c)
        return unique_chunks

    @staticmethod
    async def filter_existing_db(chunks: List[Dict[str, Any]], session) -> List[Dict[str, Any]]:
        """Filter out chunks whose SHA-256 hashes already exist in the database."""
        hashes = [c["content_hash"] for c in chunks]
        if not hashes:
            return []

        stmt = select(Chunk.content_hash).where(Chunk.content_hash.in_(hashes))
        res = await session.execute(stmt)
        existing = set(res.scalars().all())

        return [c for c in chunks if c["content_hash"] not in existing]
