"""AgentRun model for persisting agent execution state."""
import uuid
from typing import TYPE_CHECKING, Optional, Any
from sqlalchemy import ForeignKey, Text, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query


class AgentRun(TimestampMixin, Base):
    """Database model for tracking sub-agent execution runs."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False
    )
    agent_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    steps_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    elapsed_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_log: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    query: Mapped["Query"] = relationship(
        "Query",
        back_populates="agent_runs"
    )
