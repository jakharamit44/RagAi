import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func, or_, desc

from db.session import async_session_factory
from db.models import WebScrapeJob, WebScrapeManifest, Document, Chunk, ContextTier
from api.core.auth import require_role
from api.scraper.crawler import crawler
from api.scraper.url_normalizer import UrlNormalizer
from api.scraper.extractor import PageExtractor
from api.scraper.doc_downloader import DocumentDownloader
from api.scraper.delta_detector import DeltaDetector
from api.scraper.ingest_bridge import ScraperIngestBridge
from api.scraper.storage_cleaner import StorageCleaner
from api.rag.qdrant_store import qdrant_store
from api.rag.bm25_index import bm25_index
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/scraper", tags=["Web Scraper & Delta Ingestion"], dependencies=[Depends(require_role("admin"))])

# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------

class CreateJobRequest(BaseModel):
    name: str = Field(default="MDU Main Scraper", description="Display name for scraper job")
    base_url: str = Field(default="https://mdu.ac.in", description="Root website URL")
    seed_urls: List[str] = Field(default=["https://mdu.ac.in/default.aspx"], description="Starting seed URLs")
    allowed_domains: str = Field(default="mdu.ac.in", description="Comma-separated allowed domains")
    url_patterns: Optional[str] = Field(default=None, description="Optional regex/glob inclusion pattern")
    max_depth: int = Field(default=3, ge=1, le=10, description="Max BFS crawling depth")
    max_pages: int = Field(default=50, ge=1, le=2000, description="Continuous batch size: number of links per auto-advancing batch (default 50)")
    crawl_interval_minutes: int = Field(default=360, ge=15, description="Schedule interval in minutes")
    auto_ingest: bool = Field(default=True, description="Automatically chunk, embed, and index into vector DB")

class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    seed_urls: Optional[List[str]] = None
    allowed_domains: Optional[str] = None
    max_depth: Optional[int] = Field(default=None, ge=1, le=10)
    max_pages: Optional[int] = Field(default=None, ge=1, le=2000, description="Continuous batch size (links per batch)")
    crawl_interval_minutes: Optional[int] = Field(default=None, ge=5, le=10080)
    auto_ingest: Optional[bool] = None
    is_active: Optional[bool] = None

class CrawlSingleUrlRequest(BaseModel):
    url: str = Field(..., description="Target web page or PDF document URL")
    auto_ingest: bool = Field(default=True, description="Embed and index into Qdrant & BM25")

# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.get("/jobs")
async def list_scraper_jobs():
    """List all configured website scraping jobs and their telemetry."""
    async with async_session_factory() as session:
        stmt = select(WebScrapeJob).order_by(WebScrapeJob.created_at.desc())
        jobs = (await session.execute(stmt)).scalars().all()

        results = []
        for j in jobs:
            try:
                seed_list = json.loads(j.seed_urls) if isinstance(j.seed_urls, str) else [j.base_url]
            except Exception:
                seed_list = [j.seed_urls]

            try:
                stats_obj = json.loads(j.stats) if j.stats else {}
            except Exception:
                stats_obj = {}

            # Count total manifest entries for this job
            cnt_stmt = select(func.count(WebScrapeManifest.id)).where(WebScrapeManifest.job_id == j.id)
            total_items = (await session.execute(cnt_stmt)).scalar() or 0

            results.append({
                "id": str(j.id),
                "name": j.name,
                "base_url": j.base_url,
                "seed_urls": seed_list,
                "allowed_domains": j.allowed_domains,
                "max_depth": j.max_depth,
                "max_pages": j.max_pages,
                "crawl_interval_minutes": j.crawl_interval_minutes,
                "auto_ingest": j.auto_ingest,
                "is_active": j.is_active,
                "status": j.status,
                "last_run_at": j.last_run_at.isoformat() if j.last_run_at else None,
                "next_run_at": j.next_run_at.isoformat() if j.next_run_at else None,
                "stats": stats_obj,
                "total_tracked_urls": total_items,
                "created_at": j.created_at.isoformat(),
            })

        return {"status": "success", "jobs": results}


