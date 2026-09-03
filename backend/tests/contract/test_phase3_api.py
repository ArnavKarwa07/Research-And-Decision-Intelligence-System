import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
import asyncio

from app.main import app
from app.dependencies import get_db

from app.db.engine import init_db

@pytest.fixture
async def async_client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_get_claims(async_client):
    query_id = uuid4()
    response = await async_client.get(f"/api/v1/queries/{query_id}/claims")
    # Bug 3: Should be 404 when query_id does not exist
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_extract_claims(async_client):
    query_id = uuid4()
    response = await async_client.post(f"/api/v1/queries/{query_id}/claims/extract")
    assert response.status_code in (200, 404)

@pytest.mark.asyncio
async def test_verify_claim_not_found(async_client):
    query_id = uuid4()
    claim_id = uuid4()
    response = await async_client.post(f"/api/v1/queries/{query_id}/claims/{claim_id}/verify")
    # Will be 404 since db is not mocked / populated
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_evidence_graph_404(async_client):
    query_id = uuid4()
    response = await async_client.get(f"/api/v1/queries/{query_id}/evidence-graph")
    # Bug 3: Should be 404 when query_id does not exist
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_contradictions_404(async_client):
    query_id = uuid4()
    response = await async_client.get(f"/api/v1/queries/{query_id}/contradictions")
    # Bug 3: Should be 404 when query_id does not exist
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_resolve_contradiction_invalid_status(async_client):
    contradiction_id = uuid4()
    payload = {
        "resolution_status": "RESOLVED_INVALID",
        "resolution_notes": "test"
    }
    response = await async_client.post(f"/api/v1/contradictions/{contradiction_id}/resolve", json=payload)
    # Bug 5: Missing input validation, Pydantic should catch and return 422
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_sse_stream_404_not_found(async_client):
    invalid_query_id = uuid4()
    response = await async_client.get(f"/api/v1/queries/{invalid_query_id}/stream")
    # Bug 4: Stream endpoint should validate query exists before starting EventSourceResponse
    assert response.status_code == 404
