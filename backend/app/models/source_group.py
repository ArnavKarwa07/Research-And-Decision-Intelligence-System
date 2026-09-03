"""SourceGroup models."""
import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.query import Query
    from app.models.source import Source

class SourceGroup(TimestampMixin, Base):
    """Database model for a group of sources."""
    
    __tablename__ = "source_groups"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    group_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    query: Mapped["Query"] = relationship("Query", back_populates="source_groups")
    members: Mapped[list["SourceGroupMember"]] = relationship(
        "SourceGroupMember",
        back_populates="group",
        cascade="all, delete-orphan"
    )

class SourceGroupMember(TimestampMixin, Base):
    """Database model linking a source to a source group."""
    
    __tablename__ = "source_group_members"
    
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_groups.id", ondelete="CASCADE"),
        nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False
    )

    group: Mapped["SourceGroup"] = relationship("SourceGroup", back_populates="members")
    source: Mapped["Source"] = relationship("Source")
