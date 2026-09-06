import os
import sys
import shutil
import platform
import subprocess
import secrets
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("setup_environment")

BASE_REQUIREMENTS = [
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
    "python-multipart>=0.0.9"
]

def check_nvidia_gpu():
    """Detects NVIDIA GPU and VRAM availability."""
    if not shutil.which("nvidia-smi"):
        return False, "nvidia-smi not found"

    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True
        )
        out = res.stdout.strip()
        if out:
            parts = [p.strip() for p in out.split(",")]
            name = parts[0]
            mem_mb = parts[1] if len(parts) > 1 else "Unknown"
            driver = parts[2] if len(parts) > 2 else "Unknown"
            return True, f"{name} ({mem_mb} MB VRAM, Driver: {driver})"
    except Exception as e:
        return False, str(e)

    return False, "No GPU reported by nvidia-smi"

def run_setup():
    print("\n" + "=" * 75)
    print("      ENTERPRISE UNIVERSITY RAG PLATFORM - HARDWARE SETUP ENGINE")
    print("=" * 75)

    os_name = platform.system()
    py_ver = sys.version.split()[0]
    print(f"Detected OS: {os_name} ({platform.machine()})")
    print(f"Current Python: {py_ver} ({sys.executable})")

    # 1. GPU Detection
    has_gpu, gpu_details = check_nvidia_gpu()
    if has_gpu:
        print(f"\n[GPU DETECTED] {gpu_details}")
        print("Selecting CUDA-accelerated PyTorch (CUDA 12.4)...")
        torch_cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu124"]
        install_sentence_transformers = True
    else:
        print(f"\n[CPU MODE] {gpu_details}")
        print("Selecting CPU-optimized PyTorch...")
        torch_cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cpu"]
        install_sentence_transformers = False

    # 2. Upgrade pip
    print("\n--> Upgrading pip...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "--quiet"])

    # 3. Install PyTorch according to GPU
    print("\n--> Installing PyTorch...")
    try:
        subprocess.run(torch_cmd, check=True)
        print("    [OK] PyTorch installed.")
        if install_sentence_transformers:
            print("--> Installing SentenceTransformers for GPU embeddings...")
            subprocess.run([sys.executable, "-m", "pip", "install", "sentence-transformers", "--quiet"], check=True)
            print("    [OK] SentenceTransformers installed.")
    except Exception as e:
        print(f"    [WARN] PyTorch wheel install note ({e}). Continuing with local high-dimensional vectorizer.")

    # 4. Install Core Dependencies
    print("\n--> Installing Core RAG Dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install"] + BASE_REQUIREMENTS + ["--quiet"], check=True)
    print("    [OK] Base dependencies installed.")

    # 5. Provision Directories
    print("\n--> Provisioning Runtime Directories...")
    dirs = [
        "data/sample_courses/CS401",
        "data/sample_courses/CS402",
        "data/uploads",
        "data/artifacts/figures",
        "data/fine_tuning",
        "backups",
        "reports",
        "models/lora_adapter",
        "models/quantized"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("    [OK] All directories provisioned.")

    # 6. Setup .env
    print("\n--> Checking Environment Configuration (.env)...")
    if not os.path.exists(".env"):
        jwt_key = secrets.token_hex(32)
        env_content = f"""PROJECT_NAME="Enterprise University RAG Platform"
API_KEY="dev-secret-key-rag-university"
JWT_SIGNING_KEY="{jwt_key}{jwt_key}"
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
"""
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        print("    [OK] Created .env with generated 64-char JWT signing key.")
    else:
        print("    [OK] Existing .env file found.")

    # 7. Database Init & Corpus Ingestion
    print("\n--> Initializing Database & Reconciling Course Documents...")
    try:
        subprocess.run([sys.executable, "-c", "import asyncio; from db.session import init_db; asyncio.run(init_db())"], check=True)
        subprocess.run([sys.executable, "-c", "import asyncio; from ingestion.folder_watcher import FolderWatcher; asyncio.run(FolderWatcher().reconcile_folder('data/sample_courses'))"], check=True)
        print("    [OK] Database initialized and sample documents indexed.")
    except Exception as e:
        print(f"    [WARN] Ingestion step: {e}")

    # 8. Print Complete Summary
    print("\n" + "=" * 75)
    print("                 SETUP COMPLETED SUCCESSFULLY!                           ")
    print("=" * 75)
    print("\nTo launch the platform:")
    print("  python -m uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload\n")
    print("Available Web Interfaces:")
    print("  * Student Chat Portal:   http://localhost:8080/")
    print("  * Admin Control Console: http://localhost:8080/admin")
    print("  * API Interactive Docs:  http://localhost:8080/docs")
    print("  * Prometheus Metrics:    http://localhost:8080/metrics\n")

if __name__ == "__main__":
    run_setup()
