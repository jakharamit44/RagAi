<#
.SYNOPSIS
    Automated Setup Script for Enterprise University RAG Platform on Windows.
.DESCRIPTION
    Detects NVIDIA GPU, installs hardware-optimized PyTorch (CUDA or CPU),
    creates virtual environment, installs all dependencies, initializes the
    database, creates required directories, and provisions sample courses.
#>

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "       ENTERPRISE UNIVERSITY RAG PLATFORM - WINDOWS SETUP WIZARD          " -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Detect Python
Write-Host "--> Step 1: Checking Python runtime..." -ForegroundColor Yellow
$PythonCmd = "python"
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyVersions = py --list 2>&1
    if ($pyVersions -match "3\.11") {
        $PythonCmd = "py -3.11"
        Write-Host "    [OK] Detected Python 3.11 (Recommended for PyTorch/CUDA)" -ForegroundColor Green
    } elseif ($pyVersions -match "3\.12") {
        $PythonCmd = "py -3.12"
        Write-Host "    [OK] Detected Python 3.12" -ForegroundColor Green
    } else {
        $PythonCmd = "py"
        Write-Host "    [OK] Using default Python Launcher" -ForegroundColor Green
    }
} else {
    Write-Host "    [OK] Using system python" -ForegroundColor Green
}

# 2. Virtual Environment
Write-Host "`n--> Step 2: Provisioning Virtual Environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "    Creating virtual environment with $PythonCmd..." -ForegroundColor Gray
    Invoke-Expression "$PythonCmd -m venv .venv"
    Write-Host "    [OK] Created .venv directory." -ForegroundColor Green
} else {
    Write-Host "    [OK] Found existing .venv directory." -ForegroundColor Green
}

$VenvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$VenvPip = Join-Path (Get-Location) ".venv\Scripts\pip.exe"

# Upgrade pip
Write-Host "    Upgrading pip and wheel..." -ForegroundColor Gray
& $VenvPython -m pip install --upgrade pip setuptools wheel --quiet

# 3. Detect GPU & Install Hardware-Optimized PyTorch
Write-Host "`n--> Step 3: Hardware Acceleration & GPU Detection..." -ForegroundColor Yellow
$HasNvidiaGpu = $false
$GpuName = ""
$CudaIndexUrl = "https://download.pytorch.org/whl/cu124"

try {
    $smiOutput = nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>$null
    if ($smiOutput) {
        $HasNvidiaGpu = $true
        $GpuParts = $smiOutput -split ","
        $GpuName = $GpuParts[0].Trim()
        $GpuMem = $GpuParts[1].Trim()
        $GpuDriver = $GpuParts[2].Trim()
        Write-Host "    [GPU FOUND] $GpuName" -ForegroundColor Green
        Write-Host "    VRAM: $GpuMem MB | Driver: $GpuDriver" -ForegroundColor Gray
    }
} catch {
    $HasNvidiaGpu = $false
}

if ($HasNvidiaGpu) {
    # Detect Python version to select the exact CUDA wheel channel
    $PyVerStr = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($PyVerStr -eq "3.14") {
        $CudaIndexUrl = "https://download.pytorch.org/whl/nightly/cu126"
    } else {
        $CudaIndexUrl = "https://download.pytorch.org/whl/cu124"
    }
    Write-Host "    Installing PyTorch with CUDA acceleration ($CudaIndexUrl)..." -ForegroundColor Cyan
    & $VenvPip install torch torchvision torchaudio --upgrade --pre --index-url $CudaIndexUrl
    Write-Host "    Installing SentenceTransformers for GPU embeddings & reranking..." -ForegroundColor Cyan
    & $VenvPip install sentence-transformers
} else {
    Write-Host "    [NOTICE] No NVIDIA GPU detected. Installing CPU-optimized PyTorch..." -ForegroundColor Yellow
    & $VenvPip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
}

