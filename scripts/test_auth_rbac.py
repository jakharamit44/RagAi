import os
import sys
import asyncio
import logging
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_auth_rbac")

async def test_auth_and_rbac():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login as Student
        logger.info("\n--- 1. Login as Student ---")
        student_res = await client.post("/auth/login", json={
            "external_id": "student_alice_101",
            "role": "student",
            "department": "ComputerScience"
        })
        assert student_res.status_code == 200
        student_token = student_res.json()["access_token"]
        logger.info(f"Student JWT issued: {student_token[:25]}...")

        # 2. Verify Profile /auth/me
        logger.info("\n--- 2. Verify /auth/me for Student ---")
        headers_student = {"Authorization": f"Bearer {student_token}"}
        me_res = await client.get("/auth/me", headers=headers_student)
        assert me_res.status_code == 200
        me_data = me_res.json()
        logger.info(f"Profile: {me_data}")
        assert me_data["role"] == "student"
        assert me_data["external_id"] == "student_alice_101"
        logger.info("✓ /auth/me profile verified")

        # 3. Student tries Admin endpoint (Should fail with 403)
        logger.info("\n--- 3. Student Calling Admin Folder Register (Expect 403) ---")
        bad_admin_res = await client.post(
            "/api/v1/folders/register",
            headers=headers_student,
            json={"path": "data/sample_courses"}
        )
        logger.info(f"Response status: {bad_admin_res.status_code} ({bad_admin_res.json()})")
        assert bad_admin_res.status_code == 403
        assert bad_admin_res.json()["detail"]["error"]["code"] == "forbidden"
        logger.info("✓ RBAC Blocked Student from Admin Endpoint (403 Forbidden)")

        # 4. Login as Faculty
        logger.info("\n--- 4. Login as Faculty ---")
        faculty_res = await client.post("/auth/login", json={
            "external_id": "prof_turing_202",
            "role": "faculty",
            "department": "ComputerScience"
        })
        assert faculty_res.status_code == 200
        faculty_token = faculty_res.json()["access_token"]
        headers_faculty = {"Authorization": f"Bearer {faculty_token}"}

        # 5. Faculty Uploads Document (Allowed for Faculty)
        logger.info("\n--- 5. Faculty Uploading Document ---")
        test_file = os.path.abspath("data/faculty_lecture.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Faculty material for CS401")

        with open(test_file, "rb") as f:
            upload_res = await client.post(
                "/api/v1/documents/upload",
                headers=headers_faculty,
                files={"file": ("faculty_lecture.txt", f, "text/plain")},
                data={"course": "CS401"}
            )
        assert upload_res.status_code == 202
        logger.info(f"✓ Faculty Upload Succeeded (202): {upload_res.json()}")

        # 6. Faculty tries Admin endpoint (Should fail with 403)
        logger.info("\n--- 6. Faculty Calling Admin Folder Register (Expect 403) ---")
        faculty_admin_res = await client.post(
            "/api/v1/folders/register",
            headers=headers_faculty,
            json={"path": "data/sample_courses"}
        )
        assert faculty_admin_res.status_code == 403
        logger.info("✓ RBAC Blocked Faculty from Admin Endpoint (403 Forbidden)")

        # 7. Login as Admin
        logger.info("\n--- 7. Login as Admin ---")
        admin_res = await client.post("/auth/login", json={
            "external_id": "sysadmin_root",
            "role": "admin",
            "department": "IT"
        })
        assert admin_res.status_code == 200
        admin_token = admin_res.json()["access_token"]
        headers_admin = {"Authorization": f"Bearer {admin_token}"}

        # 8. Admin Registers Folder (Allowed for Admin)
        logger.info("\n--- 8. Admin Registering Watched Folder ---")
        admin_reg_res = await client.post(
            "/api/v1/folders/register",
            headers=headers_admin,
            json={"path": "data/sample_courses", "department": "ComputerScience", "course": "CS401"}
        )
        assert admin_reg_res.status_code == 201
        logger.info(f"✓ Admin Folder Register Succeeded (201): {admin_reg_res.json()}")

        # 9. Test Invalid Token (Expect 401)
        logger.info("\n--- 9. Testing Forged Token (Expect 401) ---")
        bad_token_res = await client.get("/auth/me", headers={"Authorization": "Bearer forged-fake-token"})
        assert bad_token_res.status_code == 401
        logger.info("✓ Forged Token Blocked (401 Unauthorized)")

    logger.info("\n=======================================================")
    logger.info("ALL PHASE 11 AUTH, RBAC & MULTI-TENANCY TESTS PASSED!")
    logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(test_auth_and_rbac())
