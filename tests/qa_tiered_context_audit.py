"""
tests/qa_tiered_context_audit.py
Comprehensive QA Verification and Audit Suite for OpenViking Tiered Context Engine
and Virtual Filesystem (ragai://) in RagAi.

Authored by: QA-Expert & Agency-API-Tester
Date: 2026-09-11
"""

import io
import sys
import os
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Windows UTF-8 stdout configuration
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "ragai-api-integration" / "scripts"))

import requests
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from api.main import app
from api.context.tiered_engine import tiered_engine
from api.core.auth import create_access_token
from api.core.config import settings
from db.session import async_session_factory
from db.models import ContextTier, Document, Chunk

from ragai_client import RagAiClient, RagAiError, AuthenticationError

client = TestClient(app)

audit_results = {
    "test_cases": [],
    "latencies_ms": {},
    "token_economics": {},
    "summary": {"total": 0, "passed": 0, "failed": 0}
}

def record_test(suite: str, name: str, passed: bool, latency_ms: float, details: str = "", extra: Dict[str, Any] = None):
    audit_results["summary"]["total"] += 1
    if passed:
        audit_results["summary"]["passed"] += 1
    else:
        audit_results["summary"]["failed"] += 1
    
    entry = {
        "suite": suite,
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "latency_ms": round(latency_ms, 2),
        "details": details,
        "extra": extra or {}
    }
    audit_results["test_cases"].append(entry)
    status_tag = "\033[92m[PASS]\033[0m" if passed else "\033[91m[FAIL]\033[0m"
    print(f"  {status_tag} {suite} :: {name} ({latency_ms:.2f}ms) - {details}")


# =========================================================================
# SUITE 1: GET /api/v1/context/tree
# =========================================================================
def audit_context_tree():
    print("\n--- SUITE 1: Virtual Context Tree (GET /api/v1/context/tree) ---")
    
    # 1.1 Unfiltered Tree
    t0 = time.perf_counter()
    res = client.get("/api/v1/context/tree")
    lat = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["tree_unfiltered"] = lat
    
    passed = res.status_code == 200
    data = res.json() if passed else {}
    tree = data.get("tree", {})
    root_uri = tree.get("uri")
    dept_count = len(tree.get("children", []))
    
    # Verify recursive structure
    total_courses = sum(len(d.get("children", [])) for d in tree.get("children", []))
    total_docs = 0
    for d in tree.get("children", []):
        for c in d.get("children", []):
            total_docs += len(c.get("children", []))
            
    valid_struct = root_uri == "ragai://knowledge" and dept_count > 0 and total_courses > 0 and total_docs > 0
    record_test(
        "Context Tree", "Unfiltered Hierarchy", passed and valid_struct, lat,
        f"Root: {root_uri}, Depts: {dept_count}, Courses: {total_courses}, Docs: {total_docs}",
        {"dept_count": dept_count, "courses": total_courses, "docs": total_docs}
    )
    
    # 1.2 Filtered by Department (ComputerScience)
    t0 = time.perf_counter()
    res_filt = client.get("/api/v1/context/tree?department=ComputerScience")
    lat_filt = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["tree_filtered"] = lat_filt
    
    p_filt = res_filt.status_code == 200
    data_filt = res_filt.json() if p_filt else {}
    tree_filt = data_filt.get("tree", {})
    filt_depts = [d.get("name") for d in tree_filt.get("children", [])]
    valid_filter = p_filt and ("ComputerScience" in filt_depts or "Computer Science" in filt_depts)
    record_test(
        "Context Tree", "Department Filter (ComputerScience)", valid_filter, lat_filt,
        f"Filtered departments returned: {filt_depts}",
        {"returned_departments": filt_depts}
    )
    
    # 1.3 Non-existent Department Filter
    t0 = time.perf_counter()
    res_none = client.get("/api/v1/context/tree?department=NonExistentDepartmentX99")
    lat_none = (time.perf_counter() - t0) * 1000
    p_none = res_none.status_code == 200
    tree_none = res_none.json().get("tree", {})
    valid_none = p_none and len(tree_none.get("children", [])) == 0
    record_test(
        "Context Tree", "Non-Existent Dept Filter", valid_none, lat_none,
        f"Returned root with 0 child departments as expected",
        {"children_count": len(tree_none.get("children", []))}
    )


