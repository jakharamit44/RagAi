"""API Routers package"""
from .health import router as health_router
from .ask import router as ask_router
from .chat import router as chat_router
from .documents import router as documents_router
from .auth import router as auth_router

__all__ = ["health_router", "ask_router", "chat_router", "documents_router", "auth_router"]
