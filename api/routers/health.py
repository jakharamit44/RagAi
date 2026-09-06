from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, func, text
from api.core.config import settings
from api.rag.qdrant_store import qdrant_store
from db.session import async_session_factory
from db.models import Document

router = APIRouter(tags=["Health & Monitoring"])

from typing import Dict, Any, List, Optional
from db.models import Document, Chunk, ManifestEntry
from api.core.cuda_init import get_gpu_status

class HardwareTelemetry(BaseModel):
    gpu_available: bool = False
    gpu_name: str = "CPU Mode"
    memory_total_mb: int = 0
    memory_used_mb: int = 0
    memory_free_mb: int = 0
    vram_usage_pct: float = 0.0
    gpu_utilization_pct: int = 0
    driver_version: str = "N/A"
    cuda_version: str = "N/A"
    onnx_providers: List[str] = []
    active_acceleration: str = "CPU Fallback"
    is_cuda_active: bool = False

class PipelineTelemetry(BaseModel):
    files_done: int = 0
    files_left: int = 0
    files_failed: int = 0
    files_skipped_duplicate: int = 0
    total_manifest_records: int = 0
    total_documents: int = 0
    total_chunks: int = 0
    document_breakdown: Dict[str, int] = {"born_digital": 0, "scanned": 0, "handwritten": 0}

import os
import shutil

class StorageTelemetry(BaseModel):
    database_size_mb: float = 0.0
    db_size_mb: float = 0.0
    vector_store_size_mb: float = 0.0
    uploads_size_mb: float = 0.0
    models_cache_mb: float = 0.0
    total_rag_storage_mb: float = 0.0
    disk_free_gb: float = 0.0
    host_disk_free_gb: float = 0.0
    disk_total_gb: float = 0.0
    host_disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_usage_pct: float = 0.0
    host_disk_free_pct: float = 0.0
    host_drive: str = "D:"

def get_dir_size_mb(path: str) -> float:
    if not os.path.exists(path):
        return 0.0
    total_bytes = 0
    try:
        if os.path.isfile(path):
            return round(os.path.getsize(path) / (1024 * 1024), 2)
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_bytes += os.path.getsize(fp)
                except Exception:
                    pass
    except Exception:
        pass
    return round(total_bytes / (1024 * 1024), 2)

import time

_STORAGE_TELEMETRY_CACHE = None
_LAST_STORAGE_CACHE_TIME = 0.0
_STORAGE_CACHE_TTL = 60.0  # Cache storage calculation for 60s to prevent disk thrashing & CPU spikes

