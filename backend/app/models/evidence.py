"""Evidence model."""
import uuid
from sqlalchemy import ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String

from app.models.base import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.query import Query
    from app.models.source import Source

class Evidence(TimestampMixin, Base):
    """Database model for evidence extracted during research."""
    
    __tablename__ = "evidence"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True
    )
    
    query: Mapped["Query"] = relationship(
        "Query",
        back_populates="evidence_list"
    )
    source: Mapped["Source | None"] = relationship(
        "Source",
        back_populates="evidence_list"
    )
