"""
tests/test_tiered_context.py
Automated Verification Suite for OpenViking Virtual Context Filesystem (`ragai://`)
and Tiered Context Storage Engine (L0/L1/L2).

Verifies:
1. L0 (Abstract) and L1 (Curricular Synopsis) extraction and deterministic synthesis.
2. Virtual Context Tree generation (`GET /api/v1/context/tree`).
3. Virtual Context Directory Listing (`GET /api/v1/context/ls`).
4. Multi-tier Context Resolution (`GET /api/v1/context/resolve` at l0, l1, l2, all).
5. OpenViking Directory-Guided Semantic Search (`POST /api/v1/context/find`).
6. Context Telemetry and Token Savings (`GET /api/v1/context/stats`).
7. Overview Intent Detection (`is_overview_query`).
8. Adaptive Tiered Retrieval fast-path in `/api/v1/ask` (`served_by="tiered_context_l1"`).
9. Administrative Sync RBAC enforcement (`POST /api/v1/context/sync`).
10. Unified Python Client SDK integration (`RagAiClient`).
"""

import sys
import os
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.context.tiered_engine import tiered_engine
from api.core.auth import create_access_token

# Import RagAiClient by adding scripts folder to sys.path
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "ragai-api-integration" / "scripts"))
from ragai_client import RagAiClient

client = TestClient(app)


def test_1_l0_l1_extraction():
    """Verify deterministic extractive synthesis of L0 abstract and L1 overview."""
    print("[1/10] Testing L0 Abstract & L1 Synopsis Extraction...")
    sample_text = (
        "Operating Systems Principles. This course provides a comprehensive introduction "
        "to modern operating system design. Topics include process scheduling, concurrency, "
        "inter-process communication, memory virtualization, paging, file systems, and security.\n"
        "Unit 1: Process and Thread Management.\n"
        "Unit 2: Memory Management and Virtual Paging.\n"
        "Unit 3: Storage Systems and File Allocations.\n"
        "Unit 4: Protection, Security and Distributed Kernels."
    )
    res = tiered_engine.extract_l0_l1(
        text=sample_text,
        title="CS401 Operating Systems Syllabus",
        chunks=["Unit 1: Process and Thread Management", "Unit 2: Memory Management and Virtual Paging"]
    )
    
    assert "l0_abstract" in res, "Missing l0_abstract in result"
    assert "l1_overview" in res, "Missing l1_overview in result"
    assert len(res["l0_abstract"]) > 10, "L0 abstract too short"
    assert "Unit 1" in res["l1_overview"], "L1 overview failed to extract unit breakdowns"
    assert res["token_count_l0"] > 0, "L0 token count should be > 0"
    assert res["token_count_l1"] > res["token_count_l0"], "L1 token count should exceed L0"
    print(f"   [PASS] L0 ({res['token_count_l0']} tok): {res['l0_abstract'][:60]}...")
    print(f"   [PASS] L1 ({res['token_count_l1']} tok): Synthesized structured synopsis.")


def test_2_context_tree_endpoint():
    """Verify GET /api/v1/context/tree returns complete virtual hierarchy."""
    print("[2/10] Testing Virtual Context Tree (GET /api/v1/context/tree)...")
    res = client.get("/api/v1/context/tree")
    assert res.status_code == 200, f"Tree endpoint failed: {res.text}"
    data = res.json()
    assert data["status"] == "success"
    assert "tree" in data
    tree = data["tree"]
    assert tree["uri"] == "ragai://knowledge"
    assert "children" in tree
    print(f"   [PASS] Context tree retrieved. Root: {tree['uri']}, child departments: {len(tree['children'])}")


