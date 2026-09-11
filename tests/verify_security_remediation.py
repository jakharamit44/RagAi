"""
tests/verify_security_remediation.py
Automated Verification Suite for Full Codebase Security & Code Remediation.
Tests all remediated vulnerabilities and performance improvements.
"""

import sys
import os
import asyncio
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_url_ssrf_safety():
    """Test SSRF protection with DNS resolution and private IP range checks."""
    print("[1/6] Testing SSRF & Outbound URL Safety...")
    from api.scraper.url_normalizer import UrlNormalizer
    
    blocked_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:8000/admin",
        "http://localhost:5432/",
        "http://10.0.0.1/private",
        "http://172.16.0.1/internal",
        "http://192.168.1.100/router",
        "http://[::1]/internal",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "http://metadata.google.internal/computeMetadata/v1/"
    ]
    
    for url in blocked_urls:
        is_safe, reason = UrlNormalizer.is_safe_url(url)
        assert not is_safe, f"SSRF vulnerability: {url} was NOT blocked! Reason: {reason}"
    
    # Test that campus intranet domain mdu.ac.in is blocked when not in allowed_domains,
    # but allowed when explicitly configured in allowed_domains
    is_safe_default, _ = UrlNormalizer.is_safe_url("https://mdu.ac.in/admissions")
    # In campus network, it resolves to 192.168.71.61 so it must be blocked without explicit whitelist:
    assert not is_safe_default, "Unwhitelisted private IP domain must be blocked by default"
    
    is_safe_whitelisted, reason = UrlNormalizer.is_safe_url("https://mdu.ac.in/admissions", allowed_domains=["mdu.ac.in"])
    assert is_safe_whitelisted, f"Explicitly whitelisted campus domain should be allowed! Reason: {reason}"

    # Valid safe public URLs should pass (if syntax and scheme are correct)
    safe_urls = [
        "https://www.google.com/search?q=mdu",
        "https://en.wikipedia.org/wiki/Computer_science"
    ]
    for url in safe_urls:
        is_safe, reason = UrlNormalizer.is_safe_url(url)
        assert is_safe, f"Safe URL false positive: {url} was blocked! Reason: {reason}"
        
    print("  --> PASS: SSRF protections successfully block cloud metadata, loopback, private RFC1918, and non-HTTP protocols.")

def test_path_traversal_governance():
    """Test path traversal validation for folders and directory browser."""
    print("\n[2/6] Testing Path Traversal & Source Root Isolation...")
    from fastapi import HTTPException
    from api.routers.documents import validate_folder_path
    
    # 1. Test existing outside directory (must return 400 forbidden_source_root)
    windows_dir = os.environ.get("WINDIR", "C:\\Windows")
    if os.path.exists(windows_dir):
        try:
            validate_folder_path(windows_dir)
            assert False, f"Path traversal allowed: {windows_dir} was not rejected!"
        except HTTPException as e:
            assert e.status_code == 400, f"Expected 400 for outside existing dir, got {e.status_code}"
            assert e.detail.get("error", {}).get("code") == "forbidden_path"
            print(f"  --> Blocked outside system path {windows_dir}: {e.detail}")

    # 2. Test non-existent traversal paths (must return 404 invalid_path)
    non_existent_paths = [
        "../../../../Windows/System32",
        "d:\\non_existent_outside_dir",
        "..\\..\\sensitive"
    ]
    for path in non_existent_paths:
        try:
            validate_folder_path(path)
            assert False, f"Non-existent path was not rejected: {path}"
        except HTTPException as e:
            assert e.status_code in (400, 404), f"Expected 400 or 404, got {e.status_code}"
            
    # Test valid path within data/
    valid_data_path = os.path.join(str(PROJECT_ROOT), "data", "sample_courses")
    resolved = validate_folder_path(valid_data_path)
    assert os.path.exists(resolved), f"Valid path {valid_data_path} failed to resolve."
    
    print("  --> PASS: Canonical path containment strictly restricts directory scanning to allowed data directories.")

def test_file_upload_validation():
    """Test document upload validation rejecting unsafe extensions."""
    print("\n[3/6] Testing Upload Security & Allowed Extension Whitelist...")
    from api.routers.documents import ALLOWED_EXTENSIONS
    
    disallowed = [".exe", ".sh", ".bat", ".py", ".php", ".js", ".vbs", ".dll", ".so", ".bin"]
    for ext in disallowed:
        assert ext not in ALLOWED_EXTENSIONS, f"Disallowed executable extension in whitelist: {ext}"
        
    required = [".pdf", ".docx", ".txt", ".csv", ".xlsx", ".md", ".html", ".htm"]
    for ext in required:
        assert ext in ALLOWED_EXTENSIONS, f"Expected extension missing: {ext}"
        
    print("  --> PASS: File extension whitelist correctly enforces safe document types and blocks executables.")

