import os
import re
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:[\.\-][a-zA-Z0-9]+)*")
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
        tokens = []
        for w in TOKEN_RE.findall(text.lower()):
            if len(w) > 1:
                tokens.append(w)
            norm = w.replace(".", "").replace("-", "")
            if norm != w and len(norm) > 1:
                tokens.append(norm)
        return tokens

    MAX_BM25_CHUNKS = 40000

    def reload_from_db(self):
        """Forces complete reload of BM25 corpus from database."""
        with self._load_lock:
            self.bm25 = None
            self.corpus = []
            self.tokenized_corpus = []
            self._valid_doc_ids = set()
        self.ensure_loaded()

    def ensure_loaded(self):
        """Auto-loads bounded index from database (capped at MAX_BM25_CHUNKS to prevent RAM exhaustion)."""
        if self.bm25 is not None and self.corpus:
            return

        with self._load_lock:
            if self.bm25 is not None and self.corpus:
                return

            from api.core.config import settings
            rows = []
            if "postgresql" in settings.DATABASE_URL:
                try:
                    import psycopg2
                    pg_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
                    conn = psycopg2.connect(pg_url)
                    cur = conn.cursor()
                    cur.execute(f"""
                        SELECT c.id, c.document_id, c.page_number,
                               SUBSTRING(COALESCE(c.section, ''), 1, 150),
                               SUBSTRING(COALESCE(c.text, ''), 1, 350),
                               SUBSTRING(COALESCE(d.title, ''), 1, 200),
                               COALESCE(d.department, ''),
                               COALESCE(d.semester, ''),
                               COALESCE(d.course, '')
                        FROM chunks c
                        JOIN documents d ON c.document_id = d.id
                        ORDER BY c.id DESC
                        LIMIT {self.MAX_BM25_CHUNKS}
                    """)
                    rows = cur.fetchall()
                    conn.close()
                except Exception as e:
                    logger.warning(f"Could not load BM25 corpus from PostgreSQL: {e}")
            else:
                db_path = os.path.abspath("university_rag.db")
                if os.path.exists(db_path):
                    try:
                        conn = sqlite3.connect(db_path, timeout=10.0)
                        conn.execute("PRAGMA journal_mode=WAL;")
                        conn.execute("PRAGMA synchronous=NORMAL;")
                        cur = conn.cursor()
                        cur.execute(f"""
                            SELECT c.id, c.document_id, c.page_number,
                                   SUBSTR(COALESCE(c.section, ''), 1, 150),
                                   SUBSTR(COALESCE(c.text, ''), 1, 350),
                                   SUBSTR(COALESCE(d.title, ''), 1, 200),
                                   COALESCE(d.department, ''),
                                   COALESCE(d.semester, ''),
                                   COALESCE(d.course, '')
                            FROM chunks c
                            JOIN documents d ON c.document_id = d.id
                            ORDER BY c.id DESC
                            LIMIT {self.MAX_BM25_CHUNKS}
                        """)
                        rows = cur.fetchall()
                        conn.close()
                    except Exception as e:
                        logger.warning(f"Could not load BM25 corpus from SQLite: {e}")

            if not rows:
                return

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

    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        """Append new chunks safely without freezing server on synchronous re-indexing."""
        if not new_chunks:
            return
        with self._load_lock:
            for c in new_chunks:
                item = dict(c)
                raw_text = item.get("text") or ""
                if len(raw_text) > 350:
                    item["text"] = raw_text[:350]
                self.corpus.append(item)
                if item.get("document_id"):
                    self._valid_doc_ids.add(item.get("document_id"))
            if len(self.corpus) > self.MAX_BM25_CHUNKS:
                self.corpus = self.corpus[-self.MAX_BM25_CHUNKS:]
                self._valid_doc_ids = {d.get("document_id") for d in self.corpus if d.get("document_id")}

    def build_index(self, chunks: List[Dict[str, Any]]):
        """Build BM25 index from list of chunk payloads with safe memory footprint."""
        with self._load_lock:
            if len(chunks) > self.MAX_BM25_CHUNKS:
                chunks = chunks[-self.MAX_BM25_CHUNKS:]

            lightweight = []
            for c in chunks:
                item = dict(c)
                raw_text = item.get("text") or ""
                if len(raw_text) > 350:
                    item["text"] = raw_text[:350]
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

        BM25_STOP_WORDS = {
            "who", "is", "are", "was", "were", "what", "when", "where", "which", "whom", "whose", "why", "how",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "from",
            "of", "about", "into", "through", "during", "before", "after", "above", "below", "up", "down",
            "tell", "me", "give", "details", "information", "info", "please", "can", "you", "show", "list",
            "find", "get", "do", "does", "did", "have", "has", "had", "name", "names"
        }

        tokens = self.tokenize(query)
        if not tokens:
            return []

        content_tokens = [t for t in tokens if t not in BM25_STOP_WORDS and len(t) > 2]
        base_tokens = content_tokens if content_tokens else tokens

        expanded_tokens = list(base_tokens)
        for t in base_tokens:
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

        # Check if user query is specifically seeking student marks/results/gazettes
        q_lower = query.lower()
        is_seeking_results = any(w in q_lower for w in ["gazette", "result", "marks", "roll no", "roll number", "reappear", "re-appear", "scorecard", "passed", "failed"])

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

            # Multi-term co-occurrence bonus: If document contains ALL query content terms (e.g. 'vikas' AND 'nagil')
            if len(content_tokens) >= 2:
                all_match = all((t in doc_text or t in doc_title) for t in content_tokens)
                if all_match:
                    adjusted_score += 35.0

            # Gazette result de-biasing: penalize raw student score lists unless user explicitly wants results
            is_gazette_doc = ("gazette" in doc_title or "re-appear" in doc_title or "annual exam" in doc_title)
            if is_gazette_doc and not is_seeking_results:
                adjusted_score -= 25.0

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
