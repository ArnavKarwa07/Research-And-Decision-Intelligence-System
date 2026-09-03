"""CritiqueReport model."""
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import ForeignKey, Text, Boolean, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query


class CritiqueReport(TimestampMixin, Base):
    """Database model for a critic / red-team critique report."""

    __tablename__ = "critique_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    synthesis_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[List[str] | None] = mapped_column(JSON, default=list, nullable=True)
    weak_evidence: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, default=list, nullable=True)
    missing_variables: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, default=list, nullable=True)
    overall_severity: Mapped[str] = mapped_column(String, default="LOW", nullable=False)
    recommendations: Mapped[List[str] | None] = mapped_column(JSON, default=list, nullable=True)
    replan_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    query: Mapped["Query"] = relationship("Query", back_populates="critique_reports")

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "findings" not in kwargs or kwargs["findings"] is None:
            kwargs["findings"] = []
        if "weak_evidence" not in kwargs or kwargs["weak_evidence"] is None:
            kwargs["weak_evidence"] = []
        if "missing_variables" not in kwargs or kwargs["missing_variables"] is None:
            kwargs["missing_variables"] = []
        if "overall_severity" not in kwargs or kwargs["overall_severity"] is None:
            kwargs["overall_severity"] = "LOW"
        if "recommendations" not in kwargs or kwargs["recommendations"] is None:
            kwargs["recommendations"] = []
        if "replan_triggered" not in kwargs or kwargs["replan_triggered"] is None:
            kwargs["replan_triggered"] = False
        if "iteration" not in kwargs or kwargs["iteration"] is None:
            kwargs["iteration"] = 1
        super().__init__(**kwargs)
