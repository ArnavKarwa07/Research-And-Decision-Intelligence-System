"""Integration test for Phase 6 Decision Intelligence end-to-end pipeline.
Tests full workflow: Session Creation -> Query -> Decision Analysis Creation -> Sensitivity Re-run -> Scenario Re-run.
"""
import pytest
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


@pytest.mark.asyncio
async def test_full_phase6_decision_pipeline(async_client):
    # 1. Create Session
    session_res = await async_client.post("/api/v1/sessions/", json={"title": "Phase 6 E2E Pipeline Test"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # 2. Create Query (patch background research to avoid LangGraph recursion hang)
    with patch(
        "app.services.query_service.QueryService.run_research",
        new=AsyncMock(return_value=None)
    ):
        query_res = await async_client.post(
            f"/api/v1/sessions/{session_id}/queries/",
            json={"text": "Strategic cloud platform selection for enterprise AI", "mode": "deep"}
        )
    assert query_res.status_code == 201
    query_id = query_res.json()["id"]

    # 3. Trigger Decision Analysis
    decision_payload = {
        "query_id": query_id,
        "alternatives": [
            {
                "id": "aws",
                "name": "Amazon Web Services",
                "pros": ["Extensive AI services ecosystem", "High availability"],
                "cons": ["Complex pricing structure"],
                "scores": {"c1": 0.9, "c2": 0.95, "c3": 0.7}
            },
            {
                "id": "gcp",
                "name": "Google Cloud Platform",
                "pros": ["State of the art AI/TPU infrastructure", "Vertex AI"],
                "cons": ["Market share trailing AWS"],
                "scores": {"c1": 0.85, "c2": 0.80, "c3": 0.85}
            }
        ],
        "criteria": [
            {"id": "c1", "name": "AI & ML Capabilities", "weight": 0.5},
            {"id": "c2", "name": "Infrastructure Reliability", "weight": 0.3},
            {"id": "c3", "name": "Cost Efficiency", "weight": 0.2}
        ],
        "scenarios": [
            {"name": "Best Case", "probability": 0.3, "description": "Rapid AI workload adoption"},
            {"name": "Base Case", "probability": 0.5, "description": "Steady enterprise growth"},
            {"name": "Worst Case", "probability": 0.2, "description": "Budget cutbacks"}
        ]
    }

    create_res = await async_client.post(f"/api/v1/queries/{query_id}/decisions", json=decision_payload)
    assert create_res.status_code == 201
    decision_data = create_res.json()
    decision_id = decision_data["id"]

    assert decision_data["recommendation"] is not None
    assert decision_data["confidence"] > 0.0
    assert len(decision_data["alternatives"]) == 2
    assert len(decision_data["criteria"]) == 3

    # 4. List Query Decisions
    list_res = await async_client.get(f"/api/v1/queries/{query_id}/decisions")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 5. Fetch Single Decision
    get_res = await async_client.get(f"/api/v1/decisions/{decision_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == decision_id

    # 6. Re-run Sensitivity Analysis
    sens_res = await async_client.post(
        f"/api/v1/decisions/{decision_id}/sensitivity",
        json={"weight_delta": 0.01}
    )
    assert sens_res.status_code == 200
    assert "sensitivity_analysis" in sens_res.json()

    # 7. Re-run Scenario Analysis
    scenario_res = await async_client.post(
        f"/api/v1/decisions/{decision_id}/scenarios",
        json={
            "scenarios": [
                {"name": "Bull Market", "probability": 0.6},
                {"name": "Bear Market", "probability": 0.4}
            ]
        }
    )
    assert scenario_res.status_code == 200
    assert "scenarios" in scenario_res.json()
