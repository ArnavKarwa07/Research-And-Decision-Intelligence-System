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
    
    evidence_list: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="source"
    )