# =========================================================================
# SUITE 2: GET /api/v1/context/ls
# =========================================================================
def audit_context_ls():
    print("\n--- SUITE 2: Virtual Directory Listing (GET /api/v1/context/ls) ---")
    
    # 2.1 Root Listing (ragai://knowledge)
    t0 = time.perf_counter()
    res_root = client.get("/api/v1/context/ls?uri=ragai://knowledge")
    lat_root = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["ls_root"] = lat_root
    
    p_root = res_root.status_code == 200
    data_root = res_root.json() if p_root else {}
    entries_root = data_root.get("entries", [])
    valid_entries_root = p_root and len(entries_root) > 0 and all(
        e.get("tier_type") == "department" for e in entries_root
    )
    record_test(
        "Context ls", "Root Directory Listing", valid_entries_root, lat_root,
        f"Returned {len(entries_root)} department nodes under ragai://knowledge",
        {"count": len(entries_root)}
    )
    
    # 2.2 Department Listing (ragai://knowledge/ComputerScience)
    t0 = time.perf_counter()
    res_dept = client.get("/api/v1/context/ls?uri=ragai://knowledge/ComputerScience")
    lat_dept = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["ls_dept"] = lat_dept
    
    p_dept = res_dept.status_code == 200
    entries_dept = res_dept.json().get("entries", []) if p_dept else []
    valid_dept = p_dept and len(entries_dept) > 0 and any(e.get("course") == "CS401" for e in entries_dept)
    record_test(
        "Context ls", "Department Branch Listing", valid_dept, lat_dept,
        f"Listed courses under ComputerScience: {[e.get('course') for e in entries_dept]}",
        {"courses": [e.get("course") for e in entries_dept]}
    )
    
    # 2.3 Deep Document Listing (ragai://knowledge/ComputerScience/CS401)
    t0 = time.perf_counter()
    res_course = client.get("/api/v1/context/ls?uri=ragai://knowledge/ComputerScience/CS401")
    lat_course = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["ls_course"] = lat_course
    
    p_course = res_course.status_code == 200
    entries_course = res_course.json().get("entries", []) if p_course else []
    sample_entry = entries_course[0] if entries_course else {}
    valid_course = (
        p_course and len(entries_course) >= 3 and
        "l0_abstract" in sample_entry and
        sample_entry.get("token_count_l0", 0) > 0 and
        sample_entry.get("token_count_l1", 0) > 0 and
        sample_entry.get("l2_chunk_count", 0) > 0
    )
    record_test(
        "Context ls", "Course Deep Document Listing", valid_course, lat_course,
        f"Found {len(entries_course)} documents. Sample L0 tokens: {sample_entry.get('token_count_l0')}, L2 chunks: {sample_entry.get('l2_chunk_count')}",
        {"document_count": len(entries_course), "sample": sample_entry.get("title")}
    )


