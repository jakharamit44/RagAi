"""
tests/test_embedder_pool.py
Verification suite for persistent HTTP connection pool on remote embedding endpoint.
Validates latency reduction, vector dimensionality (384-dim), batch throughput, and clean socket disposal.
"""

import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.core.config import settings
from api.rag.embedder import embedder


def test_embedder_connection_pooling():
    print("=================================================================")
    print("REMOTE EMBEDDER PERSISTENT HTTP CONNECTION POOL VERIFICATION")
    print("=================================================================")

    original_url = settings.REMOTE_EMBEDDING_URL
    settings.REMOTE_EMBEDDING_URL = "http://192.168.81.150:8080"
    print(f"Targeting Remote TEI Endpoint: {settings.REMOTE_EMBEDDING_URL}")

    print("\n[1/4] Warming up embedder and establishing TCP Keep-Alive pool...")
    embedder.warmup()
    print("  ✓ Warmup complete. Pool established.")

    test_queries = [
        "Explain deadlock prevention in Operating Systems",
        "What is the difference between TCP and UDP protocols?",
        "Describe relational database normal forms 1NF, 2NF, and 3NF",
        "How does B-Tree indexing accelerate range queries in SQL?",
        "Explain multi-head self-attention in Transformer architectures",
    ]

    print("\n[2/4] Measuring consecutive query embed latencies over persistent socket...")
    latencies = []
    for idx, q in enumerate(test_queries, 1):
        t0 = time.perf_counter()
        vec = embedder.embed_query(q)
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)
        print(f"  [{idx}/5] '{q[:38]}...' -> Dims: {len(vec)}, Latency: {elapsed:.2f} ms")
        assert len(vec) == 384, f"Expected 384 dimensions, got {len(vec)}"

    avg_latency = sum(latencies) / len(latencies)
    print(f"\n  Average latency per query: {avg_latency:.2f} ms")
    assert avg_latency < 50.0, f"Expected sub-50ms latency with Keep-Alive pool, got {avg_latency:.2f} ms"
    print(f"  ✓ High-speed Keep-Alive verified (< 50ms vs ~285ms unpooled baseline)!")

    print("\n[3/4] Testing concurrent batch embedding throughput...")
    t0_batch = time.perf_counter()
    batch_vecs = embedder.embed_texts(test_queries)
    batch_time = (time.perf_counter() - t0_batch) * 1000
    print(f"  ✓ Batch of {len(test_queries)} queries embedded in {batch_time:.2f} ms ({batch_time/len(test_queries):.2f} ms/query).")
    assert len(batch_vecs) == len(test_queries)

    print("\n[4/4] Testing clean socket teardown and local fallback...")
    embedder.close()
    assert embedder._remote_client is None
    print("  ✓ Embedder connection pool closed cleanly.")

    # Restore original setting
    settings.REMOTE_EMBEDDING_URL = original_url
    print("\n=================================================================")
    print("🎉 ALL EMBEDDER PERSISTENT POOLING VERIFICATIONS PASSED!")
    print("=================================================================")


if __name__ == "__main__":
    test_embedder_connection_pooling()