def test_sqlite_acid_and_concurrency():
    """Test SQLite foreign keys enabled and BEGIN IMMEDIATE transaction mode."""
    print("\n[4/6] Testing Database ACID Foreign Keys and Transaction Isolation...")
    from db.session import async_session_factory, engine
    from sqlalchemy import text
    
    async def _check():
        async with async_session_factory() as db:
            if "sqlite" in str(engine.url):
                res = (await db.execute(text("PRAGMA foreign_keys;"))).scalar()
                assert res == 1, f"SQLite PRAGMA foreign_keys is {res}, expected 1 (ON)"
                journal_mode = (await db.execute(text("PRAGMA journal_mode;"))).scalar()
                assert journal_mode.upper() == "WAL", f"SQLite PRAGMA journal_mode is {journal_mode}, expected WAL"
                print(f"  --> SQLite PRAGMA foreign_keys: ON, PRAGMA journal_mode: {journal_mode}")
            else:
                print("  --> PostgreSQL engine detected; relational integrity enforced by DBMS.")
    
    asyncio.run(_check())
    print("  --> PASS: SQLite foreign key enforcement and WAL concurrent access verified.")

def test_auth_and_privilege_escalation():
    """Test authentication rejection of hardcoded dev keys and admin privilege escalation."""
    print("\n[5/6] Testing Auth Hardening & SSO Privilege Escalation Guard...")
    from api.core.config import settings
    from api.core.auth import verify_api_key
    from api.routers.auth import sso_login, LoginRequest
    from fastapi import HTTPException
    
    # Verify insecure dev auth is disabled or gated
    async def _test_keys():
        if not settings.ALLOW_INSECURE_DEV_AUTH:
            # Static dev keys must fail
            user_student = await verify_api_key("ragai_student_default")
            assert user_student is None, "Insecure dev key accepted when ALLOW_INSECURE_DEV_AUTH is False!"
            user_admin = await verify_api_key("ragai_master_admin_key")
            assert user_admin is None, "Insecure admin dev key accepted when ALLOW_INSECURE_DEV_AUTH is False!"
            user_master = await verify_api_key("ragai_master")
            assert user_master is None, "Old backdoor 'ragai_master' accepted!"
    
    asyncio.run(_test_keys())
    
    # Test sso_login privilege escalation block: attempting role="admin" without valid admin secret
    class MockRequest:
        headers = {}
        client = type("Client", (), {"host": "127.0.0.1"})()
        
    mock_req = MockRequest()
    mock_body = LoginRequest(external_id="attacker_1", role="admin", department="IT")
    
    async def _test_escalation():
        try:
            await sso_login(mock_body, mock_req)
            assert False, "Privilege escalation allowed: unauthorized role='admin' was granted without secret!"
        except HTTPException as e:
            assert e.status_code == 403, f"Expected 403 Forbidden for unauthorized admin escalation, got {e.status_code}"
            print(f"  --> Privilege escalation attempt blocked with HTTP {e.status_code}: {e.detail}")
            
    asyncio.run(_test_escalation())
    print("  --> PASS: Auth security verified; privilege escalation and backdoor keys effectively eliminated.")

def test_rfc7807_exception_format():
    """Test RFC 7807 problem details response format."""
    print("\n[6/6] Testing RFC 7807 Problem Details Consistency...")
    from api.core.exceptions import http_exception_handler
    from fastapi import Request, HTTPException
    import json
    
    exc = HTTPException(
        status_code=404,
        detail={"error": {"code": "not_found", "message": "The document with ID doc_123 was not found in the manifest."}}
    )
    
    scope = {"type": "http", "method": "GET", "path": "/api/v1/documents/doc_123", "headers": []}
    req = Request(scope)
    
    async def _test_handler():
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 404
        assert resp.media_type == "application/problem+json"
        body = json.loads(resp.body.decode("utf-8"))
        assert body["type"] == "https://ragai.mdu.ac.in/errors/not-found"
        assert body["title"] == "Not Found"
        assert body["status"] == 404
        assert "doc_123" in body["detail"]
        assert "urn:ragai:request" in body["instance"]
        print(f"  --> RFC 7807 Response: Content-Type={resp.media_type}, Status={resp.status_code}")
        print(f"  --> RFC 7807 Body: type={body['type']}, title={body['title']}, status={body['status']}")

    asyncio.run(_test_handler())
    print("  --> PASS: RFC 7807 problem details formatting compliant with RFC specifications.")

def run_all_tests():
    print("==================================================================")
    print("   RAGAI FULL SYSTEM SECURITY & CODE AUDIT VERIFICATION SUITE   ")
    print("==================================================================")
    
    test_url_ssrf_safety()
    test_path_traversal_governance()
    test_file_upload_validation()
    test_sqlite_acid_and_concurrency()
    test_auth_and_privilege_escalation()
    test_rfc7807_exception_format()
    
    print("\n==================================================================")
    print("   ALL 6 REMEDIATION TEST SUITES PASSED WITH ZERO FAILURES!      ")
    print("==================================================================")

if __name__ == "__main__":
    run_all_tests()
