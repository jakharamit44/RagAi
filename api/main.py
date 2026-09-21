import os
import sys
import uuid
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
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
from api.routers.context import router as context_router
from api.routers.server_migration import router as migration_router
from api.routers.admin_auth import router as admin_auth_router, ensure_initial_superadmin
from api.context.tiered_engine import tiered_engine
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

    print("LIFESPAN: 1. init_db starting...", flush=True)
    await init_db()
    print("LIFESPAN: 1. init_db done!", flush=True)

    try:
        await ensure_initial_superadmin()
    except Exception as e:
        logger.warning(f"Note on initial superadmin setup: {e}")

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

    # Preload BM25 index from database (fast raw SQLite, zero ORM overhead)
    try:
        print("LIFESPAN: 2. BM25 ensure_loaded starting...", flush=True)
        bm25_index.ensure_loaded()
        print(f"LIFESPAN: 2. BM25 loaded with {len(bm25_index.corpus)} chunks!", flush=True)
        logger.info(f"Loaded {len(bm25_index.corpus)} document chunks into BM25 index on startup.")
    except Exception as e:
        logger.warning(f"Could not preload BM25 index on startup: {e}")

    # Pre-warm AI Embedder, Reranker, and Local Chat models so student queries experience zero first-hit latency
    try:
        from api.rag.embedder import embedder
        from api.rag.reranker import reranker
        from api.rag.chat_generator import chat_generator
        print("LIFESPAN: 3. embedder warmup...", flush=True)
        embedder.warmup()
        print("LIFESPAN: 4. reranker warmup...", flush=True)
        reranker.warmup()
        print("LIFESPAN: 5. chat_generator warmup...", flush=True)
        chat_generator.warmup()
        print("LIFESPAN: Models warmup complete!", flush=True)
        logger.info("Local Embedder, Reranker, and Chat Generator pre-warmed and ready on GPU.")
    except Exception as e:
        logger.warning(f"Model pre-warm note: {e}")

    # Start automated scraper background scheduler
    try:
        print("LIFESPAN: 6. scraper_scheduler.start()...", flush=True)
        scraper_scheduler.start()
    except Exception as e:
        logger.warning(f"Could not start scraper scheduler: {e}")

    print("LIFESPAN: 7. All startup complete! Yielding app...", flush=True)
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
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "object-src 'none';"
    )

    return response

# 4. Standardized error handlers (RFC 7807)
setup_exception_handlers(app)

# 5. Static directory setup
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount Admin UI (React production build)
admin_dist_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin-ui", "dist"))
admin_assets_dir = os.path.join(admin_dist_dir, "assets")
if os.path.isdir(admin_assets_dir):
    app.mount("/admin/assets", StaticFiles(directory=admin_assets_dir), name="admin_assets")

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse("/chat")

@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
@app.get("/admin/{full_path:path}", include_in_schema=False)
async def admin_dashboard(full_path: str = ""):
    admin_index = os.path.join(admin_dist_dir, "index.html")
    if os.path.isfile(admin_index):
        return FileResponse(admin_index)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Admin UI build not found. Please compile frontend assets: cd admin-ui && npm run build"
    )

@app.get("/chat", include_in_schema=False)
async def student_chat():
    return FileResponse(os.path.join(static_dir, "chat.html"))

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🎓</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")

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
app.include_router(context_router)
app.include_router(migration_router)
app.include_router(admin_auth_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
