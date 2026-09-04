"""Query model."""
import uuid
from sqlalchemy import ForeignKey, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String

from app.models.base import Base, TimestampMixin
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.session import Session
    from app.models.evidence import Evidence
    from app.models.agent_run import AgentRun
    from app.models.claim import Claim
    from app.models.source_group import SourceGroup
    from app.models.contradiction import Contradiction
    from app.models.hypothesis import Hypothesis
    from app.models.critique_report import CritiqueReport
    from app.models.decision import Decision
    from app.models.artifact import Artifact


class Query(TimestampMixin, Base):
    """Database model for a user query."""
    
    __tablename__ = "queries"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        default="pending",
        nullable=False
    )
    research_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="queries"
    )
    evidence_list: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    source_groups: Mapped[list["SourceGroup"]] = relationship(
        "SourceGroup",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    contradictions: Mapped[list["Contradiction"]] = relationship(
        "Contradiction",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    hypotheses: Mapped[list["Hypothesis"]] = relationship(
        "Hypothesis",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    critique_reports: Mapped[list["CritiqueReport"]] = relationship(
        "CritiqueReport",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    decisions: Mapped[list["Decision"]] = relationship(
        "Decision",
        back_populates="query",
        cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact",
        back_populates="query",
        cascade="all, delete-orphan"
    )


