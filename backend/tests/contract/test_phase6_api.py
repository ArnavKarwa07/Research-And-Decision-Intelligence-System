"""Contract tests for Phase 6 API endpoints.
Tests endpoint schemas, status codes, and HTTP contract for:
  - POST /api/v1/queries/{id}/decisions
  - GET /api/v1/queries/{id}/decisions
  - GET /api/v1/decisions/{id}
  - POST /api/v1/decisions/{id}/sensitivity
  - POST /api/v1/decisions/{id}/scenarios
"""
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
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
    """Creates a real session and query in the DB for contract testing.
    
    Patches out the LangGraph background research task to prevent the
    2+ minute pipeline from running during contract tests.
    """
    session_res = await async_client.post("/api/v1/sessions/", json={"title": "Phase 6 Contract Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # Patch run_research so the LangGraph pipeline doesn't run during contract tests
    with patch(
        "app.services.query_service.QueryService.run_research",
        new=AsyncMock(return_value=None)
    ):
        query_res = await async_client.post(
            f"/api/v1/sessions/{session_id}/queries/",
            json={"text": "Evaluate cloud infrastructure decision alternatives", "mode": "comprehensive"}
        )
    assert query_res.status_code == 201
    query_id = query_res.json()["id"]
    return session_id, query_id


@pytest.mark.asyncio
async def test_create_decision_analysis_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    payload = {
        "query_id": query_id,
        "alternatives": [
            {"id": "opt1", "name": "AWS Cloud Deployment", "pros": ["Maturity"], "cons": ["Cost"]},
            {"id": "opt2", "name": "GCP Cloud Deployment", "pros": ["AI Integration"], "cons": ["Ecosystem"]}
        ],
        "criteria": [
            {"id": "c1", "name": "Cost Efficiency", "weight": 0.4},
            {"id": "c2", "name": "Scalability", "weight": 0.6}
        ],
        "scenarios": [
            {"name": "Best Case", "probability": 0.3},
            {"name": "Base Case", "probability": 0.7}
        ]
    }

    response = await async_client.post(f"/api/v1/queries/{query_id}/decisions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["query_id"] == query_id
    assert "recommendation" in data
    assert "confidence" in data
    assert "alternatives" in data
    assert "scenarios" in data
    assert "sensitivity_analysis" in data


@pytest.mark.asyncio
async def test_list_query_decisions_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    # Create decision first
    payload = {
        "query_id": query_id,
        "alternatives": [{"id": "a1", "name": "Opt A"}],
        "criteria": [{"id": "c1", "name": "Cost", "weight": 1.0}]
    }
    await async_client.post(f"/api/v1/queries/{query_id}/decisions", json=payload)

    response = await async_client.get(f"/api/v1/queries/{query_id}/decisions")
    assert response.status_code == 200
    data = response.json()
    assert "decisions" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_decision_by_id_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    payload = {
        "query_id": query_id,
        "alternatives": [{"id": "a1", "name": "Opt A"}],
        "criteria": [{"id": "c1", "name": "Cost", "weight": 1.0}]
    }
    create_res = await async_client.post(f"/api/v1/queries/{query_id}/decisions", json=payload)
    decision_id = create_res.json()["id"]

    response = await async_client.get(f"/api/v1/decisions/{decision_id}")
    assert response.status_code == 200
    assert response.json()["id"] == decision_id


@pytest.mark.asyncio
async def test_get_decision_by_id_not_found(async_client):
    invalid_id = uuid4()
    response = await async_client.get(f"/api/v1/decisions/{invalid_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rerun_sensitivity_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    payload = {
        "query_id": query_id,
        "alternatives": [
            {"id": "a1", "name": "Opt A", "scores": {"c1": 0.8, "c2": 0.3}},
            {"id": "a2", "name": "Opt B", "scores": {"c1": 0.2, "c2": 0.9}}
        ],
        "criteria": [
            {"id": "c1", "name": "Cost", "weight": 0.6},
            {"id": "c2", "name": "Quality", "weight": 0.4}
        ]
    }
    create_res = await async_client.post(f"/api/v1/queries/{query_id}/decisions", json=payload)
    decision_id = create_res.json()["id"]

    sens_req = {"weight_delta": 0.02}
    response = await async_client.post(f"/api/v1/decisions/{decision_id}/sensitivity", json=sens_req)
    assert response.status_code == 200
    data = response.json()
    assert "sensitivity_analysis" in data


@pytest.mark.asyncio
async def test_rerun_scenarios_success(async_client, sample_session_and_query):
    _, query_id = sample_session_and_query
    payload = {
        "query_id": query_id,
        "alternatives": [{"id": "a1", "name": "Opt A"}],
        "criteria": [{"id": "c1", "name": "Cost", "weight": 1.0}]
    }
    create_res = await async_client.post(f"/api/v1/queries/{query_id}/decisions", json=payload)
    decision_id = create_res.json()["id"]

    sc_req = {
        "scenarios": [
            {"name": "Best Case", "probability": 0.4},
            {"name": "Worst Case", "probability": 0.6}
        ]
    }
    response = await async_client.post(f"/api/v1/decisions/{decision_id}/scenarios", json=sc_req)
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
