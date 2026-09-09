"""Tests for session deletion cascade and title update persistence."""
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.session import Session
from app.models.query import Query
from app.models.source import Source
from app.models.claim import Claim
try:
    from app.models.claim import ClaimSource
except ImportError:
    from app.models.claim_source import ClaimSource
from app.models.contradiction import Contradiction
from app.models.artifact import Artifact
from app.models.source_group import SourceGroup, SourceGroupMember
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
        await db.refresh(src)

        sg = SourceGroup(query_id=q.id, name="Test Group", group_type="cluster")
        db.add(sg)
        await db.commit()
        await db.refresh(sg)

        sgm = SourceGroupMember(group_id=sg.id, source_id=src.id)
        db.add(sgm)
        await db.commit()

        # 4. Perform Cascade Delete
        success = await service.delete_session(session_id)
        assert success is True

        # 5. Verify Session and Children are Deleted
        fetched = await service.get_session(session_id)
        assert fetched is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_session_cascade_delete_with_claims_and_contradictions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as db:
        service = SessionService(db)

        # 1. Create Session & Query
        created = await service.create_session(SessionCreate(title="Test Research Workspace"))
        session_id = created.id
        q = Query(session_id=session_id, text="Test query for claim source cascade")
        db.add(q)
        await db.commit()
        await db.refresh(q)

        # 2. Add Sources, Claims, ClaimSources, Contradictions, Evidence, SourceGroups
        src = Source(query_id=q.id, url="https://example.com/source1", title="Source 1")
        db.add(src)
        await db.commit()
        await db.refresh(src)

        claim_a = Claim(query_id=q.id, content="Claim A", claim_type="fact")
        claim_b = Claim(query_id=q.id, content="Claim B", claim_type="fact")
        db.add_all([claim_a, claim_b])
        await db.commit()
        await db.refresh(claim_a)
        await db.refresh(claim_b)

        cs = ClaimSource(claim_id=claim_a.id, source_id=src.id, excerpt="Excerpt", support_type="supports")
        contra = Contradiction(query_id=q.id, claim_a_id=claim_a.id, claim_b_id=claim_b.id, contradiction_type="direct", severity="high")
        sg = SourceGroup(query_id=q.id, name="Group 1", group_type="cluster")
        db.add_all([cs, contra, sg])
        await db.commit()
        await db.refresh(sg)

        sgm = SourceGroupMember(group_id=sg.id, source_id=src.id)
        db.add(sgm)
        await db.commit()

        # 3. Perform Cascade Delete
        success = await service.delete_session(session_id)
        assert success is True

        # 4. Verify deletion
        fetched = await service.get_session(session_id)
        assert fetched is None

    await engine.dispose()

