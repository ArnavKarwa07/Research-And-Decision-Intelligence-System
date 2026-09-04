"""Unit tests for Phase 12 Continuous Intelligence DB Models and Pydantic Schemas."""
import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.models.monitoring import (
    MonitoringJob,
    ResearchBaselineSnapshot,
    MonitoringExecutionLog,
    DecisionAlert,
    ScheduleType,
    MonitoringJobStatus,
    ExecutionLogStatus,
    MaterialityLevel,
    AlertSeverity,
    AlertStatus,
    WebhookStatus,
)
from app.models.project_memory import (
    ProjectMemoryItem,
    ResearchHeuristics,
    ResearchHeuristic,
    MemoryType,
    ValidityStatus,
    HumanApprovalStatus,
)
from app.schemas.monitoring import (
    MonitoringJobCreate,
    MonitoringJobResponse,
    MonitoringJobUpdate,
    BaselineSnapshotCreate,
    BaselineSnapshotResponse,
    MonitoringExecutionLogResponse,
    DecisionAlertResponse,
    MaterialityScoreBreakdown,
)
from app.schemas.project_memory import (
    ProjectMemoryItemCreate,
    ProjectMemoryItemResponse,
    ProjectMemoryItemUpdate,
    ResearchHeuristicCreate,
    ResearchHeuristicResponse,
    ProjectMemoryContext,
)
from app.agents.agent_contracts import (
    MonitoringAgentInput,
    MonitoringAgentOutput,
    MemoryAgentInput,
    MemoryAgentOutput,
)


def test_monitoring_models_instantiation():
    """Test model instantiations for monitoring models."""
    snapshot = ResearchBaselineSnapshot(
        snapshot_label="v1-baseline",
        claims_snapshot=[{"claim_id": "c1", "text": "Claim 1"}],
        sources_snapshot=[{"source_id": "s1", "url": "https://example.com"}],
        assumptions_snapshot=[{"assumption": "Market grows 10%"}],
        decision_snapshot={"recommendation": "Option A"},
    )
    assert isinstance(snapshot.id, uuid.UUID)
    assert snapshot.snapshot_label == "v1-baseline"
    assert len(snapshot.claims_snapshot) == 1

    job = MonitoringJob(
        name="Daily Competitor Monitor",
        schedule_type=ScheduleType.CRON.value,
        cron_expression="0 0 * * *",
        alert_threshold=0.6,
        status=MonitoringJobStatus.ACTIVE.value,
        baseline_snapshot_id=snapshot.id,
        metadata={"tags": ["crypto", "tech"]},
    )
    assert isinstance(job.id, uuid.UUID)
    assert job.name == "Daily Competitor Monitor"
    assert job.schedule_type == "CRON"
    assert job.alert_threshold == 0.6
    assert job.metadata_ == {"tags": ["crypto", "tech"]}

    execution_log = MonitoringExecutionLog(
        job_id=job.id,
        status=ExecutionLogStatus.ALERT_TRIGGERED.value,
        materiality_score=0.75,
        materiality_level=MaterialityLevel.HIGH.value,
        delta_summary={"new_claims": 2},
        alert_triggered=True,
        execution_duration_seconds=3.5,
    )
    assert isinstance(execution_log.id, uuid.UUID)
    assert execution_log.job_id == job.id
    assert execution_log.materiality_score == 0.75
    assert execution_log.alert_triggered is True
    assert execution_log.executed_at is not None

    alert = DecisionAlert(
        job_id=job.id,
        execution_log_id=execution_log.id,
        materiality_score=0.75,
        severity=AlertSeverity.HIGH.value,
        title="High Materiality Delta",
        message="Competitor dropped price by 20%",
        payload={"delta": "20%"},
        status=AlertStatus.UNREAD.value,
        webhook_status=WebhookStatus.NONE.value,
    )
    assert isinstance(alert.id, uuid.UUID)
    assert alert.severity == "HIGH"
    assert alert.title == "High Materiality Delta"


