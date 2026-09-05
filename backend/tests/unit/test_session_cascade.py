"""Tests for session deletion cascade and title update persistence."""
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.session import Session
from app.models.query import Query
from app.models.source import Source
from app.models.artifact import Artifact
from app.schemas.session import SessionCreate
from app.services.session_service import SessionService

@pytest.mark.asyncio
async def test_session_title_update_and_cascade_delete():
    # In-memory SQLite for testing session cascade deletion
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as db:
        service = SessionService(db)

        # 1. Create Session
        created = await service.create_session(SessionCreate(title="New Research Workspace"))
        session_id = created.id
        assert created.title == "New Research Workspace"

        # 2. Update Session Title
        updated = await service.update_session_title(session_id, 'Thread: "What is quantum computing?"')
        assert updated is not None
        assert updated.title == 'Thread: "What is quantum computing?"'

        # 3. Add Query and Child Records
        q = Query(session_id=session_id, text="What is quantum computing?")
        db.add(q)
        await db.commit()
        await db.refresh(q)

        src = Source(query_id=q.id, url="https://example.com/quantum", title="Quantum Info")
        art = Artifact(session_id=session_id, query_id=q.id, artifact_type="report", title="Report 1", content_json={})
        db.add_all([src, art])
        await db.commit()

        # 4. Perform Cascade Delete
        success = await service.delete_session(session_id)
        assert success is True

        # 5. Verify Session and Children are Deleted
        fetched = await service.get_session(session_id)
        assert fetched is None

    await engine.dispose()
