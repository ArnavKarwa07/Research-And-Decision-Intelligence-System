"""REST API endpoints for Phase 12 Project Memory & Research Heuristics."""
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user_optional
from app.models.project_memory import HumanApprovalStatus
from app.schemas.project_memory import (
    ProjectMemoryContext,
    ProjectMemoryItemCreate,
    ProjectMemoryItemResponse,
    ProjectMemoryItemUpdate,
    ResearchHeuristicCreate,
    ResearchHeuristicResponse,
)
from app.services.heuristics_store_service import HeuristicsStoreService
from app.services.memory_context_injector import MemoryContextInjector
from app.services.project_memory_service import ProjectMemoryService

router = APIRouter(prefix="/memory", tags=["project_memory"])


class ApprovalRequest(BaseModel):
    """Payload for approving or rejecting a memory assumption."""
    approval_status: str = Field(
        default=HumanApprovalStatus.APPROVED.value,
        description="Target approval status: APPROVED or REJECTED",
    )


class InjectContextRequest(BaseModel):
    """Payload for previewing memory context injection."""
    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    domain: Optional[str] = None
    query_text: Optional[str] = None


class ContextPreviewResponse(BaseModel):
    """Response schema for memory context injection preview."""
    context: ProjectMemoryContext
    formatted_prompt_text: str


@router.post(
    "/items",
    response_model=ProjectMemoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a persistent project memory item",
)
async def create_memory_item(
    item_in: ProjectMemoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = ProjectMemoryService(db)
    try:
        item = await service.create_memory_item(item_in)
        return item
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create memory item: {str(e)}",
        )


@router.get(
    "/items",
    response_model=List[ProjectMemoryItemResponse],
    summary="List project memory items with filters",
)
async def list_memory_items(
    project_id: Optional[UUID] = Query(None, description="Filter by project UUID"),
    session_id: Optional[UUID] = Query(None, description="Filter by session UUID"),
    memory_type: Optional[str] = Query(None, description="Filter by memory type (FACT, REUSABLE_ASSUMPTION, etc.)"),
    validity_status: Optional[str] = Query(None, description="Filter by validity status (ACTIVE, SUPERSEDED, INVALIDATED)"),
    human_approval_status: Optional[str] = Query(None, description="Filter by approval status (APPROVED, PENDING, REJECTED)"),
    key: Optional[str] = Query(None, description="Filter by memory key"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = ProjectMemoryService(db)
    items = await service.list_memory_items(
        project_id=project_id,
        session_id=session_id,
        memory_type=memory_type,
        validity_status=validity_status,
        human_approval_status=human_approval_status,
        key=key,
    )
    return items


@router.get(
    "/items/{id}",
    response_model=ProjectMemoryItemResponse,
    summary="Get project memory item details by ID",
)
async def get_memory_item(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = ProjectMemoryService(db)
    item = await service.get_memory_item(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project memory item '{id}' not found.",
        )
    return item


@router.patch(
    "/items/{id}",
    response_model=ProjectMemoryItemResponse,
    summary="Update a project memory item",
)
async def update_memory_item(
    id: UUID,
    item_in: ProjectMemoryItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = ProjectMemoryService(db)
    try:
        updated = await service.update_memory_item(id, item_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project memory item '{id}' not found.",
            )
        return updated
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory item: {str(e)}",
        )


@router.post(
    "/items/{id}/approve",
    response_model=ProjectMemoryItemResponse,
    summary="Approve or reject a memory assumption or item",
)
async def approve_memory_item(
    id: UUID,
    req: Optional[ApprovalRequest] = None,
    approval_status: Optional[str] = Query(None, description="Optional query parameter for approval status"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = ProjectMemoryService(db)
    target_status = approval_status
    if not target_status and req:
        target_status = req.approval_status
    if not target_status:
        target_status = HumanApprovalStatus.APPROVED.value

    try:
        updated = await service.update_approval_status(id, target_status)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project memory item '{id}' not found.",
            )
        return updated
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update approval status: {str(e)}",
        )


@router.get(
    "/heuristics",
    response_model=ResearchHeuristicResponse,
    summary="Get domain-specific research heuristics",
)
async def get_research_heuristics(
    domain: str = Query(..., description="Target domain, e.g. finance, healthcare"),
    project_id: Optional[UUID] = Query(None, description="Optional project UUID filter"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = HeuristicsStoreService(db)
    heuristics = await service.get_heuristics_by_domain(domain=domain, project_id=project_id)
    if not heuristics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research heuristics for domain '{domain}' not found.",
        )
    return heuristics


@router.post(
    "/heuristics",
    response_model=ResearchHeuristicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update domain-specific research heuristics",
)
async def create_or_update_heuristics(
    h_in: ResearchHeuristicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = HeuristicsStoreService(db)
    try:
        heuristics = await service.create_or_update_heuristics(h_in)
        return heuristics
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save research heuristics: {str(e)}",
        )


@router.post(
    "/inject-context",
    response_model=ContextPreviewResponse,
    summary="Preview project memory context injection for prompt generation",
)
async def preview_context_injection(
    req: InjectContextRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    injector = MemoryContextInjector(db)
    try:
        ctx = await injector.build_memory_context(
            project_id=req.project_id,
            session_id=req.session_id,
            domain=req.domain,
            query_text=req.query_text,
        )
        prompt_text = injector.format_context_for_prompt(ctx)
        return ContextPreviewResponse(context=ctx, formatted_prompt_text=prompt_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build memory context injection preview: {str(e)}",
        )