# =========================================================================
# SUITE 3: GET /api/v1/context/resolve
# =========================================================================
def audit_context_resolve():
    print("\n--- SUITE 3: Progressive Context Resolution (GET /api/v1/context/resolve) ---")
    doc_uri = "ragai://knowledge/ComputerScience/CS401/course_syllabus.txt"
    
    # 3.1 Tier L0 Resolution (Abstract)
    t0 = time.perf_counter()
    res_l0 = client.get(f"/api/v1/context/resolve?uri={doc_uri}&tier=l0")
    lat_l0 = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["resolve_l0"] = lat_l0
    
    p_l0 = res_l0.status_code == 200
    data_l0 = res_l0.json().get("result", {}) if p_l0 else {}
    valid_l0 = p_l0 and data_l0.get("tier") == "l0" and len(data_l0.get("content", "")) > 10 and data_l0.get("tokens", 0) > 0
    record_test(
        "Context Resolve", "Tier L0 (Dense Abstract)", valid_l0, lat_l0,
        f"L0 resolved: {data_l0.get('tokens')} tokens, Content: '{data_l0.get('content', '')[:50]}...'",
        {"tokens": data_l0.get("tokens")}
    )
    
    # 3.2 Tier L1 Resolution (Curricular Synopsis)
    t0 = time.perf_counter()
    res_l1 = client.get(f"/api/v1/context/resolve?uri={doc_uri}&tier=l1")
    lat_l1 = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["resolve_l1"] = lat_l1
    
    p_l1 = res_l1.status_code == 200
    data_l1 = res_l1.json().get("result", {}) if p_l1 else {}
    valid_l1 = (
        p_l1 and data_l1.get("tier") == "l1" and
        data_l1.get("tokens", 0) > data_l0.get("tokens", 0) and
        "### Curricular Modules" in data_l1.get("content", "")
    )
    record_test(
        "Context Resolve", "Tier L1 (Curricular Synopsis)", valid_l1, lat_l1,
        f"L1 resolved: {data_l1.get('tokens')} tokens, Contains modular unit outline",
        {"tokens": data_l1.get("tokens")}
    )
    
    # 3.3 Tier L2 Resolution (Deep Chunks)
    t0 = time.perf_counter()
    res_l2 = client.get(f"/api/v1/context/resolve?uri={doc_uri}&tier=l2")
    lat_l2 = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["resolve_l2"] = lat_l2
    
    p_l2 = res_l2.status_code == 200
    data_l2 = res_l2.json().get("result", {}) if p_l2 else {}
    chunks = data_l2.get("chunks", [])
    valid_l2 = (
        p_l2 and data_l2.get("tier") == "l2" and
        data_l2.get("total_chunks", 0) > 0 and
        len(chunks) > 0 and
        "chunk_id" in chunks[0] and
        "page_number" in chunks[0] and
        "text" in chunks[0]
    )
    record_test(
        "Context Resolve", "Tier L2 (Deep Verbatim Chunks)", valid_l2, lat_l2,
        f"L2 resolved: {len(chunks)} chunks, total tokens: {data_l2.get('tokens')}",
        {"chunks_count": len(chunks), "tokens": data_l2.get("tokens")}
    )
    
    # 3.4 Tier All Resolution
    t0 = time.perf_counter()
    res_all = client.get(f"/api/v1/context/resolve?uri={doc_uri}&tier=all")
    lat_all = (time.perf_counter() - t0) * 1000
    p_all = res_all.status_code == 200
    data_all = res_all.json().get("result", {}) if p_all else {}
    valid_all = p_all and "l0" in data_all and "l1" in data_all and "l2_chunk_count" in data_all
    record_test(
        "Context Resolve", "Tier 'all' Complete Bundle", valid_all, lat_all,
        f"Bundled L0, L1, and L2 metadata ({data_all.get('l2_chunk_count')} chunks)",
        {"l2_chunks": data_all.get("l2_chunk_count")}
    )
    
    # 3.5 RFC 7807 Error Contract on Non-Existent URI (HTTP 404)
    t0 = time.perf_counter()
    res_404 = client.get("/api/v1/context/resolve?uri=ragai://knowledge/Mathematics/Topology/Euler.pdf&tier=l1")
    lat_404 = (time.perf_counter() - t0) * 1000
    p_404 = res_404.status_code == 404
    body_404 = res_404.json()
    valid_404 = (
        p_404 and
        body_404.get("status") == 404 and
        "not found" in body_404.get("detail", "").lower() and
        body_404.get("error", {}).get("code") == "not_found"
    )
    record_test(
        "Context Resolve", "Boundary: Non-Existent URI -> 404 RFC 7807", valid_404, lat_404,
        f"Status 404 RFC 7807: type='{body_404.get('type')}', detail='{body_404.get('detail')}'",
        {"body": body_404}
    )
    
    # 3.6 Regex Pattern Validation on Invalid Tier (HTTP 422)
    t0 = time.perf_counter()
    res_422 = client.get(f"/api/v1/context/resolve?uri={doc_uri}&tier=invalid_tier_99")
    lat_422 = (time.perf_counter() - t0) * 1000
    p_422 = res_422.status_code == 422
    body_422 = res_422.json()
    valid_422 = (
        p_422 and
        body_422.get("error", {}).get("code") == "validation_error" and
        "tier" in str(body_422)
    )
    record_test(
        "Context Resolve", "Validation: Invalid Tier Regex -> 422 Unprocessable", valid_422, lat_422,
        f"Status 422, Pydantic validation rejected invalid tier query parameter",
        {"error_detail": body_422.get("error")}
    )