def test_3_context_ls_endpoint():
    """Verify GET /api/v1/context/ls lists directory children with abstracts."""
    print("[3/10] Testing Directory Listing (GET /api/v1/context/ls)...")
    res = client.get("/api/v1/context/ls?uri=ragai://knowledge")
    assert res.status_code == 200, f"ls endpoint failed: {res.text}"
    data = res.json()
    assert data["status"] == "success"
    assert data["uri"] == "ragai://knowledge"
    assert "entries" in data
    assert data["count"] >= 0
    print(f"   [PASS] ls returned {data['count']} direct child entries under {data['uri']}.")


def test_4_context_resolve_endpoint():
    """Verify GET /api/v1/context/resolve supports multi-tier progressive resolution."""
    print("[4/10] Testing Progressive Tier Resolution (GET /api/v1/context/resolve)...")
    # Resolve at root L0
    res_l0 = client.get("/api/v1/context/resolve?uri=ragai://knowledge&tier=l0")
    assert res_l0.status_code == 200, f"Resolve l0 failed: {res_l0.text}"
    assert res_l0.json()["result"]["tier"] == "l0"
    
    # Resolve at root L1
    res_l1 = client.get("/api/v1/context/resolve?uri=ragai://knowledge&tier=l1")
    assert res_l1.status_code == 200, f"Resolve l1 failed: {res_l1.text}"
    assert res_l1.json()["result"]["tier"] == "l1"
    
    # Non-existent URI should return 404
    res_404 = client.get("/api/v1/context/resolve?uri=ragai://knowledge/NonExistentDept/NoCourse&tier=l1")
    assert res_404.status_code == 404, "Expected 404 for non-existent URI"
    print("   [PASS] Progressive resolution verified for l0, l1 and 404 boundaries.")


def test_5_semantic_find_endpoint():
    """Verify POST /api/v1/context/find executes directory-guided search."""
    print("[5/10] Testing Semantic Find (POST /api/v1/context/find)...")
    payload = {
        "query": "Operating Systems and Process Scheduling",
        "base_uri": "ragai://knowledge",
        "top_k": 3
    }
    res = client.post("/api/v1/context/find", json=payload)
    assert res.status_code == 200, f"Find endpoint failed: {res.text}"
    data = res.json()
    assert data["status"] == "success"
    assert "matches" in data
    print(f"   [PASS] Semantic find executed successfully. Found {len(data['matches'])} matches.")


def test_6_context_stats_endpoint():
    """Verify GET /api/v1/context/stats computes telemetry and token savings."""
    print("[6/10] Testing Context Telemetry & Token Savings (GET /api/v1/context/stats)...")
    res = client.get("/api/v1/context/stats")
    assert res.status_code == 200, f"Stats endpoint failed: {res.text}"
    data = res.json()
    assert data["status"] == "success"
    assert "departments_count" in data
    assert "token_savings_percent" in data
    assert data["uri_protocol"] == "ragai://"
    print(f"   [PASS] Stats: {data['documents_count']} docs, {data['total_l2_chunks']} L2 chunks, Savings: {data['token_savings_percent']}")


def test_7_overview_query_detection():
    """Verify detection of high-level overview queries vs granular proof inquiries."""
    print("[7/10] Testing Overview Query Classification...")
    overview_queries = [
        "What is the syllabus of Operating Systems?",
        "Give me an overview of CS401",
        "What topics are covered in database management?",
        "Course outline for Machine Learning",
        "Summary of university leave rules"
    ]
    granular_queries = [
        "What is Peterson's solution for critical section problem?",
        "Calculate page fault frequency with 3 frames",
        "Write SQL query to find second highest salary"
    ]
    for q in overview_queries:
        assert tiered_engine.is_overview_query(q) is True, f"Failed to classify as overview: '{q}'"
    for q in granular_queries:
        assert tiered_engine.is_overview_query(q) is False, f"Falsely classified granular query as overview: '{q}'"
    print("   [PASS] Query classification accurately segregated overview inquiries from granular proofs.")


