"""Source model."""
import uuid
from datetime import datetime
from sqlalchemy import Text, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.claim_source import ClaimSource

class Source(TimestampMixin, Base):
    """Database model for a retrieved source."""
    
    __tablename__ = "sources"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reliability_rating: Mapped[str | None] = mapped_column(String, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # New Phase 3 Evidence Intelligence fields
    publisher: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    independence_group: Mapped[str | None] = mapped_column(String, nullable=True)
    freshness_category: Mapped[str | None] = mapped_column(String, nullable=True)
    
    evidence_list: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="source"
    )
    
    claim_sources: Mapped[list["ClaimSource"]] = relationship(
        "ClaimSource",
        back_populates="source",
        cascade="all, delete-orphan"
    )
