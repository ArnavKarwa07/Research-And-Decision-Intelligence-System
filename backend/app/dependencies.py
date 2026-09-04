"""Dependency injection providers."""
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import Header
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.engine import get_async_session

@lru_cache
def get_settings() -> Settings:
    """Returns cached Settings instance."""
    return Settings()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides an AsyncSession for dependency injection."""
    async for session in get_async_session():
        yield session


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> Optional[Dict[str, Any]]:
    """
    Optional security auth dependency that extracts user security context from HTTP headers if present.
    Returns user security context dict or None.
    """
    if x_user_id:
        return {"user_id": x_user_id, "auth_type": "header"}
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        return {"user_id": token, "auth_type": "bearer"}
    return None