@router.post("/jobs")
async def create_scraper_job(payload: CreateJobRequest):
    """Create a new automated website scraping job."""
    async with async_session_factory() as session:
        job = WebScrapeJob(
            name=payload.name,
            base_url=payload.base_url,
            seed_urls=json.dumps(payload.seed_urls),
            allowed_domains=payload.allowed_domains,
            url_patterns=payload.url_patterns,
            max_depth=payload.max_depth,
            max_pages=payload.max_pages,
            crawl_interval_minutes=payload.crawl_interval_minutes,
            auto_ingest=payload.auto_ingest,
            is_active=True,
            status="idle",
            next_run_at=datetime.utcnow() + timedelta(minutes=1),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        return {
            "status": "success",
            "message": "Scraper job configured successfully.",
            "job_id": str(job.id)
        }


@router.put("/jobs/{job_id}")
async def update_scraper_job(job_id: str, payload: UpdateJobRequest):
    """Update settings for an existing scraper job."""
    async with async_session_factory() as session:
        job = await session.get(WebScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if payload.name is not None:
            job.name = payload.name
        if payload.base_url is not None:
            job.base_url = payload.base_url
        if payload.seed_urls is not None:
            job.seed_urls = json.dumps(payload.seed_urls)
        if payload.allowed_domains is not None:
            job.allowed_domains = payload.allowed_domains
        if payload.max_depth is not None:
            job.max_depth = payload.max_depth
        if payload.max_pages is not None:
            job.max_pages = payload.max_pages
        if payload.crawl_interval_minutes is not None:
            job.crawl_interval_minutes = payload.crawl_interval_minutes
        if payload.auto_ingest is not None:
            job.auto_ingest = payload.auto_ingest
        if payload.is_active is not None:
            job.is_active = payload.is_active

        await session.commit()
        return {"status": "success", "message": "Scraper job updated successfully."}


@router.delete("/jobs/{job_id}")
async def delete_scraper_job(job_id: str):
    """Delete a scraper job and its manifest history."""
    async with async_session_factory() as session:
        job = await session.get(WebScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        await session.delete(job)
        await session.commit()
        return {"status": "success", "message": "Scraper job deleted."}


@router.post("/jobs/{job_id}/run")
async def trigger_crawl_job(job_id: str, background_tasks: BackgroundTasks, max_pages: Optional[int] = Query(None, description="Continuous batch size override (links per batch)")):
    """Trigger an immediate crawl run for the specified job in background."""
    if crawler.is_running:
        raise HTTPException(
            status_code=409,
            detail="Crawler is already busy running another scrape job. Stop or wait for it to finish."
        )

    async with async_session_factory() as session:
        job = await session.get(WebScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    # Launch crawl task in background
    asyncio.create_task(crawler.crawl_job(job_id, max_pages_override=max_pages))

    return {
        "status": "success",
        "message": f"Crawl run triggered for '{job.name}'. Monitoring live telemetry.",
        "job_id": job_id
    }


@router.post("/stop")
async def stop_crawl():
    """Gracefully halts the currently active crawler."""
    if not crawler.is_running:
        return {"status": "noop", "message": "Crawler is not currently running."}

    crawler.stop()
    return {"status": "success", "message": "Halt signal sent to crawler."}


@router.get("/status")
async def get_crawler_status():
    """Get live crawler status, progress metrics, and recent activity logs."""
    return {
        "is_running": crawler.is_running,
        "current_job_id": crawler.current_job_id,
        "current_url": crawler.current_url,
        "stats": crawler.stats,
        "activity_logs": list(crawler.activity_logs),
    }


@router.get("/manifest")
async def get_scrape_manifest(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=5, le=200),
    status_filter: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List tracked URLs and documents with delta status and vector links."""
    async with async_session_factory() as session:
        query = select(WebScrapeManifest)

        if status_filter:
            query = query.where(WebScrapeManifest.status == status_filter)
        if content_type:
            query = query.where(WebScrapeManifest.content_type.ilike(f"%{content_type}%"))
        if search:
            query = query.where(
                or_(
                    WebScrapeManifest.url.ilike(f"%{search}%"),
                    WebScrapeManifest.title.ilike(f"%{search}%")
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = (await session.execute(count_stmt)).scalar() or 0

        # Paginate
        offset = (page - 1) * limit
        items_stmt = query.order_by(desc(WebScrapeManifest.last_checked_at)).offset(offset).limit(limit)
        items = (await session.execute(items_stmt)).scalars().all()

        results = []
        for it in items:
            results.append({
                "id": str(it.id),
                "url": it.url,
                "title": it.title or it.url.split("/")[-1],
                "content_type": it.content_type,
                "etag": it.etag,
                "status": it.status,
                "http_status": it.http_status,
                "document_id": str(it.document_id) if it.document_id else None,
                "last_checked_at": it.last_checked_at.isoformat() if it.last_checked_at else None,
                "last_changed_at": it.last_changed_at.isoformat() if it.last_changed_at else None,
                "error_message": it.error_message,
            })

        return {
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total_count,
            "items": results
        }


@router.post("/crawl-single")
async def crawl_single_resource(payload: CrawlSingleUrlRequest):
    """
    On-demand single URL or PDF crawl and indexing into vector database.
    Instantly verifies conditional ETag / SHA-256 before doing work.
    """
    url = UrlNormalizer.normalize(payload.url)
    if not url:
        raise HTTPException(status_code=400, detail="Invalid URL format provided")

    async with async_session_factory() as session:
        # Resolve active allowed domains for SSRF boundary check
        job_stmt = select(WebScrapeJob.allowed_domains).where(WebScrapeJob.is_active == True)
        configured_domains = (await session.execute(job_stmt)).scalars().all()
        allowed_domains = ["mdu.ac.in"]
        for c_domain in configured_domains:
            if c_domain:
                allowed_domains.extend([d.strip() for d in c_domain.split(",") if d.strip()])
        allowed_domains = list(set(allowed_domains))

        # SSRF Defense Check
        is_safe, reason = UrlNormalizer.is_safe_url(url, allowed_domains=allowed_domains)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"SSRF & Security policy violation: {reason}")

        if UrlNormalizer.is_document_url(url):
            # Download and ingest PDF
            cond_headers = await DeltaDetector.get_conditional_headers(url, session)
            async with httpx.AsyncClient(verify=True, follow_redirects=True) as client:
                success, status_code, local_path, content_hash, resp_headers = await DocumentDownloader.download_file(
                    client, url, conditional_headers=cond_headers
                )

            if status_code == 304:
                if local_path:
                    StorageCleaner.cleanup_file(local_path)
                return {"status": "skipped", "message": "Document is unchanged on university server (HTTP 304)."}

            if not success or not local_path:
                raise HTTPException(status_code=502, detail=f"Failed to download document from {url}")

            should_ingest, reason, manifest_entry = await DeltaDetector.evaluate_change(
                url=url,
                http_status=status_code,
                response_headers=resp_headers,
                raw_body=b"",
                extracted_text=None,
                session=session,
                computed_hash=content_hash
            )
            if manifest_entry:
                manifest_entry.local_file_path = None
                await session.commit()

            if should_ingest and payload.auto_ingest:
                res = await ScraperIngestBridge.ingest_document_file(local_path, manifest_entry, session)
                return {
                    "status": "success",
                    "action": "ingested_document",
                    "details": res
                }
            else:
                if local_path:
                    StorageCleaner.cleanup_file(local_path)
                return {"status": "skipped", "reason": reason, "message": "Document content has not changed."}

        else:
            # Web Page with per-hop redirect safety and TLS verification
            cond_headers = await DeltaDetector.get_conditional_headers(url, session)
            async with httpx.AsyncClient(verify=True, follow_redirects=False) as client:
                curr_url = url
                resp = None
                for _ in range(3):
                    is_safe, reason = UrlNormalizer.is_safe_url(curr_url, allowed_domains=allowed_domains)
                    if not is_safe:
                        raise HTTPException(status_code=400, detail=f"SSRF & Security policy violation: {reason}")
                    try:
                        resp = await client.get(curr_url, headers=cond_headers, timeout=20.0)
                    except Exception as e:
                        raise HTTPException(status_code=502, detail=f"HTTP request failed: {e}")

                    if resp.status_code in (301, 302, 303, 307, 308):
                        loc = resp.headers.get("location")
                        if not loc:
                            break
                        curr_url = urljoin(curr_url, loc)
                        continue
                    break
                else:
                    raise HTTPException(status_code=502, detail="Exceeded maximum redirect hops")

            if resp.status_code == 304:
                return {"status": "skipped", "message": "Web page is unchanged on university server (HTTP 304)."}

            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Server returned HTTP {resp.status_code}")

            extracted = await PageExtractor.extract_html_content(
                resp.content,
                page_url=url,
                allowed_domains=allowed_domains,
                ocr_banners=True,
                client=client
            )
            title = extracted.get("title", "University Web Page")
            markdown_text = extracted.get("text", "")

            should_ingest, reason, manifest_entry = await DeltaDetector.evaluate_change(
                url=url,
                http_status=resp.status_code,
                response_headers=dict(resp.headers),
                raw_body=resp.content,
                extracted_text=markdown_text,
                session=session
            )

            if manifest_entry:
                manifest_entry.title = title
                await session.commit()

            if should_ingest and payload.auto_ingest:
                res = await ScraperIngestBridge.ingest_web_page(
                    page_url=url,
                    title=title,
                    markdown_text=markdown_text,
                    manifest_entry=manifest_entry,
                    session=session
                )
                return {
                    "status": "success",
                    "action": "ingested_web_page",
                    "title": title,
                    "details": res
                }
            else:
                return {"status": "skipped", "reason": reason, "message": "Content has not changed."}


@router.post("/cleanup")
async def cleanup_scraper_storage():
    """
    Safely prunes temporary scraped PDFs, partial downloads (.tmp), and transient web caches.
    GUARANTEES all course directories (sample_courses, uploads, watched folders) remain 100% untouched.
    """
    stats = StorageCleaner.cleanup_scraped_downloads(purge_all_cached=True)
    return {
        "status": "success",
        "message": f"Successfully cleaned temporary downloads. Reclaimed {stats.get('mb_freed', 0.0)} MB across {stats.get('files_deleted', 0)} files.",
        "metrics": stats,
        **stats
    }


@router.delete("/purge-rag-data")
async def purge_scraped_rag_data():
    """
    Permanently purges all RAG data generated from web scraping:
    - Web documents and notices (department="University Portal")
    - Downloaded official document records from scraping
    - Associated chunks and in-memory BM25 index entries
    - Qdrant vector points
    - OpenViking virtual filesystem context tiers
    - Crawl manifest history
    - Temporary scraped disk files in data/downloads/mdu_scraped/

    STRICT GUARANTEE:
    Academic course files in data/sample_courses/, data/uploads/, watched folders,
    and all registered department materials remain 100% intact.
    """
    async with async_session_factory() as session:
        # 1. Identify all documents originating from web scraping
        manifest_docs_subq = select(WebScrapeManifest.document_id).where(WebScrapeManifest.document_id.isnot(None))

        doc_stmt = select(Document).where(
            or_(
                Document.department == "University Portal",
                Document.id.in_(manifest_docs_subq),
                Document.source_path.startswith("http://"),
                Document.source_path.startswith("https://"),
                Document.source_path.ilike("%mdu_scraped%")
            )
        )
        scraped_docs = (await session.execute(doc_stmt)).scalars().all()
        scraped_doc_ids = [doc.id for doc in scraped_docs]

        # 2. Collect all chunk IDs for vector DB purge
        chunk_ids = []
        if scraped_doc_ids:
            chunk_stmt = select(Chunk.id).where(Chunk.document_id.in_(scraped_doc_ids))
            chunk_ids = (await session.execute(chunk_stmt)).scalars().all()

        # 3. Purge Qdrant vectors
        vectors_purged = 0
        try:
            if chunk_ids:
                point_ids = [str(cid) for cid in chunk_ids]
                def _delete_points():
                    for i in range(0, len(point_ids), 1000):
                        batch = point_ids[i:i + 1000]
                        qdrant_store.client.delete(
                            collection_name=qdrant_store.collection_name,
                            points_selector=batch,
                            wait=True
                        )
                await asyncio.to_thread(_delete_points)
                vectors_purged = len(point_ids)

            # Defense-in-depth: purge any vectors tagged with department="University Portal"
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                def _delete_dept():
                    qdrant_store.client.delete(
                        collection_name=qdrant_store.collection_name,
                        points_selector=Filter(
                            must=[FieldCondition(key="department", match=MatchValue(value="University Portal"))]
                        ),
                        wait=True
                    )
                await asyncio.to_thread(_delete_dept)
            except Exception:
                pass
        except Exception as q_err:
            logger.warning(f"Note on Qdrant vector deletion: {q_err}")

        # 4. Purge relational DB: Chunks, Documents, ContextTier, WebScrapeManifest
        chunks_purged = len(chunk_ids)
        docs_purged = len(scraped_doc_ids)

        if scraped_doc_ids:
            await session.execute(delete(Chunk).where(Chunk.document_id.in_(scraped_doc_ids)))
            await session.execute(delete(Document).where(Document.id.in_(scraped_doc_ids)))

        # Purge OpenViking ContextTier entries
        context_tiers_purged = 0
        try:
            ct_conditions = [ContextTier.department == "University Portal"]
            if scraped_doc_ids:
                ct_conditions.append(ContextTier.document_id.in_(scraped_doc_ids))

            ct_stmt = delete(ContextTier).where(or_(*ct_conditions))
            ct_res = await session.execute(ct_stmt)
            context_tiers_purged = ct_res.rowcount or 0
        except Exception as ct_err:
            logger.warning(f"Note on ContextTier deletion: {ct_err}")

        # Purge all WebScrapeManifest records
        manifest_res = await session.execute(delete(WebScrapeManifest))
        manifest_purged = manifest_res.rowcount or 0

        await session.commit()

        # 5. Purge BM25 in-memory corpus and rebuild index safely
        try:
            scraped_ids_set = {str(did) for did in scraped_doc_ids}
            current_snapshot = list(bm25_index.corpus)
            filtered_corpus = [
                item for item in current_snapshot
                if item.get("department") != "University Portal" and str(item.get("document_id")) not in scraped_ids_set
            ]
            await asyncio.to_thread(bm25_index.build_index, filtered_corpus)
        except Exception as bm25_err:
            logger.warning(f"Note on BM25 corpus rebuild: {bm25_err}")

        # 6. Invalidate Cognitive Brain graph cache
        try:
            from api.brain.graph_engine import brain_graph_engine
            brain_graph_engine.invalidate_cache()
        except Exception as brain_err:
            logger.warning(f"Note on Brain cache invalidation: {brain_err}")

        # 7. Sweep any residual disk downloads
        storage_res = StorageCleaner.cleanup_scraped_downloads(purge_all_cached=True)

        return {
            "status": "success",
            "message": f"Successfully purged all scraped RAG data: {docs_purged} documents, {chunks_purged} chunks, {vectors_purged} vectors, {manifest_purged} manifest entries, and reclaimed {storage_res.get('mb_freed', 0.0)} MB disk space. All course materials remain intact.",
            "metrics": {
                "documents_purged": docs_purged,
                "chunks_purged": chunks_purged,
                "vectors_purged": vectors_purged,
                "context_tiers_purged": context_tiers_purged,
                "manifest_entries_purged": manifest_purged,
                "disk_files_deleted": storage_res.get("files_deleted", 0),
                "mb_freed": storage_res.get("mb_freed", 0.0)
            }
        }

