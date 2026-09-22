"""
api/routers/admin_auth.py
Enterprise Administrator Authentication & Identity Governance Router.

Provides:
- POST /api/v1/admin/auth/login (Credential authentication, JWT issuance, audit logging)
- GET /api/v1/admin/auth/me (Current admin profile inspection)
- POST /api/v1/admin/auth/change-password (Password change with current verification & strength rules)
- GET /api/v1/admin/auth/users (List all administrator IDs)
- POST /api/v1/admin/auth/users (Create new administrator account)
- PATCH /api/v1/admin/auth/users/{user_id}/status (Toggle active status with self-lockout prevention)
- DELETE /api/v1/admin/auth/users/{user_id} (Delete administrator account with last-superadmin protection)
- ensure_initial_superadmin (Auto-seeding of initial primary administrator on startup)
"""

import os
import re
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.rate_limiter import rate_limiter
from api.core.passwords import (
    hash_password,
    verify_password,
    validate_password_strength,
)
from api.core.auth import (
    create_access_token,
    get_current_user,
    require_role,
)
from api.core.security_logger import record_security_incident_bg
from db.session import get_db, async_session_factory
from db.models import AdminUser, User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/auth",
    tags=["Admin Authentication & User Management"],
)


# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------
class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100, description="Admin username or email")
    password: str = Field(..., min_length=1, description="Admin password")


class AdminUserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    must_change_password: bool
    created_at: str
    last_login_at: Optional[str] = None


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminUserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current plaintext password")
    new_password: str = Field(..., min_length=8, description="New plaintext password meeting complexity rules")


class CreateAdminUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique admin username (alphanumeric, -, _)")
    email: str = Field(..., description="Valid email address")
    full_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="admin", description="Role: superadmin, admin, or auditor")
    password: str = Field(..., min_length=8, description="Initial password meeting complexity rules")


class UpdateStatusRequest(BaseModel):
    is_active: bool


class UpdateAdminUserRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, description="Valid email address")
    role: Optional[str] = Field(None, description="Role: superadmin, admin, or auditor")
    password: Optional[str] = Field(None, min_length=8, description="Optional new password")
    is_active: Optional[bool] = None



# -----------------------------------------------------------------------------
# AUTO-SEEDING INITIAL ADMIN
# -----------------------------------------------------------------------------
async def ensure_initial_superadmin():
    """
    Ensures at least one active superadmin exists in admin_users on database initialization.
    Seeds default 'admin' with initial password if table is empty.
    """
    try:
        async with async_session_factory() as session:
            count_stmt = select(func.count(AdminUser.id))
            admin_count = (await session.execute(count_stmt)).scalar() or 0
            if admin_count == 0:
                init_username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin").strip()
                init_email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@mdu.ac.in").strip()
                init_pw = os.environ.get("ADMIN_INITIAL_PASSWORD", "Admin@MDU2026!").strip()
                
                logger.info(f"Seeding initial superadmin '{init_username}' ({init_email})...")
                default_admin = AdminUser(
                    username=init_username,
                    email=init_email,
                    full_name="Primary System Administrator",
                    role="superadmin",
                    password_hash=hash_password(init_pw),
                    is_active=True,
                    must_change_password=True,
                )
                session.add(default_admin)
                await session.commit()
                logger.info(f"Initial superadmin '{init_username}' successfully seeded.")
    except Exception as e:
        logger.warning(f"Note on initial superadmin check: {e}")


