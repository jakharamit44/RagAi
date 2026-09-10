import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DEFAULT_HF_CACHE = os.path.join(DEFAULT_MODELS_DIR, "cache")
os.environ.setdefault("HF_HOME", DEFAULT_HF_CACHE)
os.environ.setdefault("TRANSFORMERS_CACHE", DEFAULT_HF_CACHE)
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", DEFAULT_HF_CACHE)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core & Auth (Phase 6, 11, 19)
    API_KEY: str = Field(default="dev-insecure-api-key", description="Static key for service-to-service calls")
    JWT_SIGNING_KEY: str = Field(default="dev-insecure-jwt-signing-key-university-rag-secure-secret-token-32bytes", description="Signs/verifies student/staff access tokens")
    JWT_ACCESS_TOKEN_TTL_MINUTES: int = Field(default=15, description="Short-lived access token TTL")
    JWT_REFRESH_TOKEN_TTL_DAYS: int = Field(default=30, description="Refresh token TTL")

    # Database & Storage (Phase 1, 3, 7)
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./university_rag.db", description="Relational DB connection string")
    VECTOR_STORE_HOST: str = Field(default="localhost", description="Qdrant host")
    VECTOR_STORE_PORT: int = Field(default=6333, description="Qdrant port")
    VECTOR_COLLECTION_NAME: str = Field(default="university_corpus", description="Primary vector collection")
    QDRANT_COLLECTION_NAME: str = Field(default="university_corpus", description="Qdrant collection alias")
    OBJECT_STORAGE_ENDPOINT: str = Field(default="http://localhost:9000", description="S3-compatible/MinIO endpoint")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Cache & rate limit Redis")

    # Folder Watcher & Ingestion (Phase 1, 8, 19)
    WATCHED_FOLDERS: str = Field(default="", description="Comma-separated startup watched folder paths")
    ALLOWED_SOURCE_ROOTS: str = Field(default="data,uploads,sample_courses", description="Server-side allowed path prefixes (Phase 19)")
    RESCAN_INTERVAL_SECONDS: int = Field(default=900, description="Periodic reconciliation safety net interval")
    MAX_CONCURRENT_INGESTION_JOBS: int = Field(default=10, description="Backpressure cap on ingestion jobs")
    MAX_UPLOAD_SIZE_MB: int = Field(default=100, description="Cap on single-file upload size")

    # LLM Router & Generation (Phase 5)
    CHAT_MODEL_NAME: str = Field(default="Qwen/Qwen2.5-3B-Instruct", description="Local in-project chat generation model")
    DEFAULT_LLM_MODEL: str = Field(default="Qwen/Qwen2.5-3B-Instruct", description="Default local LLM model")
    CHAT_MODEL_ALIAS: str = Field(default="Qwen/Qwen2.5-3B-Instruct", description="Resolved model alias")
    OLLAMA_HOST: Optional[str] = Field(default=None, description="Optional local Ollama endpoint")
    VLLM_ENDPOINT: Optional[str] = Field(default=None, description="Optional local vLLM endpoint")
    ENABLE_HOSTED_FALLBACK: bool = Field(default=False, description="Explicit opt-in to hosted fallback")
    HOSTED_API_BASE: Optional[str] = Field(default=None, description="Hosted provider base URL")
    HOSTED_API_KEY: Optional[str] = Field(default=None, description="Hosted provider API key")
    HOSTED_API_MODEL: Optional[str] = Field(default=None, description="Hosted model name")
    GPU_AUTODETECT: bool = Field(default=True, description="Autodetect CUDA/GPU availability")
    ENABLE_4BIT_QUANTIZATION: bool = Field(default=True, description="Enable BitsAndBytes 4-bit NF4 quantization for local LLM to reduce VRAM footprint to ~1.8GB")
    EMBEDDER_DEVICE: str = Field(default="cpu", description="Execution device for embedding model ('cpu' for zero GPU lock contention)")

    # Embedding & Reranking Models (Phase 3, 4)
    HF_TOKEN: Optional[str] = Field(default=None, description="Hugging Face API Token for fast model downloads")
    MODELS_DIR: str = Field(default=DEFAULT_MODELS_DIR, description="Local project models directory")
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Local embedding model (384-dim)")
    RERANKER_MODEL_NAME: str = Field(default="Qwen/Qwen3-Reranker-0.6B", description="Local cross-encoder reranker")

    # Retrieval & Generation (Phase 4, 5)
    TOP_K_RETRIEVE: int = Field(default=20, description="Initial hybrid candidate count")
    TOP_K_FINAL: int = Field(default=5, description="Final context chunk count for LLM")
    MAX_NEW_TOKENS: int = Field(default=384, description="Maximum tokens generated per LLM response")

    # Caching, Rate Limits & Abuse Prevention (Phase 7, 19)
    CACHE_TTL_VOLATILE_SECONDS: int = Field(default=3600, description="Fast-changing cache TTL")
    CACHE_TTL_STABLE_SECONDS: int = Field(default=86400, description="Stable syllabus cache TTL")
    RATE_LIMIT_PER_STUDENT_PER_MINUTE: int = Field(default=20, description="Student query rate limit")
    RATE_LIMIT_PER_IP_PER_MINUTE: int = Field(default=60, description="Unauthenticated IP rate limit")
    MAX_QUESTION_LENGTH_CHARS: int = Field(default=1000, description="Maximum question input length")
    CORS_ALLOWED_ORIGINS: str = Field(default="http://localhost,http://localhost:8000,http://localhost:3000", description="Comma-separated allowed origins")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def local_embedding_model_dir(self) -> str:
        return os.path.join(self.MODELS_DIR, "all-MiniLM-L6-v2")

    @property
    def local_reranker_model_dir(self) -> str:
        return os.path.join(self.MODELS_DIR, "Qwen3-Reranker-0.6B")

    @property
    def local_chat_model_dir(self) -> str:
        return os.path.join(self.MODELS_DIR, "Qwen2.5-3B-Instruct")

    @property
    def resolved_embedding_model(self) -> str:
        local_p = self.local_embedding_model_dir
        if os.path.exists(os.path.join(local_p, "config.json")):
            return local_p
        return self.EMBEDDING_MODEL_NAME

    @property
    def resolved_reranker_model(self) -> str:
        local_p = self.local_reranker_model_dir
        if os.path.exists(os.path.join(local_p, "config.json")):
            return local_p
        return self.RERANKER_MODEL_NAME

    @property
    def resolved_chat_model(self) -> str:
        local_p = self.local_chat_model_dir
        if os.path.exists(os.path.join(local_p, "config.json")):
            return local_p
        return self.CHAT_MODEL_NAME

settings = Settings()

