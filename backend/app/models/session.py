"""Session model."""
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.query import Query
    from app.models.document import Document
    from app.models.artifact import Artifact


class Session(TimestampMixin, Base):
    """Database model for a research session."""
    
    __tablename__ = "sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String,
        default="active",
        nullable=False
    )
    
    queries: Mapped[list["Query"]] = relationship(
        "Query",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact",
        back_populates="session",
        cascade="all, delete-orphan"
    )


