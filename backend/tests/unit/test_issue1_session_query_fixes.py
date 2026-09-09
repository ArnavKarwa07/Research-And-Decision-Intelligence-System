"""Unit tests for ISSUE-1: Session timestamp update in Fast-Path and list_sessions filtering."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.session import Session
from app.models.query import Query
from app.services.session_service import SessionService
from app.services.query_service import QueryService
from app.schemas.query import QueryCreate


@pytest.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session, session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_fast_path_touches_session_updated_at(test_db):
    db_session, session_factory = test_db
    session_service = SessionService(db_session)
    query_service = QueryService(db_session, settings=None)

    # 1. Create a session with an old updated_at timestamp
    old_time = datetime.now(timezone.utc) - timedelta(hours=5)
    session = Session(title="Fast Path Test Session", updated_at=old_time)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # 2. Create a conversational/fast-path query
    query_data = QueryCreate(text="hello", mode="quick")
    query = await query_service.create_query(session.id, query_data)

    # Reset session.updated_at to old_time to verify touch during run_research
    session.updated_at = old_time
    db_session.add(session)
    await db_session.commit()

    # 3. Execute run_research (mocking async_session_factory to use session_factory)
    with patch("app.services.query_service.async_session_factory", session_factory):
        await query_service.run_research(query.id, mode="quick")

    # 4. Verify parent session updated_at was refreshed
    await db_session.refresh(session)
    updated_at = session.updated_at.replace(tzinfo=timezone.utc) if session.updated_at.tzinfo is None else session.updated_at
    assert updated_at > old_time


@pytest.mark.asyncio
async def test_list_sessions_filtering_and_default_limit(test_db):
    db_session, _ = test_db
    session_service = SessionService(db_session)

    # 1. Session with query (should be included regardless of title)
    s1 = Session(title="New Research Workspace")
    db_session.add(s1)
    await db_session.commit()
    q1 = Query(session_id=s1.id, text="Query 1", status="completed")
    db_session.add(q1)

    # 2. Session with custom title (should be included even with 0 queries)
    s2 = Session(title="Custom Title Session")
    db_session.add(s2)

    # 3. Abandoned empty session with default title (should be excluded)
    s3 = Session(title="New Research Workspace")
    db_session.add(s3)

    # 4. Empty session with None title (should be excluded)
    s4 = Session(title=None)
    db_session.add(s4)

    # 5. Empty session with empty string title (should be excluded)
    s5 = Session(title="")
    db_session.add(s5)

    await db_session.commit()

    # Execute list_sessions with default limit
    sessions, total, cursor = await session_service.list_sessions()

    expected_filtered_sessions = [s1, s2]
    assert total == len(expected_filtered_sessions)

    retrieved_ids = {s.id for s in sessions}
    assert s1.id in retrieved_ids
    assert s2.id in retrieved_ids
    assert s3.id not in retrieved_ids
    assert s4.id not in retrieved_ids
    assert s5.id not in retrieved_ids


@pytest.mark.asyncio
async def test_list_sessions_invalid_cursor_raises_http_exception(test_db):
    from fastapi import HTTPException
    db_session, _ = test_db
    session_service = SessionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await session_service.list_sessions(cursor="invalid-cursor-string")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid cursor format"

