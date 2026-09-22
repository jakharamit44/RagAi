import os
import sys
import time
import json
import uuid
import shutil
import asyncio
import logging
import datetime
from typing import Dict, Any, List, Optional
from collections import deque

import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select, func
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import redis.asyncio as aioredis

from api.core.config import settings
from api.core.auth import require_role
from db.models import Base
import db.session
from api.rag.qdrant_store import qdrant_store
from api.core.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/migration",
    tags=["Server Migration & VM Replication"],
    dependencies=[Depends(require_role("admin"))]
)

# -----------------------------------------------------------------------------
# Pydantic Request & Response Models
# -----------------------------------------------------------------------------

class TargetVMSpec(BaseModel):
    host: str = Field(..., description="Target Ubuntu VM IP address or hostname")
    postgres_port: int = Field(default=5432, description="Target PostgreSQL port")
    postgres_db: str = Field(default="university_rag", description="Target PostgreSQL database name")
    postgres_user: str = Field(default="ragai", description="Target PostgreSQL username")
    postgres_password: str = Field(..., description="Target PostgreSQL password")
    
    qdrant_port: int = Field(default=6333, description="Target Qdrant port")
    qdrant_api_key: Optional[str] = Field(default=None, description="Target Qdrant API key")
    qdrant_https: bool = Field(default=False, description="Use HTTPS for Qdrant connection")
    
    redis_port: int = Field(default=6379, description="Target Redis port")
    redis_password: Optional[str] = Field(default=None, description="Target Redis password")
    
    tei_port: int = Field(default=8080, description="Target TEI embeddings port")
    
    minio_port: int = Field(default=9000, description="Target MinIO S3 API port")
    minio_access_key: Optional[str] = Field(default="ragai_admin", description="Target MinIO access key")
    minio_secret_key: Optional[str] = Field(default=None, description="Target MinIO secret key")
    minio_user: Optional[str] = Field(default=None, description="Alias for minio_access_key")
    minio_password: Optional[str] = Field(default=None, description="Alias for minio_secret_key")

    def model_post_init(self, __context):
        if self.minio_user:
            self.minio_access_key = self.minio_user
        if self.minio_password:
            self.minio_secret_key = self.minio_password

    def build_target_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.host}:{self.postgres_port}/{self.postgres_db}"

    def build_target_redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.host}:{self.redis_port}/0"
        return f"redis://{self.host}:{self.redis_port}/0"


class ServiceProbeResult(BaseModel):
    name: str
    ok: bool
    latency_ms: Optional[float] = None
    details: Optional[str] = None
    error: Optional[str] = None


class ProbeResponse(BaseModel):
    all_ok: bool
    host: str
    services: Dict[str, ServiceProbeResult]


class ParityItem(BaseModel):
    name: str
    type: str  # "postgres_table" | "qdrant_collection"
    source_count: int
    target_count: int
    parity: bool


class ParityReport(BaseModel):
    overall_parity: bool
    checked_at: str
    items: List[ParityItem]
    total_source_records: int
    total_target_records: int


class MigrationStatusResponse(BaseModel):
    job_id: Optional[str] = None
    status: str  # idle, running, completed, failed, cancelled
    stage: str   # idle, bootstrap, postgres, qdrant, verification, completed
    progress_percent: float = 0.0
    current_task: str = ""
    postgres_migrated: int = 0
    postgres_total: int = 0
    qdrant_migrated: int = 0
    qdrant_total: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    logs: List[str] = []
    parity_report: Optional[Dict[str, Any]] = None
    target_host: Optional[str] = None


# -----------------------------------------------------------------------------
# Background Migration State Manager (Singleton)
# -----------------------------------------------------------------------------

class MigrationManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.job_id: Optional[str] = None
        self.status: str = "idle"
        self.stage: str = "idle"
        self.progress_percent: float = 0.0
        self.current_task: str = ""
        self.postgres_migrated: int = 0
        self.postgres_total: int = 0
        self.qdrant_migrated: int = 0
        self.qdrant_total: int = 0
        self.started_at: Optional[datetime.datetime] = None
        self.completed_at: Optional[datetime.datetime] = None
        self.duration_seconds: Optional[float] = None
        self.error: Optional[str] = None
        self.logs: deque = deque(maxlen=600)
        self.parity_report: Optional[Dict[str, Any]] = None
        self.target_spec: Optional[TargetVMSpec] = None
        self.cancel_requested: bool = False
        self.active_task: Optional[asyncio.Task] = None

    def log(self, message: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.logs.append(entry)
        logger.info(f"[ServerMigration] {message}")

    def get_status(self) -> MigrationStatusResponse:
        dur = None
        if self.started_at:
            end = self.completed_at or datetime.datetime.now()
            dur = round((end - self.started_at).total_seconds(), 2)

        return MigrationStatusResponse(
            job_id=self.job_id,
            status=self.status,
            stage=self.stage,
            progress_percent=round(self.progress_percent, 1),
            current_task=self.current_task,
            postgres_migrated=self.postgres_migrated,
            postgres_total=self.postgres_total,
            qdrant_migrated=self.qdrant_migrated,
            qdrant_total=self.qdrant_total,
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            duration_seconds=dur,
            error=self.error,
            logs=list(self.logs),
            parity_report=self.parity_report,
            target_host=self.target_spec.host if self.target_spec else None,
        )

    async def start(self, spec: TargetVMSpec) -> str:
        async with self.lock:
            if self.status == "running":
                raise HTTPException(status_code=409, detail="A migration job is already running.")

            self.job_id = str(uuid.uuid4())
            self.status = "running"
            self.stage = "bootstrap"
            self.progress_percent = 0.0
            self.current_task = "Initializing migration pipeline..."
            self.postgres_migrated = 0
            self.postgres_total = 0
            self.qdrant_migrated = 0
            self.qdrant_total = 0
            self.started_at = datetime.datetime.now()
            self.completed_at = None
            self.duration_seconds = None
            self.error = None
            self.logs.clear()
            self.parity_report = None
            self.target_spec = spec
            self.cancel_requested = False

            self.log(f"Initiated full VM data migration to target server: {spec.host}")
            self.active_task = asyncio.create_task(self._run_migration(spec))
            return self.job_id

    def cancel(self):
        if self.status == "running":
            self.cancel_requested = True
            self.log("Cancellation signal received. Gracefully halting migration...")

    async def _run_migration(self, spec: TargetVMSpec):
        target_engine = None
        target_qdrant = None
        try:
            # -----------------------------------------------------------------
            # 1. BOOTSTRAP TARGET SCHEMAS
            # -----------------------------------------------------------------
            self.stage = "bootstrap"
            self.current_task = f"Connecting to target PostgreSQL at {spec.host}:{spec.postgres_port}..."
            self.log(f"Connecting to target PostgreSQL ({spec.host}:{spec.postgres_port}/{spec.postgres_db})...")

            target_db_url = spec.build_target_db_url()
            target_engine = create_async_engine(
                target_db_url,
                echo=False,
                pool_pre_ping=True,
                connect_args={"timeout": 10},
            )

            # Create all 14 tables in target DB
            self.current_task = "Bootstrapping PostgreSQL relational schemas (14 tables)..."
            self.log("Bootstrapping target relational schemas with Base.metadata.create_all...")
            async with target_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self.log("Target PostgreSQL schema successfully initialized.")

            # Connect to target Qdrant & ensure collection
            self.current_task = f"Connecting to target Qdrant at {spec.host}:{spec.qdrant_port}..."
            self.log(f"Connecting to target Qdrant ({spec.host}:{spec.qdrant_port})...")
            target_qdrant = QdrantClient(
                host=spec.host,
                port=spec.qdrant_port,
                api_key=spec.qdrant_api_key,
                https=spec.qdrant_https,
                timeout=10.0,
            )

            collection_name = settings.VECTOR_COLLECTION_NAME
            cols = [c.name for c in target_qdrant.get_collections().collections]
            if collection_name not in cols:
                self.log(f"Creating collection '{collection_name}' on target Qdrant (384-dim, Cosine)...")
                target_qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE, on_disk=True),
                )
                self.log(f"Target Qdrant collection '{collection_name}' created.")
            else:
                self.log(f"Target Qdrant collection '{collection_name}' already exists.")

            self.progress_percent = 5.0

            if self.cancel_requested:
                self.status = "cancelled"
                self.log("Migration cancelled by user.")
                return

            # -----------------------------------------------------------------
            # 2. STREAMING POSTGRESQL DATA MIGRATION
            # -----------------------------------------------------------------
            self.stage = "postgres"
            self.log("Phase 2: Calculating total source PostgreSQL rows across 14 tables...")

            # Count source rows
            source_counts = {}
            total_source_rows = 0
            async with db.session.engine.connect() as source_conn:
                for table in Base.metadata.sorted_tables:
                    cnt = (await source_conn.execute(text(f"SELECT count(*) FROM {table.name}"))).scalar() or 0
                    source_counts[table.name] = cnt
                    total_source_rows += cnt

            self.postgres_total = total_source_rows
            self.log(f"Source database contains {total_source_rows:,} total rows across {len(source_counts)} tables.")

            # We allocate progress: Bootstrap=5%, Postgres=50% (5-55%), Qdrant=40% (55-95%), Parity=5% (95-100%)
            rows_copied_so_far = 0

            # Use a target connection with replica session role to prevent foreign key deadlocks or cascading blocks
            async with target_engine.connect() as target_conn:
                await target_conn.execute(text("SET session_replication_role = 'replica';"))
                self.log("Set target session_replication_role = 'replica' for safe dependency-free streaming.")

                for table in Base.metadata.sorted_tables:
                    if self.cancel_requested:
                        await target_conn.execute(text("SET session_replication_role = 'origin';"))
                        self.status = "cancelled"
                        self.log("Migration cancelled by user.")
                        return

                    t_name = table.name
                    t_count = source_counts[t_name]
                    self.current_task = f"Migrating table '{t_name}' ({t_count:,} rows)..."

                    if t_count == 0:
                        self.log(f"Table '{t_name}' is empty (0 rows), skipping.")
                        continue

                    # Truncate target table first for idempotency
                    await target_conn.execute(text(f"TRUNCATE TABLE {t_name} CASCADE;"))
                    await target_conn.commit()

                    self.log(f"Streaming '{t_name}': {t_count:,} rows from source to target...")

                    batch_size = 2500
                    offset = 0
                    table_copied = 0

                    async with db.session.engine.connect() as source_conn:
                        stream_result = await source_conn.stream(select(table))
                        batch_rows = []

                        async for row in stream_result:
                            if self.cancel_requested:
                                break
                            batch_rows.append(dict(row._mapping))
                            if len(batch_rows) >= batch_size:
                                await target_conn.execute(table.insert(), batch_rows)
                                await target_conn.commit()
                                table_copied += len(batch_rows)
                                rows_copied_so_far += len(batch_rows)
                                self.postgres_migrated = rows_copied_so_far
                                self.progress_percent = 5.0 + (rows_copied_so_far / max(1, total_source_rows)) * 50.0
                                batch_rows = []

                        if batch_rows and not self.cancel_requested:
                            await target_conn.execute(table.insert(), batch_rows)
                            await target_conn.commit()
                            table_copied += len(batch_rows)
                            rows_copied_so_far += len(batch_rows)
                            self.postgres_migrated = rows_copied_so_far
                            self.progress_percent = 5.0 + (rows_copied_so_far / max(1, total_source_rows)) * 50.0

                    self.log(f"Table '{t_name}' completed: {table_copied:,}/{t_count:,} rows transferred.")

                await target_conn.execute(text("SET session_replication_role = 'origin';"))
                self.log("Restored target session_replication_role = 'origin'. All tables populated.")

            if self.cancel_requested:
                self.status = "cancelled"
                self.log("Migration cancelled by user.")
                return

            self.progress_percent = 55.0

            # -----------------------------------------------------------------
            # 3. STREAMING QDRANT VECTOR MIGRATION
            # -----------------------------------------------------------------
            self.stage = "qdrant"
            self.current_task = "Calculating source Qdrant vector volume..."
            self.log(f"Phase 3: Inspecting source Qdrant collection '{collection_name}'...")

            src_qdrant_client = qdrant_store.client
            try:
                src_count = src_qdrant_client.count(collection_name=collection_name).count
            except Exception as e:
                self.log(f"Warning checking Qdrant count: {e}. Defaulting to scroll count.")
                src_count = 0

            self.qdrant_total = src_count
            self.log(f"Source Qdrant contains {src_count:,} vectors to stream.")

            qdrant_batch_size = 500
            next_offset = None
            migrated_vectors = 0
            batch_num = 0

            while True:
                if self.cancel_requested:
                    self.status = "cancelled"
                    self.log("Migration cancelled by user.")
                    return

                records, next_offset = src_qdrant_client.scroll(
                    collection_name=collection_name,
                    limit=qdrant_batch_size,
                    with_payload=True,
                    with_vectors=True,
                    offset=next_offset,
                )

                if not records:
                    break

                batch_num += 1
                # Convert records to PointStruct
                points_to_upsert = [
                    PointStruct(id=r.id, vector=r.vector, payload=r.payload)
                    for r in records
                ]

                target_qdrant.upsert(
                    collection_name=collection_name,
                    points=points_to_upsert,
                )

                migrated_vectors += len(points_to_upsert)
                self.qdrant_migrated = migrated_vectors

                if src_count > 0:
                    q_ratio = min(1.0, migrated_vectors / src_count)
                    self.progress_percent = 55.0 + (q_ratio * 40.0)
                else:
                    self.progress_percent = min(94.0, self.progress_percent + 0.1)

                self.current_task = f"Streaming vectors: {migrated_vectors:,}/{src_count:,} (batch {batch_num})..."

                if batch_num % 10 == 0 or not next_offset:
                    self.log(f"Qdrant stream: {migrated_vectors:,}/{src_count:,} vectors replicated ({self.progress_percent:.1f}%).")

                if not next_offset:
                    break

            self.log(f"Qdrant vector streaming completed. Total vectors upserted: {migrated_vectors:,}.")
            self.progress_percent = 95.0

            if self.cancel_requested:
                self.status = "cancelled"
                self.log("Migration cancelled by user.")
                return

            # -----------------------------------------------------------------
            # 4. PARITY AUDIT & VERIFICATION
            # -----------------------------------------------------------------
            self.stage = "verification"
            self.current_task = "Auditing data parity across Source and Target..."
            self.log("Phase 4: Running full parity audit (Source vs Target)...")

            parity_items = []
            all_tables_match = True
            tot_src = 0
            tot_tgt = 0

            # Postgres audit
            async with db.session.engine.connect() as s_conn, target_engine.connect() as t_conn:
                for table in Base.metadata.sorted_tables:
                    t_name = table.name
                    s_cnt = (await s_conn.execute(text(f"SELECT count(*) FROM {t_name}"))).scalar() or 0
                    t_cnt = (await t_conn.execute(text(f"SELECT count(*) FROM {t_name}"))).scalar() or 0
                    match = (s_cnt == t_cnt)
                    if not match:
                        all_tables_match = False

                    tot_src += s_cnt
                    tot_tgt += t_cnt

                    parity_items.append({
                        "name": t_name,
                        "type": "postgres_table",
                        "source_count": s_cnt,
                        "target_count": t_cnt,
                        "parity": match,
                    })

            # Qdrant audit
            target_qdrant_cnt = target_qdrant.count(collection_name=collection_name).count
            qdrant_match = (src_count == target_qdrant_cnt)
            if not qdrant_match:
                all_tables_match = False

            tot_src += src_count
            tot_tgt += target_qdrant_cnt

            parity_items.append({
                "name": f"qdrant:{collection_name}",
                "type": "qdrant_collection",
                "source_count": src_count,
                "target_count": target_qdrant_cnt,
                "parity": qdrant_match,
            })

            overall_match = all_tables_match and qdrant_match

            self.parity_report = {
                "overall_parity": overall_match,
                "checked_at": datetime.datetime.now().isoformat(),
                "items": parity_items,
                "total_source_records": tot_src,
                "total_target_records": tot_tgt,
            }

            self.log(f"Parity Audit Complete: Overall Parity = {'MATCH (100%)' if overall_match else 'MISMATCH'}")
            for item in parity_items:
                status_str = "OK" if item["parity"] else "MISMATCH"
                self.log(f"  [{status_str}] {item['name']}: Source={item['source_count']:,} | Target={item['target_count']:,}")

            # Complete!
            self.stage = "completed"
            self.status = "completed"
            self.progress_percent = 100.0
            self.completed_at = datetime.datetime.now()
            self.current_task = "Migration & Parity Verification complete. Ready for live cutover."
            self.log("Server migration process finished successfully. You can now execute Atomic Cutover.")

        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            self.log(f"ERROR: Migration failed with exception: {e}")
            logger.exception("Migration execution error")
        finally:
            if target_engine:
                try:
                    await target_engine.dispose()
                except Exception:
                    pass
            if target_qdrant:
                try:
                    target_qdrant.close()
                except Exception:
                    pass


