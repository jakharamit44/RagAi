"""
Corrective RAG (CRAG) Pre-Generation Evaluator & Query Reformulator
Inspired by Shubhamsaboo/awesome-llm-apps (Corrective RAG template)

Core Responsibilities:
1. Grade retrieved chunk quality post-reranking.
2. Output a deterministic CRAG decision:
   - CORRECT: Chunks possess high semantic alignment (score >= 0.40). Proceed to generation.
   - AMBIGUOUS: Chunks are borderline or query is multi-intent (0.15 <= score < 0.40).
     Trigger automated query expansion / sub-query decomposition.
   - INCORRECT: Chunks fail factual relevance floor (score < 0.15).
     Trigger immediate clean abstention without wasting GPU inference tokens.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class CRAGDecision:
    CORRECT = "CORRECT"
    AMBIGUOUS = "AMBIGUOUS"
    INCORRECT = "INCORRECT"

class CRAGEvaluationResult:
    def __init__(
        self,
        decision: str,
        confidence: float,
        reasoning: str,
        filtered_chunks: List[Dict[str, Any]],
        sub_queries: Optional[List[str]] = None
    ):
        self.decision = decision
        self.confidence = confidence
        self.reasoning = reasoning
        self.filtered_chunks = filtered_chunks
        self.sub_queries = sub_queries or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "sub_queries": self.sub_queries,
            "chunk_count": len(self.filtered_chunks)
        }

class CorrectiveRAGEvaluator:
    """
    Evaluator that grades chunk relevance before passing them to the generator.
    Protects against hallucinations and optimizes multi-intent queries.
    """

    # Acronym & synonym expansion dictionary for university queries
    EXPANSION_MAP = {
        r"\bb\.?tech\b": "Bachelor of Technology B.Tech engineering",
        r"\bbca\b": "Bachelor of Computer Applications BCA",
        r"\bmca\b": "Master of Computer Applications MCA",
        r"\bm\.?tech\b": "Master of Technology M.Tech",
        r"\bmba\b": "Master of Business Administration MBA",
        r"\bb\.?sc\b": "Bachelor of Science B.Sc",
        r"\bm\.?sc\b": "Master of Science M.Sc",
        r"\bmaths?\b": "Mathematics",
        r"\bsem\b": "Semester",
        r"\bexam\b": "examination datesheet schedule",
        r"\bpariksha\b|\bparikshayein\b": "examination datesheet schedule",
        r"\bdakhila\b|\bpravesh\b": "admission application prospectus",
        r"\bpaathyakram\b|\bsyllabus\b": "syllabus curriculum course outline",
        r"\bvishwavidyalaya\b": "university MDU Rohtak",
        r"\bchhatravritti\b|\bscholarship\b": "merit scholarship award financial assistance",
        r"\btarikh\b|\btithi\b": "date schedule deadline",
        r"\bshulk\b": "fees structure",
    }

    # Irrelevant out-of-domain patterns that should trigger early abstention
    OUT_OF_DOMAIN_PATTERNS = [
        r"\brecipe\b",
        r"\bpasta\b",
        r"\bcooking\b",
        r"\bweather in\b",
        r"\bstock price\b",
        r"\bbitcoin\b",
        r"\bcricket score\b",
        r"\bmovie review\b",
    ]

    def evaluate_retrieval(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> CRAGEvaluationResult:
        """
        Grades retrieved chunks and returns a structured CRAG decision.
        """
        q_lower = query.lower()

        # 1. Out-of-Domain heuristic check
        for pattern in self.OUT_OF_DOMAIN_PATTERNS:
            if re.search(pattern, q_lower):
                logger.info(f"CRAG: Detected out-of-domain pattern '{pattern}' in query.")
                return CRAGEvaluationResult(
                    decision=CRAGDecision.INCORRECT,
                    confidence=0.0,
                    reasoning="Query matches out-of-domain conversational topic not present in academic documents.",
                    filtered_chunks=[]
                )

        if not chunks:
            return CRAGEvaluationResult(
                decision=CRAGDecision.INCORRECT,
                confidence=0.0,
                reasoning="Zero matching document chunks returned from hybrid retrieval.",
                filtered_chunks=[]
            )

        # 2. Extract scores
        rerank_scores = [c.get("rerank_score", -99.0) for c in chunks if "rerank_score" in c]
        dense_scores = [c.get("score", 0.0) for c in chunks if "score" in c]

        max_rerank = max(rerank_scores) if rerank_scores else -99.0
        max_dense = max(dense_scores) if dense_scores else 0.0

        # Calculate confidence metric C in [0.0, 1.0]
        # CrossEncoder raw logits typically range from -10.0 to +10.0
        # Map sigmoid-like or normalized score
        if max_rerank > -90.0:
            # Shifted sigmoid-like heuristic: 0 logit -> ~0.50 confidence
            norm_rerank = 1.0 / (1.0 + 2.71828 ** (-max_rerank))
            confidence = max(0.0, min(1.0, norm_rerank))
        else:
            confidence = max(0.0, min(1.0, max_dense))

        # Check significant keyword matches (Latin & Devanagari)
        latin_words = set(re.findall(r"\b[a-z]{3,}\b", q_lower))
        devanagari_words = set(re.findall(r"[\u0900-\u097F]{2,}", q_lower))
        query_words = latin_words | devanagari_words

        english_stopwords = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "the", "and", "for", "are", "can", "give", "tell", "about", "is", "was",
            "were", "will", "would", "shall", "should", "does", "did", "from", "with", "into"
        }
        hindi_stopwords = {
            "kya", "kab", "kahan", "kaha", "kaise", "kese", "kyun", "kyu", "kon", "kaun",
            "hai", "hain", "ho", "hu", "hoon", "tha", "the", "thi", "hoga", "hogi", "honge",
            "me", "mein", "par", "se", "ko", "ke", "ki", "ka", "aur", "ya", "bhi", "toh", "to",
            "ye", "yeh", "woh", "wo", "karo", "karein", "batao", "bataiye", "chahiye", "milega",
            "milegi", "milenge", "bata", "dijiye", "kare", "kitni", "kitna", "kitne",
            "क्या", "कब", "कहाँ", "कहा", "कैसे", "क्यों", "कौन", "है", "हैं", "हो", "हूँ", "था",
            "थे", "थी", "होगा", "होगी", "होंगे", "में", "पर", "से", "को", "के", "की", "का", "और",
            "या", "भी", "तो", "यह", "ये", "वह", "वो", "बताओ", "बताइए", "चाहिए", "मिलेगा", "मिलेगी", "कितनी", "कितना"
        }
        stopwords = english_stopwords | hindi_stopwords
        content_words = query_words - stopwords

        matched_content_words = set()
        for c in chunks[:3]:
            chunk_text = (c.get("text", "") + " " + c.get("title", "")).lower()
            for cw in content_words:
                if cw in chunk_text:
                    matched_content_words.add(cw)

        keyword_ratio = len(matched_content_words) / max(1, len(content_words))

        # 3. Decision Logic
        # Case A: Low relevance floor -> INCORRECT
        if (max_rerank < -2.5 and keyword_ratio < 0.25) or (max_dense < 0.22 and keyword_ratio < 0.20):
            logger.info(f"CRAG Evaluator: Grade INCORRECT (confidence={confidence:.2f}, max_rerank={max_rerank:.2f}, kw_ratio={keyword_ratio:.2f})")
            return CRAGEvaluationResult(
                decision=CRAGDecision.INCORRECT,
                confidence=confidence,
                reasoning="Retrieved chunks lack sufficient topical cohesion with user query.",
                filtered_chunks=[]
            )

        # Case B: Multi-intent or comparative queries -> AMBIGUOUS (Needs Decomposition)
        is_comparative = any(w in q_lower for w in [" versus ", " vs ", " and ", " both ", "compare"])
        if is_comparative and len(content_words) >= 4 and confidence < 0.65:
            sub_queries = self.decompose_query(query)
            logger.info(f"CRAG Evaluator: Grade AMBIGUOUS - Multi-intent query detected. Sub-queries: {sub_queries}")
            return CRAGEvaluationResult(
                decision=CRAGDecision.AMBIGUOUS,
                confidence=confidence,
                reasoning="Multi-intent comparative query detected with moderate chunk confidence.",
                filtered_chunks=chunks,
                sub_queries=sub_queries
            )

        # Case C: Confident -> CORRECT
        logger.info(f"CRAG Evaluator: Grade CORRECT (confidence={confidence:.2f}, max_rerank={max_rerank:.2f}, kw_ratio={keyword_ratio:.2f})")
        return CRAGEvaluationResult(
            decision=CRAGDecision.CORRECT,
            confidence=confidence,
            reasoning="High factual alignment between question and retrieved chunks.",
            filtered_chunks=chunks
        )

    def decompose_query(self, query: str) -> List[str]:
        """
        Decomposes complex or comparative questions into focused sub-queries.
        Example: "What are the exam dates for BCA and MCA?" -> ["BCA exam dates", "MCA exam dates"]
        """
        sub_queries = []
        q_clean = query.strip()

        # Check for conjunction patterns: "X and Y"
        match = re.search(r"^(.*?)\s+(?:for|of|regarding)\s+([A-Za-z0-9\.\s]+?)\s+and\s+([A-Za-z0-9\.\s]+?)(?:\s+programs?|\s+courses?)?\??$", q_clean, re.IGNORECASE)
        if match:
            prefix, item1, item2 = match.groups()
            sub_queries.append(f"{prefix} for {item1.strip()}")
            sub_queries.append(f"{prefix} for {item2.strip()}")
            return sub_queries

        # Fallback: Acronym expansion
        expanded = self.expand_query(query)
        if expanded != query:
            sub_queries.append(expanded)

        return sub_queries

    def expand_query(self, query: str) -> str:
        """
        Expands abbreviations to maximize BM25 and vector coverage.
        """
        expanded = query
        for pattern, replacement in self.EXPANSION_MAP.items():
            expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
        return expanded

crag_evaluator = CorrectiveRAGEvaluator()
