import math
import hashlib
import logging
from typing import List

logger = logging.getLogger(__name__)

class LocalEmbedder:
    """
    Local embedding generator.
    Produces L2-normalized 384-dimensional dense vectors.
    Supports SentenceTransformers / Qwen3-Embedding, with deterministic local fallback.
    Reference: Phase 3 of technical plan.
    """

    DIMENSION = 384

    def __init__(self, model_name: str = None):
        import threading
        from api.core.config import settings
        self.model_name = model_name or settings.resolved_embedding_model
        self._st_model = None
        self._load_attempted = False
        self._load_lock = threading.Lock()

    def _get_st_model(self):
        with self._load_lock:
            if not self._load_attempted:
                self._load_attempted = True
                try:
                    import os
                    import torch
                    from api.core.config import settings
                    from sentence_transformers import SentenceTransformer

                    embedder_device = getattr(settings, "EMBEDDER_DEVICE", "cpu")
                    token = settings.HF_TOKEN or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
                    model_target = self.model_name or settings.resolved_embedding_model

                    # 1. Primary path: Load directly from local project folder (100% offline, zero network)
                    if os.path.exists(model_target):
                        logger.info(f"Loading SentenceTransformer from local project folder: {model_target} on {embedder_device}")
                        self._st_model = SentenceTransformer(model_target, device=embedder_device)
                        logger.info(f"Loaded SentenceTransformer successfully from project folder: {model_target} on {embedder_device}")
                    else:
                        # 2. Local cache fallback
                        try:
                            self._st_model = SentenceTransformer(model_target, local_files_only=True, device=embedder_device)
                            logger.info(f"Loaded SentenceTransformer from local cache (offline mode) on {embedder_device}: {model_target}")
                        except Exception as offline_err:
                            # 3. Fallback: Download once from Hugging Face Hub if not present
                            logger.info(f"Model not found in local cache ({offline_err}). Downloading once from Hugging Face Hub...")
                            self._st_model = SentenceTransformer(model_target, token=token, device=embedder_device)
                            logger.info(f"Downloaded and cached SentenceTransformer: {model_target} on {embedder_device}")
                except Exception as e:
                    logger.info(f"SentenceTransformers not loaded ({e}). Using local high-dimensional vectorizer.")
                    self._st_model = None
        return self._st_model

    def warmup(self):
        """Pre-warm model at server startup so first student query has zero latency."""
        m = self._get_st_model()
        if m:
            try:
                _ = m.encode(["academic query warmup"], normalize_embeddings=True)
                logger.info("Embedder model warmed up successfully.")
            except Exception as e:
                logger.warning(f"Embedder warmup note: {e}")

    def _hash_vectorize(self, text: str) -> List[float]:
        """
        Deterministic fast n-gram & word feature hashing vectorizer.
        Generates dense 384-dim normalized vector in cosine space.
        """
        vec = [0.0] * self.DIMENSION
        tokens = text.lower().split()
        if not tokens:
            return vec

        for i, token in enumerate(tokens):
            # Unigram hash
            h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.DIMENSION
            sign1 = 1.0 if (h1 % 2 == 0) else -1.0
            vec[h1] += sign1 * 1.5

            # Bigram hash
            if i > 0:
                bigram = f"{tokens[i-1]}_{token}"
                h2 = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16) % self.DIMENSION
                sign2 = 1.0 if (h2 % 2 == 0) else -1.0
                vec[h2] += sign2 * 2.0

        # L2 normalization for Cosine distance
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        from api.core.config import settings
        # 1. High-throughput remote embedding inference (e.g. TEI container on Ubuntu VM)
        if getattr(settings, "REMOTE_EMBEDDING_URL", None):
            try:
                import httpx
                base_url = settings.REMOTE_EMBEDDING_URL.rstrip("/")
                res = httpx.post(f"{base_url}/embed", json={"inputs": texts}, timeout=10.0)
                if res.status_code == 200:
                    return res.json()
            except Exception as remote_err:
                logger.debug(f"Remote embedding request to {settings.REMOTE_EMBEDDING_URL} failed ({remote_err}). Falling back to local embedder.")

        # 2. Local SentenceTransformer embedding
        model = self._get_st_model()
        if model:
            try:
                import torch
                # If model is on CUDA, acquire gpu_lock; if on CPU, run directly with zero lock contention!
                is_cuda = hasattr(model, "device") and getattr(model.device, "type", "") == "cuda"
                if is_cuda:
                    from api.core.gpu_lock import gpu_lock
                    with gpu_lock:
                        with torch.inference_mode():
                            embeddings = model.encode(texts, normalize_embeddings=True)
                        if torch.cuda.is_available():
                            torch.cuda.synchronize()
                else:
                    with torch.inference_mode():
                        embeddings = model.encode(texts, normalize_embeddings=True)
                return [e.tolist() for e in embeddings]
            except Exception as e:
                logger.warning(f"Embedding inference failed: {e}. Falling back to hash vectorizer.")

        return [self._hash_vectorize(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_texts(texts)

embedder = LocalEmbedder()