# 4. Install Base Requirements
Write-Host "`n--> Step 4: Installing Core Application Dependencies..." -ForegroundColor Yellow
$BasePackages = @(
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.28.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "sqlalchemy>=2.0.28",
    "aiosqlite>=0.20.0",
    "rank-bm25>=0.2.2",
    "httpx>=0.27.0",
    "python-docx>=1.1.0",
    "pyjwt>=2.8.0",
    "cryptography>=42.0.0",
    "prometheus-client>=0.20.0",
    "celery>=5.3.6",
    "redis>=5.0.3",
    "qdrant-client>=1.8.0",
    "python-multipart>=0.0.9",
    "accelerate>=0.28.0",
    "transformers>=4.40.0"
)

& $VenvPip install $BasePackages --quiet
Write-Host "    [OK] Core dependencies installed successfully." -ForegroundColor Green

# 5. Provision Runtime Directories
Write-Host "`n--> Step 5: Provisioning Directory Structure..." -ForegroundColor Yellow
$Directories = @(
    "data/sample_courses/CS401",
    "data/sample_courses/CS402",
    "data/uploads",
    "data/artifacts/figures",
    "data/fine_tuning",
    "data/downloads/mdu_scraped",
    "data/qdrant_storage",
    "backups",
    "reports",
    "models",
    "models/all-MiniLM-L6-v2",
    "models/Qwen3-Reranker-0.6B",
    "models/Qwen2.5-3B-Instruct",
    "models/cache",
    "models/lora_adapter",
    "models/quantized"
)

foreach ($dir in $Directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "    [OK] All data, backup, and in-project model directories provisioned." -ForegroundColor Green

# 6. Generate .env Configuration
Write-Host "`n--> Step 6: Checking Environment Configuration (.env)..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    $RandomBytes = New-Object byte[] 32
    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($RandomBytes)
    $JwtKey = [BitConverter]::ToString($RandomBytes) -replace '-'

    $EnvContent = @"
PROJECT_NAME="Enterprise University RAG Platform"
API_KEY="dev-secret-key-rag-university"
JWT_SIGNING_KEY="$JwtKey$JwtKey"
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
"@
    Set-Content -Path ".env" -Value $EnvContent -Encoding UTF8
    Write-Host "    [OK] Created .env with generated 64-char JWT signing key and in-project models path." -ForegroundColor Green
} else {
    Write-Host "    [OK] Existing .env file found." -ForegroundColor Green
}

# 7. Initialize Database & Seed Corpus
Write-Host "`n--> Step 7: Initializing Database & Reconciling Course Documents..." -ForegroundColor Yellow
& $VenvPython -c "import asyncio; from db.session import init_db; asyncio.run(init_db())"
& $VenvPython -c "
import asyncio
from ingestion.folder_watcher import FolderWatcher
watcher = FolderWatcher()
asyncio.run(watcher.reconcile_folder('data/sample_courses'))
"
Write-Host "    [OK] Database initialized and sample documents indexed." -ForegroundColor Green

# 8. Pre-download & Save AI Models Directly Inside Project
Write-Host "`n--> Step 8: Pre-downloading and Saving AI Models Inside Project..." -ForegroundColor Yellow
$ProjectRoot = (Get-Location).Path
$env:HF_HOME = "$ProjectRoot\models\cache"
$env:TRANSFORMERS_CACHE = "$ProjectRoot\models\cache"
$env:SENTENCE_TRANSFORMERS_HOME = "$ProjectRoot\models\cache"
& $VenvPython scripts/preload_models.py
Write-Host "    [OK] AI Models saved directly inside project models/ folder." -ForegroundColor Green

# 9. Complete & Ready
Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "                 SETUP COMPLETED SUCCESSFULLY!                           " -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the application:" -ForegroundColor Cyan
Write-Host "  1. Activate virtual environment:" -ForegroundColor White
Write-Host "     .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  2. Launch FastAPI service:" -ForegroundColor White
Write-Host "     python -m uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload" -ForegroundColor Yellow
Write-Host ""
Write-Host "Available Web Interfaces:" -ForegroundColor Cyan
Write-Host "  * Student Chat Portal:   http://localhost:8080/" -ForegroundColor White
Write-Host "  * Admin Control Console: http://localhost:8080/admin" -ForegroundColor White
Write-Host "  * API Interactive Docs:  http://localhost:8080/docs" -ForegroundColor White
Write-Host "  * Prometheus Metrics:    http://localhost:8080/metrics" -ForegroundColor White
Write-Host ""