def get_storage_telemetry() -> StorageTelemetry:
    global _STORAGE_TELEMETRY_CACHE, _LAST_STORAGE_CACHE_TIME
    now = time.time()
    if _STORAGE_TELEMETRY_CACHE is not None and (now - _LAST_STORAGE_CACHE_TIME) < _STORAGE_CACHE_TTL:
        return _STORAGE_TELEMETRY_CACHE

    db_mb = get_dir_size_mb("university_rag.db")
    vec_mb = get_dir_size_mb("data/qdrant_storage")
    uploads_mb = get_dir_size_mb("data/uploads")
    hf_cache = os.getenv("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    hf_mb = get_dir_size_mb(hf_cache)
    total_rag_mb = round(db_mb + vec_mb + uploads_mb, 2)

    try:
        cwd = os.path.abspath(".")
        total, used, free = shutil.disk_usage(cwd)
        drive_name = os.path.splitdrive(cwd)[0] or "/"
        total_gb = round(total / (1024**3), 1)
        used_gb = round(used / (1024**3), 1)
        free_gb = round(free / (1024**3), 1)
        usage_pct = round((used / total) * 100, 1) if total > 0 else 0.0
        free_pct = round((free / total) * 100, 1) if total > 0 else 0.0
    except Exception:
        drive_name = "N/A"
        total_gb, used_gb, free_gb, usage_pct, free_pct = 0.0, 0.0, 0.0, 0.0, 0.0

    res = StorageTelemetry(
        database_size_mb=db_mb,
        db_size_mb=db_mb,
        vector_store_size_mb=vec_mb,
        uploads_size_mb=uploads_mb,
        models_cache_mb=hf_mb,
        total_rag_storage_mb=total_rag_mb,
        disk_free_gb=free_gb,
        host_disk_free_gb=free_gb,
        disk_total_gb=total_gb,
        host_disk_total_gb=total_gb,
        disk_used_gb=used_gb,
        disk_usage_pct=usage_pct,
        host_disk_free_pct=free_pct,
        host_drive=drive_name
    )
    _STORAGE_TELEMETRY_CACHE = res
    _LAST_STORAGE_CACHE_TIME = now
    return res

class HealthResponse(BaseModel):
    """Reference: Appendix B (Table 26) with extended hardware & pipeline fields."""
    status: str
    database: bool
    vector_store: bool
    llm_backend: str
    documents_indexed: int
    chunks_indexed: int = 0
    hardware: Optional[HardwareTelemetry] = None
    pipeline: Optional[PipelineTelemetry] = None
    storage: Optional[StorageTelemetry] = None

class FullRagStatusResponse(BaseModel):
    status: str
    database: bool
    vector_store: bool
    llm_model: str
    llm_backend: str
    hardware: HardwareTelemetry
    pipeline: PipelineTelemetry
    storage: StorageTelemetry

@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe: returns 200 immediately if process event loop is active."""
    return {"status": "alive", "timestamp": time.time()}

@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe: verifies core operational dependencies (DB & Vector Store)."""
    db_ok = True
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    vector_ok = True
    try:
        colls = qdrant_store.client.get_collections().collections
        vector_ok = any(c.name == qdrant_store.collection_name for c in colls)
    except Exception:
        vector_ok = False

    is_ready = db_ok and vector_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = {
        "status": "ready" if is_ready else "not_ready",
        "database": db_ok,
        "vector_store": vector_ok,
        "llm_model": settings.DEFAULT_LLM_MODEL,
        "timestamp": time.time(),
    }
    return JSONResponse(status_code=status_code, content=payload)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Liveness & readiness health probe verifying DB, Vector Store, LLM, and GPU."""
    db_ok = True
    doc_count = 0
    chunk_count = 0
    try:
        async with async_session_factory() as session:
            doc_res = await session.execute(select(func.count(Document.id)))
            doc_count = doc_res.scalar() or 0
            chunk_res = await session.execute(select(func.count(Chunk.id)))
            chunk_count = chunk_res.scalar() or 0
    except Exception:
        db_ok = False

    vector_ok = True
    try:
        colls = qdrant_store.client.get_collections().collections
        vector_ok = any(c.name == qdrant_store.collection_name for c in colls)
    except Exception:
        vector_ok = False

    llm_backend = "hosted" if settings.ENABLE_HOSTED_FALLBACK else "local"
    overall_status = "ok" if (db_ok and vector_ok) else "degraded"

    # Hardware stats
    raw_hw = get_gpu_status()
    vram_tot = raw_hw.get("memory_total_mb") or 0
    vram_usd = raw_hw.get("memory_used_mb") or 0
    vram_pct = round((vram_usd / vram_tot * 100), 1) if vram_tot > 0 else 0.0

    hw_telemetry = HardwareTelemetry(
        gpu_available=raw_hw.get("gpu_available", False),
        gpu_name=raw_hw.get("gpu_name", "CPU Mode"),
        memory_total_mb=vram_tot,
        memory_used_mb=vram_usd,
        memory_free_mb=raw_hw.get("memory_free_mb", 0),
        vram_usage_pct=vram_pct,
        gpu_utilization_pct=raw_hw.get("gpu_utilization_pct", 0),
        driver_version=raw_hw.get("driver_version", "N/A"),
        cuda_version=raw_hw.get("cuda_version", "N/A"),
        onnx_providers=raw_hw.get("onnx_providers", []),
        active_acceleration=raw_hw.get("active_acceleration", "CPU Fallback"),
        is_cuda_active=raw_hw.get("is_cuda_active", False)
    )

    return HealthResponse(
        status=overall_status,
        database=db_ok,
        vector_store=vector_ok,
        llm_backend=llm_backend,
        documents_indexed=doc_count,
        chunks_indexed=chunk_count,
        hardware=hw_telemetry,
        storage=get_storage_telemetry()
    )

@router.get("/api/v1/admin/rag/status", response_model=FullRagStatusResponse)
async def get_full_rag_status():
    """
    Comprehensive live status of the RAG system for Admin Control Center:
    - Files done, left in queue, failed, duplicate bypassed
    - Document breakdown (Born-Digital, Scanned, Handwritten)
    - Total chunks and vector DB health
    - Live GPU VRAM metrics, utilization, and CUDA execution provider
    """
    db_ok = True
    doc_count = 0
    chunk_count = 0
    manifest_counts = {"done": 0, "pending": 0, "processing": 0, "failed": 0, "skipped_duplicate": 0}
    doc_breakdown = {"born_digital": 0, "scanned": 0, "handwritten": 0}

    try:
        async with async_session_factory() as session:
            # Document counts
            doc_res = await session.execute(select(func.count(Document.id)))
            doc_count = doc_res.scalar() or 0

            chunk_res = await session.execute(select(func.count(Chunk.id)))
            chunk_count = chunk_res.scalar() or 0

            # Manifest status breakdown
            man_stmt = select(ManifestEntry.status, func.count(ManifestEntry.id)).group_by(ManifestEntry.status)
            man_rows = (await session.execute(man_stmt)).all()
            for st, cnt in man_rows:
                manifest_counts[st] = cnt

            # Document category breakdown
            cat_stmt = select(Document.doc_type, func.count(Document.id)).group_by(Document.doc_type)
            cat_rows = (await session.execute(cat_stmt)).all()
            for ct, cnt in cat_rows:
                doc_breakdown[ct] = cnt
    except Exception:
        db_ok = False

    vector_ok = True
    try:
        colls = qdrant_store.client.get_collections().collections
        vector_ok = any(c.name == qdrant_store.collection_name for c in colls)
    except Exception:
        vector_ok = False

    raw_hw = get_gpu_status()
    vram_tot = raw_hw.get("memory_total_mb") or 0
    vram_usd = raw_hw.get("memory_used_mb") or 0
    vram_pct = round((vram_usd / vram_tot * 100), 1) if vram_tot > 0 else 0.0

    files_left = manifest_counts.get("pending", 0) + manifest_counts.get("processing", 0)
    total_manifest = sum(manifest_counts.values())

    pipeline_status = PipelineTelemetry(
        files_done=manifest_counts.get("done", 0),
        files_left=files_left,
        files_failed=manifest_counts.get("failed", 0),
        files_skipped_duplicate=manifest_counts.get("skipped_duplicate", 0),
        total_manifest_records=total_manifest,
        total_documents=doc_count,
        total_chunks=chunk_count,
        document_breakdown=doc_breakdown
    )

    hardware_status = HardwareTelemetry(
        gpu_available=raw_hw.get("gpu_available", False),
        gpu_name=raw_hw.get("gpu_name", "CPU Mode"),
        memory_total_mb=vram_tot,
        memory_used_mb=vram_usd,
        memory_free_mb=raw_hw.get("memory_free_mb", 0),
        vram_usage_pct=vram_pct,
        gpu_utilization_pct=raw_hw.get("gpu_utilization_pct", 0),
        driver_version=raw_hw.get("driver_version", "N/A"),
        cuda_version=raw_hw.get("cuda_version", "N/A"),
        onnx_providers=raw_hw.get("onnx_providers", []),
        active_acceleration=raw_hw.get("active_acceleration", "CPU Fallback"),
        is_cuda_active=raw_hw.get("is_cuda_active", False)
    )

    overall_status = "ok" if (db_ok and vector_ok) else "degraded"
    llm_backend = "hosted" if settings.ENABLE_HOSTED_FALLBACK else "local"

    return FullRagStatusResponse(
        status=overall_status,
        database=db_ok,
        vector_store=vector_ok,
        llm_model=settings.DEFAULT_LLM_MODEL,
        llm_backend=llm_backend,
        hardware=hardware_status,
        pipeline=pipeline_status,
        storage=get_storage_telemetry()
    )

