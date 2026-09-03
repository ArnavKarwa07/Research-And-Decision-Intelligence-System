"""Contract tests for Phase 5 API endpoints.
Tests endpoint schemas, status codes, and HTTP contract for:
  - POST /api/v1/queries/{id}/hypotheses/generate
  - GET /api/v1/queries/{id}/hypotheses
  - PATCH /api/v1/hypotheses/{id}
  - POST /api/v1/hypotheses/{id}/falsify
  - POST /api/v1/queries/{id}/critique
  - GET /api/v1/queries/{id}/critique
  - POST /api/v1/queries/{id}/self-challenge
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.engine import init_db


@pytest.fixture
async def async_client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def sample_session_and_query(async_client):
    """Creates a real session and query in the DB for contract testing."""
    session_res = await async_client.post("/api/v1/sessions/", json={"title": "Phase 5 Contract Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    query_res = await async_client.post(
        f"/api/v1/sessions/{session_id}/queries/",
        json={"text": "Evaluate clean energy transition dynamics", "mode": "deep"}
    )
    assert query_res.status_code == 201
    query_id = query_res.json()["id"]
    return session_id, query_id


# --- 1. Hypotheses Generation & Retrieval ---
@pytest.mark.asyncio
async def test_generate_hypotheses_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    response = await async_client.post(f"/api/v1/queries/{query_id}/hypotheses/generate")
    assert response.status_code == 201
    hypotheses = response.json()
    assert isinstance(hypotheses, list)
    assert len(hypotheses) > 0
    first = hypotheses[0]
    assert "id" in first
    assert "statement" in first
    assert "status" in first
    assert "confidence" in first


@pytest.mark.asyncio
async def test_generate_hypotheses_not_found(async_client):
    invalid_query_id = uuid4()
    response = await async_client.post(f"/api/v1/queries/{invalid_query_id}/hypotheses/generate")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_hypotheses_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    # Generate hypotheses first
    await async_client.post(f"/api/v1/queries/{query_id}/hypotheses/generate")
    response = await async_client.get(f"/api/v1/queries/{query_id}/hypotheses")
    assert response.status_code == 200
    hypotheses = response.json()
    assert isinstance(hypotheses, list)
    assert len(hypotheses) > 0


@pytest.mark.asyncio
async def test_get_hypotheses_empty_list_for_new_query(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    response = await async_client.get(f"/api/v1/queries/{query_id}/hypotheses")
    assert response.status_code == 200
    assert response.json() == []


# --- 2. Hypothesis Patching & Falsification ---
@pytest.mark.asyncio
async def test_patch_hypothesis_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    gen_res = await async_client.post(f"/api/v1/queries/{query_id}/hypotheses/generate")
    hyp_id = gen_res.json()[0]["id"]

    patch_payload = {
        "statement": "Updated statement under contract test",
        "confidence": 0.82,
        "status": "supported"
    }
    response = await async_client.patch(f"/api/v1/hypotheses/{hyp_id}", json=patch_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["statement"] == patch_payload["statement"]
    assert data["confidence"] == 0.82
    assert data["status"] == "supported"


@pytest.mark.asyncio
async def test_patch_hypothesis_not_found(async_client):
    invalid_hyp_id = uuid4()
    patch_payload = {"confidence": 0.9}
    response = await async_client.patch(f"/api/v1/hypotheses/{invalid_hyp_id}", json=patch_payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_hypothesis_invalid_schema(async_client):
    invalid_hyp_id = uuid4()
    patch_payload = {"confidence": 5.0}  # Invalid: confidence must be <= 1.0
    response = await async_client.patch(f"/api/v1/hypotheses/{invalid_hyp_id}", json=patch_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_falsify_hypothesis_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    gen_res = await async_client.post(f"/api/v1/queries/{query_id}/hypotheses/generate")
    hyp_id = gen_res.json()[0]["id"]

    response = await async_client.post(f"/api/v1/hypotheses/{hyp_id}/falsify")
    assert response.status_code == 200
    data = response.json()
    assert "hypothesis_id" in data
    assert "status" in data
    assert "confidence" in data
    assert "falsification_attempts" in data


@pytest.mark.asyncio
async def test_falsify_hypothesis_not_found(async_client):
    invalid_hyp_id = uuid4()
    response = await async_client.post(f"/api/v1/hypotheses/{invalid_hyp_id}/falsify")
    assert response.status_code == 404


# --- 3. Critique Endpoints ---
@pytest.mark.asyncio
async def test_run_critique_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    response = await async_client.post(f"/api/v1/queries/{query_id}/critique")
    assert response.status_code == 201
    report = response.json()
    assert "id" in report
    assert "query_id" in report
    assert "overall_severity" in report
    assert "replan_triggered" in report
    assert "findings" in report
    assert "recommendations" in report


@pytest.mark.asyncio
async def test_run_critique_not_found(async_client):
    invalid_query_id = uuid4()
    response = await async_client.post(f"/api/v1/queries/{invalid_query_id}/critique")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_critique_reports_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    await async_client.post(f"/api/v1/queries/{query_id}/critique")
    response = await async_client.get(f"/api/v1/queries/{query_id}/critique")
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_critique_reports_not_found(async_client):
    invalid_query_id = uuid4()
    response = await async_client.get(f"/api/v1/queries/{invalid_query_id}/critique")
    assert response.status_code == 404


# --- 4. Self-Challenge Endpoint ---
@pytest.mark.asyncio
async def test_self_challenge_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    payload = {
        "max_replan_iterations": 2,
        "confidence_threshold": 0.4
    }
    response = await async_client.post(f"/api/v1/queries/{query_id}/self-challenge", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "query_id" in data
    assert "hypotheses" in data
    assert "critique_reports" in data
    assert "replan_count" in data
    assert "final_status" in data
    assert "finalized_with_caveats" in data


@pytest.mark.asyncio
async def test_self_challenge_invalid_payload(async_client):
    invalid_query_id = uuid4()
    payload = {"max_replan_iterations": 99}  # Invalid: max_replan_iterations <= 10
    response = await async_client.post(f"/api/v1/queries/{invalid_query_id}/self-challenge", json=payload)
    assert response.status_code == 422
