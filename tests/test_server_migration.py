"""
tests/test_server_migration.py
Automated Verification Suite for Ubuntu VM Server Migration & Infrastructure Transfer Subsystem.

Verifies:
1. Active Source Infrastructure Status endpoint (`GET /api/v1/admin/migration/source-status`).
2. Pre-flight probe against target VM services (`POST /api/v1/admin/migration/probe`).
3. Pre-flight probe error detection on unreachable target host.
4. Migration status polling endpoint schema (`GET /api/v1/admin/migration/status`).
5. RBAC security enforcement (admin access required, unauthenticated / student rejected).
6. Parity audit report retrieval when no job run (`GET /api/v1/admin/migration/parity`).
7. TargetVMSpec model validation and URL builders.
"""

import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.core.auth import create_access_token
from api.routers.server_migration import TargetVMSpec

client = TestClient(app)

# Helper tokens
admin_token = create_access_token(data={"sub": "admin_user", "role": "admin"})
student_token = create_access_token(data={"sub": "student_user", "role": "student"})

admin_headers = {
    "Authorization": f"Bearer {admin_token}",
    "X-API-Key": "dev-secret-key-rag-university"
}

student_headers = {
    "Authorization": f"Bearer {student_token}",
}


def test_1_target_vm_spec_builders():
    """Verify TargetVMSpec model builds correct PostgreSQL and Redis URLs."""
    print("[1/7] Testing TargetVMSpec connection URL generators...")
    spec = TargetVMSpec(
        host="192.168.81.160",
        postgres_port=5432,
        postgres_db="university_rag",
        postgres_user="ragai",
        postgres_password="secret_password",
        redis_port=6379,
        redis_password="redis_secret",
        qdrant_port=6333,
        tei_port=8080,
        minio_port=9000,
    )
    db_url = spec.build_target_db_url()
    redis_url = spec.build_target_redis_url()

    assert db_url == "postgresql+asyncpg://ragai:secret_password@192.168.81.160:5432/university_rag"
    assert redis_url == "redis://:redis_secret@192.168.81.160:6379/0"
    print("  ✓ TargetVMSpec correctly builds async PostgreSQL and Redis connection strings.")


def test_2_source_status():
    """Verify GET /api/v1/admin/migration/source-status returns active metrics."""
    print("[2/7] Testing GET /api/v1/admin/migration/source-status...")
    res = client.get("/api/v1/admin/migration/source-status", headers=admin_headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()

    assert "host" in data
    assert "total_db_rows" in data
    assert "total_vectors" in data
    assert "counts" in data
    assert isinstance(data["counts"], dict)
    assert data["total_db_rows"] > 0
    assert data["total_vectors"] > 0
    # Check key tables exist
    for table_name in ["documents", "chunks", "users", "api_keys", "watched_folders"]:
        assert table_name in data["counts"], f"Expected table {table_name} in counts"

    print(f"  ✓ Active source telemetry verified: Host={data['host']}, Total Rows={data['total_db_rows']:,}, Vectors={data['total_vectors']:,}")


def test_3_probe_active_vm():
    """Verify POST /api/v1/admin/migration/probe against current VM (192.168.81.150)."""
    print("[3/7] Testing Pre-Flight Probe against active VM services...")
    payload = {
        "host": "192.168.81.150",
        "postgres_port": 5432,
        "postgres_db": "university_rag",
        "postgres_user": "ragai",
        "postgres_password": "9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1",
        "qdrant_port": 6333,
        "qdrant_api_key": "9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1",
        "qdrant_https": False,
        "redis_port": 6379,
        "redis_password": "9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1",
        "tei_port": 8080,
        "minio_port": 9000,
        "minio_access_key": "ragai_admin",
        "minio_secret_key": "9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1"
    }

    res = client.post("/api/v1/admin/migration/probe", headers=admin_headers, json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()

    assert "all_ok" in data
    assert "services" in data
    for s_name in ["postgres", "qdrant", "redis", "tei", "minio"]:
        assert s_name in data["services"]
        s_info = data["services"][s_name]
        assert s_info["ok"] is True, f"Service {s_name} probe failed: {s_info.get('error')}"
        assert s_info["latency_ms"] is not None

    assert data["all_ok"] is True
    print(f"  ✓ Pre-Flight Probe passed for all 5 services! (Postgres latency: {data['services']['postgres']['latency_ms']}ms, Qdrant: {data['services']['qdrant']['latency_ms']}ms)")


def test_4_probe_unreachable_target():
    """Verify probe safely detects failure when target host is non-existent."""
    print("[4/7] Testing Pre-Flight Probe failure detection on unreachable target...")
    # 192.0.2.1 is reserved for documentation/testing (RFC 5737) and should timeout
    payload = {
        "host": "192.0.2.1",
        "postgres_port": 5432,
        "postgres_db": "university_rag",
        "postgres_user": "ragai",
        "postgres_password": "invalid_password",
        "qdrant_port": 6333,
        "qdrant_api_key": "invalid_key",
        "qdrant_https": False,
        "redis_port": 6379,
        "tei_port": 8080,
        "minio_port": 9000,
    }

    res = client.post("/api/v1/admin/migration/probe", headers=admin_headers, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["all_ok"] is False
    assert any(s["ok"] is False for s in data["services"].values())
    print("  ✓ Unreachable host correctly flagged with all_ok=False and descriptive errors.")


def test_5_migration_status_schema():
    """Verify GET /api/v1/admin/migration/status returns valid state response."""
    print("[5/7] Testing GET /api/v1/admin/migration/status response schema...")
    res = client.get("/api/v1/admin/migration/status", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    for field in ["status", "stage", "progress_percent", "current_task", "logs"]:
        assert field in data, f"Field {field} missing from migration status response"

    print(f"  ✓ Status response valid: Status='{data['status']}', Stage='{data['stage']}', Progress={data['progress_percent']}%")


def test_6_rbac_security_guards():
    """Verify that only admin role can access server migration routes."""
    print("[6/7] Testing RBAC security authorization guards...")
    # 1. No auth headers -> 401
    res_no_auth = client.get("/api/v1/admin/migration/source-status")
    assert res_no_auth.status_code in [401, 403]

    # 2. Student role -> 403 Forbidden
    res_student = client.get("/api/v1/admin/migration/source-status", headers=student_headers)
    assert res_student.status_code == 403, f"Expected 403 Forbidden for student, got {res_student.status_code}"

    # 3. Student attempting probe -> 403 Forbidden
    res_probe_student = client.post("/api/v1/admin/migration/probe", headers=student_headers, json={"host": "192.168.81.150", "postgres_password": "test"})
    assert res_probe_student.status_code == 403

    print("  ✓ Strict RBAC confirmed: Unauthenticated and student requests rejected with 401/403.")


def test_7_parity_report_empty():
    """Verify GET /api/v1/admin/migration/parity returns 404 when no migration completed."""
    print("[7/7] Testing GET /api/v1/admin/migration/parity 404 when uninitialized...")
    from api.routers.server_migration import migration_manager
    migration_manager.parity_report = None

    res = client.get("/api/v1/admin/migration/parity", headers=admin_headers)
    assert res.status_code == 404
    print("  ✓ Parity endpoint correctly returns 404 when no report exists.")


if __name__ == "__main__":
    test_1_target_vm_spec_builders()
    test_2_source_status()
    test_3_probe_active_vm()
    test_4_probe_unreachable_target()
    test_5_migration_status_schema()
    test_6_rbac_security_guards()
    test_7_parity_report_empty()
    print("\n🎉 ALL 7 SERVER MIGRATION TESTS PASSED SUCCESSFULLY!")
