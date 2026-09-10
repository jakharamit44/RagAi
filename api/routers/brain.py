import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.core.auth import require_role
from api.brain.graph_engine import brain_graph_engine
from api.brain.cognitive_memory import cognitive_memory
from api.brain.neural_firer import neural_firer

logger = logging.getLogger("api.routers.brain")

router = APIRouter(
    prefix="/api/v1/admin/brain",
    tags=["Cognitive AI Brain & Knowledge Cortex"],
    dependencies=[Depends(require_role("admin"))]
)


class FireSynapseRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language query or concept to fire through the brain")


@router.get("/graph")
async def get_knowledge_graph(
    department: Optional[str] = Query(None, description="Optional department filter (e.g. 'Computer Science')")
):
    """
    Returns the multi-tiered University Knowledge Cortex (nodes, links, and metadata).
    Supports optional department filtering.
    """
    try:
        graph = await brain_graph_engine.get_graph(department=department)
        return graph
    except Exception as e:
        logger.error(f"Error fetching Knowledge Graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate Knowledge Graph: {str(e)}")


@router.get("/telemetry")
async def get_brain_telemetry():
    """
    Returns real-time cognitive telemetry:
    - Cognitive state (IDLE / REFLECTING / FIRING)
    - Memory hierarchy (Semantic, Episodic, Working)
    - Coherence index and abstention rates
    - Active neuro-plasticity heuristics
    """
    try:
        telemetry = await cognitive_memory.get_telemetry()
        return telemetry
    except Exception as e:
        logger.error(f"Error fetching Brain telemetry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch Brain telemetry: {str(e)}")


@router.post("/fire-synapse")
async def fire_synapse(payload: FireSynapseRequest):
    """
    Simulates semantic neural firing for any academic question or concept.
    Returns activated graph nodes, synaptic pulses, and the 4-step Thought Pathway Trace.
    """
    try:
        result = await neural_firer.fire_synapse(query=payload.query)
        return result
    except Exception as e:
        logger.error(f"Error simulating neural firing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Neural firing simulation failed: {str(e)}")


@router.post("/rebuild")
async def rebuild_brain_graph():
    """
    Forces complete recalculation of the University Knowledge Cortex from persistent records.
    """
    try:
        brain_graph_engine.invalidate_cache()
        neural_firer.clear_cache()
        fresh_graph = await brain_graph_engine.get_graph()
        return {
            "status": "success",
            "message": "Knowledge Cortex rebuilt successfully.",
            "stats": fresh_graph.get("stats", {})
        }
    except Exception as e:
        logger.error(f"Error rebuilding Knowledge Graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rebuild Knowledge Graph.")


alias_router = APIRouter(
    prefix="/api/v1/brain",
    tags=["Cognitive AI Brain & Knowledge Cortex"],
    dependencies=[Depends(require_role("admin"))]
)

@alias_router.get("/cortex")
async def get_knowledge_cortex_alias(
    dept: Optional[str] = Query(None, description="Optional department filter"),
    department: Optional[str] = Query(None, description="Optional department filter")
):
    """Alias for /api/v1/admin/brain/graph for client SDKs."""
    target_dept = dept or department
    return await get_knowledge_graph(department=target_dept)

@alias_router.post("/fire")
async def fire_synapse_alias(payload: FireSynapseRequest):
    """Alias for /api/v1/admin/brain/fire-synapse for client SDKs."""
    return await fire_synapse(payload=payload)