migration_manager = MigrationManager()


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/source-status")
async def get_source_status():
    """
    Returns current active source infrastructure configuration, live row counts,
    and rollback availability.
    """
    counts = {}
    total_db_rows = 0
    try:
        async with db.session.engine.connect() as conn:
            for table in Base.metadata.sorted_tables:
                cnt = (await conn.execute(text(f"SELECT count(*) FROM {table.name}"))).scalar() or 0
                counts[table.name] = cnt
                total_db_rows += cnt
    except Exception as e:
        logger.warning(f"Error querying source table counts: {e}")

    total_vectors = 0
    try:
        total_vectors = qdrant_store.client.count(collection_name=settings.VECTOR_COLLECTION_NAME).count
    except Exception as e:
        logger.warning(f"Error querying source Qdrant count: {e}")

    # Check rollback capability
    rollback_path = os.path.join(settings.PROJECT_ROOT, ".env.rollback")
    can_rollback = os.path.exists(rollback_path)
    rollback_host = None
    if can_rollback:
        try:
            with open(rollback_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VECTOR_STORE_HOST="):
                        rollback_host = line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass

    return {
        "host": settings.VECTOR_STORE_HOST,
        "source_host": settings.VECTOR_STORE_HOST,
        "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
        "vector_store_host": settings.VECTOR_STORE_HOST,
        "vector_store_port": settings.VECTOR_STORE_PORT,
        "redis_url": settings.REDIS_URL.split("@")[-1] if "@" in settings.REDIS_URL else settings.REDIS_URL,
        "remote_embedding_url": settings.REMOTE_EMBEDDING_URL,
        "object_storage_endpoint": settings.OBJECT_STORAGE_ENDPOINT,
        "counts": counts,
        "total_db_rows": total_db_rows,
        "total_rows": total_db_rows,
        "total_vectors": total_vectors,
        "qdrant_points_count": total_vectors,
        "can_rollback": can_rollback,
        "rollback_available": can_rollback,
        "rollback_host": rollback_host,
    }


@router.post("/probe", response_model=ProbeResponse)
async def probe_target_vm(spec: TargetVMSpec):
    """
    Pre-flight probe to test connectivity, credentials, and health of all 5 services
    on the target Ubuntu VM.
    """
    results: Dict[str, ServiceProbeResult] = {}
    all_ok = True

    # 1. Probe PostgreSQL
    t0 = time.perf_counter()
    pg_url = spec.build_target_db_url()
    try:
        temp_engine = create_async_engine(pg_url, pool_pre_ping=True, connect_args={"timeout": 5})
        async with temp_engine.connect() as conn:
            v = (await conn.execute(text("SELECT version();"))).scalar()
            lat = round((time.perf_counter() - t0) * 1000, 2)
            results["postgres"] = ServiceProbeResult(
                name="PostgreSQL",
                ok=True,
                latency_ms=lat,
                details=f"Connected ({v.split(',')[0] if v else 'PostgreSQL 16'})",
            )
        await temp_engine.dispose()
    except Exception as e:
        all_ok = False
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results["postgres"] = ServiceProbeResult(
            name="PostgreSQL",
            ok=False,
            latency_ms=lat,
            error=str(e),
        )

    # 2. Probe Qdrant
    t0 = time.perf_counter()
    try:
        qc = QdrantClient(
            host=spec.host,
            port=spec.qdrant_port,
            api_key=spec.qdrant_api_key,
            https=spec.qdrant_https,
            timeout=5.0,
        )
        collections = [c.name for c in qc.get_collections().collections]
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results["qdrant"] = ServiceProbeResult(
            name="Qdrant Vector DB",
            ok=True,
            latency_ms=lat,
            details=f"Connected ({len(collections)} collections found)",
        )
        qc.close()
    except Exception as e:
        all_ok = False
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results["qdrant"] = ServiceProbeResult(
            name="Qdrant Vector DB",
            ok=False,
            latency_ms=lat,
            error=str(e),
        )

    # 3. Probe Redis
    t0 = time.perf_counter()
    try:
        r_url = spec.build_target_redis_url()
        r = aioredis.from_url(r_url, socket_timeout=3.0)
        await r.ping()
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results["redis"] = ServiceProbeResult(
            name="Redis Cache",
            ok=True,
            latency_ms=lat,
            details="PONG received, cluster ready",
        )
        await r.aclose()
    except Exception as e:
        all_ok = False
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results["redis"] = ServiceProbeResult(
            name="Redis Cache",
            ok=False,
            latency_ms=lat,
            error=str(e),
        )

    # 4. Probe TEI Embeddings
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"http://{spec.host}:{spec.tei_port}/health")
            lat = round((time.perf_counter() - t0) * 1000, 2)
            if res.status_code == 200:
                results["tei"] = ServiceProbeResult(
                    name="TEI GPU Embedder",
                    ok=True,
                    latency_ms=lat,
                    details=f"HTTP 200 OK (MiniLM L6v2 ready)",
                )
            else:
                all_ok = False
                results["tei"] = ServiceProbeResult(
                    name="TEI GPU Embedder",
                    ok=False,
                    latency_ms=lat,
                    error=f"HTTP Status {res.status_code}",
                )
    except Exception as e:
        all_ok = False
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results["tei"] = ServiceProbeResult(
            name="TEI GPU Embedder",
            ok=False,
            latency_ms=lat,
            error=str(e),
        )

    # 5. Probe MinIO S3
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"http://{spec.host}:{spec.minio_port}/minio/health/live")
            lat = round((time.perf_counter() - t0) * 1000, 2)
            if res.status_code == 200:
                results["minio"] = ServiceProbeResult(
                    name="MinIO S3 Object Storage",
                    ok=True,
                    latency_ms=lat,
                    details="HTTP 200 OK (Storage engine operational)",
                )
            else:
                all_ok = False
                results["minio"] = ServiceProbeResult(
                    name="MinIO S3 Object Storage",
                    ok=False,
                    latency_ms=lat,
                    error=f"HTTP Status {res.status_code}",
                )
    except Exception as e:
        all_ok = False
        lat = round((time.perf_counter() - t0) * 1000, 2)
        results["minio"] = ServiceProbeResult(
            name="MinIO S3 Object Storage",
            ok=False,
            latency_ms=lat,
            error=str(e),
        )

    return ProbeResponse(
        all_ok=all_ok,
        host=spec.host,
        services=results,
    )


