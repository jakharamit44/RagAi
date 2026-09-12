import os
import re
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

WORD_RE = re.compile(r"\W+")

class BM25Index:
    """
    Sparse BM25 Okapi index for exact keyword search across university documents.
    Reference: Phase 4 & Table 9 of technical plan.
    """

    def __init__(self):
        import threading
        self.corpus: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self._valid_doc_ids: set = set()
        self._load_lock = threading.RLock()

    @property
    def valid_doc_ids(self) -> set:
        if not self._valid_doc_ids and self.corpus:
            self._valid_doc_ids = {d.get("document_id") for d in self.corpus if d.get("document_id")}
        return self._valid_doc_ids

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return [w for w in WORD_RE.split(text.lower()) if len(w) > 1]

    def reload_from_db(self):
        """Forces complete reload of BM25 corpus from SQLite."""
        with self._load_lock:
            self.bm25 = None
            self.corpus = []
            self.tokenized_corpus = []
            self._valid_doc_ids = set()
        self.ensure_loaded()

    def ensure_loaded(self):
        """Auto-loads index from sqlite if not yet initialized in memory (zero disk I/O when already loaded)."""
        if self.bm25 is not None and self.corpus:
            return

        with self._load_lock:
            if self.bm25 is not None and self.corpus:
                return

            db_path = os.path.abspath("university_rag.db")
            if not os.path.exists(db_path):
                return

            try:
                conn = sqlite3.connect(db_path, timeout=10.0)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                cur = conn.cursor()
                cur.execute("""
                    SELECT c.id, c.document_id, c.page_number,
                           SUBSTR(COALESCE(c.section, ''), 1, 300),
                           SUBSTR(COALESCE(c.text, ''), 1, 1500),
                           SUBSTR(COALESCE(d.title, ''), 1, 300),
                           COALESCE(d.department, ''),
                           COALESCE(d.semester, ''),
                           COALESCE(d.course, '')
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                """)
                rows = cur.fetchall()
                conn.close()

                chunks = []
                for r in rows:
                    chunks.append({
                        "chunk_id": str(r[0]),
                        "document_id": str(r[1]),
                        "page_number": r[2],
                        "section": r[3] or "",
                        "text": r[4] or "",
                        "title": r[5] or "",
                        "department": r[6] or "",
                        "semester": r[7] or "",
                        "course": r[8] or "",
                    })
                del rows
                if chunks:
                    self.build_index(chunks)
            except Exception as e:
                logger.warning(f"Could not auto-load BM25 corpus from SQLite: {e}")

    def build_index(self, chunks: List[Dict[str, Any]]):
        """Build BM25 index from list of chunk payloads, including title & section for rich lexical matching."""
        with self._load_lock:
            # Create lightweight memory items (cap text to 1500 chars to prevent heap ballooning on massive gazettes)
            lightweight = []
            for c in chunks:
                item = dict(c)
                raw_text = item.get("text") or ""
                if len(raw_text) > 1500:
                    item["text"] = raw_text[:1500]
                lightweight.append(item)

            self.corpus = lightweight
            self._valid_doc_ids = {d.get("document_id") for d in lightweight if d.get("document_id")}
            tokenized = [
                self.tokenize(f"{c.get('title', '')} {c.get('section', '')} {c.get('text', '')}")
                for c in lightweight
            ]
            if tokenized:
                self.bm25 = BM25Okapi(tokenized)
                del tokenized
                self._last_chunk_count = len(self.corpus)
                logger.info(f"Built BM25 index over {len(self.corpus)} chunks.")
            else:
                self.bm25 = None
                self._last_chunk_count = 0
            import gc
            gc.collect()

    def search_sparse(
        self,
        query: str,
        limit: int = 20,
        department: Optional[str] = None,
        course: Optional[str] = None,
        semester: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self.ensure_loaded()

        if not self.bm25 or not self.corpus:
            return []

        from .query_utils import (
            extract_ordinal,
            extract_ordinals,
            extract_entity,
            get_conflicting_ordinals,
            get_conflicting_entities,
            ORDINAL_EXPANSIONS,
        )

        tokens = self.tokenize(query)
        if not tokens:
            return []

        expanded_tokens = list(tokens)
        for t in tokens:
            if t in ORDINAL_EXPANSIONS:
                for exp in ORDINAL_EXPANSIONS[t]:
                    if exp not in expanded_tokens:
                        expanded_tokens.append(exp)

        scores = self.bm25.get_scores(expanded_tokens)
        results = []

        q_ords = extract_ordinals(query)
        q_ent = extract_entity(query)
        ord_conflicts = get_conflicting_ordinals(q_ords) if q_ords else set()
        ent_conflicts = get_conflicting_entities(q_ent) if q_ent else set()

        # Extract specific alphanumeric identifiers (e.g., CS401, 23GEOD102DS02, 22DPIR12C2)
        q_codes = [
            re.sub(r"[\s\-_]", "", w).lower()
            for w in re.findall(r"\b[A-Za-z0-9\-_]{4,20}\b", query)
            if any(c.isdigit() for c in w) and any(c.isalpha() for c in w)
        ]

        target_exps = set()
        if q_ords:
            from .query_utils import CANONICAL_ORDINAL_MAP
            for k, v in ORDINAL_EXPANSIONS.items():
                if CANONICAL_ORDINAL_MAP.get(k) in q_ords:
                    target_exps.update(v)

        target_regexes = [re.compile(rf"\b{re.escape(exp)}\b") for exp in target_exps] if target_exps else []
        ord_conflict_regexes = [re.compile(rf"\b{re.escape(co)}\b") for co in ord_conflicts] if ord_conflicts else []

        for idx, score in enumerate(scores):
            doc = self.corpus[idx]

            # Metadata scope filter
            if department and doc.get("department") != department:
                continue
            if course and doc.get("course") != course:
                continue
            if semester and doc.get("semester") != semester:
                continue

            doc_title = (doc.get("title") or "").lower()
            doc_text = (doc.get("text") or "").lower()
            adjusted_score = float(score)

            # Course/Paper code boost (highest priority for academic advising and specific courses)
            if q_codes:
                clean_doc_target = re.sub(r"[\s\-_]", "", f"{doc_title} {doc.get('course', '')} {doc_text[:1200]}").lower()
                for qc in q_codes:
                    if qc in clean_doc_target:
                        adjusted_score += 15.0

            # Ordinal alignment: Title has highest authority
            if q_ords:
                title_matches_ord = any(rx.search(doc_title) for rx in target_regexes)
                title_has_ord_conflict = any(rx.search(doc_title) for rx in ord_conflict_regexes)
                text_matches_ord = any(rx.search(doc_text[:400]) for rx in target_regexes)

                if title_matches_ord:
                    adjusted_score += 10.0
                elif title_has_ord_conflict:
                    adjusted_score -= 20.0
                elif text_matches_ord:
                    adjusted_score += 3.0

            # Entity alignment: Title has highest authority
            if q_ent:
                title_matches_ent = q_ent in doc_title
                title_has_ent_conflict = any(ce in doc_title for ce in ent_conflicts)
                text_matches_ent = q_ent in doc_text[:400]

                if title_matches_ent:
                    adjusted_score += 8.0
                elif title_has_ent_conflict:
                    adjusted_score -= 20.0
                elif text_matches_ent:
                    adjusted_score += 2.0

            if adjusted_score <= 0.0:
                continue

            item = dict(doc)
            item["score"] = adjusted_score
            results.append(item)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

bm25_index = BM25Index()