# -----------------------------------------------------------------------------
# ENDPOINTS
# -----------------------------------------------------------------------------
@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    req: AdminLoginRequest,
    request: Request,
    db_session: AsyncSession = Depends(get_db),
):
    """
    Authenticates an administrator using credentials.
    Issues a cryptographically signed JWT bearer token with admin claims.
    Audits success and failure events.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Rate limiting check (max 10 login attempts per minute per IP)
    try:
        rate_limiter.check_rate_limit(f"admin_login_ip:{client_ip}", limit=10)
    except HTTPException:
        record_security_incident_bg(
            event_type="BRUTE_FORCE_SUSPECTED",
            severity="HIGH",
            client_ip=client_ip,
            user_identifier=req.username,
            endpoint=request.url.path,
            detail=f"Rate limit exceeded for admin login attempts from IP {client_ip}.",
            action_taken="RATE_LIMITED",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": {"code": "rate_limit_exceeded", "message": "Too many failed login attempts. Please wait a minute before retrying."}},
        )

    clean_identifier = req.username.strip().lower()

    # Query admin user by username or email (case-insensitive)
    stmt = select(AdminUser).where(
        or_(
            func.lower(AdminUser.username) == clean_identifier,
            func.lower(AdminUser.email) == clean_identifier,
        )
    )
    admin_user = (await db_session.execute(stmt)).scalar_one_or_none()

    if not admin_user:
        record_security_incident_bg(
            event_type="AUTH_FAILURE",
            severity="HIGH",
            client_ip=client_ip,
            user_identifier=req.username,
            endpoint=request.url.path,
            detail="Admin login failed: Account identifier not found.",
            action_taken="BLOCKED",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "invalid_credentials", "message": "Invalid administrator username or password."}},
        )

    if not admin_user.is_active:
        record_security_incident_bg(
            event_type="FORBIDDEN_ACCESS",
            severity="HIGH",
            client_ip=client_ip,
            user_identifier=admin_user.username,
            endpoint=request.url.path,
            detail="Admin login rejected: Account has been deactivated.",
            action_taken="BLOCKED",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "account_disabled", "message": "This administrator account is currently deactivated."}},
        )

    # Offload CPU-heavy PBKDF2/bcrypt hashing off the main event loop
    is_valid_pw = await asyncio.to_thread(verify_password, req.password, admin_user.password_hash)
    if not is_valid_pw:
        record_security_incident_bg(
            event_type="AUTH_FAILURE",
            severity="HIGH",
            client_ip=client_ip,
            user_identifier=admin_user.username,
            endpoint=request.url.path,
            detail="Admin login failed: Incorrect password supplied.",
            action_taken="BLOCKED",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "invalid_credentials", "message": "Invalid administrator username or password."}},
        )

    # Authentication succeeded
    now = datetime.utcnow()
    admin_user.last_login_at = now
    await db_session.commit()

    token_payload = {
        "sub": admin_user.username,
        "admin_id": str(admin_user.id),
        "role": admin_user.role,
        "user_type": "admin_user",
        "email": admin_user.email,
        "full_name": admin_user.full_name or admin_user.username,
    }
    token = create_access_token(token_payload)

    record_security_incident_bg(
        event_type="ADMIN_LOGIN_SUCCESS",
        severity="LOW",
        client_ip=client_ip,
        user_identifier=admin_user.username,
        endpoint=request.url.path,
        detail=f"Administrator '{admin_user.username}' successfully authenticated (role={admin_user.role}).",
        action_taken="ALLOWED",
    )

    return AdminLoginResponse(
        access_token=token,
        token_type="bearer",
        user=AdminUserResponse(
            id=str(admin_user.id),
            username=admin_user.username,
            email=admin_user.email,
            full_name=admin_user.full_name,
            role=admin_user.role,
            is_active=admin_user.is_active,
            must_change_password=admin_user.must_change_password,
            created_at=admin_user.created_at.isoformat(),
            last_login_at=admin_user.last_login_at.isoformat() if admin_user.last_login_at else None,
        ),
    )


@router.get("/me", response_model=AdminUserResponse)
async def get_current_admin_profile(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Returns profile information and permissions for the currently authenticated administrator.
    """
    stmt = select(AdminUser).where(AdminUser.username == current_user.external_id)
    admin_user = (await db_session.execute(stmt)).scalar_one_or_none()

    if not admin_user:
        # Fallback if authenticated via root service key
        return AdminUserResponse(
            id="00000000-0000-0000-0000-000000000000",
            username=current_user.external_id,
            email="system@mdu.ac.in",
            full_name="System Administrator (Key Auth)",
            role="superadmin",
            is_active=True,
            must_change_password=False,
            created_at=datetime.utcnow().isoformat(),
            last_login_at=datetime.utcnow().isoformat(),
        )

    return AdminUserResponse(
        id=str(admin_user.id),
        username=admin_user.username,
        email=admin_user.email,
        full_name=admin_user.full_name,
        role=admin_user.role,
        is_active=admin_user.is_active,
        must_change_password=admin_user.must_change_password,
        created_at=admin_user.created_at.isoformat(),
        last_login_at=admin_user.last_login_at.isoformat() if admin_user.last_login_at else None,
    )


