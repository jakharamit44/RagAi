import os
import sys
import uuid
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func

from api.core.config import settings
from api.core.exceptions import setup_exception_handlers
from api.routers import health_router, ask_router, chat_router, documents_router, auth_router
from api.routers.metrics import router as metrics_router
from api.routers.admin_governance import router as admin_governance_router
from api.routers.scraper import router as scraper_router
from api.routers.brain import router as brain_router, alias_router as brain_alias_router
from api.scraper.scheduler import scraper_scheduler
from db.session import init_db, async_session_factory
from db.models import Chunk, Document
from api.rag.bm25_index import bm25_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("university_rag_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI Lifespan context manager replacing deprecated @app.on_event.
    Handles startup resource preloading and graceful shutdown teardown.
    """
    logger.info("Initializing University RAG API Service...")
    try:
        from api.core.cuda_init import init_cuda_runtime
        init_cuda_runtime()
    except Exception as e:
        logger.warning(f"Could not auto-initialize CUDA runtime: {e}")

    await init_db()

    # Seed default MDU WebScrapeJob if none exists
    try:
        from db.models import WebScrapeJob
        import json
        async with async_session_factory() as session:
            job_cnt = (await session.execute(select(func.count(WebScrapeJob.id)))).scalar() or 0
            if job_cnt == 0:
                default_job = WebScrapeJob(
                    name="MDU Official Portal & Notifications",
                    base_url="https://mdu.ac.in",
                    seed_urls=json.dumps(["https://mdu.ac.in/default.aspx", "https://mdu.ac.in/defaultMatter.aspx?PageId=1"]),
                    allowed_domains="mdu.ac.in",
                    max_depth=2,
                    max_pages=200,
                    crawl_interval_minutes=360,
                    auto_ingest=True,
                    is_active=True,
                    status="idle",
                )
                session.add(default_job)
                await session.commit()
                logger.info("Initialized default MDU WebScrapeJob.")
    except Exception as e:
        logger.warning(f"Default WebScrapeJob init note: {e}")

    # Load dynamic system settings configured from Admin Portal (keeps .env untouched)

    try:
        from db.models import SystemSetting
        async with async_session_factory() as session:
            settings_rows = (await session.execute(select(SystemSetting))).scalars().all()
            for s in settings_rows:
                if s.key == "HF_TOKEN" and s.value:
                    settings.HF_TOKEN = s.value
                    os.environ["HF_TOKEN"] = s.value
                    os.environ["HUGGINGFACE_HUB_TOKEN"] = s.value
            if settings_rows:
                logger.info(f"Loaded {len(settings_rows)} dynamic system settings from database.")
    except Exception as e:
        logger.warning(f"Could not load dynamic system settings from database: {e}")

    # Preload BM25 index from database
    try:
        async with async_session_factory() as session:
            stmt = select(Chunk, Document).join(Document, Chunk.document_id == Document.id)
            rows = (await session.execute(stmt)).all()
            corpus = []
            for c, d in rows:
                corpus.append({
                    "chunk_id": str(c.id),
                    "document_id": str(d.id),
                    "title": d.title,
                    "department": d.department,
                    "semester": d.semester,
                    "course": d.course,
                    "page_number": c.page_number,
                    "section": c.section,
                    "text": c.text,
                })
            bm25_index.build_index(corpus)
            logger.info(f"Loaded {len(corpus)} document chunks into BM25 index on startup.")
    except Exception as e:
        logger.warning(f"Could not preload BM25 index on startup: {e}")

    # Pre-warm AI Embedder, Reranker, and Local Chat models so student queries experience zero first-hit latency
    try:
        from api.rag.embedder import embedder
        from api.rag.reranker import reranker
        from api.rag.chat_generator import chat_generator
        embedder.warmup()
        reranker.warmup()
        chat_generator.warmup()
        logger.info("Local Embedder, Reranker, and Chat Generator pre-warmed and ready on GPU.")
    except Exception as e:
        logger.warning(f"Model pre-warm note: {e}")

    # Purge residual non-academic points from Qdrant vector storage
    try:
        from api.rag.qdrant_store import qdrant_store
        from qdrant_client.models import Filter, FieldCondition, MatchText
        qdrant_store.client.delete(
            collection_name=qdrant_store.collection_name,
            points_selector=Filter(
                should=[
                    FieldCondition(key="title", match=MatchText(text="Enterprise_RAG")),
                    FieldCondition(key="title", match=MatchText(text="test_failed")),
                ]
            ),
            wait=True
        )
        logger.info("Synchronized Qdrant collection: purged residual non-academic vectors.")
    except Exception as e:
        logger.debug(f"Qdrant startup sync note: {e}")

    # Start automated scraper background scheduler
    try:
        scraper_scheduler.start()
    except Exception as e:
        logger.warning(f"Could not start scraper scheduler: {e}")

    logger.info("University RAG API is ready to receive queries.")
    yield
    logger.info("Shutting down University RAG API Service...")
    try:
        scraper_scheduler.stop()
    except Exception as e:
        logger.warning(f"Error stopping scraper scheduler: {e}")

    try:
        from api.rag.qdrant_store import qdrant_store
        qdrant_store.close()
        logger.info("Closed Qdrant vector store connection.")
    except Exception as e:
        logger.warning(f"Error closing Qdrant store: {e}")

    try:
        from db.session import engine
        await engine.dispose()
        logger.info("Disposed database connection pool.")
    except Exception as e:
        logger.warning(f"Error disposing database engine: {e}")

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Released CUDA VRAM cache on shutdown.")
    except Exception:
        pass

app = FastAPI(
    title="Enterprise University RAG System API",
    description="Local-first, high-throughput academic QA and document intelligence platform for university students and faculty.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 1. GZip compression middleware for payloads > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Observability, Tracing, Timing & Security Headers Middleware
@app.middleware("http")
async def observability_and_security_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)

    process_time = time.perf_counter() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"

    # Enterprise security hardening headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; font-src 'self' data: https://cdnjs.cloudflare.com; object-src 'none';"

    return response

# 4. Standardized error handlers (RFC 7807)
setup_exception_handlers(app)

# 5. Static directory setup
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse("/chat")

@app.get("/admin", include_in_schema=False)
async def admin_dashboard():
    return FileResponse(os.path.join(static_dir, "admin.html"))

@app.get("/chat", include_in_schema=False)
async def student_chat():
    return FileResponse(os.path.join(static_dir, "chat.html"))

@app.get("/api/v1/version", tags=["System"])
async def api_version():
    """Returns API runtime version, environment, and system diagnostics."""
    return {
        "service": "Enterprise University RAG System API",
        "version": "1.1.0",
        "status": "operational",
        "environment": "production",
        "python_version": sys.version.split()[0],
        "docs_url": "/docs",
    }

# 6. Include API routers
app.include_router(health_router)
app.include_router(ask_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(auth_router)
app.include_router(metrics_router)
app.include_router(admin_governance_router)
app.include_router(scraper_router)
app.include_router(brain_router)
app.include_router(brain_alias_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
