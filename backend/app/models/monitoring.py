"""Database models for Phase 12 Continuous Intelligence & Decision Monitoring."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query
    from app.models.session import Session
    from app.models.decision import Decision


class ScheduleType(str, enum.Enum):
    """Schedule types for monitoring jobs."""
    CRON = "CRON"
    INTERVAL = "INTERVAL"
    EVENT_DRIVEN = "EVENT_DRIVEN"


class MonitoringJobStatus(str, enum.Enum):
    """Lifecycle statuses for monitoring jobs."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExecutionLogStatus(str, enum.Enum):
    """Execution log status outcomes."""
    SUCCESS = "SUCCESS"
    NO_CHANGE = "NO_CHANGE"
    FAILED = "FAILED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"


class MaterialityLevel(str, enum.Enum):
    """Materiality severity levels for deltas."""
    NEGLIGIBLE = "NEGLIGIBLE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertSeverity(str, enum.Enum):
    """Severity levels for decision alerts."""
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    """Status states for decision alerts."""
    UNREAD = "UNREAD"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class WebhookStatus(str, enum.Enum):
    """Webhook notification dispatch status."""
    NONE = "NONE"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class ResearchBaselineSnapshot(TimestampMixin, Base):
    """Database model representing a baseline snapshot of research claims, sources, assumptions, and decisions."""

    __tablename__ = "research_baseline_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    snapshot_label: Mapped[str] = mapped_column(String, nullable=False)
    claims_snapshot: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)
    sources_snapshot: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)
    assumptions_snapshot: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)
    decision_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    monitoring_jobs: Mapped[List["MonitoringJob"]] = relationship(
        "MonitoringJob", back_populates="baseline_snapshot"
    )

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "claims_snapshot" not in kwargs or kwargs["claims_snapshot"] is None:
            kwargs["claims_snapshot"] = []
        if "sources_snapshot" not in kwargs or kwargs["sources_snapshot"] is None:
            kwargs["sources_snapshot"] = []
        if "assumptions_snapshot" not in kwargs or kwargs["assumptions_snapshot"] is None:
            kwargs["assumptions_snapshot"] = []
        if "decision_snapshot" not in kwargs or kwargs["decision_snapshot"] is None:
            kwargs["decision_snapshot"] = {}
        super().__init__(**kwargs)


class MonitoringJob(TimestampMixin, Base):
    """Database model representing a scheduled monitoring job for continuous decision intelligence."""

    __tablename__ = "monitoring_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    baseline_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("research_baseline_snapshots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(30), nullable=False, default=ScheduleType.INTERVAL.value)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    interval_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=MonitoringJobStatus.ACTIVE.value, index=True)
    alert_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    baseline_snapshot: Mapped[Optional["ResearchBaselineSnapshot"]] = relationship(
        "ResearchBaselineSnapshot", back_populates="monitoring_jobs"
    )
    execution_logs: Mapped[List["MonitoringExecutionLog"]] = relationship(
        "MonitoringExecutionLog", back_populates="job", cascade="all, delete-orphan"
    )
    alerts: Mapped[List["DecisionAlert"]] = relationship(
        "DecisionAlert", back_populates="job", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "run_count" not in kwargs or kwargs["run_count"] is None:
            kwargs["run_count"] = 0
        if "alert_threshold" not in kwargs or kwargs["alert_threshold"] is None:
            kwargs["alert_threshold"] = 0.5
        if "schedule_type" not in kwargs or kwargs["schedule_type"] is None:
            kwargs["schedule_type"] = ScheduleType.INTERVAL.value
        if "status" not in kwargs or kwargs["status"] is None:
            kwargs["status"] = MonitoringJobStatus.ACTIVE.value
        if "metadata" in kwargs and "metadata_" not in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")
        if "metadata_" not in kwargs or kwargs["metadata_"] is None:
            kwargs["metadata_"] = {}
        super().__init__(**kwargs)


class MonitoringExecutionLog(Base):
    """Database model for execution logs of monitoring jobs."""

    __tablename__ = "monitoring_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monitoring_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    new_query_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=ExecutionLogStatus.SUCCESS.value)
    materiality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    materiality_level: Mapped[str] = mapped_column(String(30), nullable=False, default=MaterialityLevel.NEGLIGIBLE.value)
    delta_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    alert_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    execution_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    job: Mapped["MonitoringJob"] = relationship("MonitoringJob", back_populates="execution_logs")
    alerts: Mapped[List["DecisionAlert"]] = relationship("DecisionAlert", back_populates="execution_log")

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "status" not in kwargs or kwargs["status"] is None:
            kwargs["status"] = ExecutionLogStatus.SUCCESS.value
        if "materiality_score" not in kwargs or kwargs["materiality_score"] is None:
            kwargs["materiality_score"] = 0.0
        if "materiality_level" not in kwargs or kwargs["materiality_level"] is None:
            kwargs["materiality_level"] = MaterialityLevel.NEGLIGIBLE.value
        if "alert_triggered" not in kwargs or kwargs["alert_triggered"] is None:
            kwargs["alert_triggered"] = False
        if "execution_duration_seconds" not in kwargs or kwargs["execution_duration_seconds"] is None:
            kwargs["execution_duration_seconds"] = 0.0
        if "delta_summary" not in kwargs or kwargs["delta_summary"] is None:
            kwargs["delta_summary"] = {}
        if "executed_at" not in kwargs or kwargs["executed_at"] is None:
            from datetime import timezone
            kwargs["executed_at"] = datetime.now(timezone.utc)
        super().__init__(**kwargs)


class DecisionAlert(TimestampMixin, Base):
    """Database model for decision alerts generated by continuous monitoring."""

    __tablename__ = "decision_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monitoring_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    execution_log_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("monitoring_execution_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    materiality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default=AlertSeverity.INFO.value)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=AlertStatus.UNREAD.value, index=True)
    webhook_status: Mapped[str] = mapped_column(String(30), nullable=False, default=WebhookStatus.NONE.value)

    # Relationships
    job: Mapped["MonitoringJob"] = relationship("MonitoringJob", back_populates="alerts")
    execution_log: Mapped[Optional["MonitoringExecutionLog"]] = relationship("MonitoringExecutionLog", back_populates="alerts")

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "materiality_score" not in kwargs or kwargs["materiality_score"] is None:
            kwargs["materiality_score"] = 0.0
        if "severity" not in kwargs or kwargs["severity"] is None:
            kwargs["severity"] = AlertSeverity.INFO.value
        if "status" not in kwargs or kwargs["status"] is None:
            kwargs["status"] = AlertStatus.UNREAD.value
        if "webhook_status" not in kwargs or kwargs["webhook_status"] is None:
            kwargs["webhook_status"] = WebhookStatus.NONE.value
        if "payload" not in kwargs or kwargs["payload"] is None:
            kwargs["payload"] = {}
        super().__init__(**kwargs)