@router.post("/change-password")
async def change_admin_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Changes the logged-in administrator's password.
    Requires verifying the current password and meeting password complexity standards.
    """
    stmt = select(AdminUser).where(AdminUser.username == current_user.external_id)
    admin_user = (await db_session.execute(stmt)).scalar_one_or_none()

    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "not_supported", "message": "Service key accounts cannot modify passwords via this endpoint."}},
        )

    if not verify_password(req.current_password, admin_user.password_hash):
        record_security_incident_bg(
            event_type="AUTH_FAILURE",
            severity="MEDIUM",
            client_ip=request.client.host if request.client else "127.0.0.1",
            user_identifier=admin_user.username,
            endpoint=request.url.path,
            detail="Failed password change: current password incorrect.",
            action_taken="BLOCKED",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "invalid_current_password", "message": "Current password is incorrect."}},
        )

    is_strong, reason = validate_password_strength(req.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "weak_password", "message": reason}},
        )

    if req.current_password == req.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "same_password", "message": "New password cannot be identical to the current password."}},
        )

    admin_user.password_hash = hash_password(req.new_password)
    admin_user.must_change_password = False
    admin_user.updated_at = datetime.utcnow()
    await db_session.commit()

    record_security_incident_bg(
        event_type="PASSWORD_CHANGED",
        severity="LOW",
        client_ip=request.client.host if request.client else "127.0.0.1",
        user_identifier=admin_user.username,
        endpoint=request.url.path,
        detail=f"Password successfully changed for administrator '{admin_user.username}'.",
        action_taken="ALLOWED",
    )

    return {"status": "success", "message": "Administrator password updated successfully."}


@router.get("/users", response_model=List[AdminUserResponse])
async def list_admin_users(
    current_user: User = Depends(require_role("admin")),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Returns all registered administrator accounts.
    Requires administrator privileges.
    """
    stmt = select(AdminUser).order_by(AdminUser.created_at.asc())
    users = (await db_session.execute(stmt)).scalars().all()

    return [
        AdminUserResponse(
            id=str(u.id),
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            must_change_password=u.must_change_password,
            created_at=u.created_at.isoformat(),
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in users
    ]


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    req: CreateAdminUserRequest,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Provisions a new administrator ID.
    Validates username format, uniqueness, and password complexity.
    """
    clean_username = req.username.strip().lower()
    clean_email = req.email.strip().lower()

    # Validate username formatting
    if not re.match(r"^[a-z0-9_\-\.]{3,50}$", clean_username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "invalid_username", "message": "Username must be 3-50 characters and contain only letters, numbers, hyphens, or underscores."}},
        )

    # Validate email
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "invalid_email", "message": "Please enter a valid email address."}},
        )

    # Validate role
    if req.role not in ("superadmin", "admin", "auditor"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "invalid_role", "message": "Role must be 'superadmin', 'admin', or 'auditor'."}},
        )

    # Validate password complexity
    is_strong, reason = validate_password_strength(req.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "weak_password", "message": reason}},
        )

    # Check for existing username or email
    stmt = select(AdminUser).where(
        or_(
            func.lower(AdminUser.username) == clean_username,
            func.lower(AdminUser.email) == clean_email,
        )
    )
    existing = (await db_session.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "conflict", "message": f"Administrator with this username or email already exists."}},
        )

    new_admin = AdminUser(
        username=clean_username,
        email=clean_email,
        full_name=req.full_name.strip() if req.full_name else None,
        role=req.role,
        password_hash=hash_password(req.password),
        is_active=True,
        must_change_password=True,
    )
    db_session.add(new_admin)
    await db_session.commit()
    await db_session.refresh(new_admin)

    record_security_incident_bg(
        event_type="ADMIN_USER_CREATED",
        severity="LOW",
        client_ip=request.client.host if request.client else "127.0.0.1",
        user_identifier=current_user.external_id,
        endpoint=request.url.path,
        detail=f"New administrator '{new_admin.username}' created by '{current_user.external_id}' (role={new_admin.role}).",
        action_taken="ALLOWED",
    )

    return AdminUserResponse(
        id=str(new_admin.id),
        username=new_admin.username,
        email=new_admin.email,
        full_name=new_admin.full_name,
        role=new_admin.role,
        is_active=new_admin.is_active,
        must_change_password=new_admin.must_change_password,
        created_at=new_admin.created_at.isoformat(),
        last_login_at=None,
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def toggle_admin_user_status(
    user_id: str,
    req: UpdateStatusRequest,
    current_user: User = Depends(require_role("admin")),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Enables or disables an administrator account.
    Prevents self-deactivation.
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "invalid_id", "message": "Invalid user ID format."}},
        )

    stmt = select(AdminUser).where(AdminUser.id == uid)
    target = (await db_session.execute(stmt)).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Administrator account not found."}},
        )

    if target.username == current_user.external_id and not req.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "self_deactivation", "message": "You cannot deactivate your own administrator account."}},
        )

    if target.role == "superadmin" and current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "permission_denied", "message": "Only superadministrators can modify superadmin accounts."}},
        )

    if target.role == "superadmin" and not req.is_active:
        count_super_stmt = select(func.count(AdminUser.id)).where(AdminUser.role == "superadmin", AdminUser.is_active == True)
        super_count = (await db_session.execute(count_super_stmt)).scalar() or 0
        if super_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "last_superadmin", "message": "Cannot deactivate the only active superadmin account."}},
            )

    target.is_active = req.is_active
    target.updated_at = datetime.utcnow()
    await db_session.commit()

    return AdminUserResponse(
        id=str(target.id),
        username=target.username,
        email=target.email,
        full_name=target.full_name,
        role=target.role,
        is_active=target.is_active,
        must_change_password=target.must_change_password,
        created_at=target.created_at.isoformat(),
        last_login_at=target.last_login_at.isoformat() if target.last_login_at else None,
    )


@router.put("/users/{user_id}", response_model=AdminUserResponse)
@router.patch("/users/{user_id}", response_model=AdminUserResponse)
@router.post("/users/{user_id}", response_model=AdminUserResponse)
async def update_admin_user(
    user_id: str,
    req: UpdateAdminUserRequest,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Updates administrator account details (Full Name, Email, Role, Password, Active status).
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "invalid_id", "message": "Invalid user ID format."}},
        )

    stmt = select(AdminUser).where(AdminUser.id == uid)
    target = (await db_session.execute(stmt)).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Administrator account not found."}},
        )

    # 1. Update Full Name
    if req.full_name is not None:
        target.full_name = req.full_name.strip() if req.full_name.strip() else None

    # 2. Update Email
    if req.email and req.email.strip():
        clean_email = req.email.strip().lower()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "invalid_email", "message": "Please enter a valid email address."}},
            )
        # Check uniqueness if changed
        if clean_email != target.email.lower():
            dup_stmt = select(AdminUser).where(func.lower(AdminUser.email) == clean_email, AdminUser.id != uid)
            if (await db_session.execute(dup_stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": {"code": "conflict", "message": "Another administrator account is already registered with this email address."}},
                )
            target.email = clean_email

    # 3. Update Role
    if req.role:
        if req.role not in ("superadmin", "admin", "auditor"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "invalid_role", "message": "Role must be 'superadmin', 'admin', or 'auditor'."}},
            )
        if (req.role == "superadmin" or target.role == "superadmin") and current_user.role != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "permission_denied", "message": "Only superadministrators can grant or revoke superadmin privileges."}},
            )
        # Prevent demoting the last superadmin
        if target.role == "superadmin" and req.role != "superadmin":
            count_super_stmt = select(func.count(AdminUser.id)).where(AdminUser.role == "superadmin", AdminUser.is_active == True)
            super_count = (await db_session.execute(count_super_stmt)).scalar() or 0
            if super_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": {"code": "last_superadmin", "message": "Cannot demote the only active superadmin account."}},
                )
        target.role = req.role

    # 4. Optional Password Reset
    if req.password and req.password.strip():
        is_strong, reason = validate_password_strength(req.password.strip())
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "weak_password", "message": reason}},
            )
        target.password_hash = hash_password(req.password.strip())
        target.must_change_password = False

    # 5. Update Status
    if req.is_active is not None:
        if target.username == current_user.external_id and not req.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "self_deactivation", "message": "You cannot deactivate your own administrator account."}},
            )
        if target.role == "superadmin" and not req.is_active:
            count_super_stmt = select(func.count(AdminUser.id)).where(AdminUser.role == "superadmin", AdminUser.is_active == True)
            super_count = (await db_session.execute(count_super_stmt)).scalar() or 0
            if super_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": {"code": "last_superadmin", "message": "Cannot deactivate the only active superadmin account."}},
                )
        target.is_active = req.is_active

    target.updated_at = datetime.utcnow()
    await db_session.commit()

    record_security_incident_bg(
        event_type="ADMIN_USER_UPDATED",
        severity="LOW",
        client_ip=request.client.host if request.client else "127.0.0.1",
        user_identifier=current_user.external_id,
        endpoint=request.url.path,
        detail=f"Administrator '{target.username}' details updated by '{current_user.external_id}'.",
        action_taken="ALLOWED",
    )

    return AdminUserResponse(
        id=str(target.id),
        username=target.username,
        email=target.email,
        full_name=target.full_name,
        role=target.role,
        is_active=target.is_active,
        must_change_password=target.must_change_password,
        created_at=target.created_at.isoformat(),
        last_login_at=target.last_login_at.isoformat() if target.last_login_at else None,
    )


@router.delete("/users/{user_id}")
async def delete_admin_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Deletes an administrator account.
    Prevents self-deletion and ensures at least one superadmin remains.
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "invalid_id", "message": "Invalid user ID format."}},
        )

    stmt = select(AdminUser).where(AdminUser.id == uid)
    target = (await db_session.execute(stmt)).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Administrator account not found."}},
        )

    if target.username == current_user.external_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "self_deletion", "message": "You cannot delete your own administrator account."}},
        )

    if target.role == "superadmin" and current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "permission_denied", "message": "Only superadministrators can delete superadmin accounts."}},
        )

    if target.role == "superadmin":
        count_super_stmt = select(func.count(AdminUser.id)).where(AdminUser.role == "superadmin", AdminUser.is_active == True)
        super_count = (await db_session.execute(count_super_stmt)).scalar() or 0
        if super_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "last_superadmin", "message": "Cannot delete the only active superadmin account."}},
            )

    username_deleted = target.username
    await db_session.delete(target)
    await db_session.commit()

    record_security_incident_bg(
        event_type="ADMIN_USER_DELETED",
        severity="MEDIUM",
        client_ip=request.client.host if request.client else "127.0.0.1",
        user_identifier=current_user.external_id,
        endpoint=request.url.path,
        detail=f"Administrator account '{username_deleted}' was deleted by '{current_user.external_id}'.",
        action_taken="ALLOWED",
    )

    return {"status": "success", "message": f"Administrator '{username_deleted}' has been deleted."}
