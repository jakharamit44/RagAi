"""
FastAPI Router for OpenViking-Inspired Context Filesystem and Tiered Storage (`ragai://`).
Exposes directory exploration (tree, ls), progressive context resolution (resolve),
and directory-guided semantic search (find).
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.core.auth import get_optional_current_user, require_role
from api.context.tiered_engine import tiered_engine

logger = logging.getLogger("api.routers.context")

router = APIRouter(prefix="/api/v1/context", tags=["Context Filesystem (OpenViking)"])


class ContextFindRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Semantic search query")
    base_uri: Optional[str] = Field(default="ragai://knowledge", max_length=512, pattern=r"^ragai://[a-zA-Z0-9_\-\./]*$", description="Virtual filesystem base URI to scope search")
    top_k: int = Field(default=5, ge=1, le=25, description="Maximum matches to return")


@router.get("/tree", summary="Get Hierarchical Virtual Context Tree")
async def get_context_tree(
    department: Optional[str] = Query(None, max_length=120, description="Optional department filter")
):
    """
    Returns the complete hierarchical context tree mirroring OpenViking's `ov tree` command.
    Navigates from root -> departments -> courses -> documents.
    """
    try:
        tree = await tiered_engine.get_tree(department=department)
        return {"status": "success", "tree": tree}
    except Exception as e:
        logger.error(f"Failed to generate context tree: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating context tree: {str(e)}"
        )


@router.get("/ls", summary="List Directory Contents (OpenViking ls)")
async def list_context_directory(
    uri: str = Query("ragai://knowledge", max_length=512, pattern=r"^ragai://[a-zA-Z0-9_\-\./]*$", description="Virtual filesystem directory URI to inspect")
):
    """
    Simulates the OpenViking `ls` operation. Lists direct child entries under any `ragai://` URI,
    including their L0 abstracts, L2 chunk counts, and token footprints.
    """
    try:
        entries = await tiered_engine.list_directory(uri=uri)
        return {
            "status": "success",
            "uri": uri,
            "count": len(entries),
            "entries": entries
        }
    except Exception as e:
        logger.error(f"Failed to list context directory '{uri}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to list directory: {str(e)}"
        )


@router.get("/resolve", summary="Resolve Context by URI and Tier (OpenViking read)")
async def resolve_context_uri(
    uri: str = Query(..., max_length=512, pattern=r"^ragai://[a-zA-Z0-9_\-\./]*$", description="Target ragai:// URI to resolve"),
    tier: str = Query("l1", pattern="^(l0|l1|l2|all)$", description="Target context tier: l0 (abstract), l1 (overview), l2 (deep chunks)")
):
    """
    Simulates the OpenViking `read` operation. Resolves a `ragai://` URI at the requested tier,
    enabling progressive context loading that conserves up to 90% of model token budget.
    """
    try:
        result = await tiered_engine.resolve_uri(uri=uri, tier=tier)
        return {"status": "success", "result": result}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to resolve context URI '{uri}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resolution error: {str(e)}"
        )


@router.post("/find", summary="Directory-Guided Semantic Search (OpenViking find)")
async def find_in_context(
    req: ContextFindRequest
):
    """
    Simulates the OpenViking `find` operation. Performs directory-guided semantic search
    across L0 abstracts and L1 overviews to locate the most relevant branch in the context tree.
    """
    try:
        matches = await tiered_engine.semantic_find(
            query=req.query,
            base_uri=req.base_uri,
            top_k=req.top_k
        )
        return {
            "status": "success",
            "query": req.query,
            "base_uri": req.base_uri,
            "matches": matches
        }
    except Exception as e:
        logger.error(f"Failed to execute context find: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic find error: {str(e)}"
        )


@router.post("/sync", summary="Synchronize All Context Tiers (Admin Only)")
async def sync_context_tiers(
    user = Depends(require_role("admin"))
):
    """
    Administrative endpoint to re-scan all ingested documents, re-synthesize L0/L1 summaries,
    and refresh the virtual context filesystem.
    """
    try:
        await tiered_engine.sync_database_tiers()
        return {"status": "success", "message": "Context tiers successfully synchronized."}
    except Exception as e:
        logger.error(f"Failed to sync context tiers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synchronization failed: {str(e)}"
        )


@router.get("/stats", summary="Get Context Filesystem Telemetry & Token Savings")
async def get_context_stats():
    """
    Returns telemetry on virtual context nodes, average token budgets per tier,
    and estimated LLM token savings.
    """
    from db.session import async_session_factory
    from db.models import ContextTier
    from sqlalchemy import select, func

    async with async_session_factory() as session:
        dept_cnt = await session.scalar(select(func.count()).select_from(ContextTier).where(ContextTier.tier_type == "department"))
        course_cnt = await session.scalar(select(func.count()).select_from(ContextTier).where(ContextTier.tier_type == "course"))
        doc_cnt = await session.scalar(select(func.count()).select_from(ContextTier).where(ContextTier.tier_type == "document"))
        total_l2 = await session.scalar(select(func.sum(ContextTier.l2_chunk_count)).where(ContextTier.tier_type == "document")) or 0
        avg_l0 = await session.scalar(select(func.avg(ContextTier.token_count_l0)).where(ContextTier.tier_type == "document")) or 0
        avg_l1 = await session.scalar(select(func.avg(ContextTier.token_count_l1)).where(ContextTier.tier_type == "document")) or 0

    # Token savings calculation:
    # A standard L2 load retrieves top 5 chunks (~2500 tokens).
    # L1 retrieval loads ~400 tokens -> (2500 - 400) / 2500 = 84% savings!
    typical_l2_tokens = 2500
    avg_l1_val = round(float(avg_l1), 1)
    savings_pct = round(((typical_l2_tokens - avg_l1_val) / typical_l2_tokens) * 100, 1) if typical_l2_tokens > avg_l1_val else 0.0

    return {
        "status": "success",
        "departments_count": dept_cnt or 0,
        "courses_count": course_cnt or 0,
        "documents_count": doc_cnt or 0,
        "total_l2_chunks": total_l2,
        "avg_l0_tokens": round(float(avg_l0), 1),
        "avg_l1_tokens": avg_l1_val,
        "token_savings_percent": f"{savings_pct}%",
        "uri_protocol": "ragai://"
    }