# =========================================================================
# SUITE 4: POST /api/v1/context/find
# =========================================================================
def audit_context_find():
    print("\n--- SUITE 4: Directory-Guided Semantic Search (POST /api/v1/context/find) ---")
    
    queries = [
        ("Academic Syllabi", "Operating Systems Principles, Process Scheduling, and Virtual Memory"),
        ("Exam Rules", "Passing marks, grace marks rules, and academic examination scheme"),
        ("Algorithms", "Sorting algorithms, graph traversals, and computational complexity")
    ]
    
    for domain, query in queries:
        t0 = time.perf_counter()
        payload = {
            "query": query,
            "base_uri": "ragai://knowledge",
            "top_k": 4
        }
        res = client.post("/api/v1/context/find", json=payload)
        lat = (time.perf_counter() - t0) * 1000
        audit_results["latencies_ms"][f"find_{domain.lower().replace(' ', '_')}"] = lat
        
        passed = res.status_code == 200
        data = res.json() if passed else {}
        matches = data.get("matches", [])
        
        # Verify cosine similarity scoring and rank ordering
        valid_ranking = True
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                if matches[i]["score"] < matches[i+1]["score"]:
                    valid_ranking = False
                    break
        
        valid_scores = all(-1.0 <= m["score"] <= 1.0 for m in matches)
        valid = passed and len(matches) > 0 and valid_ranking and valid_scores
        top_match = matches[0] if matches else {}
        
        record_test(
            "Context Find", f"Semantic Search: {domain}", valid, lat,
            f"Found {len(matches)} matches. Top: '{top_match.get('title')}' (Score: {top_match.get('score')})",
            {"top_uri": top_match.get("uri"), "top_score": top_match.get("score")}
        )
    
    # 4.4 Base URI Scoping Test
    t0 = time.perf_counter()
    scoped_payload = {
        "query": "Syllabus and units",
        "base_uri": "ragai://knowledge/ComputerScience",
        "top_k": 3
    }
    res_scoped = client.post("/api/v1/context/find", json=scoped_payload)
    lat_scoped = (time.perf_counter() - t0) * 1000
    p_scoped = res_scoped.status_code == 200
    scoped_matches = res_scoped.json().get("matches", []) if p_scoped else []
    all_scoped = all(m["uri"].startswith("ragai://knowledge/ComputerScience") for m in scoped_matches)
    record_test(
        "Context Find", "Directory-Scoped Base URI Filter", p_scoped and all_scoped, lat_scoped,
        f"All {len(scoped_matches)} returned matches strictly adhere to base_uri prefix",
        {"matches_count": len(scoped_matches)}
    )


