import re
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from api.core.config import settings
from .embedder import embedder
from .qdrant_store import qdrant_store
from .bm25_index import bm25_index
from .reranker import reranker

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    Hybrid retriever combining dense vector search (Qdrant) and sparse BM25
    with Reciprocal Rank Fusion (RRF), relevance floors, and metadata scope filtering.
    Optimized for non-blocking concurrent execution across worker threads.
    Reference: Phase 4 & Table 9 of technical plan.
    """

    RRF_K = 60
    MIN_DENSE_SCORE = 0.20  # Minimum cosine similarity threshold

    def __init__(self):
        self.top_k_retrieve = settings.TOP_K_RETRIEVE
        self.top_k_final = settings.TOP_K_FINAL

    async def retrieve(
        self,
        query: str,
        department: Optional[str] = None,
        course: Optional[str] = None,
        semester: Optional[str] = None,
        depth: int = 0,
        query_vector: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute parallel hybrid search with relevance thresholds:
        1. Dense ANN search via Qdrant (parallel worker thread)
        2. Sparse search via BM25 (parallel worker thread)
        3. Reciprocal Rank Fusion (RRF)
        4. Cross-Encoder reranking (worker thread)
        """
        from .query_utils import normalize_query
        query = normalize_query(query)

        async def _run_dense() -> List[Dict[str, Any]]:
            try:
                vec = query_vector if (query_vector is not None and depth == 0) else await asyncio.to_thread(embedder.embed_query, query)
                raw_dense = await asyncio.to_thread(
                    qdrant_store.search_dense,
                    query_vector=vec,
                    limit=self.top_k_retrieve,
                    department=department,
                    course=course,
                    semester=semester,
                )
                filtered_dense = []
                is_seeking_results = any(w in query.lower() for w in ["result", "marks", "grade", "roll", "regn", "gazette", "re-appear", "pass", "fail", "score"])
                gazette_count = 0
                for r in raw_dense:
                    doc_id = r.get("document_id")
                    title = (r.get("title") or "").lower()
                    if "enterprise_rag" in title or "test_failed" in title:
                        continue
                    is_gazette = "gazette" in title or "result" in title or "roll no" in (r.get("text") or "").lower()[:150]
                    if not is_seeking_results and is_gazette:
                        gazette_count += 1
                        if gazette_count > 2:
                            continue
                    if r.get("score", 0.0) >= self.MIN_DENSE_SCORE:
                        filtered_dense.append(r)
                return filtered_dense
            except Exception as e:
                logger.warning(f"Vector store search unavailable ({e}). Degrading to sparse BM25 fallback.")
                return []

        async def _run_sparse() -> List[Dict[str, Any]]:
            try:
                return await asyncio.to_thread(
                    bm25_index.search_sparse,
                    query=query,
                    limit=self.top_k_retrieve,
                    department=department,
                    course=course,
                    semester=semester,
                )
            except Exception as e:
                logger.warning(f"BM25 search error ({e}): {e}")
                return []

        # 1 & 2: Execute Dense and Sparse retrieval in parallel
        dense_results, sparse_results = await asyncio.gather(_run_dense(), _run_sparse())

        # If both sparse and dense find nothing relevant, abstain early
        if not dense_results and not sparse_results:
            return []

        # 3. Reciprocal Rank Fusion
        rrf_scores: Dict[str, float] = {}
        candidate_map: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_results):
            cid = str(item.get("chunk_id", item.get("vector_id")))
            candidate_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.RRF_K + rank + 1))

        for rank, item in enumerate(sparse_results):
            cid = str(item.get("chunk_id", item.get("id")))
            if cid not in candidate_map:
                candidate_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.RRF_K + rank + 1))

        # Sort combined candidates by RRF score
        fused_candidates = []
        for cid, score in rrf_scores.items():
            cand = dict(candidate_map[cid])
            cand["rrf_score"] = score
            fused_candidates.append(cand)

        fused_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        # Evaluate top 50 candidates across batched GPU cross-encoder
        top_candidates = fused_candidates[:50]

        # 4. Cross-encoder reranking (executed off the main event loop)
        try:
            final_ranked = await asyncio.to_thread(
                reranker.rerank,
                query=query,
                candidate_chunks=top_candidates,
                top_k=self.top_k_retrieve
            )
        except Exception as e:
            logger.warning(f"Reranking encountered error ({e}), falling back to top fused RRF candidates.")
            final_ranked = top_candidates[:self.top_k_retrieve]

        # Filter out candidates with low relevance
        filtered_final = []
        for c in final_ranked:
            r_score = c.get("rerank_score")
            if r_score is not None:
                if r_score >= -2.0:
                    filtered_final.append(c)
            else:
                if c.get("score", 0.0) >= 0.20 or c.get("rrf_score", 0.0) > 0.01:
                    filtered_final.append(c)

        candidates = filtered_final if filtered_final else final_ranked[:self.top_k_final]

        # 5. Strict Document Cohesion & Conflict Pruning
        from .query_utils import (
            extract_ordinal,
            extract_ordinals,
            extract_entity,
            get_conflicting_ordinals,
            get_conflicting_entities,
        )

        q_ords = extract_ordinals(query)
        q_ent = extract_entity(query)
        ord_conflicts = get_conflicting_ordinals(q_ords) if q_ords else set()
        ent_conflicts = get_conflicting_entities(q_ent) if q_ent else set()

        cohesive_candidates = []
        for c in candidates:
            title = (c.get("title") or "").lower()
            # If query specified ordinals, purge conflicting ordinals only
            if q_ords and any(re.search(rf"\b{re.escape(co)}\b", title) for co in ord_conflicts):
                continue
            # If query specified an entity, purge conflicting entities (e.g. Court when asking Academic Council)
            if q_ent and any(ce in title for ce in ent_conflicts):
                continue
            cohesive_candidates.append(c)

        if cohesive_candidates:
            candidates = cohesive_candidates

        # 6. Page 1 & Meeting Date/Venue Context Prioritization
        if candidates:
            top_doc_id = candidates[0].get("document_id")
            # If query asks when/where/held/date, ensure Page 1 of the top document is placed at position 0
            is_date_or_convening_query = any(w in query.lower() for w in ["when", "held", "date", "time", "where", "agenda", "first", "1st"])
            p1_chunk = None
            p1_idx = None
            for idx, c in enumerate(candidates):
                if c.get("document_id") == top_doc_id and c.get("page_number") == 1:
                    p1_chunk = c
                    p1_idx = idx
                    break

            if p1_chunk is not None:
                if is_date_or_convening_query and p1_idx > 0:
                    candidates.pop(p1_idx)
                    candidates.insert(0, p1_chunk)
            elif top_doc_id:
                # Page 1 not in candidate list, fetch and prepend it
                for doc in bm25_index.corpus:
                    if doc.get("document_id") == top_doc_id and doc.get("page_number") == 1:
                        p1_copy = dict(doc)
                        p1_copy["score"] = candidates[0].get("score", 0.9)
                        p1_copy["rerank_score"] = candidates[0].get("rerank_score", 5.0) + 1.0
                        candidates.insert(0, p1_copy)
                        break

        # If top document matches query, restrict candidate chunks to top document to prevent citation leakage
        # ONLY if query is not comparative or targeting multiple subjects/documents
        is_comparative = any(w in query.lower() for w in ["versus", "vs", "compare", "comparing", "difference", "between", "both", "apart", "and"]) or len(q_ords) > 1
        if candidates and (q_ords or q_ent) and not is_comparative:
            winning_doc_id = candidates[0].get("document_id")
            same_doc_candidates = [c for c in candidates if c.get("document_id") == winning_doc_id]
            if same_doc_candidates:
                candidates = same_doc_candidates

        # 7. Recency Prioritization for "latest / recent / current / upcoming / new" queries
        is_recency_query = any(w in query.lower() for w in ["latest", "recent", "current", "upcoming", "new", "update", "updated", "extension", "extended", "today"])
        if is_recency_query and candidates and not ((q_ords or q_ent) and not is_comparative):
            def extract_year(c):
                text = (c.get("title", "") + " " + c.get("text", "")[:300])
                years = [int(y) for y in re.findall(r"\b(20[1-3][0-9]|19[7-9][0-9])\b", text)]
                return max(years) if years else 0

            candidates.sort(key=lambda c: (extract_year(c), c.get("rerank_score", 0.0)), reverse=True)

        final_chunks = candidates[:self.top_k_final]

        # 8. Corrective RAG (CRAG) Evaluation Gate
        from .crag import crag_evaluator, CRAGDecision
        eval_result = crag_evaluator.evaluate_retrieval(query, final_chunks)

        # If CRAG grades chunks as INCORRECT, abstain early by suppressing irrelevant chunks
        if eval_result.decision == CRAGDecision.INCORRECT:
            logger.info(f"CRAG: Abstention gate triggered for query '{query[:40]}...'. Zero irrelevant chunks returned.")
            return []

        # If CRAG grades AMBIGUOUS and depth == 0, perform sub-query decomposition
        if eval_result.decision == CRAGDecision.AMBIGUOUS and eval_result.sub_queries and depth == 0:
            logger.info(f"CRAG: Expanding ambiguous query via sub-queries: {eval_result.sub_queries}")
            sub_chunks = []
            sub_queries = eval_result.sub_queries[:2]
            if sub_queries:
                sub_results = await asyncio.gather(
                    *[self.retrieve(sq, department, course, semester, depth=1) for sq in sub_queries],
                    return_exceptions=True
                )
                for res in sub_results:
                    if isinstance(res, list):
                        sub_chunks.extend(res)
                    elif isinstance(res, Exception):
                        logger.warning(f"CRAG sub-query retrieval error: {res}")

            if sub_chunks:
                # Deduplicate by chunk_id
                seen_cids = {c.get("chunk_id") for c in final_chunks}
                for sc in sub_chunks:
                    cid = sc.get("chunk_id")
                    if cid and cid not in seen_cids:
                        final_chunks.append(sc)
                        seen_cids.add(cid)

        return final_chunks[:self.top_k_final]

    async def retrieve_with_crag(
        self,
        query: str,
        department: Optional[str] = None,
        course: Optional[str] = None,
        semester: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
    ) -> Tuple[List[Dict[str, Any]], Any]:
        """
        Executes hybrid retrieval and returns both the final chunks and the CRAG diagnostic object.
        """
        from .crag import crag_evaluator
        chunks = await self.retrieve(query, department, course, semester, query_vector=query_vector)
        eval_result = crag_evaluator.evaluate_retrieval(query, chunks)
        return chunks, eval_result

retriever = HybridRetriever()