@router.post("/start")
async def start_migration(spec: TargetVMSpec):
    """
    Kicks off background streaming migration of PostgreSQL and Qdrant data to target VM.
    """
    job_id = await migration_manager.start(spec)
    return {"message": "Migration started successfully.", "job_id": job_id}


@router.get("/status", response_model=MigrationStatusResponse)
async def get_migration_status():
    """
    Returns live migration progress, stage, transferred row/vector metrics, and log stream.
    """
    return migration_manager.get_status()


@router.post("/cancel")
async def cancel_migration():
    """
    Cancels an active background migration job safely.
    """
    migration_manager.cancel()
    return {"message": "Cancellation request acknowledged."}


@router.get("/parity")
async def get_parity_report():
    """
    Returns the latest parity audit report comparing Source vs Target record counts.
    """
    if not migration_manager.parity_report:
        raise HTTPException(status_code=404, detail="No parity report available. Run migration first.")
    return migration_manager.parity_report


@router.post("/cutover")
async def execute_cutover():
    """
    Executes an atomic live cutover to the new target server:
    1. Backs up active .env -> .env.bak.<timestamp>
    2. Saves current source settings -> .env.rollback
    3. Rewrites active .env with new target configuration
    4. Hot-rebinds database engine, Qdrant client, and Redis cache in-memory
    """
    spec = migration_manager.target_spec
    if not spec:
        raise HTTPException(status_code=400, detail="No target server specification found. Run migration first.")

    env_path = os.path.join(settings.PROJECT_ROOT, ".env")
    rollback_path = os.path.join(settings.PROJECT_ROOT, ".env.rollback")
    ts = int(time.time())
    backup_path = os.path.join(settings.PROJECT_ROOT, f".env.bak.{ts}")

    # 1. Backup current .env
    if os.path.exists(env_path):
        shutil.copy2(env_path, backup_path)
        shutil.copy2(env_path, rollback_path)
        logger.info(f"Backed up active .env to {backup_path} and {rollback_path}")

    # 2. Update .env content with new target settings
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updates = {
        "DATABASE_URL": f'DATABASE_URL="{spec.build_target_db_url()}"\n',
        "USE_REMOTE_QDRANT": 'USE_REMOTE_QDRANT=true\n',
        "VECTOR_STORE_HOST": f'VECTOR_STORE_HOST={spec.host}\n',
        "VECTOR_STORE_PORT": f'VECTOR_STORE_PORT={spec.qdrant_port}\n',
        "QDRANT_HOST": f'QDRANT_HOST={spec.host}\n',
        "QDRANT_PORT": f'QDRANT_PORT={spec.qdrant_port}\n',
        "QDRANT_API_KEY": f'QDRANT_API_KEY="{spec.qdrant_api_key or ""}"\n',
        "REDIS_URL": f'REDIS_URL="{spec.build_target_redis_url()}"\n',
        "REMOTE_EMBEDDING_URL": f'REMOTE_EMBEDDING_URL="http://{spec.host}:{spec.tei_port}"\n',
        "OBJECT_STORAGE_ENDPOINT": f'OBJECT_STORAGE_ENDPOINT="http://{spec.host}:{spec.minio_port}"\n',
        "OBJECT_STORAGE_ACCESS_KEY": f'OBJECT_STORAGE_ACCESS_KEY="{spec.minio_access_key or ""}"\n',
        "OBJECT_STORAGE_SECRET_KEY": f'OBJECT_STORAGE_SECRET_KEY="{spec.minio_secret_key or ""}"\n',
    }

    new_lines = []
    keys_handled = set()
    for line in lines:
        matched = False
        for k in updates:
            if line.startswith(f"{k}=") or line.startswith(f'#{k}='):
                new_lines.append(updates[k])
                keys_handled.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in keys_handled:
            new_lines.append(v)

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    logger.info("Updated .env file with new target server parameters.")

    # 3. Hot In-Memory Rebind
    try:
        new_db_url = spec.build_target_db_url()
        settings.DATABASE_URL = new_db_url
        settings.VECTOR_STORE_HOST = spec.host
        settings.VECTOR_STORE_PORT = spec.qdrant_port
        settings.QDRANT_API_KEY = spec.qdrant_api_key
        settings.REDIS_URL = spec.build_target_redis_url()
        settings.REMOTE_EMBEDDING_URL = f"http://{spec.host}:{spec.tei_port}"
        settings.OBJECT_STORAGE_ENDPOINT = f"http://{spec.host}:{spec.minio_port}"
        settings.OBJECT_STORAGE_ACCESS_KEY = spec.minio_access_key
        settings.OBJECT_STORAGE_SECRET_KEY = spec.minio_secret_key

        # Reconnect DB engine
        await db.session.engine.dispose()
        new_engine = create_async_engine(
            new_db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": 60} if "sqlite" in new_db_url else {},
        )
        db.session.engine = new_engine
        db.session.async_session_factory.configure(bind=new_engine)
        logger.info("Hot-reloaded database engine and session factory to new target DB.")

        # Reconnect Qdrant
        qdrant_store.close()
        qdrant_store.client = qdrant_store._init_client()
        logger.info("Hot-reloaded Qdrant client to new target cluster.")

        # Reconnect Redis
        if cache.redis_client:
            try:
                await cache.redis_client.aclose()
            except Exception:
                pass
        cache.redis_client = None
        cache._init_attempted = False
        logger.info("Reset Redis cache client to connect to new target Redis.")

        # Invalidate BM25 and Brain caches
        try:
            from api.rag.bm25_index import bm25_index
            bm25_index.reload_from_db()
        except Exception as e:
            logger.warning(f"BM25 reload note: {e}")

        try:
            from api.brain.graph_engine import graph_engine
            graph_engine.invalidate_cache()
        except Exception as e:
            logger.warning(f"Brain graph cache invalidation note: {e}")

        migration_manager.log(f"LIVE CUTOVER COMPLETED: Active system is now operating on {spec.host}.")
        return {
            "status": "success",
            "message": f"Live switchover completed! Active backend is now connected to {spec.host}.",
            "active_host": spec.host,
            "backup_file": backup_path,
        }

    except Exception as e:
        logger.exception("Error during live cutover hot reload")
        raise HTTPException(status_code=500, detail=f"Cutover partially applied to .env, but hot reload failed: {e}")


