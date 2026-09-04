"""Project Memory Service for Phase 12 Continuous Intelligence."""
import logging
from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_memory import (
    HumanApprovalStatus,
    MemoryType,
    ProjectMemoryItem,
    ValidityStatus,
)
from app.schemas.project_memory import (
    ProjectMemoryItemCreate,
    ProjectMemoryItemUpdate,
)

logger = logging.getLogger(__name__)


class ProjectMemoryService:
    """
    Service for persistent project memory operations:
    - CRUD for project memory items (decision trail, facts, reusable assumptions, prior conclusions, lessons learned)
    - Human approval status transitions (PENDING -> APPROVED / REJECTED)
    - Validity status transitions (ACTIVE -> SUPERSEDED / INVALIDATED)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_memory_item(self, item_in: ProjectMemoryItemCreate) -> ProjectMemoryItem:
        """Create and persist a new ProjectMemoryItem."""
        item = ProjectMemoryItem(
            project_id=item_in.project_id,
            session_id=item_in.session_id,
            memory_type=item_in.memory_type,
            key=item_in.key,
            summary=item_in.summary,
            content=item_in.content or {},
            confidence=item_in.confidence,
            source_query_id=item_in.source_query_id,
            validity_status=item_in.validity_status,
            human_approval_status=item_in.human_approval_status,
            tags=item_in.tags or [],
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_memory_item(self, item_id: UUID) -> Optional[ProjectMemoryItem]:
        """Fetch project memory item by ID."""
        result = await self.db.execute(
            select(ProjectMemoryItem).where(ProjectMemoryItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def list_memory_items(
        self,
        project_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        memory_type: Optional[str] = None,
        validity_status: Optional[str] = None,
        human_approval_status: Optional[str] = None,
        key: Optional[str] = None,
    ) -> List[ProjectMemoryItem]:
        """List project memory items with optional filters."""
        stmt = select(ProjectMemoryItem)
        if project_id:
            stmt = stmt.where(ProjectMemoryItem.project_id == project_id)
        if session_id:
            stmt = stmt.where(ProjectMemoryItem.session_id == session_id)
        if memory_type:
            stmt = stmt.where(ProjectMemoryItem.memory_type == memory_type)
        if validity_status:
            stmt = stmt.where(ProjectMemoryItem.validity_status == validity_status)
        if human_approval_status:
            stmt = stmt.where(ProjectMemoryItem.human_approval_status == human_approval_status)
        if key:
            stmt = stmt.where(ProjectMemoryItem.key == key)

        stmt = stmt.order_by(ProjectMemoryItem.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_memory_item(
        self, item_id: UUID, item_in: ProjectMemoryItemUpdate
    ) -> Optional[ProjectMemoryItem]:
        """Update fields of an existing project memory item."""
        item = await self.get_memory_item(item_id)
        if not item:
            return None

        if item_in.summary is not None:
            item.summary = item_in.summary
        if item_in.content is not None:
            item.content = item_in.content
        if item_in.confidence is not None:
            item.confidence = item_in.confidence
        if item_in.validity_status is not None:
            item.validity_status = item_in.validity_status
        if item_in.human_approval_status is not None:
            item.human_approval_status = item_in.human_approval_status
        if item_in.tags is not None:
            item.tags = item_in.tags

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_memory_item(self, item_id: UUID) -> bool:
        """Delete a project memory item."""
        item = await self.get_memory_item(item_id)
        if not item:
            return False

        await self.db.delete(item)
        await self.db.commit()
        return True

    async def update_approval_status(
        self, item_id: UUID, approval_status: Union[HumanApprovalStatus, str]
    ) -> Optional[ProjectMemoryItem]:
        """
        Transition human approval status of a memory item (PENDING -> APPROVED / REJECTED).
        """
        status_val = (
            approval_status.value
            if isinstance(approval_status, HumanApprovalStatus)
            else str(approval_status)
        )
        item = await self.get_memory_item(item_id)
        if not item:
            return None

        item.human_approval_status = status_val
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_validity_status(
        self, item_id: UUID, validity_status: Union[ValidityStatus, str]
    ) -> Optional[ProjectMemoryItem]:
        """
        Transition validity status of a memory item (ACTIVE -> SUPERSEDED / INVALIDATED).
        """
        status_val = (
            validity_status.value
            if isinstance(validity_status, ValidityStatus)
            else str(validity_status)
        )
        item = await self.get_memory_item(item_id)
        if not item:
            return None

        item.validity_status = status_val
        await self.db.commit()
        await self.db.refresh(item)
        return item
