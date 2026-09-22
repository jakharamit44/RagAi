# Graph Report - RagAi  (2026-09-22)

## Corpus Check
- 199 files · ~156,527 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 3, .example 2, .conf 2)

## Summary
- 1971 nodes · 4201 edges · 141 communities (118 shown, 23 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 311 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `511e1ce5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- App.jsx
- ingestion/__init__.py
- bm25_index.py
- verify_security_remediation.py
- LLMRouter
- session.py
- health.py
- admin-ui/package.json
- qa_tiered_context_audit.py
- get_session_detail
- documents.py
- admin_governance.py
- scraper.py
- TieredContextEngine
- crawl_single_resource
- models.py
- admin_auth.py
- ManifestEntry
- inspect_content_safety
- User
- LocalChatGenerator
- test_tiered_context.py
- StorageCleaner
- UrlGovernanceRule
- RagAi API Integration Skill & Developer Guide
- SemanticCache
- .run_optimization_cycle
- post
- TargetVMSpec
- test_server_migration.py
- test_backup_restore.py
- crawler.py
- logging
- BannerOCRPipeline
- UniversityWebCrawler
- delete_document_cascade
- LocalEmbedder
- BrainGraphEngine
- PromptRuleManager
- .process_file
- content_guard.py
- chat_completions
- post
- UrlNormalizer
- 3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)
- student-widget/package.json
- dynamic_fetcher.py
- CorrectiveRAGEvaluator
- StudentPortalUser
- NeuralFirer
- .extract_html_content
- os
- Settings
- probe_target_vm
- context.py
- run_lora_finetuning
- log_security_event
- ask.py
- 3. Administrator Hub (/admin) — Complete Feature & Control Guide
- 3.4 Tab 0: Cognitive AI Brain & Live Neural Visualizer (tab-brain)
- sys
- main.py
- Core Endpoint Catalog
- ask_question
- get_migration_status
- ScraperScheduler
- HandwrittenOCREngine
- PrintedOCREngine
- GUID
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
- brain.py
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
- 3.16 Tab 12: Context Filesystem & Tiered Storage Explorer (tab-context)
- 3.8 Tab 4: Indexed Document Library (tab-docs)
- 4.5 Content Moderation & Institutional AI Safety Governor
- Long-term memory (ai-memory)
- ai-memory cross-project messaging
- preload_models
- pathlib
- 3.10 Tab 6: URL Access Control & SSRF Firewall (tab-urls)
- 3.14 Tab 10: Corrective RAG Diagnostics & Self-Tuning (tab-diagnostics)
- 3.6 Tab 2: Ingestion Pipeline & Queue Monitor (tab-pipeline)
- 3.9 Tab 5: API Key Lifecycle & RBAC Management (tab-apikeys)
- 4.2 Interactive Conversation Viewport
- 4.4 Bottom Query Composer
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
- run_ocr_task
- admin-ui/README.md
- rules/graphify.md
- workflows/graphify.md
- GEMINI.md
- master_test_report.md
- role_matrix.md
- student-widget/README.md

## God Nodes (most connected - your core abstractions)
1. `User` - 77 edges
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

## Communities (141 total, 23 thin omitted)

### Community 0 - "App.jsx"
Cohesion: 0.09
Nodes (43): adminApi, apiFetch(), getStoredToken(), setStoredToken(), App(), LoginView(), Header(), Navigation() (+35 more)

### Community 1 - "ingestion/__init__.py"
Cohesion: 0.05
Nodes (33): AbstractEventLoop, Re-evaluates document categorization across all documents in database against…, reclassify_all_documents(), FileSystemEventHandler, Any, pages: list of dicts with keys: {'page_number': int, 'text': str, 'section':…, Layout and structure-aware chunking preserving page numbers and section…, SemanticChunker (+25 more)

### Community 2 - "bm25_index.py"
Cohesion: 0.05
Nodes (36): BM25Index, Any, Append new chunks safely without freezing server on synchronous re-indexing., Sparse BM25 Okapi index for exact keyword search across university documents.…, Build BM25 index from list of chunk payloads with safe memory footprint., Forces complete reload of BM25 corpus from database., Auto-loads bounded index from database (capped at MAX_BM25_CHUNKS to prevent…, CRAGDecision (+28 more)

### Community 3 - "verify_security_remediation.py"
Cohesion: 0.06
Nodes (50): Validate dynamic multi-tenant API key from database or authorized service key., verify_api_key(), ErrorDetail, _get_request_id(), http_exception_handler(), _map_status_to_code(), BaseModel, Exception (+42 more)

### Community 4 - "LLMRouter"
Cohesion: 0.14
Nodes (14): get_conversational_response(), is_hindi_or_hinglish(), Checks if the user's input is a pure conversational query (greeting, identity,…, Detects if the query is in Hindi (Devanagari script) or Hinglish (Hindi written…, get_abstention_message(), LLMRouter, Any, Streams OpenAI-compatible tokens. (+6 more)

### Community 5 - "session.py"
Cohesion: 0.09
Nodes (28): create_access_token(), Create signed JWT access token (Phase 11 & Table 27)., QueryAuditLog, Content-free query audit trail for security, latency & abuse monitoring.…, do_begin(), get_db(), init_db(), Async session dependency for FastAPI routes. (+20 more)

### Community 6 - "health.py"
Cohesion: 0.16
Nodes (22): get_gpu_status(), Any, Returns real-time GPU telemetry (model, memory, utilization, active ONNX…, FullRagStatusResponse, get_dir_size_mb(), get_full_rag_status(), get_storage_telemetry(), HardwareTelemetry (+14 more)

### Community 7 - "admin-ui/package.json"
Cohesion: 0.07
Nodes (26): dependencies, lucide-react, react, react-dom, description, devDependencies, autoprefixer, postcss (+18 more)

### Community 8 - "qa_tiered_context_audit.py"
Cohesion: 0.06
Nodes (40): ContextTier, OpenViking-inspired Hierarchical Virtual Context Filesystem and Tiered Storage.…, requests, AuthenticationError, Any, Exception, RagAiClient, RagAiError (+32 more)

### Community 9 - "get_session_detail"
Cohesion: 0.11
Nodes (24): ChatMessageResponse, ChatSessionDetailResponse, ChatSessionSummary, CitationModel, ConversationStatsResponse, delete_chat_session(), get_conversation_stats(), get_session_detail() (+16 more)

### Community 10 - "documents.py"
Cohesion: 0.09
Nodes (36): ChunkItem, DocumentItem, DocumentUploadResponse, FolderRegisterRequest, FolderRegisterResponse, get_document_chunks(), get_task_status(), list_documents() (+28 more)

### Community 11 - "admin_governance.py"
Cohesion: 0.10
Nodes (33): ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyItem, batch_delete_documents(), BatchDeleteRequest, BatchDeleteResponse, create_api_key(), DirectoryItem (+25 more)

### Community 12 - "scraper.py"
Cohesion: 0.11
Nodes (27): CrawlSingleUrlRequest, create_scraper_job(), CreateJobRequest, delete_scraper_job(), get_crawler_status(), get_scrape_manifest(), list_scraper_jobs(), BaseModel (+19 more)

### Community 13 - "TieredContextEngine"
Cohesion: 0.10
Nodes (19): RagAi OpenViking-Inspired Context Filesystem and Tiered Storage Subsystem.…, clean_slug(), Any, Extractive synthesis of L0 abstract and L1 structured synopsis from text or…, Schedule a background synchronization of context tiers, debounced to avoid…, Scans SQLite metadata and ensures all Departments, Courses, and Documents have…, Creates a clean filesystem-friendly slug for ragai:// URIs., Returns the hierarchical virtual context filesystem tree mirroring OpenViking's… (+11 more)

### Community 14 - "crawl_single_resource"
Cohesion: 0.11
Nodes (17): crawl_single_resource(), On-demand single URL or PDF crawl and indexing into vector database. Instantly…, AsyncClient, AsyncSession, Retrieves If-None-Match (ETag) and If-Modified-Since headers from previous…, DocumentDownloader, AsyncClient, Asynchronous document streamer for downloading academic PDFs, circulars, and… (+9 more)

### Community 15 - "models.py"
Cohesion: 0.13
Nodes (24): RagAi OpenViking-Inspired Tiered Context Engine & Virtual Knowledge Filesystem…, metrics_endpoint(), get, Standard Prometheus metrics scrape endpoint. Exposes QPS, latencies, cache…, Chunk, Document, The retrievable passage unit with vector pointers and source locations.…, Successfully ingested university document metadata. Reference: Appendix A… (+16 more)

### Community 16 - "admin_auth.py"
Cohesion: 0.09
Nodes (46): hash_password(), api/core/passwords.py Enterprise Password Security Module for Administrator…, Hashes a plaintext password using PBKDF2-HMAC-SHA256 with a unique 16-byte…, Verifies a plaintext password against a stored '<salt_hex>:<hash_hex>' string.…, Validates enterprise password complexity: - At least 8 characters - At least…, validate_password_strength(), verify_password(), admin_login() (+38 more)

### Community 17 - "ManifestEntry"
Cohesion: 0.14
Nodes (18): force_refetch_folder(), ForceRefetchRequest, get_services_health(), list_watched_folders(), Detailed infrastructure health diagnostics. Reports Redis connection status,…, List all registered watched folders with live statistics., Force refetch: Purges all existing RAG documents, chunks, vectors, and manifest…, Base (+10 more)

### Community 18 - "inspect_content_safety"
Cohesion: 0.14
Nodes (24): inspect_content_safety(), Exhaustively scans text for abusive words, communal slurs, adversarial…, tests/test_content_guard.py Automated Verification Suite for Indian-Context AI…, Verify attempts to 'educate' or brainwash the AI with bad beliefs., Verify exam cheating, chits smuggling, paper leaks, and degree forgery., Verify promotion of ragging or harassment., CRITICAL: Ensure zero false positives for genuine academic and policy questions., Verify that toxic or poisoned feedback reason is blocked. (+16 more)

### Community 19 - "User"
Cohesion: 0.12
Nodes (21): get_active_prompt_rules(), get_models_status(), get_rag_diagnostics(), get_security_incidents(), get_security_stats(), get_self_improvement_history(), list_api_keys(), list_failed_files() (+13 more)

### Community 20 - "LocalChatGenerator"
Cohesion: 0.12
Nodes (10): LocalChatGenerator, Any, Pre-warms chat model during server startup so first student query is fast., Synchronous PyTorch generation executed within worker thread with zero-overhead…, Generates an accurate, grounded answer using verified academic context. Uses…, OpenAI-compatible generic chat completion., Enterprise In-Project Local GPU Chat Generator. Executes Qwen2.5-3B-Instruct…, Asynchronous SSE token streamer for verified academic question answering. (+2 more)

### Community 21 - "test_tiered_context.py"
Cohesion: 0.13
Nodes (22): tests/test_tiered_context.py Automated Verification Suite for OpenViking…, Verify POST /api/v1/context/find executes directory-guided search., Verify GET /api/v1/context/stats computes telemetry and token savings., Verify detection of high-level overview queries vs granular proof inquiries., Verify that overview queries hit the L1 fast-path in /api/v1/ask., Verify POST /api/v1/context/sync requires administrative authorization., Verify that RagAiClient Python SDK incorporates all context filesystem…, Verify deterministic extractive synthesis of L0 abstract and L1 overview. (+14 more)

### Community 22 - "StorageCleaner"
Cohesion: 0.15
Nodes (12): cleanup_scraper_storage(), purge_scraped_rag_data(), Safely prunes temporary scraped PDFs, partial downloads (.tmp), and transient…, Permanently purges all RAG data generated from web scraping: - Web documents…, Any, Automated storage lifecycle manager. Safely prunes transient scraped downloads…, Validates that file_path is strictly a temporary scraped file inside…, Sweeps data/downloads/mdu_scraped/ for temporary .tmp files and ingested PDFs.… (+4 more)

### Community 23 - "UrlGovernanceRule"
Cohesion: 0.18
Nodes (14): create_url_rule(), list_url_rules(), patch, Enable or disable an API key without deleting it., List all URL governance allow/disallow rules., Add a new URL allow/disallow governance rule., Toggle a URL rule active/inactive., StatusToggleRequest (+6 more)

### Community 24 - "RagAi API Integration Skill & Developer Guide"
Cohesion: 0.06
Nodes (30): RagAiChatModal(), RagAiChatOptions, RagAiCitation, RagAiMessage, useRagAiChat(), 1. Skill Purpose & Scope, 2. Integration Mental Model & Architecture, 3. Quick Start: 3 Ways to Integrate (+22 more)

### Community 25 - "SemanticCache"
Cohesion: 0.15
Nodes (9): Any, Tier-2 Semantic Cache: Evaluates cosine similarity of query embedding against…, Authorization and scope-aware cache layer. Tier 1: High-speed SHA-256 exact-…, Sets both Tier-1 exact key and Tier-2 semantic vector cache., Returns live connection diagnostics for Redis and in-memory fallback., Clears in-memory cache and attempts to flush Redis keys., Builds authorization-aware cache key. Same question in different departments or…, Purges expired items from memory cache safely without mutation during iteration. (+1 more)

### Community 26 - ".run_optimization_cycle"
Cohesion: 0.24
Nodes (9): Any, Runs one full Karpathy optimization round: 1. Measure baseline evaluation score…, Runs evaluation suite against rule set and computes percentage score., Harvests real student chat queries that produced low confidence, INCORRECT CRAG…, Extracts real failure patterns from stored student conversations and runs a…, Autonomous prompt optimization loop. Executes benchmark evaluations, identifies…, SelfImprovingRAGEngine, PromptOptimizationRun (+1 more)

### Community 27 - "post"
Cohesion: 0.09
Nodes (24): clear_query_audit_logs(), clear_system_cache(), flush_cuda_memory(), purge_corpus(), PurgeRequest, Any, post, Helper to process a single file through text/OCR, chunking, and push embeddings… (+16 more)

### Community 28 - "TargetVMSpec"
Cohesion: 0.24
Nodes (4): MigrationManager, TargetVMSpec, 8. Pre-Flight Server Migration Probe (`POST /api/v1/admin/migration/probe`), 9. Start Server Migration Pipeline (`POST /api/v1/admin/migration/start`)

### Community 29 - "test_server_migration.py"
Cohesion: 0.12
Nodes (16): fastapi_testclient, tests/test_server_migration.py Automated Verification Suite for Ubuntu VM…, Verify probe safely detects failure when target host is non-existent., Verify GET /api/v1/admin/migration/status returns valid state response., Verify that only admin role can access server migration routes., Verify GET /api/v1/admin/migration/parity returns 404 when no migration…, Verify TargetVMSpec model builds correct PostgreSQL and Redis URLs., Verify GET /api/v1/admin/migration/source-status returns active metrics. (+8 more)

### Community 30 - "test_backup_restore.py"
Cohesion: 0.30
Nodes (9): compute_sha256(), create_backup(), Creates a full, verifiable disaster recovery snapshot. Includes relational…, compute_sha256(), Restores the university RAG database and vector corpus from a verified…, restore_backup(), test_backup_and_restore_lifecycle(), shutil (+1 more)

### Community 31 - "crawler.py"
Cohesion: 0.26
Nodes (8): DeltaDetector, Intelligent 3-tier delta change detection engine. Eliminates redundant network…, Strips dynamic server noise such as live visitor counters, timestamps, and…, Evaluates whether a web page or document has changed and needs ingestion.…, Bridges scraped web pages and downloaded academic documents directly into the…, ScraperIngestBridge, Tracks all crawled URLs, documents, headers (ETag, Last-Modified), SHA-256…, WebScrapeManifest

### Community 32 - "logging"
Cohesion: 0.08
Nodes (25): CognitiveMemoryManager, Manages the Tri-Partite Memory Architecture: 1. Semantic Memory: Enduring…, Marks working memory transition to ACTIVE_FIRING., Reclaims working memory slot., Records an episodic neural firing trajectory into working memory., University Cognitive AI Brain & Knowledge Cortex Package. Provides semantic…, Self-Improving RAG Prompt Optimization Engine Inspired by Shubhamsaboo/awesome-…, api/routers/admin_conversations.py Enterprise Conversation Inspector & AI Self-… (+17 more)

### Community 33 - "BannerOCRPipeline"
Cohesion: 0.17
Nodes (11): BannerOCRPipeline, Any, AsyncClient, Finds banner images, downloads them safely, runs RapidOCR, and returns…, Downloads single image with redirect SSRF validation, runs OCR in thread with…, Formats extracted banner announcements into structured Markdown., Identifies, retrieves, and extracts textual announcements from university…, Verify synthetic graphic OCR extraction and markdown synthesis. (+3 more)

### Community 34 - "UniversityWebCrawler"
Cohesion: 0.14
Nodes (11): Scans HTML DOM to identify prominent banner, slider, and announcement graphic…, Any, High-throughput, domain-governed asynchronous crawler with intelligent 3-tier…, Signals crawler loop to stop., Executes crawl run for a specific WebScrapeJob in automatic continuous batches., UniversityWebCrawler, Normalizes a URL by stripping fragments, tracking queries, and resolving…, test_crawler_continuous_batching_auto_advancement() (+3 more)

### Community 35 - "delete_document_cascade"
Cohesion: 0.12
Nodes (16): clear_all_failed_files(), clear_security_incidents(), delete_api_key(), delete_document_cascade(), delete_single_failed_file(), delete_url_rule(), DocumentDeleteResponse, delete (+8 more)

### Community 36 - "LocalEmbedder"
Cohesion: 0.20
Nodes (6): LocalEmbedder, Pre-warm model at server startup so first student query has zero latency., Deterministic fast n-gram & word feature hashing vectorizer. Generates dense…, Thread-safe persistent HTTP/1.1 connection pool with TCP Keep-Alive., Local embedding generator. Produces L2-normalized 384-dimensional dense…, Cleanly close persistent connection pools and release sockets.

### Community 37 - "BrainGraphEngine"
Cohesion: 0.19
Nodes (7): BrainGraphEngine, Any, Filters nodes and links to focus on a target department., Constructs, maintains, and caches the multi-tiered University Knowledge Cortex.…, Forces recalculation of the knowledge graph on next query., Retrieves the Knowledge Graph. Automatically builds or refreshes if cache is…, Scans SQLite metadata and synthesizes the Knowledge Graph.

### Community 38 - "PromptRuleManager"
Cohesion: 0.24
Nodes (7): Any, Aggregates comprehensive cognitive telemetry for the Admin Live Visualizer., PromptRuleManager, Manages active system prompt rules with persistence, versioning, and rollback., Resets prompt rules to default baseline., reset_prompt_rules(), main()

### Community 39 - ".process_file"
Cohesion: 0.07
Nodes (21): event_generator(), ContentDeduplicator, Any, Filter out chunks whose SHA-256 hashes already exist in the database., Performs cross-document and within-document deduplication via chunk content…, ManifestManager, AsyncSession, Upsert a manifest entry for change detection. (+13 more)

### Community 40 - "content_guard.py"
Cohesion: 0.20
Nodes (10): get_squashed_text(), is_legitimate_policy_inquiry(), normalize_text(), api/core/content_guard.py Enterprise AI Safety Governor & Content Moderation…, Checks if a query mentioning sensitive academic topics (ragging, UMC,…, Cleans, squashes leetspeak, collapses repeated characters, and removes intra-…, Generates a version with punctuation, spaces, and intra-word separators…, SafetyInspectionResult (+2 more)

### Community 41 - "chat_completions"
Cohesion: 0.19
Nodes (12): chat_completions(), ChatChoice, ChatCompletionRequest, ChatCompletionResponse, ChatMessage, ChoiceMessage, BaseModel, post (+4 more)

### Community 42 - "post"
Cohesion: 0.22
Nodes (9): cancel_migration(), execute_cutover(), execute_rollback(), post, Kicks off background streaming migration of PostgreSQL and Qdrant data to…, Cancels an active background migration job safely., Executes an atomic live cutover to the new target server: 1. Backs up active…, Reverts active infrastructure back to previous configuration stored in… (+1 more)

### Community 43 - "UrlNormalizer"
Cohesion: 0.11
Nodes (24): PageExtractor, Extracts high-fidelity academic content, Markdown tables, banner image…, Discovers all valid internal web page links (including subdomains) and…, Checks if the URL's domain is in the allowed domain list (supports wildcard…, Returns True if the URL points to a downloadable academic document (.pdf,…, Checks if the URL is an asset or sensitive URL (images, styles, logout)., Standardizes and filters URLs for academic web crawling. Ensures safe domain…, Extracts the canonical root domain from a hostname or URL. Correctly handles… (+16 more)

### Community 44 - "3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)"
Cohesion: 0.10
Nodes (20): 3.11.10 Maximum Crawl Depth Number Box (`cfg-job-depth`), 3.11.11 Batch Size (Links per batch) Number Box (`cfg-job-max-pages`), 3.11.12 Automated Crawl Interval Number Box (`cfg-job-interval`), 3.11.13 "Auto-Ingest Discovered Documents" Toggle Checkbox (`cfg-job-auto-ingest`), 3.11.13a "Extract Banner Image & Slider Announcements (PP-OCRv4)" Checkbox (`cfg-job-ocr-banners`), 3.11.14 "Save Configuration" Button, 3.11.15 "Run Scraper Now" Button, 3.11.16 Scraper Real-Time Terminal Activity Console (+12 more)

### Community 45 - "student-widget/package.json"
Cohesion: 0.11
Nodes (17): dependencies, react, react-dom, description, devDependencies, vite, @vitejs/plugin-react, react (+9 more)

### Community 46 - "dynamic_fetcher.py"
Cohesion: 0.12
Nodes (11): DynamicWebFetcher, Any, Dynamic Web Fetcher with DevExpress ASP.NET and Scrapling / Playwright…, Extracts rows, cell links, and document URLs from an ASPxGridView table., Navigates to an ASP.NET DevExpress page (e.g. EventPage.aspx?id=2), identifies…, High-fidelity dynamic browser fetcher. Executes client-side JavaScript, steps…, Determines if a URL is an ASP.NET WebForms / DevExpress dynamic page., Quickly detects if raw HTML contains DevExpress ASPxGridView controls. (+3 more)

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

### Community 51 - "os"
Cohesion: 0.11
Nodes (22): argparse, asyncio, atexit, concurrent_futures, datetime, IngestionPipeline, Unified Ingestion Pipeline: Change Detection -> Metadata Inference -> Text…, os (+14 more)

### Community 53 - "probe_target_vm"
Cohesion: 0.25
Nodes (8): MigrationStatusResponse, ParityItem, ParityReport, probe_target_vm(), ProbeResponse, BaseModel, Pre-flight probe to test connectivity, credentials, and health of all 5…, ServiceProbeResult

### Community 54 - "context.py"
Cohesion: 0.14
Nodes (17): ContextFindRequest, find_in_context(), get_context_stats(), get_context_tree(), list_context_directory(), BaseModel, get, post (+9 more)

### Community 55 - "run_lora_finetuning"
Cohesion: 0.40
Nodes (5): Any, run_lora_finetuning(), Any, run_quantization_pipeline(), test_fine_tuning_and_quantization()

### Community 56 - "log_security_event"
Cohesion: 0.40
Nodes (5): log_security_event(), Asynchronously records a security incident into the database. Catches and…, Simulates a security incident (prompt injection, auth failure, rate limit,…, simulate_security_event(), SimulateSecurityEventRequest

### Community 57 - "ask.py"
Cohesion: 0.11
Nodes (29): decode_token(), get_current_user(), get_optional_current_user(), Any, Request, FastAPI dependency for mandatory authenticated endpoints. Accepts: 1. X-API-Key…, Optional user dependency. If no auth header is provided, returns None (allowing…, Role-based access control dependency. Enforces student < faculty < admin… (+21 more)

### Community 58 - "3. Administrator Hub (/admin) — Complete Feature & Control Guide"
Cohesion: 0.15
Nodes (13): 3.1.1 Admin API Key Text Box (`admin-token`), 3.1.2 "Set" Authorization Button, 3.1.3 "Student Chat" Portal Launch Button, 3.1 Global Header Controls, 3.2.1 GPU CUDA & VRAM Telemetry Card, 3.2.2 Document Ingestion Statistics Card, 3.2.3 Storage Footprint & "Clean Scraper Temp" Button, 3.2.4 Pipeline Ingestion Status & "Retry Failed" Button (+5 more)

### Community 59 - "3.4 Tab 0: Cognitive AI Brain & Live Neural Visualizer (tab-brain)"
Cohesion: 0.15
Nodes (13): 3.4.10 4-Phase Thought Pathway Trace Console, 3.4.11 Episodic Memory Stream Feed, 3.4.12 Glassmorphic Concept Inspector Modal & "Probe this Concept" Button, 3.4.1 Department Filter Dropdown (`cortex-dept-filter`), 3.4.2 "Rebuild Cortex" Button, 3.4.3 "Center View" Button, 3.4.4 HUD Telemetry Bento Cards, 3.4.5 Interactive HTML5 Canvas Controls & Physics Simulation (+5 more)

### Community 61 - "sys"
Cohesion: 0.08
Nodes (17): data_fine_tuning_dataset_generator, json, platform, main(), wait_for_api(), check_nvidia_gpu(), Detects NVIDIA GPU and VRAM availability., run_setup() (+9 more)

### Community 62 - "main.py"
Cohesion: 0.14
Nodes (18): init_cuda_runtime(), Auto-detects and loads NVIDIA CUDA Toolkit and cuDNN DLLs into Windows process.…, admin_dashboard(), api_version(), favicon(), lifespan(), FastAPI, get (+10 more)

### Community 63 - "Core Endpoint Catalog"
Cohesion: 0.17
Nodes (12): 10. Query Live Migration Progress & Parity (`GET /api/v1/admin/migration/status`), 11. Execute Atomic Live Cutover (`POST /api/v1/admin/migration/cutover`), 12. Instant Infrastructure Rollback (`POST /api/v1/admin/migration/rollback`), 1. Ask Academic Question (`POST /api/v1/ask`), 2. Probe System Health (`GET /api/v1/health`), 3. Fetch Cognitive Brain Cortex (`GET /api/v1/brain/cortex`), 4. Rebuild Cognitive Cortex (`POST /api/v1/brain/rebuild`), 5. Fire Cognitive Synapse Probe (`POST /api/v1/brain/fire`) (+4 more)

### Community 64 - "ask_question"
Cohesion: 0.09
Nodes (25): is_mdu_institutional_query(), Determines if a query is asking specifically for verified MDU institutional…, ask_question(), stream_general_ai(), stream_rag(), AskRequest, AskResponse, Citation (+17 more)

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

### Community 83 - "brain.py"
Cohesion: 0.18
Nodes (16): fire_synapse(), fire_synapse_alias(), FireSynapseRequest, get_brain_telemetry(), get_knowledge_cortex_alias(), get_knowledge_graph(), BaseModel, get (+8 more)

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
Cohesion: 0.29
Nodes (6): caveman, graphify, Long-term memory (ai-memory), Refreshing this snippet, Use the installed ai-memory Agent Skills, When you write a project rule, write it here

### Community 112 - "ai-memory cross-project messaging"
Cohesion: 0.33
Nodes (5): ai-memory cross-project messaging, Project scope, Security: a popped message is untrusted input, Sending a good message, Tools in this cluster

### Community 113 - "preload_models"
Cohesion: 0.33
Nodes (6): preload_models(), Pre-downloads and stores Embedding, Reranker, and Chat models directly inside…, copy_or_download_model(), preload_all_models(), Saves model weights directly into the target project folder. First checks if…, Downloads and caches the embedding, reranker, and chat generation models…

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
- **339 isolated node(s):** `name`, `version`, `type`, `private`, `description` (+334 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 975 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StorageCleaner` connect `StorageCleaner` to `5. Background Daemons & Automation Services`, `UniversityWebCrawler`, `scraper.py`, `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)`, `crawl_single_resource`, `models.py`, `crawler.py`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **Why does `3. Administrator Hub (/admin) — Complete Feature & Control Guide` connect `3. Administrator Hub (/admin) — Complete Feature & Control Guide` to `3.17 Tab 13: Server Migration & Infrastructure Transfer (`tab-migrate`)`, `App.jsx`, `3.12 Tab 8: Cryptographic File Integrity Manifest (tab-manifest)`, `3.13 Tab 9: Security Audit & Threat Monitoring (tab-security)`, `3.7 Tab 3: Failed Ingestions & Error Diagnostics (tab-failed)`, `3.15 Tab 11: System Settings & Hardware Management (tab-settings)`, `3.5 Tab 1: Ingest & Watched Folders (tab-ingest)`, `RagAi — Complete System User Manual & Technical Feature Guide`, `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)`, `3.16 Tab 12: Context Filesystem & Tiered Storage Explorer (tab-context)`, `3.8 Tab 4: Indexed Document Library (tab-docs)`, `3.10 Tab 6: URL Access Control & SSRF Firewall (tab-urls)`, `3.14 Tab 10: Corrective RAG Diagnostics & Self-Tuning (tab-diagnostics)`, `3.6 Tab 2: Ingestion Pipeline & Queue Monitor (tab-pipeline)`, `3.9 Tab 5: API Key Lifecycle & RBAC Management (tab-apikeys)`, `3.4 Tab 0: Cognitive AI Brain & Live Neural Visualizer (tab-brain)`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Why does `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)` connect `3.11 Tab 7: Automated Web Scraper & Notice Crawler (tab-scraper)` to `3. Administrator Hub (/admin) — Complete Feature & Control Guide`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `User` (e.g. with `get_optional_current_user()` and `require_role()`) actually correct?**
  _`User` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `Document` (e.g. with `CognitiveMemoryManager` and `BrainGraphEngine`) actually correct?**
  _`Document` has 27 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `type` to the rest of the system?**
  _339 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App.jsx` be split into smaller, more focused modules?**
  _Cohesion score 0.0913081650570676 - nodes in this community are weakly interconnected._