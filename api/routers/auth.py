from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.core.config import settings
from api.core.auth import create_access_token, get_current_user
from db.session import async_session_factory
from db.models import User

router = APIRouter(prefix="/auth", tags=["Authentication & SSO"])

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    role: str
    external_id: str

class LoginRequest(BaseModel):
    """SSO Identity Exchange payload (Phase 11 & Table 16)"""
    external_id: str = Field(..., description="SSO Subject identifier (e.g. student/faculty ID)")
    role: str = Field(default="student", description="Role: student | faculty | admin")
    department: Optional[str] = Field(default=None, description="Enrolled department")

class UserProfileResponse(BaseModel):
    id: str
    external_id: str
    role: str
    department: Optional[str]

from api.core.rate_limiter import rate_limiter
from fastapi import Request

@router.post("/login", response_model=AuthTokenResponse)
async def sso_login(req: LoginRequest, request: Request):
    """
    Simulated SSO / OIDC token bridge.
    Registers or updates user in local database mirror and issues signed JWT.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limiter.check_rate_limit(client_ip, limit=5, window_seconds=60)
    if req.role not in ["student", "faculty", "admin"]:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "validation_error", "message": "Role must be student, faculty, or admin."}}
        )

    async with async_session_factory() as session:
        stmt = select(User).where(User.external_id == req.external_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if not user:
            user = User(
                external_id=req.external_id,
                role=req.role,
                department=req.department,
            )
            session.add(user)
        else:
            user.role = req.role
            user.department = req.department

        await session.commit()

    token = create_access_token({
        "sub": req.external_id,
        "role": req.role,
        "department": req.department
    })

    return AuthTokenResponse(
        access_token=token,
        expires_in_minutes=settings.JWT_ACCESS_TOKEN_TTL_MINUTES,
        role=req.role,
        external_id=req.external_id
    )

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieve verified SSO identity profile."""
    return UserProfileResponse(
        id=str(current_user.id),
        external_id=current_user.external_id,
        role=current_user.role,
        department=current_user.department
    )

@router.post("/token", response_model=AuthTokenResponse)
async def obtain_service_token(api_key: str = Header(..., alias="X-API-Key")):
    """Static API key exchange for service-to-service calls (Phase 6)."""
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "unauthorized", "message": "Invalid API key provided"}}
        )

    token = create_access_token({
        "sub": "service-worker",
        "role": "admin",
        "department": "IT"
    })

    return AuthTokenResponse(
        access_token=token,
        expires_in_minutes=settings.JWT_ACCESS_TOKEN_TTL_MINUTES,
        role="admin",
        external_id="service-worker"
    )
