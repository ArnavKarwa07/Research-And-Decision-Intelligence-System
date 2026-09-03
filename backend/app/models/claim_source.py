"""ClaimSource model."""
import uuid
from sqlalchemy import Text, Float, String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.source import Source

class ClaimSource(TimestampMixin, Base):
    """Database model linking claims to their sources."""
    
    __tablename__ = "claim_sources"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt_location: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    support_type: Mapped[str] = mapped_column(String, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    claim: Mapped["Claim"] = relationship("Claim", back_populates="claim_sources")
    source: Mapped["Source"] = relationship("Source", back_populates="claim_sources")
