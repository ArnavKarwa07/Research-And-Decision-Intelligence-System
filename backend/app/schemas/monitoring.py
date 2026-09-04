from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.monitoring import (
    AlertSeverity,
    AlertStatus,
    ExecutionLogStatus,
    MaterialityLevel,
    MonitoringJobStatus,
    ScheduleType,
    WebhookStatus,
)


def _validate_cron_expression(cron_str: str) -> str:
    """Validate 5-field cron expression syntax or standard cron shorthands."""
    if not cron_str or not isinstance(cron_str, str):
        raise ValueError("Cron expression must be a non-empty string.")
    cleaned = cron_str.strip()
    shorthands = {"@hourly", "@daily", "@weekly", "@monthly", "@yearly", "@annually", "@reboot"}
    if cleaned.lower() in shorthands:
        return cleaned
    parts = cleaned.split()
    if len(parts) != 5:
        raise ValueError("Cron expression must contain exactly 5 fields (minute hour day-of-month month day-of-week).")
    return cleaned


def _validate_webhook_url_str(url_str: str) -> str:
    """Validate webhook URL scheme and security."""
    if not url_str or not isinstance(url_str, str):
        raise ValueError("Webhook URL must be a non-empty string.")
    cleaned = url_str.strip()
    if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
        raise ValueError("Webhook URL must use http:// or https:// protocol.")
    return cleaned


class MaterialityScoreBreakdown(BaseModel):
    """Breakdown of materiality score components during delta comparison."""

    claims_delta_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Delta contribution from changed or added claims")
    sources_delta_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Delta contribution from new or changed sources")
    assumptions_delta_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Delta contribution from invalidated assumptions")
    recommendation_flip_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Delta score if recommendation flipped")
    total_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall aggregated materiality score")
    materiality_level: str = Field(default=MaterialityLevel.NEGLIGIBLE.value, description="Materiality level category")

    @field_validator("materiality_level")
    @classmethod
    def validate_materiality_level(cls, v: str) -> str:
        if isinstance(v, MaterialityLevel):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in MaterialityLevel.__members__:
            raise ValueError(f"Invalid materiality_level '{v}'. Must be one of {[e.value for e in MaterialityLevel]}.")
        return upper_v


class BaselineSnapshotCreate(BaseModel):
    """Schema for creating a research baseline snapshot."""

    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    query_id: Optional[UUID] = None
    decision_id: Optional[UUID] = None
    snapshot_label: str = Field(..., description="Label or version tag for baseline snapshot")
    claims_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    sources_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    decision_snapshot: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("snapshot_label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("snapshot_label cannot be empty or whitespace.")
        return s


class BaselineSnapshotResponse(BaseModel):
    """Schema for returning a research baseline snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    query_id: Optional[UUID] = None
    decision_id: Optional[UUID] = None
    snapshot_label: str
    claims_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    sources_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    decision_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("claims_snapshot", "sources_snapshot", "assumptions_snapshot", mode="before")
    @classmethod
    def coerce_none_to_list(cls, v: Any) -> Any:
        return v if v is not None else []

    @field_validator("decision_snapshot", mode="before")
    @classmethod
    def coerce_none_to_dict(cls, v: Any) -> Any:
        return v if v is not None else {}


class MonitoringJobCreate(BaseModel):
    """Schema for creating a continuous monitoring job."""

    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    query_id: Optional[UUID] = None
    baseline_snapshot_id: Optional[UUID] = None
    name: str = Field(..., description="Descriptive name of the monitoring job")
    schedule_type: str = Field(default=ScheduleType.INTERVAL.value, description="CRON, INTERVAL, or EVENT_DRIVEN")
    cron_expression: Optional[str] = Field(default=None, description="Standard 5-field cron expression if CRON schedule")
    interval_seconds: Optional[int] = Field(default=3600, ge=10, description="Interval in seconds if INTERVAL schedule")
    alert_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Materiality threshold triggering alerts")
    webhook_url: Optional[str] = Field(default=None, description="Optional webhook URL for notifications")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("name cannot be empty or whitespace.")
        return s

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, v: str) -> str:
        if isinstance(v, ScheduleType):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in ScheduleType.__members__:
            raise ValueError(f"Invalid schedule_type '{v}'. Must be one of {[e.value for e in ScheduleType]}.")
        return upper_v

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_webhook_url_str(v)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_cron_expression(v)

    @model_validator(mode="after")
    def validate_schedule_requirements(self) -> "MonitoringJobCreate":
        if self.schedule_type == ScheduleType.CRON.value:
            if not self.cron_expression:
                raise ValueError("cron_expression is required when schedule_type is CRON.")
            _validate_cron_expression(self.cron_expression)
        elif self.schedule_type == ScheduleType.INTERVAL.value:
            if self.interval_seconds is None or self.interval_seconds < 10:
                raise ValueError("interval_seconds (>= 10) is required when schedule_type is INTERVAL.")
        return self


class MonitoringJobUpdate(BaseModel):
    """Schema for updating an existing monitoring job."""

    name: Optional[str] = None
    schedule_type: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = Field(default=None, ge=10)
    status: Optional[str] = None
    alert_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    webhook_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        if not s:
            raise ValueError("name cannot be empty or whitespace.")
        return s

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, ScheduleType):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in ScheduleType.__members__:
            raise ValueError(f"Invalid schedule_type '{v}'. Must be one of {[e.value for e in ScheduleType]}.")
        return upper_v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, MonitoringJobStatus):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in MonitoringJobStatus.__members__:
            raise ValueError(f"Invalid status '{v}'. Must be one of {[e.value for e in MonitoringJobStatus]}.")
        return upper_v

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_webhook_url_str(v)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_cron_expression(v)

    @model_validator(mode="after")
    def validate_schedule_requirements(self) -> "MonitoringJobUpdate":
        if self.schedule_type == ScheduleType.CRON.value and self.cron_expression is not None:
            _validate_cron_expression(self.cron_expression)
        return self


class MonitoringJobResponse(BaseModel):
    """Schema for returning a monitoring job."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    id: UUID
    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    query_id: Optional[UUID] = None
    baseline_snapshot_id: Optional[UUID] = None
    name: str
    schedule_type: str
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    status: str
    alert_threshold: float
    webhook_url: Optional[str] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0
    metadata_: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
        serialization_alias="metadata",
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("metadata_", mode="before")
    @classmethod
    def coerce_none_metadata(cls, v: Any) -> Any:
        return v if v is not None else {}

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.metadata_


class MonitoringExecutionLogResponse(BaseModel):
    """Schema for returning a monitoring execution log."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    new_query_id: Optional[UUID] = None
    status: str
    materiality_score: float
    materiality_level: str
    delta_summary: Dict[str, Any] = Field(default_factory=dict)
    alert_triggered: bool
    executed_at: Optional[datetime] = None
    execution_duration_seconds: float
    error_message: Optional[str] = None

    @field_validator("delta_summary", mode="before")
    @classmethod
    def coerce_none_delta(cls, v: Any) -> Any:
        return v if v is not None else {}


class DecisionAlertResponse(BaseModel):
    """Schema for returning a decision alert."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    execution_log_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    materiality_score: float
    severity: str
    title: str
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str
    webhook_status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("payload", mode="before")
    @classmethod
    def coerce_none_payload(cls, v: Any) -> Any:
        return v if v is not None else {}

