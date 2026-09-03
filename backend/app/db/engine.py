"""Database engine and session configuration."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import Settings
from app.models.base import Base

settings = Settings()

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=True,
    connect_args=connect_args,
)

# Create session maker
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def init_db() -> None:
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Generator providing an asynchronous database session."""
    async with async_session_factory() as session:
        yield session
