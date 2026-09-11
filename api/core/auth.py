import time
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, Security, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy import select

from api.core.config import settings
from db.session import async_session_factory
from db.models import User, ApiKey
from api.core.security_logger import record_security_incident_bg


logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ROLE_HIERARCHY = {
    "student": 1,
    "faculty": 2,
    "admin": 3,
}

security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT access token (Phase 11 & Table 27)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_TTL_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.JWT_SIGNING_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT signature and expiration."""
    try:
        return jwt.decode(token, settings.JWT_SIGNING_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "unauthorized", "message": "Token has expired"}}
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "unauthorized", "message": "Invalid token signature"}}
        )

async def verify_api_key(raw_key: str) -> Optional[User]:
    """Validate dynamic multi-tenant API key from database or authorized service key."""
    if not raw_key:
        return None

    # 1. Optional explicit dev fallback keys strictly in development mode if enabled
    if settings.ENVIRONMENT == "development" and getattr(settings, "ALLOW_INSECURE_DEV_AUTH", False):
        if raw_key == settings.API_KEY or (settings.ADMIN_API_KEY and raw_key == settings.ADMIN_API_KEY):
            return User(
                external_id="static_dev_admin",
                role="admin",
                department=None
            )
        if settings.STUDENT_API_KEY and raw_key == settings.STUDENT_API_KEY:
            return User(
                external_id="student_portal_user",
                role="student",
                department=None
            )
        if settings.FACULTY_API_KEY and raw_key == settings.FACULTY_API_KEY:
            return User(
                external_id="faculty_portal_user",
                role="faculty",
                department=None
            )
    elif raw_key == settings.API_KEY and settings.API_KEY not in ("", "dev-insecure-api-key"):
        # Authorized service-to-service key
        return User(
            external_id="service_account_admin",
            role="admin",
            department=None
        )

    # 2. Query hashed API Key from database
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async with async_session_factory() as session:
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash)
        api_key_rec = (await session.execute(stmt)).scalar_one_or_none()
        if not api_key_rec:
            return None

        if not api_key_rec.is_active:
            record_security_incident_bg(
                event_type="AUTH_FAILURE",
                severity="MEDIUM",
                user_identifier=f"apikey:{api_key_rec.name}",
                detail="Disabled API Key used",
                action_taken="BLOCKED"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "api_key_disabled", "message": "API Key is currently disabled. Contact administrator."}}
            )

        now = datetime.utcnow()
        if api_key_rec.expires_at and api_key_rec.expires_at < now:
            record_security_incident_bg(
                event_type="AUTH_FAILURE",
                severity="LOW",
                user_identifier=f"apikey:{api_key_rec.name}",
                detail="Expired API Key used",
                action_taken="BLOCKED"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "api_key_expired", "message": "API Key has expired."}}
            )

        # Debounce last_used_at to prevent SQLite write lock serialization on every request
        if not api_key_rec.last_used_at or (now - api_key_rec.last_used_at).total_seconds() > 3600:
            api_key_rec.last_used_at = now
            await session.commit()

        return User(
            id=api_key_rec.id,
            external_id=f"apikey:{api_key_rec.name}",
            role=api_key_rec.role,
            department=api_key_rec.department
        )

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    api_key_val: Optional[str] = Security(api_key_header)
) -> User:
    """
    FastAPI dependency for mandatory authenticated endpoints.
    Accepts:
    1. X-API-Key header (dynamic DB or static)
    2. Bearer API key ('rag_live_...')
    3. Bearer JWT access token
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    endpoint = request.url.path

    # 1. Try X-API-Key header
    if api_key_val:
        user_from_key = await verify_api_key(api_key_val)
        if user_from_key:
            return user_from_key
        record_security_incident_bg(
            event_type="AUTH_FAILURE",
            severity="HIGH",
            client_ip=client_ip,
            endpoint=endpoint,
            detail=f"Invalid X-API-Key attempted: {api_key_val[:8]}...",
            action_taken="BLOCKED"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "unauthorized", "message": "Invalid API Key"}}
        )

    # 2. Try Bearer token
    if credentials and credentials.credentials:
        raw_bearer = credentials.credentials

        # If bearer token is an API key prefix
        if raw_bearer.startswith("rag_") or raw_bearer == settings.API_KEY:
            user_from_key = await verify_api_key(raw_bearer)
            if user_from_key:
                return user_from_key
            record_security_incident_bg(
                event_type="AUTH_FAILURE",
                severity="HIGH",
                client_ip=client_ip,
                endpoint=endpoint,
                detail=f"Invalid Bearer API Key attempted: {raw_bearer[:8]}...",
                action_taken="BLOCKED"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "unauthorized", "message": "Invalid API Key"}}
            )

        # Decode standard JWT
        payload = decode_token(raw_bearer)
        external_id = payload.get("sub")
        if not external_id:
            record_security_incident_bg(
                event_type="AUTH_FAILURE",
                severity="HIGH",
                client_ip=client_ip,
                endpoint=endpoint,
                detail="Invalid JWT claims (missing sub claim)",
                action_taken="BLOCKED"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "unauthorized", "message": "Invalid token claims"}}
            )

        async with async_session_factory() as session:
            stmt = select(User).where(User.external_id == external_id)
            user = (await session.execute(stmt)).scalar_one_or_none()
            if not user:
                user = User(
                    external_id=external_id,
                    role=payload.get("role", "student"),
                    department=payload.get("department"),
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "unauthorized", "message": "Authentication required. Bearer JWT or X-API-Key missing."}}
    )

async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    api_key_val: Optional[str] = Security(api_key_header)
) -> Optional[User]:
    """
    Optional user dependency.
    If no auth header is provided, returns None (allowing public guest access).
    If an auth header or API key IS provided, it must be valid and active!
    """
    has_auth = bool(api_key_val) or (credentials is not None and bool(credentials.credentials))
    if not has_auth:
        return None
    return await get_current_user(request, credentials, api_key_val)

def require_role(min_role: str):
    """
    Role-based access control dependency.
    Enforces student < faculty < admin permissions.
    """
    async def role_checker(request: Request, user: User = Depends(get_current_user)):
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        required_level = ROLE_HIERARCHY.get(min_role, 0)

        if user_level < required_level:
            client_ip = request.client.host if request.client else "127.0.0.1"
            record_security_incident_bg(
                event_type="FORBIDDEN_ACCESS",
                severity="HIGH",
                client_ip=client_ip,
                user_identifier=user.external_id,
                endpoint=request.url.path,
                detail=f"Insufficient privileges: Role '{user.role}' attempted to access '{min_role}' endpoint",
                action_taken="BLOCKED"
            )
            logger.warning(f"Access denied for user {user.external_id} (role={user.role}) to {min_role} endpoint")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "forbidden", "message": f"Requires '{min_role}' role or higher."}}
            )
        return user

    return role_checker

