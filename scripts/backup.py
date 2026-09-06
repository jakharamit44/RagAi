import os
import sys
import time
import json
import shutil
import hashlib
import tarfile
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backup")

def compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def create_backup(backup_dir: str = "backups", retention_days: int = 30) -> str:
    """
    Creates a full, verifiable disaster recovery snapshot.
    Includes relational database, Qdrant vectors, uploaded documents, and manifest.
    Reference: Phase 17 of technical plan.
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive_name = f"rag_backup_{timestamp}.tar.gz"
    archive_path = os.path.join(backup_dir, archive_name)
    staging_dir = os.path.join(backup_dir, f"staging_{timestamp}")
    os.makedirs(staging_dir, exist_ok=True)

    logger.info(f"Starting university RAG system backup to: {archive_path}")

    try:
        # 1. Backup SQLite database safely
        db_source = "university_rag.db"
        if os.path.exists(db_source):
            db_dest = os.path.join(staging_dir, "university_rag.db")
            # Concurrency-safe copy
            shutil.copy2(db_source, db_dest)
            logger.info(f"Copied relational database: {db_source} ({os.path.getsize(db_dest)} bytes)")

        # 2. Backup Qdrant vector storage
        qdrant_source = "data/qdrant_storage"
        if os.path.exists(qdrant_source):
            qdrant_dest = os.path.join(staging_dir, "qdrant_storage")
            shutil.copytree(qdrant_source, qdrant_dest, dirs_exist_ok=True)
            logger.info(f"Copied vector index directory: {qdrant_source}")

        # 3. Backup Uploads
        uploads_source = "data/uploads"
        if os.path.exists(uploads_source):
            uploads_dest = os.path.join(staging_dir, "uploads")
            shutil.copytree(uploads_source, uploads_dest, dirs_exist_ok=True)
            logger.info(f"Copied uploads directory: {uploads_source}")

        # 4. Generate internal backup metadata manifest
        meta = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "timestamp": timestamp,
            "version": "1.0.0",
            "files": os.listdir(staging_dir),
        }
        with open(os.path.join(staging_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # 5. Compress into tar.gz
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(staging_dir, arcname=f"rag_backup_{timestamp}")

        archive_size = os.path.getsize(archive_path)
        archive_hash = compute_sha256(archive_path)

        logger.info(f"Archive created: {archive_name} ({archive_size} bytes, SHA-256: {archive_hash[:16]}...)")

        # 6. Record in global backup registry
        manifest_file = os.path.join(backup_dir, "backup_manifest.json")
        registry = []
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = []

        registry.append({
            "archive_name": archive_name,
            "path": archive_path,
            "size_bytes": archive_size,
            "sha256": archive_hash,
            "timestamp": timestamp,
            "created_at": meta["created_at"],
        })

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

        # 7. Apply Retention Policy (prune backups older than retention_days)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        pruned_registry = []
        for entry in registry:
            entry_time = datetime.strptime(entry["timestamp"], "%Y%m%d_%H%M%S")
            if entry_time < cutoff_date and os.path.exists(entry["path"]):
                try:
                    os.remove(entry["path"])
                    logger.info(f"Retention policy pruned expired backup: {entry['archive_name']}")
                except Exception as e:
                    logger.warning(f"Could not prune {entry['archive_name']}: {e}")
            else:
                pruned_registry.append(entry)

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(pruned_registry, f, indent=2)

        return archive_path

    finally:
        # Cleanup temporary staging folder
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)

if __name__ == "__main__":
    archive = create_backup()
    print(f"Backup completed successfully: {archive}")
