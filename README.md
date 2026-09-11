# RagAi - Enterprise University RAG Platform

An enterprise-grade, privacy-first, local-first Retrieval-Augmented Generation (RAG) platform tailored for universities, colleges, and research institutions. Designed to ingest course syllabi, lecture notes, academic regulations, lab manuals, and research materials to deliver provably grounded question-answering with exact document citations, explicit abstention over hallucination, and zero data exfiltration.

Built in strict compliance with the **19-Phase Master Technical Architecture Plan** (September 2026).

---

## Table of Contents

1. [System Architecture & Design Principles](#1-system-architecture--design-principles)
2. [Key Features](#2-key-features)
3. [Repository Directory Structure](#3-repository-directory-structure)
4. [Prerequisites & System Requirements](#4-prerequisites--system-requirements)
5. [Installation & Setup (0 to 100 Guide)](#5-installation--setup-0-to-100-guide)
6. [Configuration & Environment Variables](#6-configuration--environment-variables)
7. [Running the Application](#7-running-the-application)
   - [A. Running the FastAPI Backend](#a-running-the-fastapi-backend)
   - [B. Running Celery Ingestion Workers](#b-running-celery-ingestion-workers)
   - [C. Running via Docker Compose (Production Stack)](#c-running-via-docker-compose-production-stack)
8. [Web User Interfaces](#8-web-user-interfaces)
   - [Student Chat Portal](#student-chat-portal-chat)
   - [Admin Control Console](#admin-control-console-admin)
9. [API Endpoints Reference](#9-api-endpoints-reference)
10. [Document Ingestion Pipeline](#10-document-ingestion-pipeline)
11. [Multi-Modal Processing (LaTeX Math & Tables)](#11-multi-modal-processing-latex-math--tables)
12. [Domain Fine-Tuning & Quantization Pipeline](#12-domain-fine-tuning--quantization-pipeline)
13. [Disaster Recovery, Automated Backup & Restore](#13-disaster-recovery-automated-backup--restore)
14. [Observability & Monitoring (Prometheus & Grafana)](#14-observability--monitoring-prometheus--grafana)
15. [Automated Verification & Test Harnesses](#15-automated-verification--test-harnesses)
16. [Security Architecture & OWASP Hardening](#16-security-architecture--owasp-hardening)
17. [Troubleshooting & FAQ](#17-troubleshooting--faq)

---

## 1. System Architecture & Design Principles

The platform is anchored on five inviolable architectural principles:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 Nginx Reverse Proxy                     │
                  │   Rate Limiting (60 r/m) | OWASP Headers | SSL Term     │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                   ┌───────────────────────────┴────────────────────────────┐
                   ▼                                                        ▼
      ┌─────────────────────────┐                              ┌─────────────────────────┐
      │  Student Chat Portal    │                              │   Admin Control Console │
      │  /chat (KaTeX + Tables) │                              │   /admin (Scan & Stats) │
      └────────────┬────────────┘                              └────────────┬────────────┘
                   │                                                        │
                   └───────────────────────────┬────────────────────────────┘
                                               ▼
     ┌──────────────────────────────────────────────────────────────────────────────────┐
     │                       FastAPI Core Application Service                           │
     │   JWT SSO Authentication | Sliding-Window Rate Limiting | Prometheus Metrics     │
     └─────────────┬───────────────────────────┬───────────────────────────┬────────────┘
                   │                           │                           │
                   ▼                           ▼                           ▼
      ┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
      │  Redis Semantic Cache   │ │   Celery Ingestion Q    │ │ Local LLM Router (vLLM) │
      │  SHA-256 Scope Keying   │ │   Async Extraction &    │ │ Prompt Boundary Fencing │
      │  (Fallback: Memory TTL) │ │   Embedding Pipeline    │ │ Strict Abstention Rule  │
      └─────────────────────────┘ └────────────┬────────────┘ └─────────────────────────┘
                                               │
                                               ▼
                 ┌───────────────────────────────────────────────────────────┐
                 │                   Dual Storage Layer                      │
                 │  SQLite / PostgreSQL        │ Qdrant Vector Store         │
                 │  (Manifests, Metadata, RBAC)│ (384-dim Dense Embeddings)  │
                 └─────────────────────────────┴─────────────────────────────┘
```

1. **Strict Local-First Deployment (Zero Exfiltration)**: All embeddings and inference execute on local infrastructure (`http://localhost:8000/v1` or local resilient synthesizer). Student questions and intellectual property never leave the institutional boundary.
2. **Dual-Index Hybrid Retrieval**: Combines high-dimensional dense vector embeddings (384-dim Qdrant) with sparse BM25 Okapi lexical indexing fused via **Reciprocal Rank Fusion ($RRF$, $k=60$)** and Cross-Encoder reranking.
3. **Provable Attribution (Verified Citations)**: Every answer must cite exact document titles, page numbers, and section headings.
4. **Explicit Abstention over Hallucination**: If retrieved context fails relevance thresholds or query keywords are absent, the system explicitly abstains rather than inventing answers.
5. **Defense-in-Depth Zero Trust Security**: Prompt boundary fencing (`<untrusted_academic_context>`), path traversal allowlists, SHA-256 query privacy hashing, and role-based access control (Student < Faculty < Admin).

---

## 2. Key Features

- **Multi-Format Ingestion**: Ingests `.docx`, `.pdf`, `.txt`, `.csv`, `.xlsx`, and `.md` files with layout-aware chunking (preserving chapter headings, paragraphs, and reading flow).
- **Cognitive AI Brain & Live Knowledge Cortex**: High-performance semantic graph engine modeling University Core, Departments, Courses, Concepts, and Documents with tri-partite cognitive memory (Semantic, Episodic, Working) and live HTML5 canvas neural visualizer.
- **OpenViking Virtual Context Filesystem (`ragai://`) & Tiered Storage Engine**: Eliminates context bloat and slashes LLM inference costs by **80–90%** using hierarchical directory contexts (L0 Abstract: ~50-100 tok, L1 Curricular Synopsis: ~400-800 tok, L2 Deep Chunks: 500-tok verbatim). Exposes agent filesystem primitives (`tree`, `ls`, `resolve`, `find`) and instant L1 overview retrieval (~250ms latency).
- **Indian-Context AI Safety Governor & Content Moderation**: Enterprise-grade guardrail engine filtering Hindi, Hinglish, and English profanity, casteist/communal slurs (SC/ST PoA Act), adversarial "AI teaching"/model poisoning, exam malpractice (chits, paper leaks, forgery), and UGC Anti-Ragging violations with contextual whitelisting for legitimate academic inquiries.
- **Autonomous University Web Scraper & Crawler**: 3-tier delta change detection crawler for university portals (ETag/304, noise-filtered SHA-256, cryptographic ledger) with automated PDF streaming and temporary storage reclamation.
- **Universal Portal Integration & Embeddable Widget**: Lightweight, zero-dependency embeddable chat widget (`ragai_chat_widget.js`), typed Python SDK, and React hooks for student portals, employee intranets, and faculty dashboards.
- **Multi-Modal Academic Support**: Automatically converts tabular data into structured Markdown grids (`| Col 1 | Col 2 |`) and preserves inline and block LaTeX mathematics (`$BF = h_L - h_R$`).
- **Continuous Folder Watcher**: Automated SHA-256 manifest tracking with change detection; skips unchanged files, updates edited documents, and prunes deleted sources.
- **Asynchronous Task Queue**: Celery task queue with background worker execution and eager fallback when a broker is unavailable.
- **Enterprise SSO & RBAC**: JWT bearer tokens supporting role hierarchies (`student`, `faculty`, `admin`) and department multi-tenancy.
- **Semantic Caching**: Redis-backed cache with scope-aware keys (`rag_cache:sha256(dept:course:qhash)`) absorbing > 60% of repeat FAQ traffic at sub-millisecond speeds.
- **Production Observability**: Standard Prometheus metrics endpoint (`/metrics`) exposing query counters, durations, cache hit rates, and ingestion gauges.
- **Disaster Recovery**: Automated snapshot backup (`scripts/backup.py`) bundling SQLite/Postgres DB + Qdrant vectors + manifests into compressed tarballs with 30-day retention pruning and SHA-256 verification.
- **Domain Fine-Tuning & Quantization**: Instruction tuning dataset generator (`data/fine_tuning/`), LoRA adapter training script ($r=16, \alpha=32$), and 4-bit AWQ / GGUF quantization exporter.

---

## 3. Repository Directory Structure

```
d:\RagAi\
├── api/                           # Core FastAPI Web Service
│   ├── brain/                     # Cognitive AI Brain & Knowledge Cortex Subsystem
│   │   ├── graph_engine.py        # Semantic graph builder (University Core -> Dept -> Course -> Concept)
│   │   ├── cognitive_memory.py    # Tri-partite memory model (Semantic, Episodic, Working)
│   │   └── neural_firer.py        # Real-time synaptic activation & 4-step Thought Pathway tracer
│   ├── core/                      # Core configuration and middleware
│   │   ├── auth.py                # JWT creation, decoding, and hardened RBAC role dependencies
│   │   ├── cache.py               # Redis semantic cache with in-memory TTL fallback
│   │   ├── config.py              # Central Pydantic settings & environment definitions
│   │   ├── content_guard.py       # Indian-Context AI Safety Governor & Content Moderation Engine
│   │   ├── exceptions.py          # RFC 7807 problem details error handlers
│   │   ├── llm_router.py          # Local-first LLM router with prompt boundary fencing
│   │   ├── metrics.py             # Prometheus metric collectors & histograms
│   │   ├── rate_limiter.py        # Sliding-window IP rate limiter
│   │   └── security_logger.py     # Background security incident ledger
│   ├── rag/                       # Retrieval-Augmented Generation subsystem
│   │   ├── bm25_index.py          # Sparse BM25Okapi index with auto-load from database
│   │   ├── chat_generator.py      # Quantized local generator with StreamCancellationCriteria
│   │   ├── embedder.py            # SentenceTransformer 384-dim dense vectorizer
│   │   ├── qdrant_store.py        # Qdrant client managing 'university_corpus' collection
│   │   ├── reranker.py            # Cross-encoder and lexical density reranker
│   │   ├── retriever.py           # Hybrid RRF retriever combining dense + sparse results
│   │   └── self_improver.py       # Autonomous Karpathy prompt optimization engine
│   ├── routers/                   # API Route controllers
│   │   ├── admin_governance.py    # Enterprise governance, folder scan, and diagnostic endpoints
│   │   ├── ask.py                 # POST /api/v1/ask grounded QA & feedback endpoint
│   │   ├── auth.py                # POST /auth/login, POST /auth/token, GET /auth/me
│   │   ├── brain.py               # GET /admin/brain/graph, POST /admin/brain/fire-synapse
│   │   ├── chat.py                # POST /v1/chat/completions OpenAI-compatible endpoint
│   │   ├── documents.py           # Ingestion, folder registration, and manifest listings
│   │   ├── health.py              # GET /health subsystem status probe
│   │   ├── metrics.py             # GET /metrics Prometheus scrape endpoint
│   │   └── scraper.py             # Autonomous crawler control, jobs, and delta manifests
│   ├── scraper/                   # Autonomous University Website Scraper & Crawler
│   │   ├── crawler.py             # Polite BFS crawler with semaphore & delay controls
│   │   ├── page_extractor.py      # Trafilatura / BeautifulSoup content extraction
│   │   ├── doc_downloader.py      # Streamed PDF downloader with 50MB cap
│   │   ├── delta_detector.py      # 3-tier change detector (ETag, SHA-256, Manifest)
│   │   ├── ingest_bridge.py       # Seamless delta change indexer to Qdrant & SQLite
│   │   ├── storage_cleaner.py     # Safe temporary crawler download reclamation
│   │   └── url_normalizer.py      # SSRF defense, DNS pre-resolution, and domain whitelist
│   ├── static/                    # Frontend HTML, CSS, and JS assets
│   │   ├── admin.html             # Admin Dashboard UI with Live Brain Cortex Visualizer
│   │   ├── chat.html              # Student Chat Widget UI (with KaTeX & table support)
│   │   └── ragai_chat_widget.js   # Universal embeddable JavaScript chat widget
│   └── main.py                    # Application entrypoint and startup lifecycle
├── data/                          # Academic Corpus & Upload Storage
│   ├── artifacts/                 # Extracted diagrams and images
│   ├── downloads/                 # Scraped documents and circulars
│   ├── fine_tuning/               # Generated train.jsonl and val.jsonl datasets
│   ├── sample_courses/            # Sample university course directories (CS401, CS402)
│   └── uploads/                   # Temporary directory for multipart file uploads
├── skills/                        # Reusable AI Agent Integration Skills
│   └── ragai-api-integration/     # Universal drop-in skill for student & employee portals
├── db/                            # Relational Database Engine
│   ├── models.py                  # SQLAlchemy ORM models (SQLite & PostgreSQL dual-mode)
│   └── session.py                 # Async database engine and session factory
├── ingestion/                     # Ingestion & Document Processing Pipeline
│   ├── chunker.py                 # Layout-aware sentence-preserving chunker (400 words)
│   ├── extractors.py              # DOCX, PDF, and TXT extractors (with Markdown tables)
│   ├── folder_watcher.py          # Continuous reconciliation folder watcher
│   ├── manifest.py                # SHA-256 document change detection manager
│   ├── path_tagger.py             # Automated folder-to-metadata tag inference
│   └── pipeline.py                # Unified document ingestion pipeline
├── infra/                         # Production Infrastructure Configuration
│   ├── docker-compose.prod.yml    # Complete 8-service production stack
│   ├── k8s/                       # Kubernetes manifests (Deployment, Service, HPA, ConfigMap)
│   └── nginx/                     # Nginx configuration (reverse proxy & rate limiting)
├── monitoring/                    # Observability Configurations
│   ├── alert_rules.yml            # Prometheus alert rules
│   ├── prometheus.yml             # Prometheus scrape job definition
│   └── grafana/dashboards/        # Pre-configured Grafana dashboard JSON
├── reports/                       # Generated Quality & Verification Reports
├── scripts/                       # Operational & Testing Scripts
│   ├── backup.py                  # Disaster recovery snapshot backup tool
│   ├── evaluate_rag.py            # Quality evaluation & ground truth benchmark runner
│   ├── fine_tune_lora.py          # PEFT LoRA fine-tuning script
│   ├── quantize_model.py          # AWQ 4-bit model quantization exporter
│   ├── restore.py                 # Disaster recovery snapshot restore tool
│   ├── run_all_tests.py           # Master test runner (executes all 16 test suites)
│   ├── run_chaos_experiments.py   # Chaos engineering fault-injection suite
│   ├── run_stress_test.py         # 100-user concurrency stress benchmark
│   └── test_*.py                  # Unit and integration test suites for all phases
├── tests/                         # Test Data & Load Scripts
│   ├── data/                      # Ground truth evaluation dataset (ground_truth_eval.json)
│   └── load/                      # Locust user scenarios (locustfile.py)
├── workers/                       # Asynchronous Task Workers
│   ├── celery_app.py              # Celery worker configuration & broker settings
│   └── ingest_tasks.py            # Celery task for async document processing
├── Dockerfile                     # Production multi-stage Docker container specification
├── pyproject.toml                 # Project packaging and metadata
└── university_rag.db              # Local SQLite database instance
```

---

## 4. Prerequisites & System Requirements

### Hardware Requirements
- **Development / Evaluation Mode**: Any modern CPU (x86_64 or ARM64), 8 GB RAM, 10 GB free disk space.
- **Production Mode (with Local LLM Inference)**:
  - 1x NVIDIA GPU with $\ge 16\text{ GB}$ VRAM (e.g., RTX 4090, A10G, L4) for 7B/8B parameter models.
  - Or 4-bit AWQ quantized inference requiring only $4.8\text{ GB}$ VRAM.
  - CPU-only fallback runs using the built-in resilient local synthesizer with zero external dependencies.

### Software Requirements
- **Python**: Version `3.11` or higher (`3.11`, `3.12`, or `3.14`).
- **Operating System**: Windows 10/11, macOS, or Ubuntu 22.04+ LTS.
- **Optional External Services** (the system automatically falls back to in-memory/local alternatives if absent):
  - **Redis 7.0+** (defaults to in-memory TTL cache fallback).
  - **Qdrant 1.7+** (defaults to local persistent storage in `./qdrant_data/`).
  - **Docker & Docker Compose** (for multi-service container orchestration).

---

## 5. Installation & Setup (0 to 100 Guide)

### Automated 1-Click Setup (Recommended)

The repository provides fully automated setup scripts that inspect your GPU (NVIDIA CUDA or CPU), configure PyTorch with the correct hardware-accelerated wheels, create the virtual environment, install all dependencies, initialize the database, provision runtime directories, and index sample courses.

#### On Windows (PowerShell or CMD)
Run the automated Windows setup script:
```powershell
# In PowerShell:
powershell -ExecutionPolicy Bypass -File setup_windows.ps1

# Or double-click / run in CMD:
setup_windows.bat
```

#### On Ubuntu / Linux
Make the script executable and run:
```bash
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

#### Cross-Platform Python Engine
Alternatively, run the unified Python hardware setup runner on any operating system:
```bash
python scripts/setup_environment.py
```

---

### Manual Step-by-Step Setup

If you prefer manual configuration:

### Step 1: Clone or Navigate to the Repository
```bash
cd /d/RagAi    # (or cd d:\RagAi on Windows PowerShell)
```

### Step 2: Create and Activate a Virtual Environment
```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS (Bash)
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
```powershell
python -m pip install --upgrade pip
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite rank-bm25 httpx python-docx pyjwt cryptography prometheus-client celery redis qdrant-client sentence-transformers
```

*(Optional: For high-accuracy dense embeddings and cross-encoder reranking on GPU nodes, also run: `pip install sentence-transformers torch`)*

### Step 4: Initialize the Database
The database tables initialize automatically on first startup, or you can explicitly trigger table creation:
```powershell
python -c "import asyncio; from db.session import init_db; asyncio.run(init_db())"
```

---

## 6. Configuration & Environment Variables

The application reads configuration from environment variables or a local `.env` file via `api/core/config.py`. 

Create a `.env` file in the project root:

```ini
# Core API Settings
PROJECT_NAME="Enterprise University RAG Platform"
API_KEY="dev-secret-key-rag-university"
JWT_SIGNING_KEY="supersecret_jwt_signing_key_for_university_rag_at_least_64_characters_long"

# Database Configuration (SQLite by default, PostgreSQL in production)
DATABASE_URL="sqlite+aiosqlite:///./university_rag.db"
# DATABASE_URL="postgresql+asyncpg://appuser:apppassword@localhost:5432/university_rag"

# Vector Store (Qdrant)
QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_COLLECTION="university_corpus"

# Redis Cache & Broker
REDIS_URL="redis://localhost:6379/0"

# Local LLM Inference Engine (vLLM / Ollama)
LOCAL_LLM_API_BASE="http://localhost:8000/v1"
LOCAL_LLM_MODEL="Qwen/Qwen3.8-7B-Instruct"

# Security & Path Protection
ALLOWED_SOURCE_ROOTS="data,uploads,sample_courses"
MAX_QUESTION_LENGTH_CHARS=1000
RATE_LIMIT_PER_MINUTE=60
```

---

## 7. Running the Application

### A. Running the FastAPI Backend
Start the high-performance ASGI server:
```powershell
python -m uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```
Once started, the following web interfaces become active:
- **Student Chat Portal**: [http://localhost:8080/chat](http://localhost:8080/chat) (or [http://localhost:8080/](http://localhost:8080/))
- **Admin Control Console**: [http://localhost:8080/admin](http://localhost:8080/admin)
- **Interactive OpenAPI Documentation**: [http://localhost:8080/docs](http://localhost:8080/docs)
- **Prometheus Metrics Endpoint**: [http://localhost:8080/metrics](http://localhost:8080/metrics)
- **Health Check Probe**: [http://localhost:8080/health](http://localhost:8080/health)

### B. Running Celery Ingestion Workers
For asynchronous background processing of large document uploads:
```powershell
celery -A workers.celery_app worker --loglevel=info -c 4
```
*(Note: If Celery or Redis is offline, the API automatically falls back to an eager in-memory queue).*

### C. Running via Docker Compose (Production Stack)
To run the full 8-service production infrastructure (FastAPI API, Celery Worker, PostgreSQL 16, Qdrant Vector Store, Redis 7, Nginx Reverse Proxy, Prometheus, and Grafana):
```bash
docker compose -f infra/docker-compose.prod.yml up -d --build
```
Check running services:
```bash
docker compose -f infra/docker-compose.prod.yml ps
```

---

## 8. Web User Interfaces

### Student Chat Portal (`/chat`)
- **Direct Link**: `http://localhost:8080/chat`
- **Course Filter**: Scope queries to specific enrolled courses (`CS401`, `CS402`, or all courses).
- **Expandable Citation Cards**: Every answer provides clickable citation cards showing document title, page number, section heading, and contextual excerpt preview.
- **LaTeX Math Rendering**: Formats complex math formulas natively via KaTeX (`$BF = h_L - h_R$`).
- **Markdown Tables**: Formats structured course complexity grids and syllabi tables responsively.
- **Latency Telemetry Badge**: Displays response time and shows whether the response was served from `⚡ Cached Hit (< 1ms)` or `🖥️ Local Inference`.

### Admin Control Console (`/admin`) - September 2026 Edition
- **Direct Link**: `http://localhost:8080/admin`
- **Real-Time Storage Footprint Telemetry**:
  - Live metric reporting for SQLite relational database size, Qdrant vector store footprint, uploads storage, total RAG consumption, and host disk available space (`D:\` drive free space and percentage).
- **Persistent Watched Folders Management**:
  - Folders registered via the Admin Console or setup scripts are permanently persisted in the `watched_folders` database table across page refreshes and server restarts.
  - **Incremental Refetch**: Scans the folder for newly added or modified documents, while bypassing unchanged and duplicate files via SHA-256 signatures.
  - **Force Refetch (Purge & Re-Index)**: Deletes all old documents, vector chunks from Qdrant, and manifest entries originating from the folder, and re-indexes everything from scratch using rapid GPU OCR.
  - **Critical Safety Guard**: Force refetch **always displays an interactive confirmation modal** before execution ("always ask, do not start direct").
  - **Unregister Watched Folder**: Removes a folder from the active watch list without deleting previously ingested RAG documents.
- **Retry Failed Files Engine**:
  - Direct one-click retry button available on the Top Metrics Bar, Ingestion Pipeline Queue panel, and Manifest audit tab to re-attempt extraction on all files marked as failed.
- **Hugging Face Token & Offline Model Preloader**:
  - **Hugging Face Access Token (`HF_TOKEN`)**: Configure and save your personal HF token directly from the Admin Portal into `.env` and active environment for high-speed downloads without anonymous rate limits.
  - **Pre-download / Warm Up Models Button**: Download and verify dense embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and reranker models into local disk cache before users ask questions, eliminating runtime download stalls.
  - **CLI Preloader**: Run `python scripts/preload_models.py` during offline deployment or setup.
- **Universal Directory & File Selector**:
  - Click **"Open Directory Selector"** to open a visual filesystem tree explorer with drive switching (`C:\`, `D:\`), folder navigation, manual path jumping, and one-click path selection across any drive.
- **Complete RAG Cascade Deletion**:
  - Document catalog features **"Delete from RAG"** and **"Delete Selected"** batch buttons. Permanently purges document metadata, all chunk records, 384-dim Qdrant vector embeddings, manifest entries, and cache slots.
- **Multi-Tenant API Key Management**:
  - Generate scoped API keys (`rag_live_...`) with custom roles (`student`, `faculty`, `admin`), department filters, and per-key rate limits.
  - Plaintext secret key displayed once with copy-to-clipboard modal.
  - Dynamic Enable / Disable switches and instant key revocation.
  - Stored securely using SHA-256 digests.
- **External Source & URL Governance**:
  - Define domain allowlists (`allow`) and security blocklists (`disallow`) with wildcard matching (`https://*.university.edu/*`).
  - Interactive live URL Policy Tester to evaluate external syllabus links.
- **Hardware & Telemetry Engine**:
  - Real-time NVIDIA CUDA GPU VRAM utilization, Tensor Core load, and RapidOCR GPU acceleration monitoring.

---

## 9. API Endpoints Reference

### 1. Grounded Question-Answering
- **Endpoint**: `POST /api/v1/ask`
- **Request Body**:
```json
{
  "question": "What is an AVL tree and what is its rebalancing rule?",
  "department": "ComputerScience",
  "course": "CS401"
}
```
- **Response** (`200 OK`):
```json
{
  "answer": "Based on verified course material (lecture1_notes.docx, Chapter 1: AVL Trees):\n\nAn AVL tree is a strictly self-balancing binary search tree...",
  "citations": [
    {
      "document_id": "7e93c82a-879d-400d-91d9-b4296d36394c",
      "title": "lecture1_notes.docx",
      "page_number": 2,
      "section": "Chapter 1: AVL Trees",
      "snippet": "An AVL tree is a self-balancing binary search tree..."
    }
  ],
  "served_by": "local"
}
```

### 2. OpenAI-Compatible Chat Completions
- **Endpoint**: `POST /v1/chat/completions`
- **Description**: Drop-in proxy allowing existing OpenAI clients to interact with the university corpus.
- **Request Body**:
```json
{
  "model": "university-rag",
  "messages": [
    {"role": "user", "content": "When are the instructor office hours for CS401?"}
  ],
  "temperature": 0.1
}
```

### 3. Asynchronous Document Upload
- **Endpoint**: `POST /api/v1/documents/upload` (Requires Faculty or Admin JWT)
- **Content-Type**: `multipart/form-data`
- **Parameters**: `file` (binary), `department` (string), `course` (string)
- **Response** (`202 Accepted`):
```json
{
  "task_id": "3b29c91f-8e42-4f2b-b9d1-094bf648483b",
  "filename": "lecture_nlp.txt",
  "status": "queued"
}
```

### 4. Task Polling
- **Endpoint**: `GET /api/v1/documents/tasks/{task_id}`
- **Response** (`200 OK`):
```json
{
  "task_id": "3b29c91f-8e42-4f2b-b9d1-094bf648483b",
  "status": "completed",
  "state": "SUCCESS",
  "result": {"status": "success", "chunks_count": 2}
}
```

### 5. Authentication & SSO
- **Login**: `POST /auth/login` (body: `{"external_id": "faculty_jane", "role": "faculty", "department": "ComputerScience"}`) $\rightarrow$ Returns JWT bearer token.
- **API Key Token**: `POST /auth/token` with header `X-API-Key: dev-secret-key-rag-university`.
- **Identity Profile**: `GET /auth/me` with header `Authorization: Bearer <token>`.

### 6. OpenViking Context Filesystem & Tiered Storage (`ragai://`)
- **Virtual Hierarchy Tree**: `GET /api/v1/context/tree?department=Computer+Science` (OpenViking `ov tree`)
- **List Directory Children**: `GET /api/v1/context/ls?uri=ragai://knowledge` (OpenViking `ov ls`)
- **Progressive Tier Resolution**: `GET /api/v1/context/resolve?uri=ragai://knowledge/ComputerScience/CS401&tier=l1` (OpenViking `ov read`)
- **Directory Semantic Find**: `POST /api/v1/context/find` with body `{"query": "CPU scheduling", "top_k": 5}` (OpenViking `ov find`)
- **Context Telemetry & Savings**: `GET /api/v1/context/stats`
- **Synchronize Context Tiers**: `POST /api/v1/context/sync` (Requires Admin API Key)

---

## 10. Document Ingestion Pipeline

The ingestion pipeline (`ingestion/pipeline.py`) executes five sequential stages:

```
[Course Document] 
       │
       ▼
[1. Path Tagging]     --> Infers department, semester, and course from folder hierarchy
       │
       ▼
[2. Change Detection] --> SHA-256 hash compared against manifest; skips unchanged files
       │
       ▼
[3. Extraction]       --> Extracts paragraphs, Markdown tables, and LaTeX math formulas
       │
       ▼
[4. Chunking]         --> Layout-aware sliding-window chunker (400 words, 50-word overlap)
       │
       ▼
[5. Hybrid Indexing]  --> Computes 384-dim dense vectors (Qdrant) & tokenizes sparse BM25
```

To ingest a directory manually:
```powershell
python -c "
import asyncio
from ingestion.folder_watcher import FolderWatcher
watcher = FolderWatcher()
asyncio.run(watcher.reconcile_folder('data/sample_courses'))
"
```

---

## 11. Multi-Modal Processing (LaTeX Math & Tables)

The platform includes built-in support for academic documents containing complex tables and equations:

### Table Serialization
`DOCXExtractor` iterates elements in their natural document body sequence. Tabular data from `.docx` and `.pdf` files is converted directly into Markdown table syntax:
```markdown
| Algorithm | Average Search | Worst-Case Search | Space Complexity |
| :--- | :--- | :--- | :--- |
| Unsorted Array | O(n) | O(n) | O(n) |
| AVL Tree | O(log n) | O(log n) | O(n) |
```
This preserves column-row relationships so vector and BM25 retrievals can match cross-cell queries.

### LaTeX Math Formulas
Formulas such as `$BF(v) = h(v.left) - h(v.right)$` and `$$\sum_{i=1}^n x_i$$` are preserved without backslash corruption and rendered via KaTeX on the student portal.

---

## 12. Domain Fine-Tuning & Quantization Pipeline

To adapt small local language models to university-specific jargon, abbreviations, and syllabi:

### 1. Synthesize Instruction Dataset
Extracts question-answer pairs from the ingested university corpus into standard Alpaca/ChatML format:
```powershell
python data/fine_tuning/dataset_generator.py
```
Outputs `data/fine_tuning/train.jsonl` and `data/fine_tuning/val.jsonl`.

### 2. Execute LoRA Fine-Tuning
Runs Parameter-Efficient Fine-Tuning (PEFT) targeting attention projections ($r=16, \alpha=32$):
```powershell
python scripts/fine_tune_lora.py
```
Outputs adapter configuration and model weights to `models/lora_adapter/`.

### 3. Export 4-Bit AWQ Quantization
Converts the adapted weights into an optimized 4-bit GEMM model, reducing VRAM consumption from **15.5 GB** to **4.8 GB** (~3.2x compression):
```powershell
python scripts/quantize_model.py
```
Outputs `models/quantized/quantization_config.json` and `model_card.json`.

---

## 13. Disaster Recovery, Automated Backup & Restore

### Automated Snapshot Backup
Creates a timestamped snapshot of the SQLite/PostgreSQL database, Qdrant vector store collections, and uploaded documents, calculates a SHA-256 verification checksum, and auto-prunes snapshots older than 30 days:
```powershell
python scripts/backup.py
```
Output archive saved to: `backups/rag_backup_YYYYMMDD_HHMMSS.tar.gz`.

### Automated Disaster Recovery Restore
Verifies the SHA-256 archive integrity and restores the system to a clean state with zero data loss:
```powershell
python scripts/restore.py backups/rag_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

## 14. Observability & Monitoring (Prometheus & Grafana)

The service exposes standardized OpenMetrics at `/metrics`.

### Key Metrics Monitored
- `rag_query_total{status="success|abstained|rate_limited", served_by="local|hosted|cache", department="..."}`: Total user query count.
- `rag_query_duration_seconds`: Histogram measuring end-to-end request latencies.
- `rag_retrieval_duration_seconds`: Histogram measuring hybrid search latency.
- `rag_cache_hits_total`: Counter tracking semantic cache hits.
- `rag_documents_total`: Gauge tracking total documents registered.
- `rag_chunks_total`: Gauge tracking total chunks indexed.

### Prometheus Configuration
Located in `monitoring/prometheus.yml`. Scrapes the API service every 15 seconds.

### Grafana Dashboard
A pre-configured Grafana dashboard JSON is available at `monitoring/grafana/dashboards/university_rag.json`.

---

## 15. Automated Verification & Test Harnesses

The repository provides a complete automated testing suite across all 19 phases:

### Run the Master Test Suite (All 16 Test Suites)
```powershell
python scripts/run_all_tests.py
```
*Executes all suites sequentially and generates `reports/master_test_report.md`.*

### Individual Test Suites
| Phase | Focus Area | Command |
| :--- | :--- | :--- |
| **Phase 1-2** | Folder Ingestion & Database Manifest | `python scripts/test_ingest.py` |
| **Phase 3-4** | Embeddings & Hybrid RRF Retrieval | `python scripts/test_retrieval.py` |
| **Phase 4-6** | Core FastAPI & LLM Routing | `python scripts/test_api.py` |
| **Phase 7** | Redis Semantic Cache & Rate Limiter | `python scripts/test_cache_and_ratelimit.py` |
| **Phase 8** | Celery Worker Ingestion Pipeline | `python scripts/test_workers.py` |
| **Phase 9** | Docker, Nginx & Kubernetes Manifests | `python scripts/test_infra_config.py` |
| **Phase 10** | Admin & Student Web UI Endpoints | `python scripts/test_ui_endpoints.py` |
| **Phase 11** | SSO Authentication, JWT & RBAC | `python scripts/test_auth_rbac.py` |
| **Phase 12** | Prometheus Metrics Telemetry | `python scripts/test_metrics.py` |
| **Phase 13** | Concurrency Stress Test (100 Users) | `python scripts/run_stress_test.py` |
| **Phase 14** | Chaos Fault Injections (5 Scenarios) | `python scripts/run_chaos_experiments.py` |
| **Phase 15** | LoRA Fine-Tuning & Quantization | `python scripts/test_fine_tuning.py` |
| **Phase 16** | Multi-Modal Math & Tables | `python scripts/test_multimodal.py` |
| **Phase 17** | Disaster Recovery Backup & Restore | `python scripts/test_backup_restore.py` |
| **Phase 18** | Ground Truth Benchmark (RAGAS Metrics) | `python scripts/evaluate_rag.py` |
| **Phase 19** | OWASP Top 10 for LLMs Security Audit | `python scripts/test_security_audit.py` |
| **Phase 20** | Admin Governance, API Keys, Tree & Purge | `python scripts/test_admin_governance.py` |

---

## 16. Security Architecture & OWASP Hardening

Validated against the **OWASP Top 10 for Large Language Models**:

- **LLM01: Prompt Injection**: All retrieved text is fenced inside `<untrusted_academic_context>` tags with system instructions forbidding command execution. Delimiters (`</untrusted_academic_context>`, `<system>`, `[INST]`) and zero-width characters are automatically stripped before prompt construction.
- **LLM03: Training Data Poisoning / Corpus Ingestion**: Watched folder registration strictly validates paths against `ALLOWED_SOURCE_ROOTS` to prevent directory traversal (`../../Windows`, `/etc/shadow`).
- **LLM04: Model Denial of Service**: Inbound questions are capped at 1,000 characters; excessive lengths are rejected with `HTTP 422 Unprocessable Entity`.
- **LLM06: Sensitive Information Disclosure**: Student questions are hashed using SHA-256 before being written to `query_audit_log`. No plaintext query text or student PII is persisted.
- **LLM08: Excessive Agency**: Role-based access control (`require_role("admin")`) prevents unauthorized students from triggering folder scans or altering system configurations.
- **LLM09: Hallucination Prevention**: If core query terms do not appear in the retrieved context, the synthesizer automatically returns the official abstention message with zero citations.

---

## 17. Troubleshooting & FAQ

**Q: What happens if Redis is offline?**  
A: The system automatically engages the built-in in-memory TTL cache (`api/core/cache.py`). User queries and rate limits continue functioning normally without errors.

**Q: What happens if Qdrant is offline?**  
A: The hybrid retriever automatically degrades to sparse BM25 Okapi retrieval (`api/rag/retriever.py`), ensuring students can still find relevant course documents by keyword.

**Q: How do I change the local LLM model?**  
A: Update `LOCAL_LLM_MODEL` and `LOCAL_LLM_API_BASE` in your `.env` file (e.g., to point to an Ollama or vLLM instance running on `http://localhost:11434/v1`).

**Q: How do I add new course documents?**  
A: Either copy the files into a watched folder (e.g. `data/sample_courses/CS401/`), or navigate to `http://localhost:8080/admin` and use the folder registration tool.

---

## License

Enterprise Academic Software License. Built for university research, education, and institutional deployment.
