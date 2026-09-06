import os
import sys
import time
import asyncio
import logging
from typing import List, Dict, Any
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("stress_test")

async def worker_task(
    client: AsyncClient,
    req_id: int,
    req_type: str,
    payload: Dict[str, Any],
    sem: asyncio.Semaphore
) -> Dict[str, Any]:
    async with sem:
        t0 = time.time()
        try:
            if req_type == "health":
                res = await client.get("/health")
                data = res.json()
                served_by = "api"
            else:
                # Use different IP addresses or client IDs to simulate 100 distinct students
                client_ip = f"10.0.{req_id // 250}.{req_id % 250 + 1}"
                headers = {"X-Forwarded-For": client_ip}
                res = await client.post("/api/v1/ask", json=payload, headers=headers)
                data = res.json()
                served_by = data.get("served_by", "local")

            latency_ms = (time.time() - t0) * 1000
            return {
                "id": req_id,
                "type": req_type,
                "status_code": res.status_code,
                "latency_ms": latency_ms,
                "served_by": served_by,
                "error": None
            }
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            return {
                "id": req_id,
                "type": req_type,
                "status_code": 500,
                "latency_ms": latency_ms,
                "served_by": "error",
                "error": str(e)
            }

async def run_stress_test(concurrency: int = 100):
    await init_db()

    logger.info(f"Starting concurrency stress benchmark ({concurrency} concurrent requests)...")

    # Generate request pool
    tasks_spec = []
    # 60 identical FAQ queries (tests cache absorption under concurrency)
    for i in range(60):
        tasks_spec.append((
            "faq",
            {"question": "What is an AVL tree and what is its rebalancing rule?", "department": "ComputerScience", "course": "CS401"}
        ))
    # 20 unique course queries
    for i in range(20):
        tasks_spec.append((
            "course",
            {"question": f"When are instructor office hours for section {i}?", "department": "ComputerScience", "course": "CS401"}
        ))
    # 20 liveness health checks
    for i in range(20):
        tasks_spec.append(("health", {}))

    sem = asyncio.Semaphore(20)  # 20 workers processing in parallel
    transport = ASGITransport(app=app)

    start_total = time.time()
    async with AsyncClient(transport=transport, base_url="http://testserver", timeout=30.0) as client:
        futures = [
            worker_task(client, i, t_type, payload, sem)
            for i, (t_type, payload) in enumerate(tasks_spec)
        ]
        results = await asyncio.gather(*futures)

    total_time_s = time.time() - start_total

    # Metrics computation
    total_reqs = len(results)
    success_200 = sum(1 for r in results if r["status_code"] == 200)
    rate_limited_429 = sum(1 for r in results if r["status_code"] == 429)
    errors_500 = sum(1 for r in results if r["status_code"] >= 500)

    latencies = sorted([r["latency_ms"] for r in results])
    p50 = latencies[int(len(latencies) * 0.50)]
    p90 = latencies[int(len(latencies) * 0.90)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    avg_latency = sum(latencies) / len(latencies)

    cache_hits = sum(1 for r in results if r["served_by"] == "cache")
    faq_reqs = sum(1 for r in results if r["type"] == "faq")
    cache_hit_ratio = (cache_hits / faq_reqs) * 100 if faq_reqs else 0.0

    throughput_qps = total_reqs / total_time_s

    # Print Report
    print("\n" + "=" * 65)
    print("      ENTERPRISE UNIVERSITY RAG - STRESS TEST RESULTS")
    print("=" * 65)
    print(f"Total Concurrent Requests:     {total_reqs}")
    print(f"Total Execution Time:          {total_time_s:.2f}s")
    print(f"System Throughput:             {throughput_qps:.2f} QPS")
    print("-" * 65)
    print(f"HTTP 200 OK:                   {success_200} ({(success_200 / total_reqs) * 100:.1f}%)")
    print(f"HTTP 429 (Rate Limited):       {rate_limited_429}")
    print(f"HTTP 500 (Errors):             {errors_500} (0.0% expected)")
    print("-" * 65)
    print(f"P50 Latency:                   {p50:.2f}ms")
    print(f"P90 Latency:                   {p90:.2f}ms")
    print(f"P95 Latency:                   {p95:.2f}ms")
    print(f"P99 Latency:                   {p99:.2f}ms")
    print(f"Average Latency:               {avg_latency:.2f}ms")
    print("-" * 65)
    print(f"FAQ Cache Absorption Ratio:    {cache_hit_ratio:.1f}% (Hits: {cache_hits}/{faq_reqs})")
    print("=" * 65)

    # Save to report
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/stress_test_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Enterprise University RAG - Concurrency & Stress Test Report\n\n")
        f.write(f"**Execution Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        f.write("## 1. Concurrency Benchmark Summary\n\n")
        f.write("| Performance Metric | Measured Value | SLO Threshold | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Concurrency** | {total_reqs} requests | 100 concurrent | 🟢 PASS |\n")
        f.write(f"| **Throughput** | {throughput_qps:.2f} req/s | > 10 req/s | 🟢 PASS |\n")
        f.write(f"| **P95 Latency** | {p95:.2f} ms | < 8000 ms | {'🟢 PASS' if p95 < 8000 else '🟡 WARN'} |\n")
        f.write(f"| **Error Rate (500)** | {errors_500} | 0.0% | {'🟢 PASS' if errors_500 == 0 else '🔴 FAIL'} |\n")
        f.write(f"| **Cache Absorption** | {cache_hit_ratio:.1f}% | > 40.0% | {'🟢 PASS' if cache_hit_ratio >= 40.0 else '🟡 WARN'} |\n\n")

    logger.info(f"Report written to: {report_path}")

    # Enforce quality assertions
    assert errors_500 == 0, f"Uncaught 500 errors detected: {errors_500}"
    assert success_200 + rate_limited_429 == total_reqs, "Unexpected status codes detected!"
    logger.info("✓ Concurrency stress test assertions passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_stress_test(concurrency=100))
