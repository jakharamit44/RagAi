import asyncio
import logging
import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.session import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")

async def main():
    logger.info("Initializing relational database tables according to Appendix A...")
    try:
        await init_db()
        logger.info("Successfully created database tables: watched_folders, manifest_entries, documents, chunks, users, query_audit_log.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