# =========================================================================
# SUITE 5: GET /api/v1/context/stats
# =========================================================================
def audit_context_stats():
    print("\n--- SUITE 5: Context Telemetry & Token Savings (GET /api/v1/context/stats) ---")
    
    t0 = time.perf_counter()
    res = client.get("/api/v1/context/stats")
    lat = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["stats"] = lat
    
    passed = res.status_code == 200
    data = res.json() if passed else {}
    
    # Query database directly for reconciliation
    async def get_db_counts():
        async with async_session_factory() as s:
            depts = await s.scalar(select(func.count()).select_from(ContextTier).where(ContextTier.tier_type == "department"))
            courses = await s.scalar(select(func.count()).select_from(ContextTier).where(ContextTier.tier_type == "course"))
            docs = await s.scalar(select(func.count()).select_from(ContextTier).where(ContextTier.tier_type == "document"))
            chunks = await s.scalar(select(func.sum(ContextTier.l2_chunk_count)).where(ContextTier.tier_type == "document"))
            return depts, courses, docs, chunks
            
    db_depts, db_courses, db_docs, db_chunks = asyncio.run(get_db_counts())
    
    acc_check = (
        data.get("departments_count") == db_depts and
        data.get("courses_count") == db_courses and
        data.get("documents_count") == db_docs and
        data.get("total_l2_chunks") == db_chunks
    )
    
    # Formula check: ((2500 - avg_l1) / 2500) * 100
    avg_l1 = data.get("avg_l1_tokens", 0)
    expected_savings = round(((2500 - avg_l1) / 2500) * 100, 1)
    reported_savings = float(data.get("token_savings_percent", "0%").replace("%", ""))
    formula_ok = abs(expected_savings - reported_savings) < 0.2
    
    audit_results["token_economics"] = {
        "avg_l0_tokens": data.get("avg_l0_tokens"),
        "avg_l1_tokens": avg_l1,
        "typical_l2_tokens": 2500,
        "token_savings_percent": data.get("token_savings_percent"),
        "formula_accurate": formula_ok
    }
    
    valid = passed and acc_check and formula_ok
    record_test(
        "Context Stats", "Telemetry Counters & Token Savings Reconciliation", valid, lat,
        f"Docs: {data.get('documents_count')}, Chunks: {data.get('total_l2_chunks')}, Avg L1: {avg_l1} tok, Savings: {data.get('token_savings_percent')}",
        {"db_reconciliation": acc_check, "formula_verified": formula_ok}
    )


# =========================================================================
# SUITE 6: POST /api/v1/context/sync
# =========================================================================
def audit_context_sync():
    print("\n--- SUITE 6: Synchronization RBAC Enforcement (POST /api/v1/context/sync) ---")
    
    # 6.1 Unauthenticated Request -> HTTP 401
    t0 = time.perf_counter()
    res_unauth = client.post("/api/v1/context/sync")
    lat_unauth = (time.perf_counter() - t0) * 1000
    p_unauth = res_unauth.status_code in (401, 403)
    record_test(
        "Context Sync", "RBAC: Anonymous Access Blocked", p_unauth, lat_unauth,
        f"Unauthenticated caller received HTTP {res_unauth.status_code}",
        {"status_code": res_unauth.status_code}
    )
    
    # 6.2 Student Role Request -> HTTP 403 Forbidden
    student_jwt = create_access_token({"sub": "student_qa_auditor", "role": "student"})
    t0 = time.perf_counter()
    res_student = client.post("/api/v1/context/sync", headers={"Authorization": f"Bearer {student_jwt}"})
    lat_student = (time.perf_counter() - t0) * 1000
    p_student = res_student.status_code == 403
    record_test(
        "Context Sync", "RBAC: Student Role Forbidden", p_student, lat_student,
        f"Student caller correctly rejected with HTTP 403 Forbidden",
        {"status_code": res_student.status_code}
    )
    
    # 6.3 Admin Role Request -> HTTP 200 OK
    admin_jwt = create_access_token({"sub": "admin_qa_auditor", "role": "admin"})
    t0 = time.perf_counter()
    res_admin = client.post("/api/v1/context/sync", headers={"Authorization": f"Bearer {admin_jwt}"})
    lat_admin = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["sync_admin"] = lat_admin
    p_admin = res_admin.status_code == 200 and res_admin.json().get("status") == "success"
    record_test(
        "Context Sync", "RBAC: Admin Role Authorized", p_admin, lat_admin,
        f"Admin caller granted sync execution. Message: '{res_admin.json().get('message')}'",
        {"status_code": res_admin.status_code}
    )


