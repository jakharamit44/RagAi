"""
Always-On University Notice Ingestion Scout
Inspired by Shubhamsaboo/awesome-llm-apps (Always-on Agents)

Continuously monitors target notice directories or web drop locations for new
university circulars, datesheets, syllabi, and administrative notices.
Automatically runs change detection (SHA-256 deduplication), text extraction,
semantic chunking, vector embedding, Qdrant indexing, and BM25 index updating.
"""

import os
import sys
import time
import asyncio
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("always_on_notice_scout")

DEFAULT_INCOMING_DIR = os.path.join(PROJECT_ROOT, "data", "notices_incoming")

class AlwaysOnNoticeScout:
    """
    Autonomous always-on agent for university notice ingestion.
    Watches designated folder, detects new/updated PDF/DOCX notices,
    and automatically indexes them into the RAG platform.
    """

    def __init__(self, watch_dir: str = DEFAULT_INCOMING_DIR, interval_sec: int = 15):
        self.watch_dir = os.path.abspath(watch_dir)
        self.interval_sec = interval_sec
        self._running = False
        os.makedirs(self.watch_dir, exist_ok=True)

    async def _try_api_ingest(self, file_paths: List[str], api_url: str = "http://127.0.0.1:8000") -> Optional[Dict[str, Any]]:
        """Attempt to delegate notice ingestion to live running API server."""
        import httpx
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                health_resp = await client.get(f"{api_url}/health")
                if health_resp.status_code != 200:
                    logger.warning(f"[Notice Scout] Health check returned status {health_resp.status_code}")
                    return None

                login_resp = await client.post(
                    f"{api_url}/auth/login",
                    json={"external_id": "admin", "role": "admin"}
                )
                if login_resp.status_code != 200:
                    logger.warning(f"[Notice Scout] Admin login failed: {login_resp.status_code} - {login_resp.text}")
                    return None
                token = login_resp.json().get("access_token")
                if not token:
                    logger.warning("[Notice Scout] No access_token returned")
                    return None

                ingest_resp = await client.post(
                    f"{api_url}/api/v1/admin/scout/ingest",
                    json={"file_paths": file_paths, "watch_dir": self.watch_dir, "force": False},
                    headers={"Authorization": f"Bearer {token}"}
                )
                if ingest_resp.status_code == 200:
                    data = ingest_resp.json()
                    logger.info(f"[Notice Scout] Delegated ingestion of {len(file_paths)} file(s) to live server successfully.")
                    return {
                        "timestamp": datetime.utcnow().isoformat(),
                        "watch_dir": self.watch_dir,
                        "total_scanned": data.get("total_scanned", len(file_paths)),
                        "newly_ingested": data.get("newly_ingested", 0),
                        "skipped_unchanged": data.get("skipped_unchanged", 0),
                        "failed": data.get("failed", 0),
                        "results": data.get("results", [])
                    }
                else:
                    logger.warning(f"[Notice Scout] Ingest endpoint returned status {ingest_resp.status_code}: {ingest_resp.text}")
        except Exception as e:
            logger.debug(f"[Notice Scout] Live API not available for ingestion delegation ({e}), falling back to direct processing.")
            return None
        return None

    async def scan_and_ingest_once(self) -> Dict[str, Any]:
        """Scans the watch directory and ingests any new or modified documents."""
        supported_exts = {".pdf", ".docx", ".txt", ".doc"}
        files_found = []

        # Scan watch directory
        for root, _, files in os.walk(self.watch_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in supported_exts:
                    files_found.append(os.path.join(root, f))

        logger.info(f"[Notice Scout] Found {len(files_found)} candidate file(s) in {self.watch_dir}")

        if not files_found:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "watch_dir": self.watch_dir,
                "total_scanned": 0,
                "newly_ingested": 0,
                "skipped_unchanged": 0,
                "failed": 0,
                "results": []
            }

        # 1. First attempt: delegate to running server if active
        api_res = await self._try_api_ingest(files_found)
        if api_res is not None:
            return api_res

        # 2. Fallback: local direct database + vector store processing (only if server is offline)
        from db.session import async_session_factory
        from db.models import SecurityIncident, Chunk, Document
        from ingestion.pipeline import IngestionPipeline
        from api.rag.embedder import embedder
        from api.rag.qdrant_store import qdrant_store
        from api.rag.bm25_index import bm25_index
        from sqlalchemy import select

        ingested_count = 0
        skipped_count = 0
        failed_count = 0
        results = []

        async with async_session_factory() as session:
            for file_path in files_found:
                filename = os.path.basename(file_path)
                try:
                    res = await IngestionPipeline.process_file(
                        file_path=file_path,
                        session=session,
                        watched_root=self.watch_dir
                    )

                    if res.get("status") == "skipped":
                        skipped_count += 1
                        results.append({"file": filename, "status": "skipped", "reason": res.get("reason")})
                        continue

                    if res.get("status") == "success":
                        doc_id = res.get("document_id")
                        # Fetch newly created chunks without embedding
                        query = select(Chunk).where(Chunk.document_id == doc_id, Chunk.embedding_ref.is_(None))
                        unembedded_chunks = (await session.execute(query)).scalars().all()

                        if unembedded_chunks:
                            texts = [c.text for c in unembedded_chunks]
                            vectors = await asyncio.to_thread(embedder.embed_texts, texts)

                            t_ms = int(time.time() * 1000) % 1000000000
                            points_to_upsert = []

                            for idx, chunk in enumerate(unembedded_chunks):
                                p_id = t_ms + idx
                                payload = {
                                    "chunk_id": str(chunk.id),
                                    "document_id": str(doc_id),
                                    "title": res.get("title", filename),
                                    "department": res.get("tags", {}).get("department", "General"),
                                    "course": res.get("tags", {}).get("course", "General"),
                                    "semester": res.get("tags", {}).get("semester", "All"),
                                    "page_number": chunk.page_number,
                                    "section": chunk.section,
                                    "text": chunk.text,
                                    "content_hash": chunk.content_hash,
                                }
                                points_to_upsert.append({
                                    "id": p_id,
                                    "vector": vectors[idx],
                                    "payload": payload
                                })
                                chunk.embedding_ref = str(p_id)

                            await asyncio.to_thread(qdrant_store.upsert_chunks, points_to_upsert)
                            await session.commit()

                            # Refresh BM25 index with new content
                            bm25_index.reload_from_db()

                        # Record event in Security/Governance Audit Log
                        incident = SecurityIncident(
                            timestamp=datetime.utcnow(),
                            event_type="AUTO_NOTICE_SCOUT_INGEST",
                            severity="LOW",
                            client_ip="127.0.0.1",
                            user_identifier="system:notice_scout",
                            action_taken="LOGGED",
                            detail=f"Always-On Scout auto-ingested '{filename}' ({res.get('chunks_count', 0)} chunks, doc_id={doc_id})"
                        )
                        session.add(incident)
                        await session.commit()

                        ingested_count += 1
                        results.append({
                            "file": filename,
                            "status": "ingested",
                            "chunks": res.get("chunks_count", 0),
                            "doc_id": doc_id
                        })
                        logger.info(f"[Notice Scout] Successfully ingested & vector-indexed '{filename}'")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"[Notice Scout] Error ingesting '{filename}': {e}", exc_info=True)
                    results.append({"file": filename, "status": "failed", "error": str(e)})

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "watch_dir": self.watch_dir,
            "total_scanned": len(files_found),
            "newly_ingested": ingested_count,
            "skipped_unchanged": skipped_count,
            "failed": failed_count,
            "results": results
        }
        return summary

    async def run_daemon(self):
        """Runs continuous background monitoring loop."""
        self._running = True
        logger.info(f"[*] Starting Always-On Notice Scout daemon. Polling '{self.watch_dir}' every {self.interval_sec}s...")
        try:
            while self._running:
                try:
                    summary = await self.scan_and_ingest_once()
                    if summary["newly_ingested"] > 0:
                        logger.info(f"[Notice Scout] Auto-indexed {summary['newly_ingested']} new circular(s) into RAG system.")
                except Exception as err:
                    logger.warning(f"[Notice Scout] Cycle warning: {err}")

                await asyncio.sleep(self.interval_sec)
        except asyncio.CancelledError:
            logger.info("[Notice Scout] Daemon task cancelled.")
        finally:
            self._running = False
            logger.info("[Notice Scout] Daemon stopped.")

    def stop(self):
        self._running = False


async def main():
    parser = argparse.ArgumentParser(description="Always-On University Notice Ingestion Scout")
    parser.add_argument("--dir", type=str, default=DEFAULT_INCOMING_DIR, help="Directory to monitor for incoming notices")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds (default 15s)")
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit (ideal for cron/triggers)")
    args = parser.parse_args()

    scout = AlwaysOnNoticeScout(watch_dir=args.dir, interval_sec=args.interval)

    if args.once:
        logger.info(f"[*] Running single-pass notice scan on '{scout.watch_dir}'...")
        summary = await scout.scan_and_ingest_once()
        print("\n--- SCOUT SCAN SUMMARY ---")
        import json
        print(json.dumps(summary, indent=2))
    else:
        await scout.run_daemon()

if __name__ == "__main__":
    asyncio.run(main())
