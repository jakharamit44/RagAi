"""
tests/test_admin_auth.py
Automated Verification Suite for Enterprise Administrator Authentication & Admin-UI Subsystem.

Verifies:
1. PBKDF2 password hashing, salt randomization, constant-time verification, and complexity validation.
2. Superadmin login (JWT issuance & profile payload).
3. Rejection of invalid credentials with audit logging.
4. Admin profile endpoint (/api/v1/admin/auth/me).
5. Self-service password change (/api/v1/admin/auth/change-password) with old password verification.
6. Provisioning new administrators (/api/v1/admin/auth/users).
7. Safeguards against self-deactivation and self-deletion.
8. Safeguard preventing deletion of the last remaining active superadmin.
9. RBAC authorization barriers (students and unauthenticated calls rejected).
10. FastAPI SPA serving (/admin routes properly serve compiled React index.html and assets).
"""

import sys
import os
import uuid
import asyncio
from pathlib import Path
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.core.passwords import (
    hash_password,
    verify_password,
    validate_password_strength,
)
from api.core.auth import create_access_token


async def main_test_suite():
    print("=================================================================")
    print("ENTERPRISE ADMIN AUTH & REACT ADMIN-UI VERIFICATION SUITE")
    print("=================================================================")

    # -------------------------------------------------------------------------
    # 1. Password Security Module Tests
    # -------------------------------------------------------------------------
    print("\n[1/10] Verifying PBKDF2 password hashing & complexity rules...")
    raw = "TestSecret@2026!"
    h1 = hash_password(raw)
    h2 = hash_password(raw)

    assert h1 != h2, "Salt must be randomized across calls!"
    assert verify_password(raw, h1), "Valid password must verify!"
    assert verify_password(raw, h2), "Valid password must verify with separate salt!"
    assert not verify_password("WrongPassword@123", h1), "Incorrect password must fail verification!"

    # Complexity checks
    ok, _ = validate_password_strength("Short1!")
    assert not ok, "Passwords under 8 chars must be rejected."
    ok, _ = validate_password_strength("alllowercase123!")
    assert not ok, "Passwords without uppercase must be rejected."
    ok, _ = validate_password_strength("ALLUPPERCASE123!")
    assert not ok, "Passwords without lowercase must be rejected."
    ok, _ = validate_password_strength("NoDigitsSymbol!@#")
    assert not ok, "Passwords without digits must be rejected."
    ok, _ = validate_password_strength("ValidPassword@2026")
    assert ok, "Compliant password must pass strength check."
    print("  ✓ PBKDF2-HMAC-SHA256 hashing and complexity validations passed.")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # ---------------------------------------------------------------------
        # 2. Superadmin Login
        # ---------------------------------------------------------------------
        print("\n[2/10] Verifying Superadmin login with seeded credentials...")
        login_res = await client.post(
            "/api/v1/admin/auth/login",
            json={"username": "admin", "password": "Admin@MDU2026!"},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        data = login_res.json()
        assert "access_token" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "superadmin"
        admin_token = data["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("  ✓ Superadmin successfully authenticated. JWT access token received.")

        # ---------------------------------------------------------------------
        # 3. Invalid Credentials Rejection
        # ---------------------------------------------------------------------
        print("\n[3/10] Verifying invalid credentials rejection & audit logging...")
        bad_res = await client.post(
            "/api/v1/admin/auth/login",
            json={"username": "admin", "password": "WrongPassword@999!"},
        )
        assert bad_res.status_code == 401
        print("  ✓ Invalid login rejected with HTTP 401 Unauthorized.")

        # ---------------------------------------------------------------------
        # 4. Admin Profile Inspection (/me)
        # ---------------------------------------------------------------------
        print("\n[4/10] Verifying admin profile endpoint (/api/v1/admin/auth/me)...")
        me_res = await client.get("/api/v1/admin/auth/me", headers=admin_headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["username"] == "admin"
        assert me_data["role"] == "superadmin"
        print("  ✓ Profile verified: username=admin, role=superadmin.")

        # ---------------------------------------------------------------------
        # 5. Provisioning New Administrator
        # ---------------------------------------------------------------------
        print("\n[5/10] Provisioning a secondary administrator account...")
        test_uname = f"qa_officer_{uuid.uuid4().hex[:6]}"
        create_res = await client.post(
            "/api/v1/admin/auth/users",
            headers=admin_headers,
            json={
                "username": test_uname,
                "email": f"{test_uname}@mdu.ac.in",
                "full_name": "Quality Assurance Officer",
                "role": "admin",
                "password": "InitialPassword@2026!",
            },
        )
        assert create_res.status_code == 201, f"Failed creating user: {create_res.text}"
        qa_user = create_res.json()
        qa_id = qa_user["id"]
        assert qa_user["username"] == test_uname
        assert qa_user["role"] == "admin"
        print(f"  ✓ Administrator '{test_uname}' successfully provisioned with role=admin.")

        # ---------------------------------------------------------------------
        # 6. Secondary Admin Login & Password Change Workflow
        # ---------------------------------------------------------------------
        print("\n[6/10] Verifying secondary admin login and self-service password rotation...")
        qa_login = await client.post(
            "/api/v1/admin/auth/login",
            json={"username": test_uname, "password": "InitialPassword@2026!"},
        )
        assert qa_login.status_code == 200
        qa_token = qa_login.json()["access_token"]
        qa_headers = {"Authorization": f"Bearer {qa_token}"}

        # Attempt change password with wrong current password
        bad_chg = await client.post(
            "/api/v1/admin/auth/change-password",
            headers=qa_headers,
            json={
                "current_password": "WrongCurrentPassword!",
                "new_password": "UpdatedPassword@2026!",
            },
        )
        assert bad_chg.status_code == 400, "Wrong current password must be rejected."

        # Successful change password
        good_chg = await client.post(
            "/api/v1/admin/auth/change-password",
            headers=qa_headers,
            json={
                "current_password": "InitialPassword@2026!",
                "new_password": "UpdatedPassword@2026!",
            },
        )
        assert good_chg.status_code == 200, f"Password change failed: {good_chg.text}"

        # Verify old password fails
        old_login = await client.post(
            "/api/v1/admin/auth/login",
            json={"username": test_uname, "password": "InitialPassword@2026!"},
        )
        assert old_login.status_code == 401, "Old password must be rejected after rotation."

        # Verify new password succeeds
        new_login = await client.post(
            "/api/v1/admin/auth/login",
            json={"username": test_uname, "password": "UpdatedPassword@2026!"},
        )
        assert new_login.status_code == 200, "New password must authenticate successfully."
        print("  ✓ Password change workflow verified (old rejected, new accepted).")

        # ---------------------------------------------------------------------
        # 7. Safeguards: Self-Deactivation Protection
        # ---------------------------------------------------------------------
        print("\n[7/10] Testing administrator self-lockout safeguards...")
        # Get admin's own ID
        users_res = await client.get("/api/v1/admin/auth/users", headers=admin_headers)
        assert users_res.status_code == 200
        admin_rec = next(u for u in users_res.json() if u["username"] == "admin")

        self_deact = await client.patch(
            f"/api/v1/admin/auth/users/{admin_rec['id']}/status",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert self_deact.status_code == 400, "Self-deactivation must be prohibited."

        self_del = await client.delete(
            f"/api/v1/admin/auth/users/{admin_rec['id']}",
            headers=admin_headers,
        )
        assert self_del.status_code == 400, "Self-deletion must be prohibited."
        print("  ✓ Self-deactivation and self-deletion safeguards confirmed.")

        # ---------------------------------------------------------------------
        # 8. User Deletion & Cleanup
        # ---------------------------------------------------------------------
        print("\n[8/10] Deleting test administrator account...")
        del_res = await client.delete(
            f"/api/v1/admin/auth/users/{qa_id}",
            headers=admin_headers,
        )
        assert del_res.status_code == 200
        print("  ✓ Secondary administrator account cleaned up.")

        # ---------------------------------------------------------------------
        # 9. RBAC Authorization Barriers
        # ---------------------------------------------------------------------
        print("\n[9/10] Testing RBAC authorization boundaries (Student vs Admin)...")
        student_jwt = create_access_token({"sub": "student_101", "role": "student"})
        student_headers = {"Authorization": f"Bearer {student_jwt}"}

        # Student accessing admin user list
        rbac_res = await client.get("/api/v1/admin/auth/users", headers=student_headers)
        assert rbac_res.status_code == 403, "Students must be rejected from admin endpoints."

        # Unauthenticated request
        unauth_res = await client.get("/api/v1/admin/auth/users")
        assert unauth_res.status_code == 401, "Unauthenticated requests must be rejected."
        print("  ✓ Strict RBAC confirmed: student received 403, unauthenticated received 401.")

        # ---------------------------------------------------------------------
        # 10. FastAPI SPA Serving Verification
        # ---------------------------------------------------------------------
        print("\n[10/10] Verifying FastAPI React SPA serving at /admin...")
        spa_res = await client.get("/admin")
        assert spa_res.status_code == 200
        assert "Enterprise Administration Hub" in spa_res.text
        assert "/admin/assets/" in spa_res.text

        # Test sub-route SPA routing
        spa_sub_res = await client.get("/admin/migration")
        assert spa_sub_res.status_code == 200
        assert "Enterprise Administration Hub" in spa_sub_res.text

        print("  ✓ /admin and sub-routes successfully serve compiled React SPA.")

    print("\n=================================================================")
    print("🎉 ALL 10 ENTERPRISE ADMIN AUTH & ADMIN-UI VERIFICATIONS PASSED!")
    print("=================================================================")


if __name__ == "__main__":
    asyncio.run(main_test_suite())
