"""Decision model for decision intelligence."""
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import ForeignKey, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query


class Decision(TimestampMixin, Base):
    """Database model for a structured decision analysis."""

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternatives: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)
    criteria: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)
    weighted_matrix: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    scenarios: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    sensitivity_analysis: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    expected_values: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=True)
    key_risks: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=True)
    assumptions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=True)
    decision_triggers: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=True)

    query: Mapped["Query"] = relationship("Query", back_populates="decisions")

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "alternatives" not in kwargs or kwargs["alternatives"] is None:
            kwargs["alternatives"] = []
        if "criteria" not in kwargs or kwargs["criteria"] is None:
            kwargs["criteria"] = []
        if "weighted_matrix" not in kwargs or kwargs["weighted_matrix"] is None:
            kwargs["weighted_matrix"] = {}
        if "scenarios" not in kwargs or kwargs["scenarios"] is None:
            kwargs["scenarios"] = {}
        if "sensitivity_analysis" not in kwargs or kwargs["sensitivity_analysis"] is None:
            kwargs["sensitivity_analysis"] = {}
        if "expected_values" not in kwargs or kwargs["expected_values"] is None:
            kwargs["expected_values"] = {}
        if "key_risks" not in kwargs or kwargs["key_risks"] is None:
            kwargs["key_risks"] = []
        if "assumptions" not in kwargs or kwargs["assumptions"] is None:
            kwargs["assumptions"] = []
        if "decision_triggers" not in kwargs or kwargs["decision_triggers"] is None:
            kwargs["decision_triggers"] = []
        if "metadata" in kwargs and "metadata_" not in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")
        if "metadata_" not in kwargs or kwargs["metadata_"] is None:
            kwargs["metadata_"] = {}
        super().__init__(**kwargs)
