import os
import time
import asyncio
import logging
from typing import List, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from db.session import async_session_factory
from .pipeline import IngestionPipeline

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}

class AsyncFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, watched_root: str):
        self.loop = loop
        self.watched_root = watched_root

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_ingest(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_ingest(event.src_path)

    def _schedule_ingest(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            asyncio.run_coroutine_threadsafe(
                FolderWatcher.ingest_single(file_path, self.watched_root),
                self.loop
            )


class FolderWatcher:
    """
    Folder watcher supporting native OS filesystem events (watchdog)
    and periodic reconciliation scans for SMB/NFS network shares.
    Reference: Phase 1 of technical plan.
    """

    def __init__(self, rescan_interval: int = 900):
        self.rescan_interval = rescan_interval
        self.observer = Observer()
        self.watched_roots: List[str] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @staticmethod
    async def ingest_single(file_path: str, watched_root: str):
        """Asynchronously process a single file through the ingestion pipeline."""
        from workers.ingest_tasks import process_document_pipeline
        task = process_document_pipeline.delay(file_path)
        return {"task_id": task.id, "file": file_path}

    def add_folder(self, path: str, loop: Optional[asyncio.AbstractEventLoop] = None):
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Path does not exist: {abs_path}")

        if abs_path not in self.watched_roots:
            self.watched_roots.append(abs_path)

        if loop:
            self._loop = loop

        if self._loop:
            handler = AsyncFileSystemEventHandler(self._loop, abs_path)
            self.observer.schedule(handler, abs_path, recursive=True)
            logger.info(f"Subscribed watchdog observer to: {abs_path}")

    async def reconcile_folder(
        self,
        root_path: str,
        department: Optional[str] = None,
        course: Optional[str] = None,
        semester: Optional[str] = None
    ) -> List[dict]:
        """
        Durable reconciliation scan: enumerates all files in folder,
        processes any new or changed files through the pipeline with optional manual tagging.
        """
        from workers.ingest_tasks import process_document_pipeline
        abs_root = os.path.abspath(root_path)
        results = []
        logger.info(f"Starting durable reconciliation scan on: {abs_root}")

        for dirpath, _, filenames in os.walk(abs_root):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    fpath = os.path.join(dirpath, fname)
                    task = process_document_pipeline.delay(
                        fpath,
                        department=department,
                        course=course,
                        semester=semester
                    )
                    results.append({"task_id": task.id, "file": fpath})

        logger.info(f"Reconciliation scan finished for {abs_root}: {len(results)} files evaluated.")
        return results

    def start(self):
        self.observer.start()
        logger.info("Folder watcher watchdog observer started.")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("Folder watcher stopped.")