def test_project_memory_models_instantiation():
    """Test model instantiations for project memory models."""
    memory_item = ProjectMemoryItem(
        memory_type=MemoryType.FACT.value,
        key="market_size_2025",
        summary="Global TAM for AI decision tools is $50B in 2025.",
        content={"tam_usd": 50000000000},
        confidence=0.95,
        validity_status=ValidityStatus.ACTIVE.value,
        human_approval_status=HumanApprovalStatus.APPROVED.value,
        tags=["market", "tam"],
    )
    assert isinstance(memory_item.id, uuid.UUID)
    assert memory_item.key == "market_size_2025"
    assert memory_item.memory_type == "FACT"
    assert memory_item.confidence == 0.95

    heuristics = ResearchHeuristics(
        domain="fintech",
        untrusted_domains=["spam-finance.com"],
        effective_query_templates=["{company} Q4 earnings report"],
        verified_tool_patterns=[{"tools": ["sec_edgar", "calculator"]}],
        failure_modes=[{"reason": "Paywall on news sites"}],
    )
    assert isinstance(heuristics.id, uuid.UUID)
    assert heuristics.domain == "fintech"
    assert "spam-finance.com" in heuristics.untrusted_domains
    assert ResearchHeuristic is ResearchHeuristics


def test_monitoring_pydantic_schemas():
    """Test Pydantic schema validation for monitoring schemas."""
    create_schema = MonitoringJobCreate(
        name="Weekly Monitor",
        schedule_type="INTERVAL",
        interval_seconds=86400,
        alert_threshold=0.4,
        webhook_url="https://hooks.slack.com/services/123",
        metadata={"env": "prod"},
    )
    assert create_schema.name == "Weekly Monitor"
    assert create_schema.interval_seconds == 86400

    job_id = uuid.uuid4()
    job_orm = MonitoringJob(
        id=job_id,
        name="Weekly Monitor",
        schedule_type="INTERVAL",
        interval_seconds=86400,
        status="ACTIVE",
        alert_threshold=0.4,
        webhook_url="https://hooks.slack.com/services/123",
        metadata_={"env": "prod"},
    )
    resp_schema = MonitoringJobResponse.model_validate(job_orm)
    assert resp_schema.id == job_id
    assert resp_schema.metadata_ == {"env": "prod"}
    assert resp_schema.metadata == {"env": "prod"}

    breakdown = MaterialityScoreBreakdown(
        claims_delta_score=0.2,
        sources_delta_score=0.1,
        assumptions_delta_score=0.3,
        recommendation_flip_score=0.0,
        total_score=0.6,
        materiality_level=MaterialityLevel.HIGH.value,
    )
    assert breakdown.total_score == 0.6
    assert breakdown.materiality_level == "HIGH"


def test_project_memory_pydantic_schemas():
    """Test Pydantic schema validation for project memory schemas."""
    item_create = ProjectMemoryItemCreate(
        key="cost_per_token",
        summary="LLM token cost assumptions for 2026",
        content={"prompt_cost": 0.0015, "completion_cost": 0.002},
        confidence=0.9,
        memory_type=MemoryType.REUSABLE_ASSUMPTION.value,
        tags=["llm", "cost"],
    )
    assert item_create.key == "cost_per_token"
    assert item_create.confidence == 0.9

    ctx = ProjectMemoryContext(
        active_facts=[],
        prior_conclusions=[],
        reusable_assumptions=[],
        lessons_learned=[],
        heuristics=None,
    )
    assert ctx.active_facts == []


def test_agent_contracts():
    """Test Agent contracts for MonitoringAgent and MemoryAgent."""
    job_id = str(uuid.uuid4())
    mon_in = MonitoringAgentInput(job_id=job_id, query_id=str(uuid.uuid4()), alert_threshold=0.5)
    assert mon_in.job_id == job_id
    assert mon_in.token_budget == 20000

    mon_out = MonitoringAgentOutput(
        job_id=job_id,
        execution_log_id=str(uuid.uuid4()),
        status="ALERT_TRIGGERED",
        materiality_score=0.8,
        materiality_level="HIGH",
        alert_triggered=True,
    )
    assert mon_out.status == "ALERT_TRIGGERED"
    assert mon_out.alert_triggered is True

    mem_in = MemoryAgentInput(action="RETRIEVE", domain="healthcare")
    assert mem_in.action == "RETRIEVE"
    assert mem_in.domain == "healthcare"
    assert mem_in.retry_limit == 2

    mem_out = MemoryAgentOutput(is_success=True, action_performed="RETRIEVE", items=[])
    assert mem_out.is_success is True


