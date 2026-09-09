import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import Settings
from app.models.base import Base

settings = Settings()

raw_db_url = os.environ.get("DATABASE_URL") or settings.database_url
# Normalize postgres URL scheme to postgresql+asyncpg://
if raw_db_url.startswith("postgres://"):
    db_url = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_db_url.startswith("postgresql://") and not raw_db_url.startswith("postgresql+asyncpg://"):
    db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    db_url = raw_db_url

# asyncpg does not accept sslmode or channel_binding query params in URL string directly if passed as libpq style
# Clean up query params if asyncpg is used with sslmode/channel_binding
connect_args = {}
if "sqlite" in db_url:
    connect_args = {"check_same_thread": False}
elif "postgresql+asyncpg" in db_url:
    # If sslmode=require is in URL, asyncpg expects ssl=True or ssl='require'
    if "sslmode=" in db_url or "channel_binding=" in db_url:
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)
        query_dict = urllib.parse.parse_qs(parsed.query)
        # remove incompatible asyncpg query params
        query_dict.pop("sslmode", None)
        query_dict.pop("channel_binding", None)
        new_query = urllib.parse.urlencode(query_dict, doseq=True)
        db_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
        connect_args["ssl"] = "require"

# Create async engine
engine = create_async_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Create session maker
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

def _run_sqlite_column_migrations(conn) -> None:
    """Safely adds any missing columns to SQLite tables without dropping data."""
    try:
        result = conn.exec_driver_sql("PRAGMA table_info(sources);").fetchall()
        if result:
            existing_cols = {row[1] for row in result}
            expected_cols = {
                "query_id": "CHAR(32)",
                "publisher": "VARCHAR",
                "source_type": "VARCHAR",
                "published_at": "DATETIME",
                "content_hash": "VARCHAR",
                "independence_group": "VARCHAR",
                "freshness_category": "VARCHAR",
            }
            for col_name, col_type in expected_cols.items():
                if col_name not in existing_cols:
                    conn.exec_driver_sql(f"ALTER TABLE sources ADD COLUMN {col_name} {col_type};")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"SQLite migration check skipped or encountered error: {e}")

async def init_db() -> None:
    """Initialize the database by creating all tables and ensuring column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in db_url:
            await conn.run_sync(_run_sqlite_column_migrations)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Generator providing an asynchronous database session."""
    async with async_session_factory() as session:
        yield session
