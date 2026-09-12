import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
import httpx

from db.session import async_session_factory
from db.models import WebScrapeJob, WebScrapeManifest
from .url_normalizer import UrlNormalizer
from .extractor import PageExtractor
from .delta_detector import DeltaDetector
from .doc_downloader import DocumentDownloader
from .ingest_bridge import ScraperIngestBridge
from .storage_cleaner import StorageCleaner

logger = logging.getLogger(__name__)

class UniversityWebCrawler:
    """
    High-throughput, domain-governed asynchronous crawler with intelligent 3-tier delta change detection.
    """

    def __init__(self):
        self.is_running: bool = False
        self.stop_requested: bool = False
        self.current_job_id: Optional[str] = None
        self.current_url: str = ""
        self.stats: Dict[str, Any] = {
            "pages_scraped": 0,
            "documents_downloaded": 0,
            "skipped_unchanged": 0,
            "errors": 0,
            "total_urls_visited": 0,
            "current_batch": 1,
            "batch_size": 50,
            "batch_urls_processed": 0,
            "queue_remaining": 0,
            "start_time": None,
            "end_time": None,
        }
        self.activity_logs: deque = deque(maxlen=200)

    def log_activity(self, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "message": message,
            "level": level
        }
        self.activity_logs.append(entry)
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    def stop(self):
        """Signals crawler loop to stop."""
        self.stop_requested = True
        self.log_activity("Halt signal received. Finishing in-flight requests and pausing crawl loop...", level="warning")

    async def crawl_job(self, job_id: str, max_pages_override: Optional[int] = None) -> Dict[str, Any]:
        """Executes crawl run for a specific WebScrapeJob in automatic continuous batches."""
        self.is_running = True
        self.stop_requested = False
        self.current_job_id = job_id
        self.stats = {
            "pages_scraped": 0,
            "documents_downloaded": 0,
            "skipped_unchanged": 0,
            "errors": 0,
            "total_urls_visited": 0,
            "current_batch": 1,
            "batch_size": max_pages_override or 50,
            "batch_urls_processed": 0,
            "queue_remaining": 0,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
        }
        self.activity_logs.clear()

        # Safeguard: Configure process scheduling to BELOW_NORMAL on Windows so crawling never freezes or lags host PC
        try:
            import psutil
            p = psutil.Process()
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            logger.info("Configured process scheduling to BELOW_NORMAL_PRIORITY_CLASS to preserve host PC responsiveness.")
        except Exception:
            pass

        self.log_activity(f"Starting continuous batched web crawl for job ID: {job_id}")

        async with async_session_factory() as session:
            job = await session.get(WebScrapeJob, job_id)
            if not job:
                self.is_running = False
                return {"status": "error", "message": f"Job {job_id} not found."}

            job.status = "running"
            job.last_run_at = datetime.utcnow()
            await session.commit()

            try:
                seed_urls = json.loads(job.seed_urls) if isinstance(job.seed_urls, str) else [job.base_url]
            except Exception:
                seed_urls = [job.base_url]

            allowed_domains = [d.strip() for d in job.allowed_domains.split(",") if d.strip()]
            base_root = UrlNormalizer.extract_root_domain(job.base_url)
            if base_root and base_root not in allowed_domains:
                allowed_domains.append(base_root)

            max_depth = job.max_depth or 3
            batch_size = max_pages_override or job.max_pages or 50
            auto_ingest = job.auto_ingest

        try:
            await self._run_crawl_loop(
                job_id=job_id,
                seeds=seed_urls,
                allowed_domains=allowed_domains,
                max_depth=max_depth,
                batch_size=batch_size,
                auto_ingest=auto_ingest
            )
        except Exception as e:
            self.log_activity(f"Crawl encountered critical exception: {e}", level="error")
        finally:
            self.is_running = False
            self.stats["end_time"] = datetime.utcnow().isoformat()

            async with async_session_factory() as session:
                job = await session.get(WebScrapeJob, job_id)
                if job:
                    job.status = "idle"
                    job.stats = json.dumps(self.stats)
                    if job.crawl_interval_minutes:
                        job.next_run_at = datetime.utcnow() + timedelta(minutes=job.crawl_interval_minutes)
                    await session.commit()

            # Post-crawl temporary file sweep
            clean_res = StorageCleaner.cleanup_scraped_downloads(purge_all_cached=True)
            if clean_res.get("files_deleted", 0) > 0:
                self.log_activity(f"🧹 Post-crawl sweep: Purged {clean_res['files_deleted']} temporary files ({clean_res['mb_freed']} MB reclaimed).")

            if self.stop_requested:
                self.log_activity(
                    f"🛑 Crawl halted by user. Processed {self.stats['current_batch']} batches, "
                    f"Total URLs visited: {self.stats['total_urls_visited']} ({self.stats['pages_scraped']} pages, "
                    f"{self.stats['documents_downloaded']} docs, {self.stats['skipped_unchanged']} skipped)."
                )
            else:
                self.log_activity(
                    f"🎉 All batches completed. Processed {self.stats['current_batch']} batches, "
                    f"Scraped {self.stats['pages_scraped']} pages, "
                    f"Downloaded {self.stats['documents_downloaded']} docs, "
                    f"Skipped {self.stats['skipped_unchanged']} unchanged."
                )

            try:
                import psutil
                p = psutil.Process()
                p.nice(psutil.NORMAL_PRIORITY_CLASS)
            except Exception:
                pass

        return self.stats

    async def _run_crawl_loop(
        self,
        job_id: str,
        seeds: List[str],
        allowed_domains: List[str],
        max_depth: int,
        batch_size: int,
        auto_ingest: bool
    ):
        queue: deque = deque()
        visited: Set[str] = set()

        for s in seeds:
            norm = UrlNormalizer.normalize(s)
            if norm:
                queue.append((norm, 0))
                visited.add(norm)

        # Configure continuous batching
        batch_size = max(5, batch_size or 50)
        self.stats["batch_size"] = batch_size
        self.stats["current_batch"] = 1
        self.stats["batch_urls_processed"] = 0
        self.stats["queue_remaining"] = len(queue)

        semaphore = asyncio.Semaphore(2)  # Polite concurrency to protect CPU, RAM & network
        client_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UnivRAG-Scraper/1.1 (Academic Indexer)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }

        self.log_activity(
            f"🚀 [Continuous Batched Crawl Initiated] Batch size: {batch_size} links/batch. "
            f"Initial queue: {len(queue)} seed URLs. Auto-advancing across batches until discovery queue is complete."
        )

        async with httpx.AsyncClient(headers=client_headers, timeout=20.0, verify=True, follow_redirects=True) as client:
            while queue and not self.stop_requested:
                current_url, depth = queue.popleft()
                self.current_url = current_url
                self.stats["total_urls_visited"] += 1
                self.stats["batch_urls_processed"] += 1
                self.stats["queue_remaining"] = len(queue)

                async with semaphore:
                    try:
                        await self._process_single_url(
                            client=client,
                            job_id=job_id,
                            url=current_url,
                            depth=depth,
                            max_depth=max_depth,
                            allowed_domains=allowed_domains,
                            queue=queue,
                            visited=visited,
                            auto_ingest=auto_ingest
                        )
                        # Polite inter-request pause to let CPU, network and OS breathe
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        self.stats["errors"] += 1
                        self.log_activity(f"Error processing {current_url}: {e}", level="error")

                self.stats["queue_remaining"] = len(queue)

                # Check if current batch is finished
                if self.stats["batch_urls_processed"] >= batch_size and queue and not self.stop_requested:
                    batch_num = self.stats["current_batch"]
                    rem = len(queue)

                    self.log_activity(
                        f"🏁 [Batch {batch_num} Finished] Successfully processed {batch_size} links in this batch "
                        f"(Cumulative: {self.stats['total_urls_visited']} visited, {self.stats['pages_scraped']} pages, "
                        f"{self.stats['documents_downloaded']} docs, {self.stats['skipped_unchanged']} skipped). "
                        f"{rem} URLs pending in discovery queue."
                    )

                    # Checkpoint job stats to SQLite
                    try:
                        async with async_session_factory() as session:
                            job = await session.get(WebScrapeJob, job_id)
                            if job:
                                job.stats = json.dumps(self.stats)
                                await session.commit()
                    except Exception:
                        pass

                    # Clean memory & caches between batches
                    import gc
                    gc.collect()
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass

                    # Trim working set memory on Windows to release unused physical RAM
                    try:
                        import ctypes
                        ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
                    except Exception:
                        pass

                    # Refresh BM25 index once every 5 batches
                    if batch_num % 5 == 0:
                        try:
                            from api.rag.bm25_index import bm25_index
                            bm25_index.reload_from_db()
                        except Exception:
                            pass

                    # Auto-advance to the next batch
                    next_batch_num = batch_num + 1
                    self.stats["current_batch"] = next_batch_num
                    self.stats["batch_urls_processed"] = 0

                    self.log_activity(
                        f"🔄 [Auto-Starting Batch {next_batch_num}] Auto-advancing to next batch ({min(batch_size, rem)} links) from discovery queue..."
                    )
                    # Brief polite batch cooldown allowing system memory & OS to settle
                    await asyncio.sleep(2.0)

    async def _process_single_url(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        url: str,
        depth: int,
        max_depth: int,
        allowed_domains: List[str],
        queue: deque,
        visited: Set[str],
        auto_ingest: bool
    ):
        # SSRF guard: strictly re-validate URL safety prior to fetching
        is_safe, reason = UrlNormalizer.is_safe_url(url, allowed_domains)
        if not is_safe:
            self.log_activity(f"Blocked unsafe/unauthorized URL {url}: {reason}", level="warning")
            return

        async with async_session_factory() as session:
            # Check if this is a document (.pdf, .docx) or a web page
            if UrlNormalizer.is_document_url(url):
                # 1. Process Document
                cond_headers = await DeltaDetector.get_conditional_headers(url, session)
                success, status_code, local_path, content_hash, resp_headers = await DocumentDownloader.download_file(
                    client, url, conditional_headers=cond_headers
                )

                if status_code == 304:
                    self.stats["skipped_unchanged"] += 1
                    self.log_activity(f"⚡ [304 Unchanged] Document: {url.split('/')[-1]}")
                    if local_path:
                        StorageCleaner.cleanup_file(local_path)
                    return

                if not success or not local_path:
                    self.stats["errors"] += 1
                    return

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
                    manifest_entry.job_id = job_id
                    manifest_entry.local_file_path = None
                    await session.commit()

                if should_ingest and auto_ingest:
                    self.log_activity(f"📥 [Processing Document] Verifying content: {url.split('/')[-1]}")
                    ingest_res = await ScraperIngestBridge.ingest_document_file(local_path, manifest_entry, session)
                    if ingest_res.get("status") == "success":
                        self.stats["documents_downloaded"] += 1
                        self.log_activity(f"✅ Ingested PDF: {url.split('/')[-1]} ({ingest_res.get('chunks_count', 0)} chunks)")
                    elif ingest_res.get("status") == "skipped":
                        self.stats["skipped_unchanged"] += 1
                        self.log_activity(f"⚡ [Skipped Duplicate] Document content already indexed: {url.split('/')[-1]}")
                    else:
                        self.stats["errors"] += 1
                        self.log_activity(f"⚠️ Ingest note for {url.split('/')[-1]}: {ingest_res.get('message', 'Pipeline skipped')}", level="warning")
                else:
                    self.stats["skipped_unchanged"] += 1
                    self.log_activity(f"⚡ [Unchanged Hash] Skipped duplicate document: {url.split('/')[-1]}")
                    if local_path:
                        StorageCleaner.cleanup_file(local_path)

            else:
                # 2. Process HTML Web Page
                if UrlNormalizer.is_skippable_url(url):
                    self.stats["skipped_unchanged"] += 1
                    return

                cond_headers = await DeltaDetector.get_conditional_headers(url, session)
                try:
                    resp = await client.get(url, headers=cond_headers)
                except Exception as net_err:
                    self.stats["errors"] += 1
                    self.log_activity(f"HTTP GET failed for {url}: {net_err}", level="error")
                    return

                # Re-validate final redirected URL against SSRF
                is_safe_target, target_reason = UrlNormalizer.is_safe_url(str(resp.url), allowed_domains)
                if not is_safe_target:
                    self.stats["errors"] += 1
                    self.log_activity(f"Redirected to unsafe URL {resp.url}: {target_reason}", level="warning")
                    return

                if resp.status_code == 304:
                    self.stats["skipped_unchanged"] += 1
                    self.log_activity(f"⚡ [304 Unchanged] Web page: {url}")
                    return

                if resp.status_code != 200:
                    self.stats["errors"] += 1
                    self.log_activity(f"HTTP {resp.status_code} for {url}", level="warning")
                    return

                # Content extraction (including visual banner announcement OCR)
                extracted = await PageExtractor.extract_html_content(
                    resp.content,
                    page_url=url,
                    allowed_domains=allowed_domains,
                    ocr_banners=True,
                    client=client
                )
                title = extracted.get("title", "University Web Page")
                markdown_text = extracted.get("text", "")
                banners = extracted.get("banner_announcements", [])
                if banners:
                    self.log_activity(f"🖼️ [Banner OCR] Extracted {len(banners)} visual announcements from {title[:30]}")

                should_ingest, reason, manifest_entry = await DeltaDetector.evaluate_change(
                    url=url,
                    http_status=resp.status_code,
                    response_headers=dict(resp.headers),
                    raw_body=resp.content,
                    extracted_text=markdown_text,
                    session=session
                )
                if manifest_entry:
                    manifest_entry.job_id = job_id
                    manifest_entry.title = title
                    await session.commit()

                if should_ingest and auto_ingest and len(markdown_text) > 60:
                    self.log_activity(f"📄 [New Web Page] Indexing: {title[:40]}...")
                    ingest_res = await ScraperIngestBridge.ingest_web_page(
                        page_url=url,
                        title=title,
                        markdown_text=markdown_text,
                        manifest_entry=manifest_entry,
                        session=session
                    )
                    if ingest_res.get("status") == "success":
                        self.stats["pages_scraped"] += 1
                        self.log_activity(f"✅ Ingested Web Page: {title[:35]} ({ingest_res.get('chunks_count', 0)} chunks)")
                    else:
                        self.stats["errors"] += 1
                else:
                    self.stats["skipped_unchanged"] += 1

                # Link Discovery: Enqueue children if depth < max_depth
                if depth < max_depth:
                    page_links, doc_links = PageExtractor.harvest_links(resp.content, url, allowed_domains)
                    new_links_count = 0
                    for child_url in doc_links + page_links:
                        if child_url not in visited:
                            visited.add(child_url)
                            queue.append((child_url, depth + 1))
                            new_links_count += 1
                    if new_links_count > 0:
                        self.log_activity(f"🔗 Discovered {new_links_count} links on {title[:30]} (Depth {depth+1})")


# Singleton Crawler Instance
crawler = UniversityWebCrawler()
