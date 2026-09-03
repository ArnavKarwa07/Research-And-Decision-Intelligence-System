"""Dependency injection providers."""
from typing import AsyncGenerator
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
