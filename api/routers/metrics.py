from fastapi import APIRouter, Response
from sqlalchemy import select, func
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from db.session import async_session_factory
from db.models import Document, Chunk
from api.core.metrics import RAG_DOCUMENTS_TOTAL, RAG_CHUNKS_TOTAL

router = APIRouter(tags=["Observability & Metrics"])

@router.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    """
    Standard Prometheus metrics scrape endpoint.
    Exposes QPS, latencies, cache ratios, and corpus size.
    Reference: Phase 12 & Appendix B (Table 21).
    """
    # Refresh live corpus gauges from database
    try:
        async with async_session_factory() as session:
            doc_count = (await session.execute(select(func.count(Document.id)))).scalar() or 0
            chunk_count = (await session.execute(select(func.count(Chunk.id)))).scalar() or 0
            RAG_DOCUMENTS_TOTAL.set(doc_count)
            RAG_CHUNKS_TOTAL.set(chunk_count)
    except Exception:
        pass

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
