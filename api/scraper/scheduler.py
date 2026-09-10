import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from db.session import async_session_factory
from db.models import WebScrapeJob
from .crawler import crawler

logger = logging.getLogger(__name__)

class ScraperScheduler:
    """
    Background scheduler for automated university website crawling and delta change ingestion.
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval_seconds = check_interval_seconds
        self.task: Optional[asyncio.Task] = None
        self._running: bool = False

    def start(self):
        if self._running:
            return
        self._running = True
        self.task = asyncio.create_task(self._schedule_loop())
        logger.info("Scraper background scheduler started.")

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self.task and not self.task.done():
            self.task.cancel()
        logger.info("Scraper background scheduler stopped.")

    async def _schedule_loop(self):
        # Initial brief wait to let server finish startup warmup
        await asyncio.sleep(15)

        while self._running:
            try:
                await self._check_and_trigger_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scraper schedule loop: {e}")

            await asyncio.sleep(self.check_interval_seconds)

    async def _check_and_trigger_jobs(self):
        if crawler.is_running:
            return

        async with async_session_factory() as session:
            stmt = select(WebScrapeJob).where(
                WebScrapeJob.is_active == True,
                WebScrapeJob.status != "running"
            )
            jobs = (await session.execute(stmt)).scalars().all()

            now = datetime.utcnow()
            for job in jobs:
                should_run = False
                if job.next_run_at is None:
                    # First run scheduled
                    should_run = True
                elif now >= job.next_run_at:
                    should_run = True

                if should_run:
                    logger.info(f"Triggering scheduled crawl for job: {job.name} ({job.id})")
                    asyncio.create_task(crawler.crawl_job(str(job.id)))
                    break  # Run one job at a time to prevent server overload


scraper_scheduler = ScraperScheduler()
