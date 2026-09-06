import os
import sys
import shutil
import sqlite3
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.pipeline import IngestionPipeline
from db.session import async_session_factory
from api.routers.health import get_full_rag_status

async def test_duplicate_bypass():
    # 1. Pick a file that is already 'done' in manifest_entries
    conn = sqlite3.connect('university_rag.db')
    cursor = conn.cursor()
    row = cursor.execute("SELECT path FROM manifest_entries WHERE status = 'done' LIMIT 1").fetchone()
    conn.close()

    if not row or not os.path.exists(row[0]):
        print("No valid source file found in manifest")
        return

    src_path = row[0]
    print(f"Using known completed source file: {src_path}")

    # 2. Create a duplicate copy in a temporary test directory
    test_dir = os.path.abspath("data/test_dup_dir")
    os.makedirs(test_dir, exist_ok=True)
    dup_file = os.path.join(test_dir, "identical_duplicate_copy.pdf")
    shutil.copyfile(src_path, dup_file)
    print(f"Created duplicate copy: {dup_file}")

    try:
        async with async_session_factory() as session:
            res = await IngestionPipeline.process_file(dup_file, session)
            print(f"Pipeline Result: {res}")
            assert res.get("status") == "skipped", f"Expected status 'skipped', got {res}"
            assert res.get("reason") == "duplicate_skipped", f"Expected reason 'duplicate_skipped', got {res}"

        # 3. Verify in full RAG status
        status = await get_full_rag_status()
        dup_count = status.pipeline.files_skipped_duplicate
        print(f"Live RAG Status - files_skipped_duplicate: {dup_count}")
        assert dup_count >= 1, "Duplicate skipped counter should be >= 1"

        print("=== ALL DUPLICATE BYPASS ASSERTIONS PASSED SUCCESSFULLY! ===")
    finally:
        # Cleanup
        if os.path.exists(dup_file):
            os.remove(dup_file)
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)

        # Remove duplicate entry from manifest so it leaves no test debris
        conn = sqlite3.connect('university_rag.db')
        c = conn.cursor()
        c.execute("DELETE FROM manifest_entries WHERE path = ?", (dup_file,))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    asyncio.run(test_duplicate_bypass())