# --- Adversarial & Vulnerability Edge Case Tests ---

def test_cron_expression_validation():
    """Adversarial test: Valid and invalid cron expressions."""
    # Valid 5-field cron
    job_valid = MonitoringJobCreate(
        name="Valid Cron",
        schedule_type="CRON",
        cron_expression="0 0 * * *",
    )
    assert job_valid.cron_expression == "0 0 * * *"

    # Valid shorthand
    job_shorthand = MonitoringJobCreate(
        name="Shorthand Cron",
        schedule_type="CRON",
        cron_expression="@daily",
    )
    assert job_shorthand.cron_expression == "@daily"

    # Missing cron expression when schedule_type == CRON
    with pytest.raises(ValidationError) as exc_info:
        MonitoringJobCreate(
            name="Missing Cron",
            schedule_type="CRON",
            cron_expression=None,
        )
    assert "cron_expression is required" in str(exc_info.value)

    # Invalid field count (4 fields)
    with pytest.raises(ValidationError) as exc_info:
        MonitoringJobCreate(
            name="Invalid Cron 4 fields",
            schedule_type="CRON",
            cron_expression="0 0 * *",
        )
    assert "Cron expression must contain exactly 5 fields" in str(exc_info.value)


def test_webhook_url_security_validation():
    """Adversarial test: Webhook URL validation against SSRF and malicious schemes."""
    # Valid http / https URLs
    job_http = MonitoringJobCreate(
        name="HTTP Webhook",
        schedule_type="INTERVAL",
        interval_seconds=600,
        webhook_url="http://hooks.slack.com/services/abc",
    )
    assert job_http.webhook_url == "http://hooks.slack.com/services/abc"

    job_https = MonitoringJobCreate(
        name="HTTPS Webhook",
        schedule_type="INTERVAL",
        interval_seconds=600,
        webhook_url="https://hooks.slack.com/services/abc",
    )
    assert job_https.webhook_url == "https://hooks.slack.com/services/abc"

    # Invalid schemes: javascript, file, ftp, malformed
    for invalid_url in ["javascript:alert(1)", "file:///etc/passwd", "ftp://example.com", "not-a-url"]:
        with pytest.raises(ValidationError) as exc_info:
            MonitoringJobCreate(
                name="Malicious Webhook",
                schedule_type="INTERVAL",
                interval_seconds=600,
                webhook_url=invalid_url,
            )
        assert "http:// or https://" in str(exc_info.value)


def test_enum_validation_rejection():
    """Adversarial test: Rejection of invalid enum strings."""
    # Invalid schedule_type
    with pytest.raises(ValidationError):
        MonitoringJobCreate(name="Bad Schedule", schedule_type="INVALID_TYPE")

    # Invalid job status
    with pytest.raises(ValidationError):
        MonitoringJobUpdate(status="NON_EXISTENT_STATUS")

    # Invalid memory_type
    with pytest.raises(ValidationError):
        ProjectMemoryItemCreate(key="k", summary="s", memory_type="INVALID_MEMORY")

    # Invalid validity_status
    with pytest.raises(ValidationError):
        ProjectMemoryItemCreate(key="k", summary="s", validity_status="BAD_VALIDITY")

    # Invalid human_approval_status
    with pytest.raises(ValidationError):
        ProjectMemoryItemCreate(key="k", summary="s", human_approval_status="BAD_APPROVAL")

    # Invalid Agent action
    with pytest.raises(ValidationError):
        MemoryAgentInput(action="DROP_DATABASE")

    # Invalid AgentOutput status
    with pytest.raises(ValidationError):
        MonitoringAgentOutput(job_id="j1", execution_log_id="l1", status="UNKNOWN_STATUS")


