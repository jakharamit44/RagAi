import os
import sys
import asyncio
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.folder_watcher import FolderWatcher
from db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_ingestion")

async def main():
    parser = argparse.ArgumentParser(description="University RAG Ingestion Pipeline Runner")
    parser.add_argument("folder", help="Folder path to watch/reconcile")
    parser.add_argument("--scan-only", action="store_true", help="Run durable reconciliation scan once and exit")
    args = parser.parse_args()

    await init_db()

    target_folder = os.path.abspath(args.folder)
    if not os.path.exists(target_folder):
        logger.error(f"Target folder does not exist: {target_folder}")
        sys.exit(1)

    watcher = FolderWatcher()

    if args.scan_only:
        logger.info(f"Running one-shot durable reconciliation on: {target_folder}")
        results = await watcher.reconcile_folder(target_folder)
        logger.info(f"Scan complete. Processed {len(results)} files.")
        for r in results:
            logger.info(f"  Result: {r}")
    else:
        logger.info(f"Starting continuous folder watch on: {target_folder}")
        loop = asyncio.get_running_loop()
        watcher.add_folder(target_folder, loop=loop)
        watcher.start()

        # Initial durable reconciliation scan
        await watcher.reconcile_folder(target_folder)

        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Stopping watcher...")
            watcher.stop()

if __name__ == "__main__":
    asyncio.run(main())
