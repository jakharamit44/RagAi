# Enterprise University RAG Platform - Fixes Report

This document outlines the 8 critical issues that have been addressed in the Enterprise University RAG Platform.

## 1. Qdrant Lock Memory Fallback
**Issue:** Qdrant lock silently fell back to `:memory:`, splitting the database between FastAPI and Celery.
**Fix:** Removed the silent `try-except` fallback block in `api/rag/qdrant_store.py`. If Qdrant is locked or inaccessible via local path, the system will now explicitly raise an error rather than creating split-brain in-memory instances.

## 2. FolderWatcher Skipping Vector Indexing
**Issue:** `FolderWatcher` was calling `IngestionPipeline.process_file` directly, which chunks text into the DB but skips the embedding and Qdrant indexing steps handled by Celery.
**Fix:** Updated `ingestion/folder_watcher.py` (`ingest_single` and `reconcile_folder` methods) to dispatch the Celery background task `process_document_pipeline.delay()` instead of calling the pipeline synchronously.

## 3 & 4. Qdrant Point ID Mismatches & Collisions
**Issue:**
- Deletion endpoints used UUIDs (`Chunk.id`) to delete vectors, but ingestion used deterministic integers.
- Point IDs were generated via modulo 10 million, guaranteeing vector overwrite collisions after ~3,000 documents.
**Fix:** Updated `workers/ingest_tasks.py` to use `str(chunk.id)` (the UUID from the database) as the Qdrant point ID. This resolves both the deletion mismatch (since deletions already expect UUIDs) and the collision vulnerability completely.

## 5. BM25 In-Memory Index Desynchronization
**Issue:** The BM25 lexical index was strictly in-memory. Celery updated its own worker-local instance, leaving the FastAPI web process unaware of newly ingested documents.
**Fix:** Modified `ensure_loaded()` in `api/rag/bm25_index.py` to compare the memory state against the current database chunk count (`SELECT COUNT(id) FROM chunks`). If the count changes due to Celery processing, the FastAPI process will instantly and automatically reload the BM25 index from SQLite.

## 6. Path Traversal Vulnerability via File Uploads
**Issue:** File uploads were vulnerable to path traversal due to unsanitized use of `file.filename` when saving uploaded files.
**Fix:** Applied `os.path.basename()` to `file.filename` in `api/routers/documents.py` to safely extract just the filename and prevent `../` attacks on the host filesystem.

## 7. ManifestManager TOCTOU Race Condition
**Issue:** `ManifestManager` had a Time-Of-Check to Time-Of-Use race condition when the watchdog fired multiple concurrent `on_modified` events, leading to duplicated chunks.
**Fix:** Introduced an `asyncio.Lock` in `ingestion/manifest.py` to serialize concurrent requests. Modified `should_process` to atomically verify the status and commit the `processing` status *before* releasing the lock, fully neutralizing the TOCTOU flaw.

## 8. Purge Endpoint Missing Vector Deletion
**Issue:** The `/purge` endpoint deleted relational DB records but forgot to call Qdrant to purge the corresponding vectors.
**Fix:** Updated `purge_corpus` in `api/routers/admin_governance.py`. The endpoint now extracts the associated chunk IDs for the deleted documents and invokes `qdrant_store.client.delete()` to purge the vectors before cascading the database deletions.

## API & Security Improvements (Sep 2026)
- **Rate Limiting**: Added strict endpoint rate-limiting to SSO login via existing custom sliding-window limiter to prevent brute-force attacks.
- **Input Validation**: Hardened Pydantic models in `admin_governance.py` (`ApiKeyCreateRequest`, `UrlRuleCreateRequest`) with strict length, range, and regex pattern constraints.
- **Secure Headers (CORS/HSTS)**: Modified CORS wildcard defaults to strict host list in configuration and reinforced Strict-Transport-Security (HSTS) with `preload`. Added Content-Security-Policy (CSP) headers in core middleware.
- **Endpoint Security**: Verified RBAC dependencies across routers and ensured auth checks cascade cleanly over administrative and student endpoints.

## Performance & Stability Optimizations
**1. N+1 Query Optimization:**
Refactored the /api/v1/documents endpoint to use an optimized LEFT JOIN with GROUP BY, avoiding a correlated subquery execution for every row in the pagination slice.

**2. Celery Worker Stability:**
Enhanced all background Celery tasks (ingest_tasks, ocr_tasks, embed_tasks, index_tasks) with cks_late=True, max_retries=3, and 
etry_backoff=True to ensure idempotency and prevent task loss during worker crashes.

**3. Caching:**
Maintained Redis-backed semantic caching for student queries (/ask) with fallback to bounded in-memory LRU cache. Ensured dynamic system settings are actively cached during startup to prevent repetitive DB queries.


## Admin UI Enhancements
- **System Settings Tab**: Added a new UI tab for managing global configuration like OpenAI Fallback Keys and Auto-purge settings.
- **Document Upload Feature**: Added an Upload Document button to the Document Catalog toolbar to support manual single-file ingestion.
- **Visual Bug Fix**: Fixed a CSS specificity issue where Tailwind inline border-transparent class overrode the custom .tab-active highlight style, causing the active tab indicator to be invisible.
