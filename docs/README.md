# Enterprise University RAG System

Enterprise-Grade, Local-First, Security-Aware Retrieval-Augmented Generation system designed for 1,00,000+ university students.

## Architecture Highlights
- **Local-First LLM**: Runs on-premise vLLM / Ollama by default. Hosted OpenAI-format API is an explicit, off-by-default fallback.
- **Folder-Watch Ingestion**: Point admin UI at a directory or network share once; watchdog events + reconciliation automatically indexes new and updated documents.
- **Handwriting OCR**: Local VLM (PaddleOCR-VL baseline) for scanned handwritten notes.
- **Hybrid Retrieval**: BM25 sparse + Qdrant dense vector search with Reciprocal Rank Fusion and cross-encoder reranking (Qwen3).
- **Enterprise Plumbing**: Redis semantic cache, PostgreSQL manifest & metadata, RabbitMQ/Celery workers, Nginx load balancer.

## Quickstart (Local Dev)
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Start infrastructure via Docker Compose:
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```
3. Initialize the database schema:
   ```bash
   python scripts/init_db.py
   ```
4. Start the API service:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```
