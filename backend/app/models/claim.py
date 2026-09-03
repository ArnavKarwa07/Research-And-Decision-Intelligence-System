"""Claim model."""
import uuid
from datetime import datetime
from sqlalchemy import Text, Float, DateTime, String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query
    from app.models.claim_source import ClaimSource

class Claim(TimestampMixin, Base):
    """Database model for a claim extracted from sources."""
    
    __tablename__ = "claims"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    status: Mapped[str] = mapped_column(String, default="unverified", nullable=False)
    created_by_agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    query: Mapped["Query"] = relationship("Query", back_populates="claims")
    
    claim_sources: Mapped[list["ClaimSource"]] = relationship(
        "ClaimSource",
        back_populates="claim",
        cascade="all, delete-orphan"
    )
