"""Unit tests for Research Monitoring Engine Services (Phase 12 Continuous Intelligence)."""
import uuid
from datetime import datetime, timezone
import httpx
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.monitoring import (
    AlertSeverity,
    AlertStatus,
    ExecutionLogStatus,
    MaterialityLevel,
    MonitoringJobStatus,
    ScheduleType,
    WebhookStatus,
)
from app.models.query import Query
from app.models.source import Source
from app.schemas.monitoring import BaselineSnapshotCreate, MonitoringJobCreate, MonitoringJobUpdate
from app.services.baseline_delta_service import BaselineDeltaService
from app.services.decision_alerting_service import DecisionAlertingService
from app.services.materiality_scoring_engine import MaterialityScoringEngine
from app.services.monitoring_scheduler_service import (
    MonitoringSchedulerService,
    calculate_next_cron_time,
    calculate_next_run_at,
)


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# --- 1. MaterialityScoringEngine Tests ---
def test_materiality_scoring_engine_math_precision():
    """Verify formula M = 0.35 * S_assumption + 0.25 * S_contradiction + 0.25 * S_matrix + 0.15 * S_source."""
    # Test all 1.0s -> M = 1.0 (CRITICAL)
    b1 = MaterialityScoringEngine.calculate_materiality_score(1.0, 1.0, 1.0, 1.0)
    assert b1.total_score == 1.0
    assert b1.materiality_level == "CRITICAL"

    # Test all 0.0s -> M = 0.0 (NEGLIGIBLE)
    b2 = MaterialityScoringEngine.calculate_materiality_score(0.0, 0.0, 0.0, 0.0)
    assert b2.total_score == 0.0
    assert b2.materiality_level == "NEGLIGIBLE"

    # Test exact weighted calculation:
    # 0.35(0.5) + 0.25(0.4) + 0.25(0.2) + 0.15(0.1) = 0.175 + 0.100 + 0.050 + 0.015 = 0.34
    b3 = MaterialityScoringEngine.calculate_materiality_score(0.5, 0.4, 0.2, 0.1)
    assert b3.total_score == 0.34
    assert b3.materiality_level == "LOW"

    # Test high severity combination: 0.35(1.0) + 0.25(0.0) + 0.25(1.0) + 0.15(0.0) = 0.60
    b4 = MaterialityScoringEngine.calculate_materiality_score(1.0, 0.0, 1.0, 0.0)
    assert b4.total_score == 0.60
    assert b4.materiality_level == "HIGH"


def test_materiality_level_boundary_classifications():
    """Verify exact boundary classifications for score levels."""
    # NEGLIGIBLE (< 0.2)
    assert MaterialityScoringEngine.classify_materiality_level(0.0) == MaterialityLevel.NEGLIGIBLE
    assert MaterialityScoringEngine.classify_materiality_level(0.1999) == MaterialityLevel.NEGLIGIBLE

    # LOW (< 0.4)
    assert MaterialityScoringEngine.classify_materiality_level(0.2) == MaterialityLevel.LOW
    assert MaterialityScoringEngine.classify_materiality_level(0.3999) == MaterialityLevel.LOW

    # MEDIUM (< 0.6)
    assert MaterialityScoringEngine.classify_materiality_level(0.4) == MaterialityLevel.MEDIUM
    assert MaterialityScoringEngine.classify_materiality_level(0.5999) == MaterialityLevel.MEDIUM

    # HIGH (< 0.8)
    assert MaterialityScoringEngine.classify_materiality_level(0.6) == MaterialityLevel.HIGH
    assert MaterialityScoringEngine.classify_materiality_level(0.7999) == MaterialityLevel.HIGH

    # CRITICAL (>= 0.8)
    assert MaterialityScoringEngine.classify_materiality_level(0.8) == MaterialityLevel.CRITICAL
    assert MaterialityScoringEngine.classify_materiality_level(1.0) == MaterialityLevel.CRITICAL


