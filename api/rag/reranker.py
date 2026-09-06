import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class LocalReranker:
    """
    Local cross-encoder reranker.
    Reorders top candidates for precision.
    Reference: Phase 4 & Table 9 of technical plan.
    """

    def __init__(self, model_name: str = None):
        import threading
        from api.core.config import settings
        self.model_name = model_name or settings.resolved_reranker_model
        self._st_reranker = None
        self._load_attempted = False
        self._load_lock = threading.Lock()

    def _get_reranker(self):
        with self._load_lock:
            if not self._load_attempted:
                self._load_attempted = True
                try:
                    import os
                    import torch
                    from api.core.config import settings
                    from sentence_transformers import CrossEncoder

                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    token = settings.HF_TOKEN or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
                    model_target = self.model_name or settings.resolved_reranker_model

                    # 1. Primary path: Load directly from local project folder (100% offline, zero network)
                    if os.path.exists(model_target):
                        logger.info(f"Loading CrossEncoder from local project folder: {model_target} on {device}")
                        self._st_reranker = CrossEncoder(model_target, max_length=256, device=device)
                        logger.info(f"Loaded CrossEncoder successfully from project folder: {model_target}")
                    else:
                        # 2. Local cache fallback
                        try:
                            self._st_reranker = CrossEncoder(model_target, max_length=256, local_files_only=True, device=device)
                            logger.info(f"Loaded CrossEncoder from local cache (offline mode) on {device}: {model_target}")
                        except Exception as offline_err:
                            # 3. Fallback: Download once from Hugging Face Hub if not present
                            logger.info(f"Reranker not found in local cache ({offline_err}). Downloading once from Hugging Face Hub...")
                            self._st_reranker = CrossEncoder(model_target, max_length=256, token=token, device=device)
                            logger.info(f"Downloaded and cached CrossEncoder: {model_target}")
                except Exception as e:
                    logger.info(f"CrossEncoder not loaded ({e}). Using lexical-density reranker.")
                    self._st_reranker = None
        return self._st_reranker

    def warmup(self):
        """Pre-warm reranker at server startup so first student query has zero latency."""
        m = self._get_reranker()
        if m:
            try:
                from api.core.gpu_lock import gpu_lock
                with gpu_lock:
                    _ = m.predict([["query warmup", "passage warmup"]])
                logger.info("Reranker model warmed up successfully.")
            except Exception as e:
                logger.warning(f"Reranker warmup note: {e}")

    def rerank(self, query: str, candidate_chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        if not candidate_chunks:
            return []

        from .query_utils import (
            extract_ordinal,
            extract_ordinals,
            extract_entity,
            get_conflicting_ordinals,
            get_conflicting_entities,
            ORDINAL_EXPANSIONS,
            CANONICAL_ORDINAL_MAP,
        )

        q_ords = extract_ordinals(query)
        q_ent = extract_entity(query)
        ord_conflicts = get_conflicting_ordinals(q_ords) if q_ords else set()
        ent_conflicts = get_conflicting_entities(q_ent) if q_ent else set()

        target_exps = set()
        if q_ords:
            for k, v in ORDINAL_EXPANSIONS.items():
                if CANONICAL_ORDINAL_MAP.get(k) in q_ords:
                    target_exps.update(v)

        target_regexes = [re.compile(rf"\b{re.escape(exp)}\b") for exp in target_exps]
        conflict_regexes = [re.compile(rf"\b{re.escape(co)}\b") for co in ord_conflicts]

        model = self._get_reranker()
        if model:
            try:
                # GPU-accelerated evaluation across top candidates in parallel batches
                eval_candidates = candidate_chunks[:15]
                pairs = [
                    [query, f"{c.get('title', '')} (Page {c.get('page_number', 1)}): {c.get('text', '')[:650]}"]
                    for c in eval_candidates
                ]
                import torch
                from api.core.gpu_lock import gpu_lock
                with gpu_lock:
                    with torch.inference_mode():
                        if torch.cuda.is_available():
                            with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                                scores = model.predict(pairs, batch_size=16)
                            torch.cuda.synchronize()
                        else:
                            scores = model.predict(pairs, batch_size=16)
                for i, score in enumerate(scores):
                    c = eval_candidates[i]
                    doc_title = (c.get("title") or "").lower()
                    doc_text = (c.get("text") or "").lower()
                    adj_score = float(score)

                    # Ordinal coherence bonus/penalty
                    if q_ords:
                        title_matches = any(rgx.search(doc_title) for rgx in target_regexes)
                        title_conflict = any(rgx.search(doc_title) for rgx in conflict_regexes)
                        text_matches = any(rgx.search(doc_text[:400]) for rgx in target_regexes)
                        if title_matches:
                            adj_score += 4.0
                        elif title_conflict:
                            adj_score -= 10.0
                        elif text_matches:
                            adj_score += 1.5

                    # Entity coherence bonus/penalty
                    if q_ent:
                        title_ent_matches = q_ent in doc_title
                        title_ent_conflict = any(ce in doc_title for ce in ent_conflicts)
                        if title_ent_matches:
                            adj_score += 3.0
                        elif title_ent_conflict:
                            adj_score -= 10.0

                    c["rerank_score"] = adj_score

                eval_candidates.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
                return eval_candidates[:top_k]
            except Exception as e:
                logger.warning(f"CrossEncoder predict failed: {e}")

        # High-precision lexical & coverage alignment reranker fallback
        query_words = set(w for w in re.split(r"\W+", query.lower()) if len(w) > 2)
        for c in candidate_chunks:
            doc_title = (c.get("title") or "").lower()
            text = c.get("text", "").lower()
            overlap_count = sum(1 for qw in query_words if qw in text or qw in doc_title)
            base_score = c.get("rrf_score", c.get("score", 0.0))
            bonus = 0.0
            if q_ord:
                if any(rgx.search(doc_title) for rgx in target_regexes):
                    bonus += 5.0
                elif any(rgx.search(doc_title) for rgx in conflict_regexes):
                    bonus -= 10.0
            if q_ent:
                if q_ent in doc_title:
                    bonus += 3.0
                elif any(ce in doc_title for ce in ent_conflicts):
                    bonus -= 10.0

            c["rerank_score"] = base_score + (overlap_count * 0.2) + bonus

        candidate_chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return candidate_chunks[:top_k]

reranker = LocalReranker()
