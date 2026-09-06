import logging
from typing import List, Dict, Any
from .celery_app import celery_app
from api.rag.embedder import embedder

logger = logging.getLogger(__name__)

@celery_app.task(
    name="tasks.embed_chunks", 
    bind=True, 
    acks_late=True, 
    max_retries=3, 
    autoretry_for=(Exception,), 
    retry_backoff=True
)
def embed_chunks_task(self, chunks: List[Dict[str, Any]]):
    """
    Asynchronously batch-embed document chunks using local model on worker GPU.
    Reference: Phase 3 & 8 of technical plan.
    """
    logger.info(f"Generating embeddings for {len(chunks)} chunks.")
    texts = [c["text"] for c in chunks]
    vectors = embedder.embed_texts(texts)
    for i, vec in enumerate(vectors):
        chunks[i]["vector"] = vec
    return chunks