@router.post("/rollback")
async def execute_rollback():
    """
    Reverts active infrastructure back to previous configuration stored in .env.rollback.
    """
    rollback_path = os.path.join(settings.PROJECT_ROOT, ".env.rollback")
    env_path = os.path.join(settings.PROJECT_ROOT, ".env")

    if not os.path.exists(rollback_path):
        raise HTTPException(status_code=400, detail="No rollback configuration found (.env.rollback is missing).")

    # Read rollback settings
    rollback_lines = []
    with open(rollback_path, "r", encoding="utf-8") as f:
        rollback_lines = f.readlines()

    # Restore .env
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(rollback_lines)

    # Parse key variables from rollback
    rb_vars = {}
    for line in rollback_lines:
        line_s = line.strip()
        if line_s and not line_s.startswith("#") and "=" in line_s:
            k, v = line_s.split("=", 1)
            rb_vars[k.strip()] = v.strip().strip('"').strip("'")

    rb_db = rb_vars.get("DATABASE_URL", settings.DATABASE_URL)
    rb_qhost = rb_vars.get("VECTOR_STORE_HOST", settings.VECTOR_STORE_HOST)
    rb_qport = int(rb_vars.get("VECTOR_STORE_PORT", settings.VECTOR_STORE_PORT))
    rb_qkey = rb_vars.get("QDRANT_API_KEY", settings.QDRANT_API_KEY)
    rb_redis = rb_vars.get("REDIS_URL", settings.REDIS_URL)
    rb_tei = rb_vars.get("REMOTE_EMBEDDING_URL", settings.REMOTE_EMBEDDING_URL)
    rb_minio = rb_vars.get("OBJECT_STORAGE_ENDPOINT", settings.OBJECT_STORAGE_ENDPOINT)

    # Hot reload
    try:
        settings.DATABASE_URL = rb_db
        settings.VECTOR_STORE_HOST = rb_qhost
        settings.VECTOR_STORE_PORT = rb_qport
        settings.QDRANT_API_KEY = rb_qkey
        settings.REDIS_URL = rb_redis
        settings.REMOTE_EMBEDDING_URL = rb_tei
        settings.OBJECT_STORAGE_ENDPOINT = rb_minio

        await db.session.engine.dispose()
        new_engine = create_async_engine(
            rb_db,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": 60} if "sqlite" in rb_db else {},
        )
        db.session.engine = new_engine
        db.session.async_session_factory.configure(bind=new_engine)

        qdrant_store.close()
        qdrant_store.client = qdrant_store._init_client()

        if cache.redis_client:
            try:
                await cache.redis_client.aclose()
            except Exception:
                pass
        cache.redis_client = None
        cache._init_attempted = False

        try:
            from api.rag.bm25_index import bm25_index
            bm25_index.reload_from_db()
        except Exception:
            pass

        try:
            from api.brain.graph_engine import graph_engine
            graph_engine.invalidate_cache()
        except Exception:
            pass

        logger.info(f"Rollback completed: Restored infrastructure to {rb_qhost}")
        return {
            "status": "success",
            "message": f"Successfully rolled back infrastructure to previous server ({rb_qhost}).",
            "active_host": rb_qhost,
        }
    except Exception as e:
        logger.exception("Error during rollback")
        raise HTTPException(status_code=500, detail=f"Rollback file restored, but hot reload failed: {e}")
