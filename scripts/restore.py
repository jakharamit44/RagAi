import os
import sys
import json
import shutil
import hashlib
import tarfile
import logging
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("restore")

def compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def restore_backup(
    archive_path: Optional[str] = None,
    backup_dir: str = "backups",
    verify_checksum: bool = True
) -> bool:
    """
    Restores the university RAG database and vector corpus from a verified snapshot.
    Reference: Phase 17 of technical plan.
    """
    manifest_file = os.path.join(backup_dir, "backup_manifest.json")

    # If no specific archive passed, pick latest from manifest
    if not archive_path:
        if not os.path.exists(manifest_file):
            raise FileNotFoundError(f"No backup manifest found at: {manifest_file}")
        with open(manifest_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        if not registry:
            raise ValueError("Backup registry is empty.")
        latest = registry[-1]
        archive_path = latest["path"]
        expected_hash = latest.get("sha256")
    else:
        expected_hash = None
        if os.path.exists(manifest_file):
            with open(manifest_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            match = next((e for e in registry if os.path.basename(e["path"]) == os.path.basename(archive_path)), None)
            if match:
                expected_hash = match.get("sha256")

    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Backup archive not found: {archive_path}")

    logger.info(f"Initiating restoration from: {archive_path}")

    # 1. Verify Checksum
    if verify_checksum and expected_hash:
        logger.info("Verifying archive SHA-256 integrity...")
        actual_hash = compute_sha256(archive_path)
        if actual_hash != expected_hash:
            raise ValueError(f"Checksum mismatch! Expected {expected_hash}, got {actual_hash}. Archive may be corrupt.")
        logger.info(f"✓ Checksum verified ({actual_hash[:16]}...)")

    extract_tmp = os.path.join(backup_dir, "restore_staging")
    if os.path.exists(extract_tmp):
        shutil.rmtree(extract_tmp, ignore_errors=True)
    os.makedirs(extract_tmp, exist_ok=True)

    try:
        # 2. Extract Archive
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_tmp)

        extracted_subdirs = [os.path.join(extract_tmp, d) for d in os.listdir(extract_tmp) if os.path.isdir(os.path.join(extract_tmp, d))]
        source_dir = extracted_subdirs[0] if extracted_subdirs else extract_tmp

        # 3. Restore SQLite Database
        staged_db = os.path.join(source_dir, "university_rag.db")
        if os.path.exists(staged_db):
            shutil.copy2(staged_db, "university_rag.db")
            logger.info("✓ Restored relational database: university_rag.db")

        # 4. Restore Qdrant Vector Storage
        staged_qdrant = os.path.join(source_dir, "qdrant_storage")
        if os.path.exists(staged_qdrant):
            os.makedirs("data", exist_ok=True)
            if os.path.exists("data/qdrant_storage"):
                shutil.rmtree("data/qdrant_storage", ignore_errors=True)
            shutil.copytree(staged_qdrant, "data/qdrant_storage")
            logger.info("✓ Restored vector store directory: data/qdrant_storage")

        # 5. Restore Uploads
        staged_uploads = os.path.join(source_dir, "uploads")
        if os.path.exists(staged_uploads):
            shutil.copytree(staged_uploads, "data/uploads", dirs_exist_ok=True)
            logger.info("✓ Restored document uploads: data/uploads")

        logger.info("Restoration completed successfully.")
        return True

    finally:
        if os.path.exists(extract_tmp):
            shutil.rmtree(extract_tmp, ignore_errors=True)

if __name__ == "__main__":
    archive_arg = sys.argv[1] if len(sys.argv) > 1 else None
    restore_backup(archive_arg)
    print("Disaster recovery restoration finished successfully.")
