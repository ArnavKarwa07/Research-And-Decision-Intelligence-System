"""Pytest test suite for Phase 11 Artifacts, Reports, & Export Packages."""
import io
import json
import uuid
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.models.base import Base
from app.models.session import Session as SessionModel
from app.models.query import Query as QueryModel
from app.models.decision import Decision as DecisionModel
from app.models.source import Source as SourceModel
from app.models.claim import Claim as ClaimModel
from app.models.artifact import Artifact as ArtifactModel
from app.services.artifact_service import ArtifactService
from app.services.export_package_service import ExportPackageService
from app.dependencies import get_db

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
async def test_data(async_session: AsyncSession):
    session_obj = SessionModel(title="Phase 11 Test Session")
    async_session.add(session_obj)
    await async_session.commit()
    await async_session.refresh(session_obj)

    query_obj = QueryModel(
        session_id=session_obj.id,
        text="Compare AWS vs GCP for ML workloads with $5k/mo budget limit",
        summary="Detailed comparison of AWS vs GCP for machine learning workloads.",
        confidence=0.88
    )
    async_session.add(query_obj)
    await async_session.commit()
    await async_session.refresh(query_obj)

    decision_obj = DecisionModel(
        query_id=query_obj.id,
        recommendation="Migrate primary training to GCP TPU/GPU instances while keeping data lake on AWS S3.",
        confidence=0.88,
        rationale="GCP offers 30% lower TPU instance pricing for LLM fine-tuning.",
        alternatives=[
            {"name": "GCP TPU Instances", "weighted_score": 0.88, "pros": ["30% lower cost"], "cons": ["Egress fees"]},
            {"name": "AWS EC2 P4d", "weighted_score": 0.76, "pros": ["Native S3 access"], "cons": ["Higher hourly rate"]}
        ],
        criteria=[
            {"name": "Total Cost", "weight": 0.40},
            {"name": "Performance", "weight": 0.35},
            {"name": "Operational Overhead", "weight": 0.25}
        ],
        key_risks=["Egress bandwidth cost spikes", "Team retraining"],
        assumptions=["Workload scales 20% YoY", "Budget remains fixed at $5k/mo"]
    )
    async_session.add(decision_obj)

    source_obj = SourceModel(
        url="https://cloud.google.com/tpu/pricing",
        title="GCP TPU Pricing Guide",
        publisher="Google Cloud",
        quality_score=0.92,
        source_type="web"
    )
    async_session.add(source_obj)

    claim_obj = ClaimModel(
        query_id=query_obj.id,
        content="GCP v4 TPU preemptible instances cost $1.35/hour per chip.",
        claim_type="FACT",
        confidence=0.95,
        status="verified"
    )

    async_session.add(claim_obj)

    await async_session.commit()
    return {"session": session_obj, "query": query_obj, "decision": decision_obj}


@pytest.mark.asyncio
async def test_artifact_model_creation(async_session: AsyncSession, test_data):
    query_obj = test_data["query"]
    artifact = ArtifactModel(
        query_id=query_obj.id,
        session_id=query_obj.session_id,
        artifact_type="decision_memo",
        title="Test Decision Memo",
        content_json={"test": True},
        markdown_content="# Test Memo",
        html_content="<h1>Test Memo</h1>"
    )
    async_session.add(artifact)
    await async_session.commit()
    await async_session.refresh(artifact)

    assert artifact.id is not None
    assert artifact.artifact_type == "decision_memo"
    assert artifact.query_id == query_obj.id


@pytest.mark.asyncio
async def test_artifact_service_decision_memo(async_session: AsyncSession, test_data):
    query_obj = test_data["query"]
    service = ArtifactService(async_session)

    memo = await service.generate_decision_memo(query_obj.id)
    assert memo.query_id == query_obj.id
    assert memo.artifact_type == "decision_memo"
    assert "Migrate primary training to GCP" in memo.executive_summary
    assert "# EXECUTIVE DECISION MEMO" in memo.markdown_content
    assert memo.html_content != ""


@pytest.mark.asyncio
async def test_artifact_service_research_report(async_session: AsyncSession, test_data):
    query_obj = test_data["query"]
    service = ArtifactService(async_session)

    report = await service.generate_research_report(query_obj.id)
    assert report.query_id == query_obj.id
    assert report.artifact_type == "research_report"
    assert "# FULL TECHNICAL RESEARCH REPORT" in report.markdown_content


@pytest.mark.asyncio
async def test_export_package_service_zip(async_session: AsyncSession, test_data):
    query_obj = test_data["query"]
    service = ExportPackageService(async_session)

    zip_buffer, filename = await service.generate_zip_package(query_obj.id)
    assert filename.startswith("radis_research_export_")
    assert filename.endswith(".zip")

    # Read zip entries
    with zipfile.ZipFile(zip_buffer, "r") as z:
        names = z.namelist()
        assert "decision_memo.md" in names
        assert "research_report.md" in names
        assert "executive_summary.html" in names
        assert "research_state.json" in names
        assert "sources_manifest.csv" in names
        assert "mcda_comparison.csv" in names

        state_json = json.loads(z.read("research_state.json"))
        assert state_json["query"]["id"] == str(query_obj.id)


@pytest.mark.asyncio
async def test_artifacts_api_endpoints(async_session: AsyncSession, test_data):
    query_obj = test_data["query"]

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Decision Memo Endpoint
        res = await client.get(f"/api/v1/queries/{query_obj.id}/artifacts/decision-memo")
        assert res.status_code == 200
        data = res.json()
        assert data["artifact_type"] == "decision_memo"

        # Comparison Table Endpoint
        res_table = await client.get(f"/api/v1/queries/{query_obj.id}/artifacts/comparison-table")
        assert res_table.status_code == 200
        table_data = res_table.json()
        assert "csv_spec" in table_data

        # ZIP Package Export Endpoint
        res_zip = await client.get(f"/api/v1/queries/{query_obj.id}/artifacts/export-package")
        assert res_zip.status_code == 200
        assert res_zip.headers["content-type"] == "application/zip"

    app.dependency_overrides.clear()
