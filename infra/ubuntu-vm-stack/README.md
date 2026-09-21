# RagAi Infrastructure Deployment Guide

Production deployment guide for hosting the **Data & Vector Storage Tier** (PostgreSQL, Qdrant, Redis) on any Linux VM (Ubuntu, Debian, RHEL) or bare metal server.

---

## 1. Quick Start (Any New Server)

### Step 1: Install Docker & Compose on the Server
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
```

### Step 2: Copy this Directory to the Server
```bash
# On the remote server:
mkdir -p ~/rag-infra
cd ~/rag-infra

# Copy docker-compose.yml and .env.example from RagAi/infra/ubuntu-vm-stack/
cp .env.example .env
```

### Step 3: Start Core Services
```bash
# Starts PostgreSQL (5432), Qdrant (6333), and Redis (6379)
docker compose up -d
```

### Step 4: Verify Health
```bash
docker ps
```

---

## 2. Included Services

| Service | Port | Auth / Key | Description |
| :--- | :--- | :--- | :--- |
| **PostgreSQL 16** | `5432` | Username & Password | Stores all document metadata, chunks, scrape history, and audit logs. Row-level MVCC locking. |
| **Qdrant** | `6333` (REST), `6334` (gRPC) | `api-key` header | 384-dimensional vector embeddings with on-disk storage. Built-in Web dashboard at `http://<VM_IP>:6333/dashboard`. |
| **Redis 7** | `6379` | `requirepass` | Distributed semantic cache, rate-limiting counters, and real-time pub/sub. |

---

## 3. Optional Management GUIs

To enable web management dashboards on the server:

```bash
# Starts Core + CloudBeaver (PostgreSQL Web UI) + RedisInsight (Redis Web UI)
docker compose --profile tools up -d
```

* **PostgreSQL Web GUI (CloudBeaver)**: `http://<VM_IP>:8978`
* **Redis Web GUI (RedisInsight)**: `http://<VM_IP>:5540`
* **Qdrant Web GUI**: `http://<VM_IP>:6333/dashboard`

---

## 4. Optional S3-Compatible Object Storage (MinIO)

To store raw PDFs, syllabus scans, and uploaded documents in an S3-compatible bucket:

```bash
docker compose --profile storage up -d
```

* **MinIO API**: `http://<VM_IP>:9000`
* **MinIO Web Console**: `http://<VM_IP>:9001`

---

## 5. Connecting RagAi on Windows or Application Server

In your application `.env`:

```env
DATABASE_URL="postgresql+asyncpg://ragai:<PASSWORD>@<VM_IP>:5432/university_rag"
USE_REMOTE_QDRANT=true
VECTOR_STORE_HOST=<VM_IP>
VECTOR_STORE_PORT=6333
QDRANT_API_KEY=<QDRANT_KEY>
REDIS_URL="redis://:<PASSWORD>@<VM_IP>:6379/0"
```