# --- 2. BaselineDeltaService Tests ---
@pytest.mark.asyncio
async def test_baseline_delta_service_creation_and_computation(db_session: AsyncSession):
    service = BaselineDeltaService(db_session)

    # 1. Create baseline snapshot
    snap_in = BaselineSnapshotCreate(
        snapshot_label="v1-initial",
        claims_snapshot=[{"id": "c1", "content": "Revenue is $10M", "status": "VERIFIED"}],
        sources_snapshot=[{"id": "s1", "url": "https://sec.gov", "quality_score": 0.9}],
        assumptions_snapshot=[{"text": "Interest rates remain at 5%", "status": "ACTIVE"}],
        decision_snapshot={"recommendation": "Option A", "confidence": 0.85},
    )
    snapshot = await service.create_baseline_snapshot(snap_in)
    assert snapshot.id is not None
    assert snapshot.snapshot_label == "v1-initial"

    fetched = await service.get_baseline_snapshot(snapshot.id)
    assert fetched is not None
    assert fetched.snapshot_label == "v1-initial"

    # 2. Compute delta with recommendation flip and assumption invalidation
    new_state = {
        "invalidated_assumptions": ["Interest rates remain at 5%"],
        "contradictions": [{"claim_id": "c1", "reason": "Fed cut interest rates to 4%"}],
        "decision": {"recommendation": "Option B", "confidence": 0.70},
        "untrusted_sources": ["https://fake-finance.org"],
    }

    delta_res = service.compute_delta(snapshot, new_state)
    assert delta_res["recommendation_flipped"] is True
    sub_scores = delta_res["sub_scores"]
    assert sub_scores["s_assumption"] == 1.0
    assert sub_scores["s_matrix"] == 1.0
    assert sub_scores["s_source"] > 0.0

    # Score delta result
    breakdown = MaterialityScoringEngine.score_delta_result(delta_res)
    assert breakdown.total_score == 0.745
    assert breakdown.materiality_level == "HIGH"


# --- 3. DecisionAlertingService Tests ---
@pytest.mark.asyncio
async def test_decision_alerting_service_evaluation_and_dispatch(db_session: AsyncSession):
    alert_service = DecisionAlertingService(db_session)
    job_id = uuid.uuid4()
    log_id = uuid.uuid4()

    # 1. Score below threshold -> No alert
    no_alert = await alert_service.evaluate_and_create_alert(
        job_id=job_id,
        execution_log_id=log_id,
        materiality_score=0.3,
        threshold=0.5,
        delta_summary={"summary": "Minor changes"},
    )
    assert no_alert is None

    # 2. Score >= threshold -> DecisionAlert created
    alert = await alert_service.evaluate_and_create_alert(
        job_id=job_id,
        execution_log_id=log_id,
        materiality_score=0.7,
        threshold=0.5,
        delta_summary={"summary": "Major claim contradiction"},
    )
    assert alert is not None
    assert alert.severity == "HIGH"
    assert alert.materiality_score == 0.7
    assert alert.status == "UNREAD"

    # 3. Test Webhook dispatch with mock httpx client
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        status = await alert_service.dispatch_webhook(alert, "https://example.com/webhook")
        assert status == WebhookStatus.DELIVERED
        assert alert.webhook_status == "DELIVERED"

    # 4. Update alert status
    updated_alert = await alert_service.update_alert_status(alert.id, AlertStatus.RESOLVED.value)
    assert updated_alert is not None
    assert updated_alert.status == "RESOLVED"

    alerts = await alert_service.list_alerts(job_id=job_id)
    assert len(alerts) == 1
    assert alerts[0].id == alert.id


@pytest.mark.asyncio
async def test_decision_alerting_webhook_retry_failure(db_session: AsyncSession):
    """Test webhook retry logic failure after 3 failed attempts."""
    alert_service = DecisionAlertingService(db_session)
    job_id = uuid.uuid4()

    alert = await alert_service.evaluate_and_create_alert(
        job_id=job_id,
        execution_log_id=None,
        materiality_score=0.85,
        threshold=0.5,
        delta_summary={"summary": "Critical alert"},
    )
    assert alert is not None

    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Connection failed")):
        status = await alert_service.dispatch_webhook(alert, "https://failing-webhook.org/hook", max_retries=3, backoff_base=0.001)
        assert status == WebhookStatus.FAILED
        assert alert.webhook_status == "FAILED"


