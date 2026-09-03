"""API contract tests for Critique Endpoints (Phase 5 P5-12)."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.models.base import Base
from app.models.query import Query
from app.dependencies import get_db


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_critique_api_routes():
    client = TestClient(app)
    fake_query_id = uuid4()

    # GET 404 for non-existent query
    res_get = client.get(f"/api/v1/queries/{fake_query_id}/critique")
    assert res_get.status_code == 404

    # POST 404 for non-existent query
    res_post = client.post(f"/api/v1/queries/{fake_query_id}/critique")
    assert res_post.status_code == 404
