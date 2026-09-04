"""Database models for Phase 12 Project Memory & Long-term Research Heuristics."""
import enum
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query
    from app.models.session import Session


class MemoryType(str, enum.Enum):
    """Types of project memory items."""
    DECISION_TRAIL = "DECISION_TRAIL"
    FACT = "FACT"
    REUSABLE_ASSUMPTION = "REUSABLE_ASSUMPTION"
    PRIOR_CONCLUSION = "PRIOR_CONCLUSION"
    LESSON_LEARNED = "LESSON_LEARNED"


class ValidityStatus(str, enum.Enum):
    """Validity states for project memory items."""
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


class HumanApprovalStatus(str, enum.Enum):
    """Human-in-the-loop approval statuses for memory items."""
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProjectMemoryItem(TimestampMixin, Base):
    """Database model for persistent project memory items (facts, decision trails, assumptions, lessons)."""

    __tablename__ = "project_memory_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_query_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    validity_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ValidityStatus.ACTIVE.value, index=True
    )
    human_approval_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=HumanApprovalStatus.NOT_REQUIRED.value, index=True
    )
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "confidence" not in kwargs or kwargs["confidence"] is None:
            kwargs["confidence"] = 1.0
        if "validity_status" not in kwargs or kwargs["validity_status"] is None:
            kwargs["validity_status"] = ValidityStatus.ACTIVE.value
        if "human_approval_status" not in kwargs or kwargs["human_approval_status"] is None:
            kwargs["human_approval_status"] = HumanApprovalStatus.NOT_REQUIRED.value
        if "content" not in kwargs or kwargs["content"] is None:
            kwargs["content"] = {}
        if "tags" not in kwargs or kwargs["tags"] is None:
            kwargs["tags"] = []
        super().__init__(**kwargs)


class ResearchHeuristics(TimestampMixin, Base):
    """Database model for domain-specific research heuristics, untrusted domains, and tool patterns."""

    __tablename__ = "research_heuristics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    untrusted_domains: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=True)
    effective_query_templates: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=True)
    verified_tool_patterns: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)
    failure_modes: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "untrusted_domains" not in kwargs or kwargs["untrusted_domains"] is None:
            kwargs["untrusted_domains"] = []
        if "effective_query_templates" not in kwargs or kwargs["effective_query_templates"] is None:
            kwargs["effective_query_templates"] = []
        if "verified_tool_patterns" not in kwargs or kwargs["verified_tool_patterns"] is None:
            kwargs["verified_tool_patterns"] = []
        if "failure_modes" not in kwargs or kwargs["failure_modes"] is None:
            kwargs["failure_modes"] = []
        super().__init__(**kwargs)


# Alias for singular form compatibility
ResearchHeuristic = ResearchHeuristics
