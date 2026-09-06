import os
import sys
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("master_test_runner")

TEST_SUITES = [
    ("Phase 1-2: Folder Ingestion & DB", "scripts/test_ingest.py"),
    ("Phase 3-4: Embeddings & Retrieval", "scripts/test_retrieval.py"),
    ("Phase 4-6: RAG Core API & Routing", "scripts/test_api.py"),
    ("Phase 7: Redis Cache & Rate Limiting", "scripts/test_cache_and_ratelimit.py"),
    ("Phase 8: Celery Task Workers", "scripts/test_workers.py"),
    ("Phase 9: Production Infrastructure", "scripts/test_infra_config.py"),
    ("Phase 10: Web UI & Dashboard", "scripts/test_ui_endpoints.py"),
    ("Phase 11: SSO Authentication & RBAC", "scripts/test_auth_rbac.py"),
    ("Phase 12: Prometheus Observability", "scripts/test_metrics.py"),
    ("Phase 13: Stress & Concurrency Test", "scripts/run_stress_test.py"),
    ("Phase 14: Chaos & Fault Injection", "scripts/run_chaos_experiments.py"),
    ("Phase 15: Fine-Tuning & Quantization", "scripts/test_fine_tuning.py"),
    ("Phase 16: Multi-Modal Ingestion", "scripts/test_multimodal.py"),
    ("Phase 17: Disaster Recovery Backup/Restore", "scripts/test_backup_restore.py"),
    ("Phase 18: Quality Evaluation Benchmark", "scripts/evaluate_rag.py"),
    ("Phase 19: Security & OWASP Audit", "scripts/test_security_audit.py"),
    ("Phase 20: Admin Governance & Cascade Purge", "scripts/test_admin_governance.py"),
]

def run_master_test_suite():
    python_bin = sys.executable
    summary_results = []

    print("\n" + "=" * 75)
    print("      ENTERPRISE UNIVERSITY RAG - MASTER VERIFICATION RUNNER")
    print("=" * 75)

    start_all = time.time()

    for phase_name, script_rel_path in TEST_SUITES:
        script_path = os.path.abspath(script_rel_path)
        if not os.path.exists(script_path):
            summary_results.append((phase_name, script_rel_path, "MISSING", 0.0, "Script file not found"))
            continue

        print(f"\n>>> Running: {phase_name} ({script_rel_path})...")
        t0 = time.time()
        try:
            res = subprocess.run(
                [python_bin, script_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600
            )
            duration_s = time.time() - t0

            if res.returncode == 0:
                print(f"    [PASS] in {duration_s:.2f}s")
                summary_results.append((phase_name, script_rel_path, "PASSED", duration_s, ""))
            else:
                print(f"    [FAIL] (Exit Code: {res.returncode}) in {duration_s:.2f}s")
                error_tail = "\n".join(res.stderr.strip().split("\n")[-6:]) or "\n".join(res.stdout.strip().split("\n")[-6:])
                print(f"    Error trace:\n{error_tail}")
                summary_results.append((phase_name, script_rel_path, "FAILED", duration_s, error_tail))
        except subprocess.TimeoutExpired:
            duration_s = time.time() - t0
            print(f"    [TIMEOUT] in {duration_s:.2f}s (>600s CPU limit)")
            summary_results.append((phase_name, script_rel_path, "TIMEOUT", duration_s, "Exceeded 600s timeout"))

    total_time_s = time.time() - start_all
    passed_count = sum(1 for r in summary_results if r[2] == "PASSED")
    total_count = len(summary_results)

    print("\n" + "=" * 75)
    print("                MASTER TEST EXECUTION SCORECARD")
    print("=" * 75)
    for phase_name, script, status, duration, err in summary_results:
        print(f"[{status:<6}] | {duration:>6.2f}s | {phase_name}")
    print("-" * 75)
    print(f"Overall Pass Rate: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%) in {total_time_s:.2f}s")
    print("=" * 75 + "\n")

    # Export master report
    os.makedirs("reports", exist_ok=True)
    report_file = "reports/master_test_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Master Test Execution & Quality Verification Report\n\n")
        f.write(f"**Execution Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        f.write("| Phase | Test Script | Status | Duration | Result |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for phase_name, script, status, duration, err in summary_results:
            status_icon = "🟢 PASS" if status == "PASSED" else "🔴 FAIL"
            f.write(f"| **{phase_name}** | `{script}` | {status_icon} | {duration:.2f}s | {'Success' if status == 'PASSED' else f'Error: {err}'} |\n")
        f.write(f"\n**Summary:** {passed_count}/{total_count} suites passed ({passed_count/total_count*100:.1f}%) in {total_time_s:.2f}s.\n")

    assert passed_count == total_count, f"Not all test suites passed: {passed_count}/{total_count}"
    return summary_results

if __name__ == "__main__":
    run_master_test_suite()
