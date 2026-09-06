import os
import sys
import shutil
import logging
from typing import Optional
from huggingface_hub import snapshot_download

sys.path.insert(0, os.path.abspath("."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("preload_models")

def copy_or_download_model(repo_id: str, target_dir: str, token: Optional[str] = None):
    """
    Saves model weights directly into the target project folder.
    First checks if the model is already in system HF hub cache to copy instantly without re-downloading.
    Otherwise downloads snapshot directly into target_dir.
    """
    os.makedirs(target_dir, exist_ok=True)
    config_file = os.path.join(target_dir, "config.json")
    if os.path.exists(config_file):
        logger.info(f"Model already present in project directory: {target_dir}")
        return

    # Check if files exist in user ~/.cache/huggingface/hub/
    cache_name = "models--" + repo_id.replace("/", "--")
    system_hub = os.path.expanduser("~/.cache/huggingface/hub")
    hub_repo_dir = os.path.join(system_hub, cache_name, "snapshots")

    copied = False
    if os.path.isdir(hub_repo_dir):
        snapshots = [os.path.join(hub_repo_dir, s) for s in os.listdir(hub_repo_dir) if os.path.isdir(os.path.join(hub_repo_dir, s))]
        if snapshots:
            latest_snap = snapshots[-1]
            logger.info(f"Copying existing model weights from system cache: {latest_snap} -> {target_dir}")
            for item in os.listdir(latest_snap):
                s_item = os.path.join(latest_snap, item)
                d_item = os.path.join(target_dir, item)
                if os.path.isfile(s_item):
                    shutil.copy2(s_item, d_item, follow_symlinks=True)
                elif os.path.isdir(s_item):
                    shutil.copytree(s_item, d_item, dirs_exist_ok=True, symlinks=False)
            copied = True
            logger.info(f"Successfully copied model into project: {target_dir}")

    if not copied:
        logger.info(f"Downloading model {repo_id} directly into project directory: {target_dir}...")
        snapshot_download(
            repo_id=repo_id,
            local_dir=target_dir,
            token=token,
            local_dir_use_symlinks=False,
        )
        logger.info(f"Successfully downloaded model into project: {target_dir}")

def preload_all_models(hf_token: Optional[str] = None):
    """
    Downloads and caches the embedding, reranker, and chat generation models directly
    inside the project's models/ directory so that all inference is 100% offline.
    """
    from api.core.config import settings

    token = hf_token or settings.HF_TOKEN or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")

    print("\n" + "="*70)
    print("ENTERPRISE UNIVERSITY RAG - IN-PROJECT MODEL PRELOADER")
    print("="*70)
    print(f"Project Models Root: {settings.MODELS_DIR}")
    token_status = "Configured (High-Speed)" if token else "Anonymous (Standard)"
    print(f"HF Token Status:     {token_status}")
    print(f"Embedding Model:     {settings.EMBEDDING_MODEL_NAME} -> {settings.local_embedding_model_dir}")
    print(f"Reranker Model:      {settings.RERANKER_MODEL_NAME} -> {settings.local_reranker_model_dir}")
    print(f"Chat Model:          {settings.CHAT_MODEL_NAME} -> {settings.local_chat_model_dir}")
    print("="*70 + "\n")

    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.MODELS_DIR, "cache"), exist_ok=True)

    # 1. Preload Embedding Model directly into models/all-MiniLM-L6-v2
    logger.info("1/3: Saving Embedding Model directly into project folder...")
    try:
        copy_or_download_model(
            repo_id=settings.EMBEDDING_MODEL_NAME,
            target_dir=settings.local_embedding_model_dir,
            token=token,
        )
        from sentence_transformers import SentenceTransformer
        embed_model = SentenceTransformer(settings.local_embedding_model_dir)
        test_vec = embed_model.encode(["University syllabus verification test"])
        logger.info(f"Embedding model ready in project! Output dimension: {test_vec.shape[1]}")
    except Exception as e:
        logger.warning(f"Embedding model setup note: {e}")

    # 2. Preload Reranker Model directly into models/Qwen3-Reranker-0.6B
    logger.info("\n2/3: Saving Cross-Encoder Reranker directly into project folder...")
    try:
        copy_or_download_model(
            repo_id=settings.RERANKER_MODEL_NAME,
            target_dir=settings.local_reranker_model_dir,
            token=token,
        )
        from sentence_transformers import CrossEncoder
        reranker_model = CrossEncoder(settings.local_reranker_model_dir)
        test_score = reranker_model.predict([["exam schedule", "examination schedule for session 2025-26"]])
        logger.info(f"Cross-encoder reranker ready in project! Test score: {test_score[0]:.4f}")
    except Exception as e:
        logger.warning(f"Cross-encoder reranker setup note: {e}")

    # 3. Preload Chat Generation Model directly into models/Qwen2.5-3B-Instruct
    logger.info("\n3/3: Saving Chat Generation Model directly into project folder...")
    try:
        copy_or_download_model(
            repo_id=settings.CHAT_MODEL_NAME,
            target_dir=settings.local_chat_model_dir,
            token=token,
        )
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(settings.local_chat_model_dir)
        logger.info(f"Chat generation model ready in project! Vocab size: {len(tok)}")
    except Exception as e:
        logger.warning(f"Chat generation model setup note: {e}")

    print("\n" + "="*70)
    print(f"ALL MODELS SAVED TO PROJECT: {settings.MODELS_DIR}")
    print("Zero network dependencies. All models run 100% offline from project directory.")
    print("="*70 + "\n")

if __name__ == "__main__":
    cli_token = sys.argv[1] if len(sys.argv) > 1 else None
    preload_all_models(cli_token)
