"""API unit tests for Phase 12 Continuous Intelligence, Monitoring & Project Memory REST Endpoints."""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.dependencies import get_db
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def api_client(async_session: AsyncSession):
    async def _get_db_override():
        yield async_session

    app.dependency_overrides[get_db] = _get_db_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# --- 1. Monitoring REST Endpoints Tests ---
@pytest.mark.asyncio
async def test_monitoring_jobs_crud_and_run(api_client: AsyncClient):
    # 1. Create Baseline Snapshot
    snap_payload = {
        "snapshot_label": "v1-baseline",
        "claims_snapshot": [{"id": "c1", "content": "Initial revenue $5M"}],
        "assumptions_snapshot": [{"text": "Market share grows by 10%"}],
    }
    resp = await api_client.post("/api/v1/monitoring/baselines", json=snap_payload)
    assert resp.status_code == 201
    baseline_data = resp.json()
    baseline_id = baseline_data["id"]

    # Get baseline snapshot
    resp = await api_client.get(f"/api/v1/monitoring/baselines/{baseline_id}")
    assert resp.status_code == 200
    assert resp.json()["snapshot_label"] == "v1-baseline"

    # Get non-existent baseline
    resp = await api_client.get(f"/api/v1/monitoring/baselines/{uuid.uuid4()}")
    assert resp.status_code == 404

    # 2. Create Monitoring Job
    job_payload = {
        "name": "Hourly Revenue Monitor",
        "schedule_type": "INTERVAL",
        "interval_seconds": 3600,
        "alert_threshold": 0.5,
        "baseline_snapshot_id": baseline_id,
    }
    resp = await api_client.post("/api/v1/monitoring/jobs", json=job_payload)
    assert resp.status_code == 201
    job_data = resp.json()
    job_id = job_data["id"]
    assert job_data["name"] == "Hourly Revenue Monitor"
    assert job_data["status"] == "ACTIVE"

    # 3. List Monitoring Jobs
    resp = await api_client.get("/api/v1/monitoring/jobs")
    assert resp.status_code == 200
    jobs_list = resp.json()
    assert len(jobs_list) >= 1

    # 4. Get Job Details
    resp = await api_client.get(f"/api/v1/monitoring/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id

    # 5. Patch (Update/Pause) Job
    resp = await api_client.patch(f"/api/v1/monitoring/jobs/{job_id}", json={"status": "PAUSED", "alert_threshold": 0.6})
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"
    assert resp.json()["alert_threshold"] == 0.6

    # 6. Trigger Job Run
    run_payload = {
        "current_state": {
            "sub_scores": {"s_assumption": 0.8, "s_contradiction": 0.8, "s_matrix": 0.8, "s_source": 0.8},
        }
    }
    resp = await api_client.post(f"/api/v1/monitoring/jobs/{job_id}/run", json=run_payload)
    assert resp.status_code == 200
    log_data = resp.json()
    assert log_data["job_id"] == job_id
    assert log_data["alert_triggered"] is True

    # 7. Get Job Execution Logs
    resp = await api_client.get(f"/api/v1/monitoring/jobs/{job_id}/logs")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1

    # 8. List Alerts & Acknowledge
    resp = await api_client.get(f"/api/v1/monitoring/alerts?job_id={job_id}")
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    resp = await api_client.post(f"/api/v1/monitoring/alerts/{alert_id}/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACKNOWLEDGED"

    # 9. Delete Job
    resp = await api_client.delete(f"/api/v1/monitoring/jobs/{job_id}")
    assert resp.status_code == 204

    resp = await api_client.get(f"/api/v1/monitoring/jobs/{job_id}")
    assert resp.status_code == 404


# --- 2. Project Memory REST Endpoints Tests ---
@pytest.mark.asyncio
async def test_project_memory_crud_approval_and_heuristics(api_client: AsyncClient):
    proj_id = str(uuid.uuid4())
    sess_id = str(uuid.uuid4())

    # 1. Create Fact Memory Item
    item_payload = {
        "project_id": proj_id,
        "session_id": sess_id,
        "memory_type": "FACT",
        "key": "tam_fact_key",
        "summary": "Global Market TAM is $100B",
        "confidence": 0.95,
        "human_approval_status": "APPROVED",
        "tags": ["market"],
    }
    resp = await api_client.post("/api/v1/memory/items", json=item_payload)
    assert resp.status_code == 201
    fact_data = resp.json()
    fact_id = fact_data["id"]
    assert fact_data["key"] == "tam_fact_key"

    # 2. Create Reusable Assumption Item (PENDING)
    assump_payload = {
        "project_id": proj_id,
        "session_id": sess_id,
        "memory_type": "REUSABLE_ASSUMPTION",
        "key": "interest_rate_assump",
        "summary": "Interest rates remain steady at 4%",
        "confidence": 0.8,
        "human_approval_status": "PENDING",
        "tags": ["macro"],
    }
    resp = await api_client.post("/api/v1/memory/items", json=assump_payload)
    assert resp.status_code == 201
    assump_data = resp.json()
    assump_id = assump_data["id"]
    assert assump_data["human_approval_status"] == "PENDING"

    # 3. List Memory Items with Filters
    resp = await api_client.get(f"/api/v1/memory/items?project_id={proj_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await api_client.get(f"/api/v1/memory/items?project_id={proj_id}&human_approval_status=PENDING")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == assump_id

    # 4. Get Single Item
    resp = await api_client.get(f"/api/v1/memory/items/{fact_id}")
    assert resp.status_code == 200
    assert resp.json()["key"] == "tam_fact_key"

    # 5. Patch Update Memory Item
    resp = await api_client.patch(f"/api/v1/memory/items/{fact_id}", json={"summary": "Updated Market TAM $120B"})
    assert resp.status_code == 200
    assert resp.json()["summary"] == "Updated Market TAM $120B"

    # 6. Approve Assumption (HITL)
    resp = await api_client.post(f"/api/v1/memory/items/{assump_id}/approve", json={"approval_status": "APPROVED"})
    assert resp.status_code == 200
    assert resp.json()["human_approval_status"] == "APPROVED"

    # 7. Create/Update Research Heuristics
    heur_payload = {
        "project_id": proj_id,
        "domain": "fintech",
        "untrusted_domains": ["fake-crypto-blog.com"],
        "effective_query_templates": ["{ticker} SEC 10-K filing"],
    }
    resp = await api_client.post("/api/v1/memory/heuristics", json=heur_payload)
    assert resp.status_code == 201
    heur_data = resp.json()
    assert heur_data["domain"] == "fintech"

    # Get Research Heuristics
    resp = await api_client.get(f"/api/v1/memory/heuristics?domain=fintech&project_id={proj_id}")
    assert resp.status_code == 200
    assert "fake-crypto-blog.com" in resp.json()["untrusted_domains"]

    # 8. Preview Context Injection
    inj_payload = {
        "project_id": proj_id,
        "session_id": sess_id,
        "domain": "fintech",
        "query_text": "Analyze fintech market baseline",
    }
    resp = await api_client.post("/api/v1/memory/inject-context", json=inj_payload)
    assert resp.status_code == 200
    preview = resp.json()
    assert "context" in preview
    assert "formatted_prompt_text" in preview
    assert "PERSISTENT PROJECT MEMORY CONTEXT" in preview["formatted_prompt_text"]
