"""Hypothesis model."""
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import ForeignKey, Text, Float, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query


class Hypothesis(TimestampMixin, Base):
    """Database model for a generated hypothesis."""

    __tablename__ = "hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="proposed", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    supporting_claim_ids: Mapped[List[str] | None] = mapped_column(JSON, default=list, nullable=True)
    falsifying_claim_ids: Mapped[List[str] | None] = mapped_column(JSON, default=list, nullable=True)
    evidence_map: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, default=list, nullable=True)
    falsification_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_falsification_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    metadata_: Mapped[Dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    query: Mapped["Query"] = relationship("Query", back_populates="hypotheses")

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "status" not in kwargs or kwargs["status"] is None:
            kwargs["status"] = "proposed"
        if "confidence" not in kwargs or kwargs["confidence"] is None:
            kwargs["confidence"] = 0.5
        if "supporting_claim_ids" not in kwargs or kwargs["supporting_claim_ids"] is None:
            kwargs["supporting_claim_ids"] = []
        if "falsifying_claim_ids" not in kwargs or kwargs["falsifying_claim_ids"] is None:
            kwargs["falsifying_claim_ids"] = []
        if "evidence_map" not in kwargs or kwargs["evidence_map"] is None:
            kwargs["evidence_map"] = []
        if "falsification_attempts" not in kwargs or kwargs["falsification_attempts"] is None:
            kwargs["falsification_attempts"] = 0
        if "max_falsification_attempts" not in kwargs or kwargs["max_falsification_attempts"] is None:
            kwargs["max_falsification_attempts"] = 5
        if "metadata" in kwargs and "metadata_" not in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")
        super().__init__(**kwargs)
