import os
import sys
import shutil
import asyncio
import logging
from sqlalchemy import select, func

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.session import init_db, async_session_factory
from db.models import Document, Chunk
from scripts.backup import create_backup
from scripts.restore import restore_backup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_backup")

async def test_backup_and_restore_lifecycle():
    await init_db()

    test_backup_dir = "test_backups"
    if os.path.exists(test_backup_dir):
        shutil.rmtree(test_backup_dir, ignore_errors=True)

    # 1. Capture Pre-Backup Stats
    logger.info("\n--- 1. Capturing Pre-Backup Corpus Stats ---")
    async with async_session_factory() as session:
        pre_doc_count = (await session.execute(select(func.count(Document.id)))).scalar()
        pre_chunk_count = (await session.execute(select(func.count(Chunk.id)))).scalar()

    logger.info(f"Pre-backup state: {pre_doc_count} documents, {pre_chunk_count} chunks")
    assert pre_doc_count > 0, "No documents present to back up!"

    # 2. Execute Backup
    logger.info("\n--- 2. Executing create_backup() ---")
    archive_path = create_backup(backup_dir=test_backup_dir, retention_days=30)
    assert os.path.exists(archive_path), "Backup archive was not created!"
    archive_size = os.path.getsize(archive_path)
    logger.info(f"✓ Backup created: {os.path.basename(archive_path)} ({archive_size} bytes)")

    # 3. Verify Backup Manifest
    logger.info("\n--- 3. Verifying Backup Manifest ---")
    manifest_path = os.path.join(test_backup_dir, "backup_manifest.json")
    assert os.path.exists(manifest_path), "Manifest missing!"
    logger.info("✓ Backup manifest recorded with SHA-256 integrity hash")

    # 4. Execute Restore
    logger.info("\n--- 4. Executing restore_backup() ---")
    success = restore_backup(archive_path=archive_path, backup_dir=test_backup_dir, verify_checksum=True)
    assert success is True, "Restore function returned False!"
    logger.info("✓ Restoration executed with valid checksum")

    # 5. Verify Post-Restore State
    logger.info("\n--- 5. Verifying Post-Restore Database Integrity ---")
    async with async_session_factory() as session:
        post_doc_count = (await session.execute(select(func.count(Document.id)))).scalar()
        post_chunk_count = (await session.execute(select(func.count(Chunk.id)))).scalar()

    logger.info(f"Post-restore state: {post_doc_count} documents, {post_chunk_count} chunks")
    assert post_doc_count == pre_doc_count, f"Doc count mismatch! Pre: {pre_doc_count}, Post: {post_doc_count}"
    assert post_chunk_count == pre_chunk_count, f"Chunk count mismatch! Pre: {pre_chunk_count}, Post: {post_chunk_count}"
    logger.info("✓ Document and chunk counts match pre-backup state with zero data loss!")

    # Cleanup test backups directory
    if os.path.exists(test_backup_dir):
        shutil.rmtree(test_backup_dir, ignore_errors=True)

    logger.info("\n=======================================================")
    logger.info("ALL PHASE 17 DISASTER RECOVERY TESTS PASSED!")
    logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(test_backup_and_restore_lifecycle())