# =========================================================================
# SUITE 7: POST /api/v1/ask Adaptive Tiered Retrieval
# =========================================================================
def audit_ask_adaptive_retrieval():
    print("\n--- SUITE 7: Adaptive Tiered Retrieval in /api/v1/ask ---")
    student_jwt = create_access_token({"sub": "student_qa_auditor", "role": "student"})
    headers = {"Authorization": f"Bearer {student_jwt}"}
    
    # 7.1 Overview Query -> L1 Fast-Path (served_by="tiered_context_l1")
    overview_query = "What is the syllabus and course overview of Operating Systems CS401?"
    t0 = time.perf_counter()
    res_ov = client.post(
        "/api/v1/ask",
        json={"query": overview_query, "department": "Computer Science", "course": "CS401"},
        headers=headers
    )
    lat_ov = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["ask_overview_fastpath"] = lat_ov
    
    p_ov = res_ov.status_code == 200
    data_ov = res_ov.json() if p_ov else {}
    served_by_ov = data_ov.get("served_by")
    citations_ov = data_ov.get("citations", [])
    valid_ov = (
        p_ov and
        served_by_ov == "tiered_context_l1" and
        len(citations_ov) >= 1 and
        "answer" in data_ov and
        len(data_ov["answer"]) > 100
    )
    record_test(
        "Adaptive Ask", "Overview Query Hits L1 Fast-Path", valid_ov, lat_ov,
        f"Served by: '{served_by_ov}', Citations: {len(citations_ov)}, Answer tokens: ~{len(data_ov.get('answer', '').split())}",
        {"served_by": served_by_ov, "citations_count": len(citations_ov)}
    )
    
    # 7.2 Granular Proof Query -> Normal Pipeline Fallback (served_by != "tiered_context_l1")
    granular_query = "Explain Peterson's algorithm for mutual exclusion with turn variable and flag array in Operating Systems"
    t0 = time.perf_counter()
    res_gran = client.post(
        "/api/v1/ask",
        json={"query": granular_query, "department": "Computer Science", "course": "CS401"},
        headers=headers
    )
    lat_gran = (time.perf_counter() - t0) * 1000
    audit_results["latencies_ms"]["ask_granular_pipeline"] = lat_gran
    
    p_gran = res_gran.status_code == 200
    data_gran = res_gran.json() if p_gran else {}
    served_by_gran = data_gran.get("served_by")
    valid_gran = p_gran and served_by_gran != "tiered_context_l1"
    record_test(
        "Adaptive Ask", "Granular Proof Query Uses Deep Pipeline", valid_gran, lat_gran,
        f"Correctly bypassed L1 fast-path. Served by: '{served_by_gran}'",
        {"served_by": served_by_gran}
    )


