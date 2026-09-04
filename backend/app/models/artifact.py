"""Artifact database model for Phase 11."""
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query
    from app.models.session import Session


class Artifact(TimestampMixin, Base):
    """Database model for generated research artifacts and export packages."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    markdown_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    html_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=True)

    query: Mapped["Query"] = relationship("Query", back_populates="artifacts")
    session: Mapped[Optional["Session"]] = relationship("Session", back_populates="artifacts")

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        if "content_json" not in kwargs or kwargs["content_json"] is None:
            kwargs["content_json"] = {}
        if "metadata" in kwargs and "metadata_" not in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")
        if "metadata_" not in kwargs or kwargs["metadata_"] is None:
            kwargs["metadata_"] = {}
        super().__init__(**kwargs)
