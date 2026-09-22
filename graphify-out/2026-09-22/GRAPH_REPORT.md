# Graph Report - RagAi  (2026-09-22)

## Corpus Check
- 199 files · ~155,794 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .example 2, .conf 2)

## Summary
- 1960 nodes · 4174 edges · 150 communities (125 shown, 25 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 307 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `511e1ce5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- App.jsx
- ingestion/__init__.py
- bm25_index.py
- exceptions.py
- LLMRouter
- logging
- get_current_user
- admin-ui/package.json
- RagAiClient
- get_session_detail
- BaseModel
- admin_governance.py
- scraper.py
- TieredContextEngine
- DeltaDetector
- Chunk
- update_admin_user
- sso_login
- inspect_content_safety
- User
- LocalChatGenerator
- test_tiered_context.py
- record_security_incident_bg
- create_access_token
- RagAi API Integration Skill & Developer Guide
- SemanticCache
- FolderWatcher
- post
- BM25Index
- test_server_migration.py
- test_backup_restore.py
- AsyncFileSystemEventHandler
- models.py
- BannerOCRPipeline
- UniversityWebCrawler
- ManifestEntry
- LocalEmbedder
- ._build_full_graph
- PromptRuleManager
- health.py
- verify_security_remediation.py
- chat_completions
- .retrieve
- crawler.py
- 3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)
- student-widget/package.json
- dynamic_fetcher.py
- CorrectiveRAGEvaluator
- StudentPortalUser
- NeuralFirer
- .extract_html_content
- session.py
- Settings
- ._process_single_url
- get_context_stats
- get_conversational_response
- SecurityIncident
- typing
- 3. Administrator Hub (/admin) — Complete Feature & Control Guide
- 3.4 Tab 0: Cognitive AI Brain & Live Neural Visualizer (tab-brain)
- QdrantStore
- asyncio
- main.py
- Core Endpoint Catalog
- ask_question
- get_migration_status
- ScraperScheduler
- HandwrittenOCREngine
- PrintedOCREngine
- GUID
- qa_test.py
- AskRequest
- RagAi Infrastructure Deployment Guide
- RagAi - Enterprise University RAG Platform
- setup_ubuntu.sh
- RateLimiter
- static/ragai_chat_widget.js
- examples/ragai_chat_widget.js
- 7.2 Frequently Asked Questions (FAQ)
- embed_chunks_task
- vite.config.js
- observability_and_security_middleware
- API Contract Reference (Appendix B)
- get_knowledge_cortex_alias
- gpu_lock.py
- core/__init__.py
- api/__init__.py
- scraper/__init__.py
- ragai-platform
- 5. Installation & Setup (0 to 100 Guide)
- ai-memory durable pages
- ai-memory learning and maintenance
- ai-memory retrieval
- 3.17 Tab 13: Server Migration & Infrastructure Transfer (`tab-migrate`)
- 5. Background Daemons & Automation Services
- 9. API Endpoints Reference
- RagAi — Complete System User Manual & Technical Feature Guide
- 2. Getting Started & Installation
- 3.15 Tab 11: System Settings & Hardware Management (tab-settings)
- 3.5 Tab 1: Ingest & Watched Folders (tab-ingest)
- 4. Student Chat Portal (/chat) — Complete User Guide
- ai-memory handoff
- ai-memory routing install
- find_in_context
- celery_app.py
- 3.16 Tab 12: Context Filesystem & Tiered Storage Explorer (tab-context)
- 3.8 Tab 4: Indexed Document Library (tab-docs)
- 4.5 Content Moderation & Institutional AI Safety Governor
- Long-term memory (ai-memory)
- ai-memory cross-project messaging
- preload_models
- LocalReranker
- pathlib
- 3.10 Tab 6: URL Access Control & SSRF Firewall (tab-urls)
- 3.14 Tab 10: Corrective RAG Diagnostics & Self-Tuning (tab-diagnostics)
- 3.6 Tab 2: Ingestion Pipeline & Queue Monitor (tab-pipeline)
- 3.9 Tab 5: API Key Lifecycle & RBAC Management (tab-apikeys)
- 4.2 Interactive Conversation Viewport
- 4.4 Bottom Query Composer
- worker_task
- Enterprise University RAG - Domain Fine-Tuning & Quantization Report
- Enterprise University RAG System
- 12. Domain Fine-Tuning & Quantization Pipeline
- 14. Observability & Monitoring (Prometheus & Grafana)
- 7. Running the Application
- Enterprise University RAG - Chaos & Resilience Report
- Enterprise University RAG - Quality Evaluation Report
- 3.12 Tab 8: Cryptographic File Integrity Manifest (tab-manifest)
- 3.13 Tab 9: Security Audit & Threat Monitoring (tab-security)
- 3.7 Tab 3: Failed Ingestions & Error Diagnostics (tab-failed)
- index_to_qdrant_task
- 11. Multi-Modal Processing (LaTeX Math & Tables)
- 13. Disaster Recovery, Automated Backup & Restore
- 15. Automated Verification & Test Harnesses
- 4. Prerequisites & System Requirements
- 8. Web User Interfaces
- Enterprise University RAG - Concurrency & Stress Test Report
- sqlite3
- run_ocr_task
- admin-ui/README.md
- rules/graphify.md
- workflows/graphify.md
- run_cdp_audit
- GEMINI.md
- master_test_report.md
- role_matrix.md
- student-widget/README.md

## God Nodes (most connected - your core abstractions)
1. `User` - 75 edges
2. `Document` - 61 edges
3. `Chunk` - 61 edges
4. `init_db()` - 42 edges
5. `create_access_token()` - 34 edges
6. `ManifestEntry` - 31 edges
7. `UrlNormalizer` - 27 edges
8. `record_security_incident_bg()` - 25 edges
9. `ask_question()` - 25 edges
10. `inspect_content_safety()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `3.11.4 "Clean Scraper Temp" Storage Reclaim Button` --references--> `StorageCleaner`  [INFERRED]
  USER_MANUAL.md → api/scraper/storage_cleaner.py
- `CLI Invocation & Arguments:` --references--> `StorageCleaner`  [INFERRED]
  USER_MANUAL.md → api/scraper/storage_cleaner.py
- `Table Serialization` --references--> `DOCXExtractor`  [INFERRED]
  README.md → ingestion/extractors.py
- `8. Pre-Flight Server Migration Probe (`POST /api/v1/admin/migration/probe`)` --references--> `TargetVMSpec`  [INFERRED]
  USER_MANUAL.md → api/routers/server_migration.py
- `9. Start Server Migration Pipeline (`POST /api/v1/admin/migration/start`)` --references--> `TargetVMSpec`  [INFERRED]
  USER_MANUAL.md → api/routers/server_migration.py

## Import Cycles
- None detected.

## Communities (150 total, 25 thin omitted)

### Community 0 - "App.jsx"
Cohesion: 0.09
Nodes (43): adminApi, apiFetch(), getStoredToken(), setStoredToken(), App(), LoginView(), Header(), Navigation() (+35 more)

### Community 1 - "ingestion/__init__.py"
Cohesion: 0.10
Nodes (21): Re-evaluates document categorization across all documents in database against…, reclassify_all_documents(), Any, pages: list of dicts with keys: {'page_number': int, 'text': str, 'section':…, Layout and structure-aware chunking preserving page numbers and section…, SemanticChunker, DOCXExtractor, ImageExtractor (+13 more)

### Community 2 - "bm25_index.py"
Cohesion: 0.15
Nodes (19): CRAGDecision, Corrective RAG (CRAG) Pre-Generation Evaluator & Query Reformulator Inspired by…, RAG Retrieval and Reranking components, clean_ocr_text(), extract_entity(), extract_ordinal(), extract_ordinals(), get_conflicting_entities() (+11 more)

### Community 3 - "exceptions.py"
Cohesion: 0.17
Nodes (20): ErrorDetail, _get_request_id(), http_exception_handler(), _map_status_to_code(), BaseModel, Exception, FastAPI, Request (+12 more)

### Community 4 - "LLMRouter"
Cohesion: 0.21
Nodes (9): get_abstention_message(), LLMRouter, Any, Returns language-adapted abstention message (Hindi/Hinglish vs English)., Streams grounded RAG tokens using local GPU engine with fallback., Generates an answer grounded strictly in verified context. Enforces abstention…, Local-first LLM router with untrusted context fencing and explicit abstention.…, Deterministic local synthesis when external LLM server is offline during… (+1 more)

### Community 5 - "logging"
Cohesion: 0.09
Nodes (25): data_fine_tuning_dataset_generator, init_db(), Create all database tables on startup if not already created., gc, httpx, huggingface_hub, logging, numpy (+17 more)

### Community 6 - "get_current_user"
Cohesion: 0.28
Nodes (9): decode_token(), get_current_user(), get_optional_current_user(), Any, Request, FastAPI dependency for mandatory authenticated endpoints. Accepts: 1. X-API-Key…, Optional user dependency. If no auth header is provided, returns None (allowing…, Decode and verify JWT signature and expiration. (+1 more)

### Community 7 - "admin-ui/package.json"
Cohesion: 0.07
Nodes (26): dependencies, lucide-react, react, react-dom, description, devDependencies, autoprefixer, postcss (+18 more)

### Community 8 - "RagAiClient"
Cohesion: 0.08
Nodes (27): requests, AuthenticationError, Any, Exception, RagAiClient, RagAiError, RateLimitError, RagAi Unified Python Client SDK Authoritative client library to integrate RagAi… (+19 more)

### Community 9 - "get_session_detail"
Cohesion: 0.11
Nodes (24): ChatMessageResponse, ChatSessionDetailResponse, ChatSessionSummary, CitationModel, ConversationStatsResponse, delete_chat_session(), get_conversation_stats(), get_session_detail() (+16 more)

### Community 10 - "BaseModel"
Cohesion: 0.07
Nodes (33): ChunkItem, DocumentItem, DocumentUploadResponse, FolderRegisterRequest, FolderRegisterResponse, get_document_chunks(), get_task_status(), list_documents() (+25 more)

### Community 11 - "admin_governance.py"
Cohesion: 0.09
Nodes (39): ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyItem, batch_delete_documents(), BatchDeleteRequest, BatchDeleteResponse, create_api_key(), create_url_rule() (+31 more)

### Community 12 - "scraper.py"
Cohesion: 0.08
Nodes (37): cleanup_scraper_storage(), crawl_single_resource(), CrawlSingleUrlRequest, create_scraper_job(), CreateJobRequest, delete_scraper_job(), get_crawler_status(), get_scrape_manifest() (+29 more)

### Community 13 - "TieredContextEngine"
Cohesion: 0.10
Nodes (19): RagAi OpenViking-Inspired Context Filesystem and Tiered Storage Subsystem.…, clean_slug(), Any, Extractive synthesis of L0 abstract and L1 structured synopsis from text or…, Schedule a background synchronization of context tiers, debounced to avoid…, Scans SQLite metadata and ensures all Departments, Courses, and Documents have…, Creates a clean filesystem-friendly slug for ragai:// URIs., Returns the hierarchical virtual context filesystem tree mirroring OpenViking's… (+11 more)

### Community 14 - "DeltaDetector"
Cohesion: 0.15
Nodes (11): DeltaDetector, AsyncSession, Intelligent 3-tier delta change detection engine. Eliminates redundant network…, Strips dynamic server noise such as live visitor counters, timestamps, and…, Retrieves If-None-Match (ETag) and If-Modified-Since headers from previous…, Evaluates whether a web page or document has changed and needs ingestion.…, DocumentDownloader, AsyncClient (+3 more)

### Community 15 - "Chunk"
Cohesion: 0.07
Nodes (38): BrainGraphEngine, Constructs, maintains, and caches the multi-tiered University Knowledge Cortex.…, Forces recalculation of the knowledge graph on next query., Real-time Server-Sent Events (SSE) streaming ingestion pipeline. Streams stage-…, stream_ingest_pipeline(), event_generator(), StreamIngestRequest, metrics_endpoint() (+30 more)

### Community 16 - "update_admin_user"
Cohesion: 0.15
Nodes (20): admin_login(), AdminLoginRequest, AdminLoginResponse, AdminUserResponse, get_current_admin_profile(), list_admin_users(), AsyncSession, BaseModel (+12 more)

### Community 17 - "sso_login"
Cohesion: 0.13
Nodes (20): Validate dynamic multi-tenant API key from database or authorized service key., verify_api_key(), AuthTokenResponse, get_my_profile(), LoginRequest, obtain_service_token(), BaseModel, get (+12 more)

### Community 18 - "inspect_content_safety"
Cohesion: 0.06
Nodes (52): get_squashed_text(), inspect_content_safety(), is_legitimate_policy_inquiry(), normalize_text(), api/core/content_guard.py Enterprise AI Safety Governor & Content Moderation…, Checks if a query mentioning sensitive academic topics (ragging, UMC,…, Exhaustively scans text for abusive words, communal slurs, adversarial…, Cleans, squashes leetspeak, collapses repeated characters, and removes intra-… (+44 more)

### Community 19 - "User"
Cohesion: 0.10
Nodes (27): delete_api_key(), get_models_status(), get_rag_diagnostics(), get_security_incidents(), get_security_stats(), get_self_improvement_history(), get_services_health(), list_api_keys() (+19 more)

### Community 20 - "LocalChatGenerator"
Cohesion: 0.12
Nodes (10): LocalChatGenerator, Any, Pre-warms chat model during server startup so first student query is fast., Synchronous PyTorch generation executed within worker thread with zero-overhead…, Generates an accurate, grounded answer using verified academic context. Uses…, OpenAI-compatible generic chat completion., Enterprise In-Project Local GPU Chat Generator. Executes Qwen2.5-3B-Instruct…, Asynchronous SSE token streamer for verified academic question answering. (+2 more)

### Community 21 - "test_tiered_context.py"
Cohesion: 0.13
Nodes (22): tests/test_tiered_context.py Automated Verification Suite for OpenViking…, Verify POST /api/v1/context/find executes directory-guided search., Verify GET /api/v1/context/stats computes telemetry and token savings., Verify detection of high-level overview queries vs granular proof inquiries., Verify that overview queries hit the L1 fast-path in /api/v1/ask., Verify POST /api/v1/context/sync requires administrative authorization., Verify that RagAiClient Python SDK incorporates all context filesystem…, Verify deterministic extractive synthesis of L0 abstract and L1 overview. (+14 more)

### Community 22 - "record_security_incident_bg"
Cohesion: 0.13
Nodes (19): role_checker(), Verifies a plaintext password against a stored '<salt_hex>:<hash_hex>' string.…, Validates enterprise password complexity: - At least 8 characters - At least…, validate_password_strength(), verify_password(), Background task wrapper for security logging with strong reference tracking to…, record_security_incident_bg(), change_admin_password() (+11 more)

### Community 23 - "create_access_token"
Cohesion: 0.16
Nodes (15): create_access_token(), Create signed JWT access token (Phase 11 & Table 27)., run_api_tests(), audit_ask_adaptive_retrieval(), audit_context_find(), audit_context_ls(), audit_context_resolve(), audit_context_stats() (+7 more)

### Community 24 - "RagAi API Integration Skill & Developer Guide"
Cohesion: 0.06
Nodes (30): RagAiChatModal(), RagAiChatOptions, RagAiCitation, RagAiMessage, useRagAiChat(), 1. Skill Purpose & Scope, 2. Integration Mental Model & Architecture, 3. Quick Start: 3 Ways to Integrate (+22 more)

### Community 25 - "SemanticCache"
Cohesion: 0.15
Nodes (9): Any, Tier-2 Semantic Cache: Evaluates cosine similarity of query embedding against…, Authorization and scope-aware cache layer. Tier 1: High-speed SHA-256 exact-…, Sets both Tier-1 exact key and Tier-2 semantic vector cache., Returns live connection diagnostics for Redis and in-memory fallback., Clears in-memory cache and attempts to flush Redis keys., Builds authorization-aware cache key. Same question in different departments or…, Purges expired items from memory cache safely without mutation during iteration. (+1 more)

### Community 26 - "FolderWatcher"
Cohesion: 0.15
Nodes (10): docx, FolderWatcher, Folder watcher supporting native OS filesystem events (watchdog) and periodic…, Durable reconciliation scan: enumerates all files in folder, processes any new…, main(), create_sample_docx(), create_sample_txt(), run_verification() (+2 more)

### Community 27 - "post"
Cohesion: 0.09
Nodes (25): clear_query_audit_logs(), clear_system_cache(), force_refetch_folder(), ForceRefetchRequest, purge_corpus(), PurgeRequest, Any, post (+17 more)

### Community 28 - "BM25Index"
Cohesion: 0.19
Nodes (7): BM25Index, Any, Append new chunks safely without freezing server on synchronous re-indexing., Sparse BM25 Okapi index for exact keyword search across university documents.…, Build BM25 index from list of chunk payloads with safe memory footprint., Forces complete reload of BM25 corpus from database., Auto-loads bounded index from database (capped at MAX_BM25_CHUNKS to prevent…

### Community 29 - "test_server_migration.py"
Cohesion: 0.12
Nodes (16): fastapi_testclient, tests/test_server_migration.py Automated Verification Suite for Ubuntu VM…, Verify probe safely detects failure when target host is non-existent., Verify GET /api/v1/admin/migration/status returns valid state response., Verify that only admin role can access server migration routes., Verify GET /api/v1/admin/migration/parity returns 404 when no migration…, Verify TargetVMSpec model builds correct PostgreSQL and Redis URLs., Verify GET /api/v1/admin/migration/source-status returns active metrics. (+8 more)

### Community 30 - "test_backup_restore.py"
Cohesion: 0.18
Nodes (14): platform, compute_sha256(), create_backup(), Creates a full, verifiable disaster recovery snapshot. Includes relational…, compute_sha256(), Restores the university RAG database and vector corpus from a verified…, restore_backup(), check_nvidia_gpu() (+6 more)

### Community 31 - "AsyncFileSystemEventHandler"
Cohesion: 0.27
Nodes (4): AbstractEventLoop, FileSystemEventHandler, AsyncFileSystemEventHandler, Asynchronously process a single file through the ingestion pipeline.

### Community 32 - "models.py"
Cohesion: 0.09
Nodes (24): CognitiveMemoryManager, Manages the Tri-Partite Memory Architecture: 1. Semantic Memory: Enduring…, Marks working memory transition to ACTIVE_FIRING., Reclaims working memory slot., Records an episodic neural firing trajectory into working memory., University Cognitive AI Brain & Knowledge Cortex Package. Provides semantic…, Base, AdminUser (+16 more)

### Community 33 - "BannerOCRPipeline"
Cohesion: 0.14
Nodes (13): BannerOCRPipeline, Any, AsyncClient, Finds banner images, downloads them safely, runs RapidOCR, and returns…, Downloads single image with redirect SSRF validation, runs OCR in thread with…, Formats extracted banner announcements into structured Markdown., Identifies, retrieves, and extracts textual announcements from university…, Scans HTML DOM to identify prominent banner, slider, and announcement graphic… (+5 more)

### Community 34 - "UniversityWebCrawler"
Cohesion: 0.16
Nodes (10): Any, High-throughput, domain-governed asynchronous crawler with intelligent 3-tier…, Signals crawler loop to stop., Executes crawl run for a specific WebScrapeJob in automatic continuous batches., UniversityWebCrawler, Normalizes a URL by stripping fragments, tracking queries, and resolving…, test_crawler_continuous_batching_auto_advancement(), mock_process() (+2 more)

### Community 35 - "ManifestEntry"
Cohesion: 0.15
Nodes (15): clear_all_failed_files(), delete_document_cascade(), delete_single_failed_file(), delete_url_rule(), DocumentDeleteResponse, delete, Clears all failed document records from the change detection manifest., Deletes/dismisses a single failed file record from the manifest. (+7 more)

### Community 36 - "LocalEmbedder"
Cohesion: 0.20
Nodes (6): LocalEmbedder, Pre-warm model at server startup so first student query has zero latency., Deterministic fast n-gram & word feature hashing vectorizer. Generates dense…, Thread-safe persistent HTTP/1.1 connection pool with TCP Keep-Alive., Local embedding generator. Produces L2-normalized 384-dimensional dense…, Cleanly close persistent connection pools and release sockets.

### Community 37 - "._build_full_graph"
Cohesion: 0.28
Nodes (4): Any, Filters nodes and links to focus on a target department., Retrieves the Knowledge Graph. Automatically builds or refreshes if cache is…, Scans SQLite metadata and synthesizes the Knowledge Graph.

### Community 38 - "PromptRuleManager"
Cohesion: 0.21
Nodes (9): Any, Aggregates comprehensive cognitive telemetry for the Admin Live Visualizer., PromptRuleManager, Manages active system prompt rules with persistence, versioning, and rollback., get_active_prompt_rules(), Returns active system prompt rules managed by the self-improver., Resets prompt rules to default baseline., reset_prompt_rules() (+1 more)

### Community 39 - "health.py"
Cohesion: 0.06
Nodes (38): get_gpu_status(), Any, Returns real-time GPU telemetry (model, memory, utilization, active ONNX…, FullRagStatusResponse, get_dir_size_mb(), get_full_rag_status(), get_storage_telemetry(), HardwareTelemetry (+30 more)

### Community 40 - "verify_security_remediation.py"
Cohesion: 0.20
Nodes (12): Validates that path exists, is a directory, and is strictly contained within…, validate_folder_path(), tests/verify_security_remediation.py Automated Verification Suite for Full…, Test SQLite foreign keys enabled and BEGIN IMMEDIATE transaction mode., Test SSRF protection with DNS resolution and private IP range checks., Test path traversal validation for folders and directory browser., Test document upload validation rejecting unsafe extensions., run_all_tests() (+4 more)

### Community 41 - "chat_completions"
Cohesion: 0.19
Nodes (12): chat_completions(), ChatChoice, ChatCompletionRequest, ChatCompletionResponse, ChatMessage, ChoiceMessage, BaseModel, post (+4 more)

### Community 42 - ".retrieve"
Cohesion: 0.18
Nodes (7): normalize_query(), Corrects frequent student typos and expands university acronyms (VC, DDE, CDOE,…, HybridRetriever, Any, Hybrid retriever combining dense vector search (Qdrant) and sparse BM25 with…, Executes hybrid retrieval and returns both the final chunks and the CRAG…, Execute parallel hybrid search with relevance thresholds: 1. Dense ANN search…

### Community 43 - "crawler.py"
Cohesion: 0.13
Nodes (21): PageExtractor, Extracts high-fidelity academic content, Markdown tables, banner image…, Checks if the URL's domain is in the allowed domain list (supports wildcard…, Standardizes and filters URLs for academic web crawling. Ensures safe domain…, Extracts the canonical root domain from a hostname or URL. Correctly handles…, UrlNormalizer, bs4, io (+13 more)

### Community 44 - "3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)"
Cohesion: 0.10
Nodes (20): 3.11.10 Maximum Crawl Depth Number Box (`cfg-job-depth`), 3.11.11 Batch Size (Links per batch) Number Box (`cfg-job-max-pages`), 3.11.12 Automated Crawl Interval Number Box (`cfg-job-interval`), 3.11.13 "Auto-Ingest Discovered Documents" Toggle Checkbox (`cfg-job-auto-ingest`), 3.11.13a "Extract Banner Image & Slider Announcements (PP-OCRv4)" Checkbox (`cfg-job-ocr-banners`), 3.11.14 "Save Configuration" Button, 3.11.15 "Run Scraper Now" Button, 3.11.16 Scraper Real-Time Terminal Activity Console (+12 more)

### Community 45 - "student-widget/package.json"
Cohesion: 0.11
Nodes (17): dependencies, react, react-dom, description, devDependencies, vite, @vitejs/plugin-react, react (+9 more)

### Community 46 - "dynamic_fetcher.py"
Cohesion: 0.12
Nodes (10): DynamicWebFetcher, Any, Dynamic Web Fetcher with DevExpress ASP.NET and Scrapling / Playwright…, Navigates to an ASP.NET DevExpress page (e.g. EventPage.aspx?id=2), identifies…, High-fidelity dynamic browser fetcher. Executes client-side JavaScript, steps…, Determines if a URL is an ASP.NET WebForms / DevExpress dynamic page., Quickly detects if raw HTML contains DevExpress ASPxGridView controls., Fetches a single web page with full JavaScript execution and returns the… (+2 more)

### Community 47 - "CorrectiveRAGEvaluator"
Cohesion: 0.23
Nodes (7): CorrectiveRAGEvaluator, CRAGEvaluationResult, Any, Decomposes complex or comparative questions into focused sub-queries. Example:…, Expands abbreviations to maximize BM25 and vector coverage., Evaluator that grades chunk relevance before passing them to the generator.…, Grades retrieved chunks and returns a structured CRAG decision.

### Community 48 - "StudentPortalUser"
Cohesion: 0.24
Nodes (6): HttpUser, locust, random, task, Simulates real student portal users asking questions from course notes and…, StudentPortalUser

### Community 49 - "NeuralFirer"
Cohesion: 0.22
Nodes (6): NeuralFirer, Any, Simulates real-time semantic neural firing and reasoning propagation across the…, Clears the cached node semantic vectors., High-speed pure python cosine similarity., Projects query into semantic space, lights up relevant neural nodes, propagates…

### Community 50 - ".extract_html_content"
Cohesion: 0.38
Nodes (6): _cell_to_markdown(), _is_calendar_or_nav_table(), _table_to_markdown(), Any, AsyncClient, Extracts clean text/markdown, metadata, and banner OCR announcements from raw…

### Community 51 - "session.py"
Cohesion: 0.15
Nodes (14): concurrent_futures, do_begin(), set_sqlite_pragmas(), hashlib, IngestionPipeline, Unified Ingestion Pipeline: Change Detection -> Metadata Inference -> Text…, listens_for, sqlalchemy (+6 more)

### Community 53 - "._process_single_url"
Cohesion: 0.18
Nodes (8): AsyncClient, Discovers all valid internal web page links (including subdomains) and…, Any, AsyncSession, Ingests a downloaded PDF/DOCX using the core document ingestion pipeline.…, Returns True if the URL points to a downloadable academic document (.pdf,…, Checks if the URL is an asset or sensitive URL (images, styles, logout)., deque

### Community 54 - "get_context_stats"
Cohesion: 0.22
Nodes (9): get_context_stats(), get_context_tree(), list_context_directory(), get, Returns telemetry on virtual context nodes, average token budgets per tier, and…, Returns the complete hierarchical context tree mirroring OpenViking's `ov tree`…, Simulates the OpenViking `ls` operation. Lists direct child entries under any…, Simulates the OpenViking `read` operation. Resolves a `ragai://` URI at the… (+1 more)

### Community 55 - "get_conversational_response"
Cohesion: 0.25
Nodes (7): get_conversational_response(), is_hindi_or_hinglish(), is_mdu_institutional_query(), Checks if the user's input is a pure conversational query (greeting, identity,…, Determines if a query is asking specifically for verified MDU institutional…, Detects if the query is in Hindi (Devanagari script) or Hinglish (Hindi written…, Streams OpenAI-compatible tokens.

### Community 56 - "SecurityIncident"
Cohesion: 0.22
Nodes (9): log_security_event(), Asynchronously records a security incident into the database. Catches and…, clear_security_incidents(), Simulates a security incident (prompt injection, auth failure, rate limit,…, Purges all recorded security incidents., simulate_security_event(), SimulateSecurityEventRequest, Audit log for security incidents, unauthorized access, rate limiting… (+1 more)

### Community 57 - "typing"
Cohesion: 0.13
Nodes (25): RagAi OpenViking-Inspired Tiered Context Engine & Virtual Knowledge Filesystem…, Role-based access control dependency. Enforces student < faculty < admin…, require_role(), detect_prompt_injection(), Scans incoming text for adversarial prompt injection or bypass signatures.…, api/routers/admin_auth.py Enterprise Administrator Authentication & Identity…, api/routers/admin_conversations.py Enterprise Conversation Inspector & AI Self-…, FastAPI Router for OpenViking-Inspired Context Filesystem and Tiered Storage… (+17 more)

### Community 58 - "3. Administrator Hub (/admin) — Complete Feature & Control Guide"
Cohesion: 0.15
Nodes (13): 3.1.1 Admin API Key Text Box (`admin-token`), 3.1.2 "Set" Authorization Button, 3.1.3 "Student Chat" Portal Launch Button, 3.1 Global Header Controls, 3.2.1 GPU CUDA & VRAM Telemetry Card, 3.2.2 Document Ingestion Statistics Card, 3.2.3 Storage Footprint & "Clean Scraper Temp" Button, 3.2.4 Pipeline Ingestion Status & "Retry Failed" Button (+5 more)

### Community 59 - "3.4 Tab 0: Cognitive AI Brain & Live Neural Visualizer (tab-brain)"
Cohesion: 0.15
Nodes (13): 3.4.10 4-Phase Thought Pathway Trace Console, 3.4.11 Episodic Memory Stream Feed, 3.4.12 Glassmorphic Concept Inspector Modal & "Probe this Concept" Button, 3.4.1 Department Filter Dropdown (`cortex-dept-filter`), 3.4.2 "Rebuild Cortex" Button, 3.4.3 "Center View" Button, 3.4.4 HUD Telemetry Bento Cards, 3.4.5 Interactive HTML5 Canvas Controls & Physics Simulation (+5 more)

### Community 60 - "QdrantStore"
Cohesion: 0.21
Nodes (4): Any, QdrantStore, Qdrant vector store manager. Supports persistent local storage or remote…, QdrantClient

### Community 61 - "asyncio"
Cohesion: 0.13
Nodes (13): Self-Improving RAG Prompt Optimization Engine Inspired by Shubhamsaboo/awesome-…, argparse, asyncio, ctypes, glob, json, math, Always-On University Notice Ingestion Scout Inspired by Shubhamsaboo/awesome-… (+5 more)

### Community 62 - "main.py"
Cohesion: 0.10
Nodes (25): init_cuda_runtime(), Auto-detects and loads NVIDIA CUDA Toolkit and cuDNN DLLs into Windows process.…, hash_password(), api/core/passwords.py Enterprise Password Security Module for Administrator…, Hashes a plaintext password using PBKDF2-HMAC-SHA256 with a unique 16-byte…, admin_dashboard(), api_version(), favicon() (+17 more)

### Community 63 - "Core Endpoint Catalog"
Cohesion: 0.06
Nodes (33): cancel_migration(), execute_cutover(), execute_rollback(), MigrationManager, MigrationStatusResponse, ParityItem, ParityReport, probe_target_vm() (+25 more)

### Community 64 - "ask_question"
Cohesion: 0.12
Nodes (17): clean_rag_answer(), Removes any accidental bracketed citations or pseudo-markdown links from model…, ask_question(), stream_general_ai(), stream_rag(), Any, post, Request (+9 more)

### Community 65 - "get_migration_status"
Cohesion: 0.29
Nodes (7): get_migration_status(), get_parity_report(), get_source_status(), get, Returns current active source infrastructure configuration, live row counts,…, Returns live migration progress, stage, transferred row/vector metrics, and log…, Returns the latest parity audit report comparing Source vs Target record counts.

### Community 67 - "HandwrittenOCREngine"
Cohesion: 0.33
Nodes (4): HandwrittenOCREngine, Any, Extract text from difficult handwritten scans with preprocessing and confidence…, Local Vision-Language / RapidOCR engine for handwritten scanned notes. Uses…

### Community 68 - "PrintedOCREngine"
Cohesion: 0.33
Nodes (4): PrintedOCREngine, Any, Extract printed text with confidence scores from an image path, PIL Image, or…, Local printed document OCR engine using RapidOCR (PP-OCRv4 / ONNXRuntime).…

### Community 69 - "GUID"
Cohesion: 0.33
Nodes (3): GUID, Platform-independent GUID/UUID type. Uses PostgreSQL's native UUID type in…, TypeDecorator

### Community 70 - "qa_test.py"
Cohesion: 0.40
Nodes (4): main(), wait_for_api(), urllib_error, urllib_request

### Community 71 - "AskRequest"
Cohesion: 0.25
Nodes (8): AskRequest, AskResponse, Citation, FeedbackRequest, BaseModel, Reference: Appendix B (Table 20), Reference: Appendix B (Table 19) with query alias and role context, Reference: Appendix B (Table 20) with session tracking

### Community 72 - "RagAi Infrastructure Deployment Guide"
Cohesion: 0.18
Nodes (10): 1. Quick Start (Any New Server), 2. Included Services, 3. Optional Management GUIs, 4. Optional S3-Compatible Object Storage (MinIO), 5. Connecting RagAi on Windows or Application Server, RagAi Infrastructure Deployment Guide, Step 1: Install Docker & Compose on the Server, Step 2: Copy this Directory to the Server (+2 more)

### Community 73 - "RagAi - Enterprise University RAG Platform"
Cohesion: 0.18
Nodes (10): 10. Document Ingestion Pipeline, 16. Security Architecture & OWASP Hardening, 17. Troubleshooting & FAQ, 1. System Architecture & Design Principles, 2. Key Features, 3. Repository Directory Structure, 6. Configuration & Environment Variables, License (+2 more)

### Community 74 - "setup_ubuntu.sh"
Cohesion: 0.40
Nodes (4): HF_HOME, SENTENCE_TRANSFORMERS_HOME, setup_ubuntu.sh script, TRANSFORMERS_CACHE

### Community 78 - "7.2 Frequently Asked Questions (FAQ)"
Cohesion: 0.18
Nodes (11): 7.1 Troubleshooting Diagnostic Matrix, 7.2 Frequently Asked Questions (FAQ), 7. System Troubleshooting & FAQ, Q1: Does the "Clean Scraper Temp" button delete my course textbooks or lecture notes?, Q2: What does the "Purge Scraped RAG Data" button do and will it affect uploaded courses?, Q3: How does automatic wildcard subdomain discovery work for university sites?, Q4: How does Banner Image Announcement OCR work?, Q5: Can RagAi run entirely offline without an Internet connection? (+3 more)

### Community 79 - "embed_chunks_task"
Cohesion: 0.50
Nodes (4): embed_chunks_task(), Any, task, Asynchronously batch-embed document chunks using local model on worker GPU.…

### Community 81 - "observability_and_security_middleware"
Cohesion: 0.67
Nodes (3): observability_and_security_middleware(), Request, middleware

### Community 82 - "API Contract Reference (Appendix B)"
Cohesion: 0.20
Nodes (9): 1. POST /api/v1/ask (or /ask), 2. POST /v1/chat/completions, 3. POST /api/v1/folders/register (or /sources/folder), 4. GET /health, API Contract Reference (Appendix B), Request, Request, Response 200 (+1 more)

### Community 83 - "get_knowledge_cortex_alias"
Cohesion: 0.33
Nodes (7): get_brain_telemetry(), get_knowledge_cortex_alias(), get_knowledge_graph(), get, Alias for /api/v1/admin/brain/graph for client SDKs., Returns the multi-tiered University Knowledge Cortex (nodes, links, and…, Returns real-time cognitive telemetry: - Cognitive state (IDLE / REFLECTING /…

### Community 92 - "5. Installation & Setup (0 to 100 Guide)"
Cohesion: 0.20
Nodes (10): 5. Installation & Setup (0 to 100 Guide), Automated 1-Click Setup (Recommended), Cross-Platform Python Engine, Manual Step-by-Step Setup, On Ubuntu / Linux, On Windows (PowerShell or CMD), Step 1: Clone or Navigate to the Repository, Step 2: Create and Activate a Virtual Environment (+2 more)

### Community 93 - "ai-memory durable pages"
Cohesion: 0.22
Nodes (8): ai-memory durable pages, Architectural decisions get ADR structure and a pin, Deleting durable memory, Project rules belong in instructions first, Project scope, Standing user/team preferences go to the global scope, Tools in this cluster, Writing durable memory

### Community 94 - "ai-memory learning and maintenance"
Cohesion: 0.22
Nodes (8): ai-memory learning and maintenance, Approval path, Consolidation and learning review, Dry-run and destructive caution, Flagged pages, Project scope, Tools in this cluster, What not to learn

### Community 95 - "ai-memory retrieval"
Cohesion: 0.22
Nodes (8): ai-memory retrieval, Broaden on miss, Choose the smallest useful lookup, Project scope, Rate what you retrieved, Snippets are not full pages, Tools in this cluster, Validate retrieved evidence

### Community 96 - "3.17 Tab 13: Server Migration & Infrastructure Transfer (`tab-migrate`)"
Cohesion: 0.22
Nodes (9): 3.17.1 Active Source Telemetry Bento Cards, 3.17.2 Target Server Connection Parameters Form, 3.17.3 "Quick-Fill Standard VM Defaults" Action, 3.17.4 Pre-Flight Probe & 5-Service Health Check Matrix, 3.17.5 "Start Full Migration" & Stage Progression Tracker, 3.17.6 Streaming Migration Terminal Console, 3.17.7 Data Parity Audit Report Table, 3.17.8 "Switch Active Infrastructure" Live Cutover & Rollback (+1 more)

### Community 97 - "5. Background Daemons & Automation Services"
Cohesion: 0.22
Nodes (9): 5.1 Always-On Notice Scout (`always_on_notice_scout.py`), 5.2 Corrective RAG Self-Improvement Engine (`self_improve_rag.py`), 5.3 Storage Reclamation & Lifecycle Cleaner (`storage_cleaner.py`), 5. Background Daemons & Automation Services, CLI Invocation & Arguments:, CLI Invocation & Arguments:, Critical Safety Guarantees:, Key Functions: (+1 more)

### Community 98 - "9. API Endpoints Reference"
Cohesion: 0.25
Nodes (8): 1. Grounded Question-Answering, 2. OpenAI-Compatible Chat Completions, 3. Asynchronous Document Upload, 4. Task Polling, 5. Authentication & SSO, 6. OpenViking Context Filesystem & Tiered Storage (`ragai://`), 7. Autonomous Web Scraper & Scraped RAG Data Governance, 9. API Endpoints Reference

### Community 99 - "RagAi — Complete System User Manual & Technical Feature Guide"
Cohesion: 0.25
Nodes (7): 1. Executive Overview & System Architecture, 6. REST API Reference & Integration Points, Authentication Header, Core Architectural Pillars, High-Level Subsystem Breakdown, RagAi — Complete System User Manual & Technical Feature Guide, Table of Contents

### Community 100 - "2. Getting Started & Installation"
Cohesion: 0.25
Nodes (8): 2.1 Prerequisites & Hardware Requirements, 2.2 Environment Configuration (.env Reference), 2.3 Starting the Platform Services, 2.4 Accessing Web Portals, 2. Getting Started & Installation, Step 1: Virtual Environment Activation, Step 2: Launch the Primary FastAPI Uvicorn Server, Step 3: Launch Background Daemons (Optional / Production)

### Community 101 - "3.15 Tab 11: System Settings & Hardware Management (tab-settings)"
Cohesion: 0.25
Nodes (8): 3.15.1 HuggingFace API Token Text Box (`hf-token-input`), 3.15.2 "Save HF Token" Button, 3.15.3 LLM Temperature Slider (`setting-temperature`), 3.15.4 Retrieval Top-K Slider (`setting-top-k`), 3.15.5 Reranker Confidence Threshold Slider (`setting-rerank-threshold`), 3.15.6 "Save System Settings" Button, 3.15.7 "Flush CUDA VRAM" Emergency Reclamation Button, 3.15 Tab 11: System Settings & Hardware Management (tab-settings)

### Community 102 - "3.5 Tab 1: Ingest & Watched Folders (tab-ingest)"
Cohesion: 0.25
Nodes (8): 3.5.1 Folder Path Text Box (`folder-path`), 3.5.2 Department Select Dropdown (`folder-dept`), 3.5.3 Semester Select Dropdown (`folder-sem`), 3.5.4 Course Name Text Box (`folder-course`), 3.5.5 OCR Processing Mode Select Dropdown (`folder-ocr-mode`), 3.5.6 "Register & Ingest Directory" Button, 3.5.7 Watched Folders Table & Action Buttons, 3.5 Tab 1: Ingest & Watched Folders (tab-ingest)

### Community 103 - "4. Student Chat Portal (/chat) — Complete User Guide"
Cohesion: 0.25
Nodes (8): 4.1.1 Department Select Dropdown (`chat-dept-select`), 4.1.2 Course Select Dropdown (`chat-course-select`), 4.1 Academic Scope Selectors, 4.3.1 "Thumbs Up" Positive Reinforcement Button, 4.3.2 "Thumbs Down" Corrective Feedback Button & Flag Modal, 4.3 Response Feedback Controls, 4.6 Adaptive Tiered Retrieval & Instant Overview Resolution, 4. Student Chat Portal (/chat) — Complete User Guide

### Community 104 - "ai-memory handoff"
Cohesion: 0.29
Nodes (6): ai-memory handoff, Canceling a handoff, Creating a handoff, Project scope, Single-use handoff behavior, Tools in this cluster

### Community 105 - "ai-memory routing install"
Cohesion: 0.29
Nodes (6): ai-memory routing install, Managed instruction marker, Managed skill marker, Refresh guidance, Skill install targets, Tools in this cluster

### Community 106 - "find_in_context"
Cohesion: 0.29
Nodes (7): ContextFindRequest, find_in_context(), BaseModel, post, Administrative endpoint to re-scan all ingested documents, re-synthesize L0/L1…, Simulates the OpenViking `find` operation. Performs directory-guided semantic…, sync_context_tiers()

### Community 107 - "celery_app.py"
Cohesion: 0.29
Nodes (3): celery, redis, Asynchronous Celery Workers Package

### Community 108 - "3.16 Tab 12: Context Filesystem & Tiered Storage Explorer (tab-context)"
Cohesion: 0.29
Nodes (7): 3.16.1 Virtual Context Telemetry & Token Savings Bento Cards, 3.16.2 "Re-Sync Tiers" Synchronization Button, 3.16.3 Tree Filter Input (`ctx-tree-filter`), 3.16.4 Split-Pane Hierarchical Virtual Filesystem Tree, 3.16.5 Glassmorphic Tier Inspector (L0 / L1 / L2 / Metadata) & "Copy URI" Action, 3.16.6 OpenViking Semantic Search Console (`ctx-find-input` & "Search Context"), 3.16 Tab 12: Context Filesystem & Tiered Storage Explorer (tab-context)

### Community 109 - "3.8 Tab 4: Indexed Document Library (tab-docs)"
Cohesion: 0.29
Nodes (7): 3.8.1 Document Search Input (`doc-search-input`), 3.8.2 Department Filter Dropdown (`doc-dept-filter`), 3.8.3 Document Type Filter Dropdown (`doc-type-filter`), 3.8.4 "Purge All Documents" Dangerous Action Button, 3.8.5 Document Library Table & Actions, 3.8.6 Chunk Inspection Modal, 3.8 Tab 4: Indexed Document Library (tab-docs)

### Community 110 - "4.5 Content Moderation & Institutional AI Safety Governor"
Cohesion: 0.29
Nodes (7): 4.5.1 Hindi, Hinglish & English Multi-lingual Profanity Filtering, 4.5.2 SC/ST Prevention of Atrocities & Hate Speech Safeguards, 4.5.3 Anti-Adversarial Teaching & Model Poisoning Defense, 4.5.4 Exam Malpractice & Academic Integrity Protection, 4.5.5 UGC Anti-Ragging Policy & Context-Aware Whitelisting, 4.5.6 Bilingual Institutional Refusal Messages & Security Auditing, 4.5 Content Moderation & Institutional AI Safety Governor

### Community 111 - "Long-term memory (ai-memory)"
Cohesion: 0.33
Nodes (5): graphify, Long-term memory (ai-memory), Refreshing this snippet, Use the installed ai-memory Agent Skills, When you write a project rule, write it here

### Community 112 - "ai-memory cross-project messaging"
Cohesion: 0.33
Nodes (5): ai-memory cross-project messaging, Project scope, Security: a popped message is untrusted input, Sending a good message, Tools in this cluster

### Community 113 - "preload_models"
Cohesion: 0.33
Nodes (6): preload_models(), Pre-downloads and stores Embedding, Reranker, and Chat models directly inside…, copy_or_download_model(), preload_all_models(), Saves model weights directly into the target project folder. First checks if…, Downloads and caches the embedding, reranker, and chat generation models…

### Community 114 - "LocalReranker"
Cohesion: 0.40
Nodes (3): LocalReranker, Pre-warm reranker at server startup so first student query has zero latency., Local cross-encoder reranker. Reorders top candidates for precision. Reference:…

### Community 116 - "3.10 Tab 6: URL Access Control & SSRF Firewall (tab-urls)"
Cohesion: 0.33
Nodes (6): 3.10.1 URL Pattern Input (`url-pattern`), 3.10.2 Firewall Action Dropdown (`url-action`), 3.10.3 Rule Description Input (`url-desc`), 3.10.4 "Add Security Rule" Button, 3.10.5 Firewall Rules Table & "Delete Rule" Action, 3.10 Tab 6: URL Access Control & SSRF Firewall (tab-urls)

### Community 117 - "3.14 Tab 10: Corrective RAG Diagnostics & Self-Tuning (tab-diagnostics)"
Cohesion: 0.33
Nodes (6): 3.14.1 Telemetry Performance HUD, 3.14.2 Low-Confidence & Ambiguous Query Failures Table, 3.14.3 "Trigger Self-Improvement Run" Button, 3.14.4 Dynamic Prompt Rules Table & "Deactivate" Action, 3.14.5 Self-Tuning Execution History Log Feed, 3.14 Tab 10: Corrective RAG Diagnostics & Self-Tuning (tab-diagnostics)

### Community 118 - "3.6 Tab 2: Ingestion Pipeline & Queue Monitor (tab-pipeline)"
Cohesion: 0.33
Nodes (6): 3.6.1 Pipeline Status Badge, 3.6.2 Real-time Ingestion Progress Bar, 3.6.3 Throughput Telemetry, 3.6.4 Active Processing File Display, 3.6.5 Live Activity Stream Console Log, 3.6 Tab 2: Ingestion Pipeline & Queue Monitor (tab-pipeline)

### Community 119 - "3.9 Tab 5: API Key Lifecycle & RBAC Management (tab-apikeys)"
Cohesion: 0.33
Nodes (6): 3.9.1 Key Label / Name Input (`key-name`), 3.9.2 Role Assignment Dropdown (`key-role`), 3.9.3 Rate Limit Number Input (`key-rate-limit`), 3.9.4 "Generate API Key" Button, 3.9.5 Active Keys Management Table & Actions, 3.9 Tab 5: API Key Lifecycle & RBAC Management (tab-apikeys)

### Community 120 - "4.2 Interactive Conversation Viewport"
Cohesion: 0.33
Nodes (6): 4.2.1 User & Assistant Dialogue Bubbles, 4.2.2 Mathematical Formulas & Equations (KaTeX Engine), 4.2.3 Structured Data Tables, 4.2.4 Code Blocks & "Copy Code" Button, 4.2.5 Evidence Badges & Source Drawer, 4.2 Interactive Conversation Viewport

### Community 121 - "4.4 Bottom Query Composer"
Cohesion: 0.33
Nodes (6): 4.4.1 Multi-line Question Textarea (`chat-input`), 4.4.2 Character & Token Counter, 4.4.3 "Send Query" Button, 4.4.4 Quick Prompt Suggestion Chips, 4.4.5 "Clear Chat" Conversation Reset Button, 4.4 Bottom Query Composer

### Community 122 - "worker_task"
Cohesion: 0.50
Nodes (4): Any, AsyncClient, worker_task(), Semaphore

### Community 123 - "Enterprise University RAG - Domain Fine-Tuning & Quantization Report"
Cohesion: 0.40
Nodes (4): 1. Instruction Dataset Summary, 2. LoRA Adapter Specifications, 3. Quantization Deployment Profile, Enterprise University RAG - Domain Fine-Tuning & Quantization Report

### Community 124 - "Enterprise University RAG System"
Cohesion: 0.50
Nodes (3): Architecture Highlights, Enterprise University RAG System, Quickstart (Local Dev)

### Community 125 - "12. Domain Fine-Tuning & Quantization Pipeline"
Cohesion: 0.50
Nodes (4): 12. Domain Fine-Tuning & Quantization Pipeline, 1. Synthesize Instruction Dataset, 2. Execute LoRA Fine-Tuning, 3. Export 4-Bit AWQ Quantization

### Community 126 - "14. Observability & Monitoring (Prometheus & Grafana)"
Cohesion: 0.50
Nodes (4): 14. Observability & Monitoring (Prometheus & Grafana), Grafana Dashboard, Key Metrics Monitored, Prometheus Configuration

### Community 127 - "7. Running the Application"
Cohesion: 0.50
Nodes (4): 7. Running the Application, A. Running the FastAPI Backend, B. Running Celery Ingestion Workers, C. Running via Docker Compose (Production Stack)

### Community 128 - "Enterprise University RAG - Chaos & Resilience Report"
Cohesion: 0.50
Nodes (3): 1. Fault Injection Experiments, 2. Verdict, Enterprise University RAG - Chaos & Resilience Report

### Community 129 - "Enterprise University RAG - Quality Evaluation Report"
Cohesion: 0.50
Nodes (3): 1. Summary Scorecard, 2. Test Case Breakdown, Enterprise University RAG - Quality Evaluation Report

### Community 130 - "3.12 Tab 8: Cryptographic File Integrity Manifest (tab-manifest)"
Cohesion: 0.50
Nodes (4): 3.12.1 Manifest Search Input (`manifest-search`), 3.12.2 Integrity Status Filter Dropdown (`manifest-status-filter`), 3.12.3 Cryptographic SHA-256 Manifest Table & "Verify Integrity" Action, 3.12 Tab 8: Cryptographic File Integrity Manifest (tab-manifest)

### Community 131 - "3.13 Tab 9: Security Audit & Threat Monitoring (tab-security)"
Cohesion: 0.50
Nodes (4): 3.13.1 Threat Summary Bento Cards, 3.13.2 Real-time Security Event Audit Log Table, 3.13.3 "Export Logs" Action Button, 3.13 Tab 9: Security Audit & Threat Monitoring (tab-security)

### Community 132 - "3.7 Tab 3: Failed Ingestions & Error Diagnostics (tab-failed)"
Cohesion: 0.50
Nodes (4): 3.7.1 Total Failed Count Badge, 3.7.2 "Retry All Failed" Button, 3.7.3 Failed Items Diagnostics Table & Actions, 3.7 Tab 3: Failed Ingestions & Error Diagnostics (tab-failed)

### Community 133 - "index_to_qdrant_task"
Cohesion: 0.50
Nodes (4): index_to_qdrant_task(), Any, task, Asynchronously write vectors and metadata payload to Qdrant vector database.…

### Community 134 - "11. Multi-Modal Processing (LaTeX Math & Tables)"
Cohesion: 0.67
Nodes (3): 11. Multi-Modal Processing (LaTeX Math & Tables), LaTeX Math Formulas, Table Serialization

### Community 135 - "13. Disaster Recovery, Automated Backup & Restore"
Cohesion: 0.67
Nodes (3): 13. Disaster Recovery, Automated Backup & Restore, Automated Disaster Recovery Restore, Automated Snapshot Backup

### Community 136 - "15. Automated Verification & Test Harnesses"
Cohesion: 0.67
Nodes (3): 15. Automated Verification & Test Harnesses, Individual Test Suites, Run the Master Test Suite (All 16 Test Suites)

### Community 137 - "4. Prerequisites & System Requirements"
Cohesion: 0.67
Nodes (3): 4. Prerequisites & System Requirements, Hardware Requirements, Software Requirements

### Community 138 - "8. Web User Interfaces"
Cohesion: 0.67
Nodes (3): 8. Web User Interfaces, Admin Control Console (`/admin`) - September 2026 Edition, Student Chat Portal (`/chat`)

### Community 141 - "run_ocr_task"
Cohesion: 0.67
Nodes (3): task, Asynchronously run OCR on scanned or handwritten images/PDFs. Reference: Phase…, run_ocr_task()

## Knowledge Gaps
- **338 isolated node(s):** `name`, `version`, `type`, `private`, `description` (+333 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 970 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StorageCleaner` connect `scraper.py` to `5. Background Daemons & Automation Services`, `UniversityWebCrawler`, `logging`, `crawler.py`, `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)`, `Chunk`, `session.py`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **Why does `3. Administrator Hub (/admin) — Complete Feature & Control Guide` connect `3. Administrator Hub (/admin) — Complete Feature & Control Guide` to `3.17 Tab 13: Server Migration & Infrastructure Transfer (`tab-migrate`)`, `App.jsx`, `3.12 Tab 8: Cryptographic File Integrity Manifest (tab-manifest)`, `3.13 Tab 9: Security Audit & Threat Monitoring (tab-security)`, `3.7 Tab 3: Failed Ingestions & Error Diagnostics (tab-failed)`, `3.15 Tab 11: System Settings & Hardware Management (tab-settings)`, `3.5 Tab 1: Ingest & Watched Folders (tab-ingest)`, `RagAi — Complete System User Manual & Technical Feature Guide`, `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)`, `3.16 Tab 12: Context Filesystem & Tiered Storage Explorer (tab-context)`, `3.8 Tab 4: Indexed Document Library (tab-docs)`, `3.10 Tab 6: URL Access Control & SSRF Firewall (tab-urls)`, `3.14 Tab 10: Corrective RAG Diagnostics & Self-Tuning (tab-diagnostics)`, `3.6 Tab 2: Ingestion Pipeline & Queue Monitor (tab-pipeline)`, `3.9 Tab 5: API Key Lifecycle & RBAC Management (tab-apikeys)`, `3.4 Tab 0: Cognitive AI Brain & Live Neural Visualizer (tab-brain)`?**
  _High betweenness centrality (0.193) - this node is a cross-community bridge._
- **Why does `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)` connect `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)` to `3. Administrator Hub (/admin) — Complete Feature & Control Guide`?**
  _High betweenness centrality (0.181) - this node is a cross-community bridge._
- **Are the 60 inferred relationships involving `User` (e.g. with `get_optional_current_user()` and `require_role()`) actually correct?**
  _`User` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `Document` (e.g. with `CognitiveMemoryManager` and `BrainGraphEngine`) actually correct?**
  _`Document` has 27 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `type` to the rest of the system?**
  _338 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App.jsx` be split into smaller, more focused modules?**
  _Cohesion score 0.0913081650570676 - nodes in this community are weakly interconnected._