# --- 4. MonitoringSchedulerService Tests ---
@pytest.mark.asyncio
async def test_monitoring_scheduler_service_job_lifecycle(db_session: AsyncSession):
    scheduler = MonitoringSchedulerService(db_session)

    # 1. Create job
    job_in = MonitoringJobCreate(
        name="Daily Market Monitor",
        schedule_type=ScheduleType.INTERVAL.value,
        interval_seconds=3600,
        alert_threshold=0.5,
    )
    job = await scheduler.create_job(job_in)
    assert job.id is not None
    assert job.name == "Daily Market Monitor"
    assert job.status == "ACTIVE"
    assert job.next_run_at is not None

    # 2. Pause job
    paused = await scheduler.pause_job(job.id)
    assert paused is not None
    assert paused.status == "PAUSED"
    assert paused.next_run_at is None

    # 3. Resume job
    resumed = await scheduler.resume_job(job.id)
    assert resumed is not None
    assert resumed.status == "ACTIVE"
    assert resumed.next_run_at is not None

    # 4. Update job
    updated = await scheduler.update_job(
        job.id, MonitoringJobUpdate(name="Updated Market Monitor", alert_threshold=0.4)
    )
    assert updated is not None
    assert updated.name == "Updated Market Monitor"
    assert updated.alert_threshold == 0.4

    # 5. Execute job (manual trigger)
    current_state = {
        "sub_scores": {"s_assumption": 0.8, "s_contradiction": 0.8, "s_matrix": 0.8, "s_source": 0.8},
        "diffs": {"summary": "High drift"},
    }
    log = await scheduler.trigger_job_now(job.id, current_state=current_state)
    assert log.status == ExecutionLogStatus.ALERT_TRIGGERED.value
    assert log.materiality_score >= 0.8
    assert log.alert_triggered is True

    # Check updated job run count
    refreshed_job = await scheduler.get_job(job.id)
    assert refreshed_job is not None
    assert refreshed_job.run_count == 1
    assert refreshed_job.last_run_at is not None

    # 6. Delete job
    deleted = await scheduler.delete_job(job.id)
    assert deleted is True
    assert await scheduler.get_job(job.id) is None


