import logging
from typing import Any, Optional, Dict, List
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("university_rag_api.exceptions")

class ErrorDetail(BaseModel):
    code: str
    message: str
    status_code: int
    request_id: Optional[str] = None
    details: Optional[Any] = None

class StandardErrorResponse(BaseModel):
    error: ErrorDetail

def _get_request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)

def _map_status_to_code(status_code: int) -> str:
    mapping = {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_401_UNAUTHORIZED: "unauthorized",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
        status.HTTP_409_CONFLICT: "conflict",
        getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413): "payload_too_large",
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
        getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422): "validation_error",
        status.HTTP_429_TOO_MANY_REQUESTS: "rate_limit_exceeded",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_error",
        status.HTTP_502_BAD_GATEWAY: "bad_gateway",
        status.HTTP_503_SERVICE_UNAVAILABLE: "service_unavailable",
        status.HTTP_504_GATEWAY_TIMEOUT: "gateway_timeout",
    }
    return mapping.get(status_code, "error")

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = _get_request_id(request)
    code = _map_status_to_code(exc.status_code)
    category = None
    if isinstance(exc.detail, dict):
        if "error" in exc.detail and isinstance(exc.detail["error"], dict):
            err_obj = exc.detail["error"]
            code = err_obj.get("code", code)
            msg = err_obj.get("message", str(err_obj))
            details = err_obj.get("details")
            category = err_obj.get("category")
        else:
            code = exc.detail.get("code", code)
            msg = exc.detail.get("message", str(exc.detail))
            details = exc.detail.get("details")
            category = exc.detail.get("category")
    else:
        msg = str(exc.detail)

    payload = {
        "type": f"https://ragai.mdu.ac.in/errors/{code.replace('_', '-')}",
        "title": code.replace("_", " ").title(),
        "status": exc.status_code,
        "detail": msg,
        "instance": f"urn:ragai:request:{request_id or 'unknown'}",
        "error": {
            "code": code,
            "message": msg,
            "status_code": exc.status_code,
            "request_id": request_id,
            "details": details,
        }
    }
    if category:
        payload["error"]["category"] = category
        payload["category"] = category
    headers = getattr(exc, "headers", None) or {}
    if request_id and "X-Request-ID" not in headers:
        headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers=headers,
        media_type="application/problem+json",
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = _get_request_id(request)
    
    # Format Pydantic errors cleanly
    clean_errors = []
    for err in exc.errors():
        clean_errors.append({
            "loc": err.get("loc", []),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        })

    payload = {
        "error": {
            "code": "validation_error",
            "message": "The request body or parameters failed validation.",
            "status_code": getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            "request_id": request_id,
            "details": clean_errors,
        }
    }
    headers = {"X-Request-ID": request_id} if request_id else None

    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content=payload,
        headers=headers,
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _get_request_id(request)
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path} (request_id={request_id}): {exc}",
        exc_info=True,
    )
    
    payload = {
        "error": {
            "code": "internal_error",
            "message": "An internal server error occurred. Please contact IT support.",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "request_id": request_id,
        }
    }
    headers = {"X-Request-ID": request_id} if request_id else None

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload,
        headers=headers,
    )

def setup_exception_handlers(app: FastAPI) -> None:
    """Register all enterprise exception handlers onto the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
