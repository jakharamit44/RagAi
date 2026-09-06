#!/usr/bin/env bash
# ==============================================================================
# Enterprise University RAG Platform - Ubuntu / Linux Automated Setup Script
# ==============================================================================
set -e

echo ""
echo "=========================================================================="
echo "       ENTERPRISE UNIVERSITY RAG PLATFORM - UBUNTU / LINUX SETUP         "
echo "=========================================================================="
echo ""

# 1. Check Python installation
echo "--> Step 1: Checking Python runtime..."
if ! command -v python3 &> /dev/null; then
    echo "    [ERROR] python3 is not installed."
    echo "    Please run: sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "    [OK] Detected Python version: $PYTHON_VERSION"

# 2. Virtual Environment Setup
echo ""
echo "--> Step 2: Provisioning Virtual Environment (.venv)..."
if [ ! -d ".venv" ]; then
    echo "    Creating Python virtual environment..."
    python3 -m venv .venv || {
        echo "    [ERROR] Failed to create virtual environment."
        echo "    Please run: sudo apt install -y python3-venv"
        exit 1
    }
    echo "    [OK] Virtual environment created."
else
    echo "    [OK] Existing .venv directory found."
fi

VENV_PYTHON=".venv/bin/python"
VENV_PIP=".venv/bin/pip"

# Upgrade pip
echo "    Upgrading pip and wheel..."
$VENV_PYTHON -m pip install --upgrade pip setuptools wheel --quiet

# 3. Detect GPU & Install Optimized PyTorch
echo ""
echo "--> Step 3: Hardware Acceleration & GPU Detection..."
HAS_NVIDIA_GPU=false

if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>/dev/null || true)
    if [ -n "$GPU_INFO" ]; then
        HAS_NVIDIA_GPU=true
        echo "    [GPU FOUND] $GPU_INFO"
    fi
fi

if [ "$HAS_NVIDIA_GPU" = true ]; then
    PY_VER_STR=$($VENV_PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$PY_VER_STR" = "3.14" ]; then
        CUDA_INDEX_URL="https://download.pytorch.org/whl/nightly/cu126"
    else
        CUDA_INDEX_URL="https://download.pytorch.org/whl/cu124"
    fi
    echo "    Installing PyTorch with CUDA acceleration ($CUDA_INDEX_URL)..."
    $VENV_PIP install torch torchvision torchaudio --upgrade --pre --index-url $CUDA_INDEX_URL
    echo "    Installing SentenceTransformers for GPU embeddings & reranking..."
    $VENV_PIP install sentence-transformers
else
    echo "    [NOTICE] No NVIDIA GPU detected. Installing CPU-optimized PyTorch..."
    $VENV_PIP install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# 4. Install Base Requirements
echo ""
echo "--> Step 4: Installing Core Application Dependencies..."
$VENV_PIP install \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.28.0" \
    "pydantic>=2.6.0" \
    "pydantic-settings>=2.2.0" \
    "sqlalchemy>=2.0.28" \
    "aiosqlite>=0.20.0" \
    "rank-bm25>=0.2.2" \
    "httpx>=0.27.0" \
    "python-docx>=1.1.0" \
    "pyjwt>=2.8.0" \
    "cryptography>=42.0.0" \
    "prometheus-client>=0.20.0" \
    "celery>=5.3.6" \
    "redis>=5.0.3" \
    "qdrant-client>=1.8.0" \
    "python-multipart>=0.0.9" \
    "accelerate>=0.28.0" \
    "transformers>=4.40.0" \
    --quiet

echo "    [OK] Core dependencies installed successfully."

# 5. Provision Directory Structure
echo ""
echo "--> Step 5: Provisioning Directory Structure..."
mkdir -p data/sample_courses/CS401
mkdir -p data/sample_courses/CS402
mkdir -p data/uploads
mkdir -p data/artifacts/figures
mkdir -p data/fine_tuning
mkdir -p backups
mkdir -p reports
mkdir -p models
mkdir -p models/all-MiniLM-L6-v2
mkdir -p models/Qwen3-Reranker-0.6B
mkdir -p models/Qwen2.5-3B-Instruct
mkdir -p models/cache
mkdir -p models/lora_adapter
mkdir -p models/quantized
echo "    [OK] All directories provisioned."

# 6. Generate .env Configuration
echo ""
echo "--> Step 6: Checking Environment Configuration (.env)..."
if [ ! -f ".env" ]; then
    JWT_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat <<EOF > .env
PROJECT_NAME="Enterprise University RAG Platform"
API_KEY="dev-secret-key-rag-university"
JWT_SIGNING_KEY="${JWT_KEY}${JWT_KEY}"
DATABASE_URL="sqlite+aiosqlite:///./university_rag.db"
QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_COLLECTION="university_corpus"
REDIS_URL="redis://localhost:6379/0"
LOCAL_LLM_API_BASE="http://localhost:8000/v1"
LOCAL_LLM_MODEL="Qwen/Qwen2.5-7B-Instruct"
ALLOWED_SOURCE_ROOTS="data,uploads,sample_courses"
MAX_QUESTION_LENGTH_CHARS=1000
RATE_LIMIT_PER_MINUTE=60
MODELS_DIR="models"
HF_HOME="models/cache"
EOF
    echo "    [OK] Created .env with generated 64-char JWT signing key and in-project models path."
else
    echo "    [OK] Existing .env file found."
fi

# 7. Initialize Database & Seed Corpus
echo ""
echo "--> Step 7: Initializing Database & Reconciling Course Documents..."
$VENV_PYTHON -c "import asyncio; from db.session import init_db; asyncio.run(init_db())"
$VENV_PYTHON -c "
import asyncio
from ingestion.folder_watcher import FolderWatcher
watcher = FolderWatcher()
asyncio.run(watcher.reconcile_folder('data/sample_courses'))
"
echo "    [OK] Database initialized and sample documents indexed."

# 8. Pre-download & Save AI Models Directly Inside Project
echo ""
echo "--> Step 8: Pre-downloading and Saving AI Models Inside Project..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HF_HOME="$SCRIPT_DIR/models/cache"
export TRANSFORMERS_CACHE="$SCRIPT_DIR/models/cache"
export SENTENCE_TRANSFORMERS_HOME="$SCRIPT_DIR/models/cache"
$VENV_PYTHON scripts/preload_models.py
echo "    [OK] AI Models saved directly inside project models/ folder."

# 9. Complete & Ready
echo ""
echo "=========================================================================="
echo "                 SETUP COMPLETED SUCCESSFULLY!                           "
echo "=========================================================================="
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment:"
echo "     source .venv/bin/activate"
echo "  2. Launch FastAPI service:"
echo "     python -m uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload"
echo ""
echo "Available Web Interfaces:"
echo "  * Student Chat Portal:   http://localhost:8080/"
echo "  * Admin Control Console: http://localhost:8080/admin"
echo "  * API Interactive Docs:  http://localhost:8080/docs"
echo "  * Prometheus Metrics:    http://localhost:8080/metrics"
echo ""
