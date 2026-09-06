from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Query counters and histograms (Appendix B Table 21)
RAG_QUERY_TOTAL = Counter(
    "rag_query_total",
    "Total RAG queries processed by status, origin, and department",
    ["status", "served_by", "department"]
)

RAG_QUERY_DURATION = Histogram(
    "rag_query_duration_seconds",
    "End-to-end RAG query latency in seconds",
    ["served_by"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

RAG_RETRIEVAL_DURATION = Histogram(
    "rag_retrieval_duration_seconds",
    "Hybrid dense/sparse retrieval and reranking latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

# Semantic Cache metrics (Phase 7)
RAG_CACHE_HITS = Counter(
    "rag_cache_hits_total",
    "Total requests resolved directly by semantic cache"
)

RAG_CACHE_MISSES = Counter(
    "rag_cache_misses_total",
    "Total requests requiring full RAG retrieval pipeline"
)

# Corpus volume gauges (Phase 1, 3)
RAG_DOCUMENTS_TOTAL = Gauge(
    "rag_documents_total",
    "Total ingested academic documents in system"
)

RAG_CHUNKS_TOTAL = Gauge(
    "rag_chunks_total",
    "Total semantic chunks indexed in vector store"
)

# Rate limiting and security counters (Phase 11, 19)
RAG_RATE_LIMIT_EXCEEDED = Counter(
    "rag_rate_limit_exceeded_total",
    "Total requests rejected by sliding-window rate limiter"
)