# =========================================================================
# SUITE 8: Python Client SDK Integration (ragai_client.py)
# =========================================================================
def audit_python_sdk():
    print("\n--- SUITE 8: Python Client SDK End-to-End Integration ---")
    
    class TestClientAdapter(requests.adapters.HTTPAdapter):
        """Routes requests.Session calls synchronously through the FastAPI TestClient."""
        def send(self, request, **kwargs):
            url = request.url
            parts = url.split("://", 1)[1].split("/", 1)
            path = "/" + (parts[1] if len(parts) > 1 else "")
            resp = client.request(
                method=request.method,
                url=path,
                headers=dict(request.headers),
                content=request.body
            )
            r = requests.Response()
            r.status_code = resp.status_code
            r.raw = io.BytesIO(resp.content)
            r.url = request.url
            r.request = request
            r.headers.update(resp.headers)
            return r

    sdk = RagAiClient(base_url="http://testserver", api_key=settings.API_KEY)
    sdk.session.mount("http://testserver", TestClientAdapter())
    
    # 8.1 sdk.get_context_tree
    t0 = time.perf_counter()
    tree = sdk.get_context_tree()
    lat = (time.perf_counter() - t0) * 1000
    valid_tree = tree.get("status") == "success" and "tree" in tree
    record_test(
        "Python SDK", "RagAiClient.get_context_tree()", valid_tree, lat,
        f"SDK retrieved context tree. Root: {tree.get('tree', {}).get('uri')}",
        {"root_uri": tree.get("tree", {}).get("uri")}
    )
    
    # 8.2 sdk.list_context_dir
    t0 = time.perf_counter()
    ls_res = sdk.list_context_dir("ragai://knowledge")
    lat = (time.perf_counter() - t0) * 1000
    valid_ls = ls_res.get("status") == "success" and ls_res.get("count", 0) > 0
    record_test(
        "Python SDK", "RagAiClient.list_context_dir()", valid_ls, lat,
        f"SDK listed directory entries: {ls_res.get('count')} entries",
        {"count": ls_res.get("count")}
    )
    
    # 8.3 sdk.resolve_context
    t0 = time.perf_counter()
    res_l1 = sdk.resolve_context("ragai://knowledge/ComputerScience/CS401/course_syllabus.txt", tier="l1")
    lat = (time.perf_counter() - t0) * 1000
    valid_res = res_l1.get("status") == "success" and res_l1.get("result", {}).get("tier") == "l1"
    record_test(
        "Python SDK", "RagAiClient.resolve_context()", valid_res, lat,
        f"SDK resolved L1 tier. Tokens: {res_l1.get('result', {}).get('tokens')}",
        {"tokens": res_l1.get("result", {}).get("tokens")}
    )
    
    # 8.4 sdk.find_context
    t0 = time.perf_counter()
    find_res = sdk.find_context(query="Operating Systems", top_k=2)
    lat = (time.perf_counter() - t0) * 1000
    valid_find = find_res.get("status") == "success" and len(find_res.get("matches", [])) > 0
    record_test(
        "Python SDK", "RagAiClient.find_context()", valid_find, lat,
        f"SDK semantic find returned {len(find_res.get('matches', []))} matches",
        {"matches": len(find_res.get("matches", []))}
    )
    
    # 8.5 sdk.get_context_stats
    t0 = time.perf_counter()
    stats_res = sdk.get_context_stats()
    lat = (time.perf_counter() - t0) * 1000
    valid_stats = stats_res.get("status") == "success" and "token_savings_percent" in stats_res
    record_test(
        "Python SDK", "RagAiClient.get_context_stats()", valid_stats, lat,
        f"SDK telemetry: Docs: {stats_res.get('documents_count')}, Savings: {stats_res.get('token_savings_percent')}",
        {"savings": stats_res.get("token_savings_percent")}
    )
    
    # 8.6 sdk.sync_context_tiers
    t0 = time.perf_counter()
    sync_res = sdk.sync_context_tiers(api_key=settings.API_KEY)
    lat = (time.perf_counter() - t0) * 1000
    valid_sync = sync_res.get("status") == "success"
    record_test(
        "Python SDK", "RagAiClient.sync_context_tiers()", valid_sync, lat,
        f"SDK administrative sync succeeded: '{sync_res.get('message')}'",
        {"message": sync_res.get("message")}
    )


def print_final_audit_summary():
    tot = audit_results["summary"]["total"]
    passed = audit_results["summary"]["passed"]
    failed = audit_results["summary"]["failed"]
    
    print("\n" + "=" * 76)
    print("      OPENVIKING TIERED CONTEXT ENGINE & VIRTUAL FILESYSTEM QA AUDIT")
    print("=" * 76)
    print(f"Total Test Cases Executed: {tot}")
    print(f"Passed:                   \033[92m{passed}\033[0m")
    print(f"Failed:                   \033[91m{failed}\033[0m")
    print(f"Success Rate:             {(passed/tot)*100:.1f}%")
    print("=" * 76)
    
    print("\nLatency Benchmarks:")
    for k, v in audit_results["latencies_ms"].items():
        print(f"  - {k:30}: {v:8.2f} ms")
        
    print("\nToken Economics Evaluation:")
    te = audit_results["token_economics"]
    print(f"  - Average L0 Dense Abstract:    {te.get('avg_l0_tokens')} tokens")
    print(f"  - Average L1 Synopsis:          {te.get('avg_l1_tokens')} tokens")
    print(f"  - Typical L2 Chunk Load:        {te.get('typical_l2_tokens')} tokens")
    print(f"  - Net Token Savings Rate:       {te.get('token_savings_percent')}")
    print("=" * 76)
    
    # Save full audit results to JSON artifact
    out_path = PROJECT_ROOT / "tests" / "qa_audit_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"\nAudit results serialized to: {out_path}")


if __name__ == "__main__":
    audit_context_tree()
    audit_context_ls()
    audit_context_resolve()
    audit_context_find()
    audit_context_stats()
    audit_context_sync()
    audit_ask_adaptive_retrieval()
    audit_python_sdk()
    print_final_audit_summary()
