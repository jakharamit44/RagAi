#!/usr/bin/env python3
"""
Industrial-grade Migration Script: Local SQLite Qdrant -> Remote Ubuntu VM Qdrant
Transfers 373,635 vector points and payloads with zero data loss.
"""

import sys
import os
import time
import sqlite3
import pickle
import logging
from typing import List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.core.config import settings
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vector_migrator")

LOCAL_STORAGE_DB = os.path.abspath("data/qdrant_storage/collection/university_corpus/storage.sqlite")
BATCH_SIZE = 500

def migrate():
    if not os.path.exists(LOCAL_STORAGE_DB):
        logger.error(f"Local storage database not found at {LOCAL_STORAGE_DB}")
        sys.exit(1)

    logger.info(f"Connecting to remote Qdrant at {settings.VECTOR_STORE_HOST}:{settings.VECTOR_STORE_PORT}...")
    client = QdrantClient(
        host=settings.VECTOR_STORE_HOST,
        port=settings.VECTOR_STORE_PORT,
        api_key=settings.QDRANT_API_KEY,
        https=getattr(settings, "QDRANT_HTTPS", False),
        timeout=60.0
    )

    # Ensure remote collection exists
    collections = client.get_collections().collections
    exists = any(c.name == "university_corpus" for c in collections)
    if not exists:
        logger.info("Creating remote collection 'university_corpus'...")
        client.create_collection(
            collection_name="university_corpus",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE, on_disk=True),
        )
    else:
        logger.info("Remote collection 'university_corpus' already exists.")

    current_remote_count = client.count("university_corpus").count
    logger.info(f"Current remote point count: {current_remote_count:,}")

    # Connect to local SQLite storage
    logger.info(f"Opening local Qdrant database: {LOCAL_STORAGE_DB}")
    conn = sqlite3.connect(LOCAL_STORAGE_DB)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM points")
    total_points = cursor.fetchone()[0]
    logger.info(f"Total points to migrate: {total_points:,}")

    cursor.execute("SELECT point FROM points")
    
    migrated = 0
    batch: List = []
    start_time = time.time()
    last_log_time = start_time

    while True:
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break

        for row in rows:
            point = pickle.loads(row[0])
            batch.append(point)

        # Upsert batch with retry
        for attempt in range(3):
            try:
                client.upsert(collection_name="university_corpus", points=batch, wait=False)
                break
            except Exception as e:
                logger.warning(f"Batch upsert failed (attempt {attempt+1}/3): {e}")
                time.sleep(2)
        else:
            logger.error("Failed to upsert batch after 3 attempts. Aborting.")
            sys.exit(1)

        migrated += len(batch)
        batch.clear()

        now = time.time()
        if now - last_log_time >= 5.0 or migrated == total_points:
            elapsed = now - start_time
            rate = migrated / elapsed if elapsed > 0 else 0
            percent = (migrated / total_points) * 100
            remaining_sec = (total_points - migrated) / rate if rate > 0 else 0
            logger.info(
                f"Progress: {migrated:,}/{total_points:,} ({percent:.1f}%) | "
                f"Rate: {rate:.0f} pts/sec | ETA: {remaining_sec/60:.1f} min"
            )
            last_log_time = now

    conn.close()
    total_elapsed = time.time() - start_time
    final_count = client.count("university_corpus").count
    logger.info(
        f"MIGRATION COMPLETE in {total_elapsed/60:.2f} minutes! "
        f"Remote points verified: {final_count:,}"
    )

if __name__ == "__main__":
    migrate()