def test_float_range_bounds_validation():
    """Adversarial test: Float bounds validation for alert_threshold and materiality_score."""
    with pytest.raises(ValidationError):
        MonitoringJobCreate(name="Job", schedule_type="INTERVAL", interval_seconds=60, alert_threshold=-0.1)

    with pytest.raises(ValidationError):
        MonitoringJobCreate(name="Job", schedule_type="INTERVAL", interval_seconds=60, alert_threshold=1.5)

    with pytest.raises(ValidationError):
        ProjectMemoryItemCreate(key="k", summary="s", confidence=2.0)

    with pytest.raises(ValidationError):
        MaterialityScoreBreakdown(total_score=-0.5)


def test_null_database_value_coercion():
    """Adversarial test: Handling of NULL database values in response schemas."""
    # ResearchBaselineSnapshot with NULL JSON columns
    snap = ResearchBaselineSnapshot(snapshot_label="null-test")
    snap.claims_snapshot = None
    snap.sources_snapshot = None
    snap.assumptions_snapshot = None
    snap.decision_snapshot = None
    snap_resp = BaselineSnapshotResponse.model_validate(snap)
    assert snap_resp.claims_snapshot == []
    assert snap_resp.sources_snapshot == []
    assert snap_resp.assumptions_snapshot == []
    assert snap_resp.decision_snapshot == {}

    # MonitoringExecutionLog with NULL delta_summary and uncommitted executed_at
    log = MonitoringExecutionLog(job_id=uuid.uuid4())
    log.delta_summary = None
    log_resp = MonitoringExecutionLogResponse.model_validate(log)
    assert log_resp.delta_summary == {}
    assert log_resp.executed_at is not None

    # DecisionAlert with NULL payload
    alert = DecisionAlert(job_id=uuid.uuid4(), title="t", message="m")
    alert.payload = None
    alert_resp = DecisionAlertResponse.model_validate(alert)
    assert alert_resp.payload == {}

    # ProjectMemoryItem with NULL content and tags
    mem = ProjectMemoryItem(key="k", summary="s", memory_type="FACT")
    mem.content = None
    mem.tags = None
    mem_resp = ProjectMemoryItemResponse.model_validate(mem)
    assert mem_resp.content == {}
    assert mem_resp.tags == []

    # ResearchHeuristics with NULL list fields
    h = ResearchHeuristics(domain="fintech")
    h.untrusted_domains = None
    h.effective_query_templates = None
    h.verified_tool_patterns = None
    h.failure_modes = None
    h_resp = ResearchHeuristicResponse.model_validate(h)
    assert h_resp.untrusted_domains == []
    assert h_resp.effective_query_templates == []
    assert h_resp.verified_tool_patterns == []
    assert h_resp.failure_modes == []


def test_monitoring_job_response_alias_serialization():
    """Adversarial test: Verify serialize_by_alias=True outputs 'metadata' key in JSON/dict."""
    job_id = uuid.uuid4()
    job = MonitoringJob(id=job_id, name="Alias Job", metadata_={"env": "staging"})
    job.metadata_ = None  # test NULL handling too
    resp = MonitoringJobResponse.model_validate(job)
    
    # model_dump should include 'metadata' key
    d = resp.model_dump()
    assert "metadata" in d
    assert d["metadata"] == {}

    # JSON output should have "metadata" key
    json_str = resp.model_dump_json()
    assert '"metadata":{}' in json_str or '"metadata": {}' in json_str or '"metadata":' in json_str


def test_agents_md_compliance():
    """Adversarial test: Verify AGENTS.md rule compliance."""
    # AGENTS.md Rule 3: Retry policy required on input contract
    mem_input = MemoryAgentInput(action="RETRIEVE")
    assert hasattr(mem_input, "retry_limit")
    assert mem_input.retry_limit >= 0

    mon_input = MonitoringAgentInput(job_id="j1")
    assert hasattr(mon_input, "retry_limit")
    assert mon_input.retry_limit >= 0