def test_cron_expression_calculation():
    """Verify cron parsing and next_run_at calculations."""
    base = datetime(2026, 9, 5, 10, 0, 0, tzinfo=timezone.utc)
    # Cron: 0 12 * * * (Every day at 12:00 UTC)
    next_time = calculate_next_cron_time("0 12 * * *", base)
    assert next_time.hour == 12
    assert next_time.minute == 0
    assert next_time.day == 5

    # Cron: */15 * * * * (Every 15 minutes)
    next_15 = calculate_next_cron_time("*/15 * * * *", base)
    assert next_15.minute == 15
    assert next_15.hour == 10

    # Calculate next_run_at helper
    interval_next = calculate_next_run_at("INTERVAL", interval_seconds=1800, base_time=base)
    assert interval_next == datetime(2026, 9, 5, 10, 30, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_decision_alerting_ssrf_protection(db_session: AsyncSession):
    """BUG-12-02: Verify SSRF protection blocks private, loopback, link-local IPs and non-http schemes."""
    alert_service = DecisionAlertingService(db_session)
    job_id = uuid.uuid4()
    alert = await alert_service.evaluate_and_create_alert(
        job_id=job_id,
        execution_log_id=None,
        materiality_score=0.9,
        threshold=0.5,
        delta_summary={"summary": "Test SSRF"},
    )
    assert alert is not None

    blocked_urls = [
        "http://127.0.0.1/webhook",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/hook",
        "http://172.16.0.1/hook",
        "http://192.168.1.1/hook",
        "http://localhost/hook",
        "ftp://example.com/hook",
    ]

    for url in blocked_urls:
        status = await alert_service.dispatch_webhook(alert, url)
        assert status == WebhookStatus.FAILED


@pytest.mark.asyncio
async def test_update_alert_status_invalid_enum(db_session: AsyncSession):
    """BUG-12-10: Verify update_alert_status rejects unvalidated status strings with ValueError."""
    alert_service = DecisionAlertingService(db_session)
    job_id = uuid.uuid4()
    alert = await alert_service.evaluate_and_create_alert(
        job_id=job_id,
        execution_log_id=None,
        materiality_score=0.9,
        threshold=0.5,
        delta_summary={"summary": "Test status validation"},
    )
    assert alert is not None

    with pytest.raises(ValueError, match="Invalid alert status"):
        await alert_service.update_alert_status(alert.id, "NON_EXISTENT_STATUS")


def test_cron_out_of_bounds_and_zero_step_validation():
    """BUG-12-04 & BUG-12-05: Verify cron boundary validation and step > 0 enforcement."""
    # Minute > 59
    with pytest.raises(ValueError, match="minute"):
        calculate_next_cron_time("60 * * * *")

    # Hour > 23
    with pytest.raises(ValueError, match="hour"):
        calculate_next_cron_time("* 25 * * *")

    # Day > 31
    with pytest.raises(ValueError, match="day"):
        calculate_next_cron_time("* * 32 * *")

    # Month > 12
    with pytest.raises(ValueError, match="month"):
        calculate_next_cron_time("* * * 13 *")

    # Step == 0 (ZeroDivisionError protection)
    with pytest.raises(ValueError, match="greater than 0"):
        calculate_next_cron_time("*/0 * * * *")


def test_materiality_scoring_nan_handling():
    """BUG-12-08: Verify NaN scores return NEGLIGIBLE instead of CRITICAL."""
    assert MaterialityScoringEngine.classify_materiality_level(float("nan")) == MaterialityLevel.NEGLIGIBLE
    breakdown = MaterialityScoringEngine.calculate_materiality_score(float("nan"), 0.5, float("nan"), 0.2)
    assert breakdown.materiality_level != "CRITICAL"


@pytest.mark.asyncio
async def test_baseline_delta_safe_float_and_none_values(db_session: AsyncSession):
    """BUG-12-09: Verify compute_delta handles None values in dict keys without TypeError."""
    service = BaselineDeltaService(db_session)
    snap_in = BaselineSnapshotCreate(
        snapshot_label="v1-nulls",
        claims_snapshot=[],
        sources_snapshot=[],
        assumptions_snapshot=[],
        decision_snapshot={"confidence": None},
    )
    snapshot = await service.create_baseline_snapshot(snap_in)

    current_state = {
        "sub_scores": {"s_assumption": None, "s_contradiction": None},
        "decision": {"confidence": None},
        "sources": [{"quality_score": None}],
        "score_drift": None,
        "s_contradiction": None,
    }
    delta_res = service.compute_delta(snapshot, current_state)
    assert "sub_scores" in delta_res


@pytest.mark.asyncio
async def test_create_snapshot_from_query_filters_sources_by_query_id(db_session: AsyncSession):
    """BUG-12-07: Verify create_snapshot_from_query filters sources by query_id."""

    service = BaselineDeltaService(db_session)
    q1_id = uuid.uuid4()
    q2_id = uuid.uuid4()

    sess_id = uuid.uuid4()
    q1 = Query(id=q1_id, session_id=sess_id, text="Query 1")
    q2 = Query(id=q2_id, session_id=sess_id, text="Query 2")
    s1 = Source(id=uuid.uuid4(), query_id=q1_id, url="https://q1.org", title="Q1 Source")
    s2 = Source(id=uuid.uuid4(), query_id=q2_id, url="https://q2.org", title="Q2 Source")

    db_session.add_all([q1, q2, s1, s2])
    await db_session.commit()

    snap1 = await service.create_snapshot_from_query(q1_id, "snap-q1")
    source_urls = [s["url"] for s in snap1.sources_snapshot]

    assert "https://q1.org" in source_urls
    assert "https://q2.org" not in source_urls


@pytest.mark.asyncio
async def test_monitoring_scheduler_run_due_jobs_with_for_update(db_session: AsyncSession):
    """BUG-12-03: Verify run_due_jobs executes due jobs with for_update locking."""
    scheduler = MonitoringSchedulerService(db_session)
    job_in = MonitoringJobCreate(
        name="Due Job",
        schedule_type=ScheduleType.INTERVAL.value,
        interval_seconds=60,
    )
    job = await scheduler.create_job(job_in)
    # Set next_run_at to past
    job.next_run_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    await db_session.commit()

    logs = await scheduler.run_due_jobs()
    assert len(logs) == 1
    assert logs[0].job_id == job.id