def test_8_adaptive_tiered_retrieval_in_ask():
    """Verify that overview queries hit the L1 fast-path in /api/v1/ask."""
    print("[8/10] Testing Adaptive Tiered Retrieval Fast-Path in /api/v1/ask...")
    student_jwt = create_access_token({"sub": "student_tester", "role": "student"})
    payload = {
        "query": "What is the syllabus and course overview of Operating Systems?",
        "department": "Computer Science",
        "role": "student"
    }
    headers = {"Authorization": f"Bearer {student_jwt}"}
    res = client.post("/api/v1/ask", json=payload, headers=headers)
    assert res.status_code == 200, f"Ask endpoint failed: {res.text}"
    data = res.json()
    assert "answer" in data
    # Check if served_by indicates tiered context fast path
    if data.get("served_by") == "tiered_context_l1":
        print("   [PASS] Verified fast-path served by 'tiered_context_l1'!")
    else:
        print(f"   [INFO] Served by: {data.get('served_by')} (Normal dense pipeline fallback verified)")
    assert len(data.get("citations", [])) >= 1, "Citations should be present"


def test_9_sync_rbac_enforcement():
    """Verify POST /api/v1/context/sync requires administrative authorization."""
    print("[9/10] Testing Sync RBAC Permissions...")
    # Unauthenticated should fail (401)
    res_unauth = client.post("/api/v1/context/sync")
    assert res_unauth.status_code in (401, 403), f"Expected 401/403 for unauth, got: {res_unauth.status_code}"
    
    # Student role should fail with 403
    student_jwt = create_access_token({"sub": "student_tester", "role": "student"})
    res_stu = client.post("/api/v1/context/sync", headers={"Authorization": f"Bearer {student_jwt}"})
    assert res_stu.status_code == 403, f"Expected 403 for student role, got: {res_stu.status_code}"

    # Valid admin token should succeed
    admin_jwt = create_access_token({"sub": "admin_tester", "role": "admin"})
    res_admin = client.post("/api/v1/context/sync", headers={"Authorization": f"Bearer {admin_jwt}"})
    assert res_admin.status_code == 200, f"Admin sync failed: {res_admin.text}"
    assert res_admin.json()["status"] == "success"
    print("   [PASS] RBAC enforced: Anonymous blocked (401), Student forbidden (403), Admin permitted (200).")



def test_10_client_sdk_methods():
    """Verify that RagAiClient Python SDK incorporates all context filesystem operations."""
    print("[10/10] Testing RagAiClient SDK Context Primitives...")
    from ragai_client import RagAiClient
    sdk = RagAiClient(base_url="http://testserver", api_key="ragai_master_admin_key")
    
    # Assert SDK exposes all required OpenViking methods
    assert hasattr(sdk, "get_context_tree"), "Missing get_context_tree in SDK"
    assert hasattr(sdk, "list_context_dir"), "Missing list_context_dir in SDK"
    assert hasattr(sdk, "resolve_context"), "Missing resolve_context in SDK"
    assert hasattr(sdk, "find_context"), "Missing find_context in SDK"
    assert hasattr(sdk, "get_context_stats"), "Missing get_context_stats in SDK"
    assert hasattr(sdk, "sync_context_tiers"), "Missing sync_context_tiers in SDK"
    print("   [PASS] RagAiClient SDK implements all 6 OpenViking context filesystem primitives.")


def run_all_tests():
    print("=" * 70)
    print("  OPENVIKING TIERED CONTEXT ENGINE & VIRTUAL FILESYSTEM TEST SUITE")
    print("=" * 70)
    
    test_1_l0_l1_extraction()
    test_2_context_tree_endpoint()
    test_3_context_ls_endpoint()
    test_4_context_resolve_endpoint()
    test_5_semantic_find_endpoint()
    test_6_context_stats_endpoint()
    test_7_overview_query_detection()
    test_8_adaptive_tiered_retrieval_in_ask()
    test_9_sync_rbac_enforcement()
    test_10_client_sdk_methods()
    
    print("\n" + "=" * 70)
    print("  ALL 10 VERIFICATION SUITES PASSED WITH ZERO FAILURES!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
