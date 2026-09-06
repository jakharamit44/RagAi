import os
import sys
import time
import json
import asyncio
import logging
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from db.session import init_db
from api.core.llm_router import ABSTENTION_MESSAGE

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("evaluator")

async def run_evaluation():
    await init_db()

    eval_file = os.path.abspath("tests/data/ground_truth_eval.json")
    if not os.path.exists(eval_file):
        raise FileNotFoundError(f"Evaluation benchmark dataset missing: {eval_file}")

    with open(eval_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    transport = ASGITransport(app=app)
    results = []

    logger.info(f"Loaded {len(test_cases)} evaluation cases from benchmark dataset.")
    logger.info("Executing evaluation runs against University RAG API...\n")

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for tc in test_cases:
            tc_id = tc["id"]
            question = tc["question"]
            dept = tc.get("department")
            course = tc.get("course")
            should_abstain = tc["should_abstain"]
            expected_doc = tc.get("expected_document")

            payload = {
                "question": question,
                "department": dept,
                "course": course
            }

            t0 = time.time()
            res = await client.post("/api/v1/ask", json=payload)
            latency_ms = (time.time() - t0) * 1000

            assert res.status_code == 200, f"Query failed for {tc_id}: {res.status_code}"
            data = res.json()
            answer = data.get("answer", "")
            citations = data.get("citations", [])

            # Evaluation criteria
            if should_abstain:
                is_abstained = (answer == ABSTENTION_MESSAGE and len(citations) == 0)
                hit = is_abstained
                citation_match = (len(citations) == 0)
            else:
                is_abstained = False
                # Check if expected document was retrieved
                hit = any(expected_doc in c.get("title", "") for c in citations) if expected_doc else True
                # Check citation precision
                citation_match = any(
                    expected_doc in c.get("title", "") and (tc.get("expected_section") is None or tc.get("expected_section") in (c.get("section") or ""))
                    for c in citations
                ) if expected_doc else True

            passed = (hit and citation_match) if not should_abstain else is_abstained

            results.append({
                "id": tc_id,
                "question": question,
                "should_abstain": should_abstain,
                "passed": passed,
                "hit": hit,
                "citation_match": citation_match,
                "latency_ms": latency_ms,
                "served_by": data.get("served_by"),
                "citations_count": len(citations),
            })

            status_symbol = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"[{status_symbol}] {tc_id}: '{question[:45]}...' ({latency_ms:.1f}ms, served_by={data.get('served_by')})")

    # Aggregate Metrics
    pos_cases = [r for r in results if not r["should_abstain"]]
    neg_cases = [r for r in results if r["should_abstain"]]

    retrieval_hit_rate = sum(1 for r in pos_cases if r["hit"]) / len(pos_cases) if pos_cases else 1.0
    citation_accuracy = sum(1 for r in pos_cases if r["citation_match"]) / len(pos_cases) if pos_cases else 1.0
    abstention_accuracy = sum(1 for r in neg_cases if r["passed"]) / len(neg_cases) if neg_cases else 1.0
    overall_pass_rate = sum(1 for r in results if r["passed"]) / len(results)
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)

    # Print Summary Table
    print("\n" + "=" * 65)
    print("      ENTERPRISE UNIVERSITY RAG - EVALUATION SCORECARD")
    print("=" * 65)
    print(f"Total Benchmark Test Cases:    {len(results)}")
    print(f"Positive Question Cases:       {len(pos_cases)}")
    print(f"Negative (Abstention) Cases:   {len(neg_cases)}")
    print("-" * 65)
    print(f"Retrieval Recall / Hit Rate:   {retrieval_hit_rate * 100:.1f}%   (Target >= 90.0%)")
    print(f"Citation Precision:            {citation_accuracy * 100:.1f}%   (Target >= 85.0%)")
    print(f"Abstention Accuracy:           {abstention_accuracy * 100:.1f}%   (Target == 100.0%)")
    print(f"Overall Benchmark Pass Rate:   {overall_pass_rate * 100:.1f}%")
    print(f"Average Query Latency:         {avg_latency:.2f}ms")
    print("=" * 65)

    # Export report to reports/evaluation_report.md
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Enterprise University RAG - Quality Evaluation Report\n\n")
        f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        f.write("## 1. Summary Scorecard\n\n")
        f.write("| Metric | Result | Quality SLO Target | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Retrieval Hit Rate** | {retrieval_hit_rate * 100:.1f}% | $\\ge 90\\%$ | {'🟢 PASS' if retrieval_hit_rate >= 0.90 else '🔴 FAIL'} |\n")
        f.write(f"| **Citation Precision** | {citation_accuracy * 100:.1f}% | $\\ge 85\\%$ | {'🟢 PASS' if citation_accuracy >= 0.85 else '🔴 FAIL'} |\n")
        f.write(f"| **Abstention Accuracy** | {abstention_accuracy * 100:.1f}% | $100\\%$ | {'🟢 PASS' if abstention_accuracy == 1.0 else '🔴 FAIL'} |\n")
        f.write(f"| **Overall Accuracy** | {overall_pass_rate * 100:.1f}% | $\\ge 90\\%$ | {'🟢 PASS' if overall_pass_rate >= 0.90 else '🔴 FAIL'} |\n\n")
        f.write("## 2. Test Case Breakdown\n\n")
        f.write("| ID | Question | Expected Doc | Result | Latency |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            f.write(f"| `{r['id']}` | {r['question'][:40]}... | {'[Abstain]' if r['should_abstain'] else 'Doc match'} | {'PASS' if r['passed'] else 'FAIL'} | {r['latency_ms']:.1f}ms |\n")

    logger.info(f"Report exported to: {report_path}")

    # Enforce quality SLOs
    assert retrieval_hit_rate >= 0.90, f"Retrieval hit rate failed threshold: {retrieval_hit_rate}"
    assert abstention_accuracy == 1.0, f"Abstention accuracy failed threshold: {abstention_accuracy}"
    assert citation_accuracy >= 0.85, f"Citation accuracy failed threshold: {citation_accuracy}"

    return results

if __name__ == "__main__":
    asyncio.run(run_evaluation())
