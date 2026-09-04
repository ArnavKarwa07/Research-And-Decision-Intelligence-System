"""API endpoints for Decision Intelligence (Phase 6)."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.decision import (
    DecisionCreateRequest,
    DecisionResponse,
    DecisionListResponse,
    SensitivityRequest,
    ScenarioRequest,
)
from app.services.decision_service import DecisionService

router = APIRouter(tags=["decisions"])


@router.post(
    "/queries/{query_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run and persist a decision analysis for a query"
)
async def create_decision_analysis(
    query_id: UUID,
    request: DecisionCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    if request.query_id != query_id:
        request = request.model_copy(update={"query_id": query_id})

    service = DecisionService(db)
    try:
        decision = await service.create_decision(request)
        return decision
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute decision analysis: {str(e)}"
        )


@router.get(
    "/queries/{query_id}/decisions",
    response_model=DecisionListResponse,
    summary="List all decisions generated for a query"
)
async def list_query_decisions(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = DecisionService(db)
    decisions = await service.list_decisions_for_query(query_id)
    return DecisionListResponse(decisions=decisions, total=len(decisions))


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionResponse,
    summary="Fetch a specific decision by ID"
)
async def get_decision_by_id(
    decision_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = DecisionService(db)
    decision = await service.get_decision(decision_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision with ID '{decision_id}' not found."
        )
    return decision


@router.post(
    "/decisions/{decision_id}/sensitivity",
    response_model=DecisionResponse,
    summary="Re-run sensitivity analysis on an existing decision"
)
async def rerun_decision_sensitivity(
    decision_id: UUID,
    request: SensitivityRequest,
    db: AsyncSession = Depends(get_db)
):
    service = DecisionService(db)
    try:
        updated = await service.rerun_sensitivity(decision_id, request)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Decision with ID '{decision_id}' not found."
            )
        return updated
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-run sensitivity analysis: {str(e)}"
        )


@router.post(
    "/decisions/{decision_id}/scenarios",
    response_model=DecisionResponse,
    summary="Re-run scenario analysis on an existing decision"
)
async def rerun_decision_scenarios(
    decision_id: UUID,
    request: ScenarioRequest,
    db: AsyncSession = Depends(get_db)
):
    service = DecisionService(db)
    try:
        updated = await service.rerun_scenarios(decision_id, request)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Decision with ID '{decision_id}' not found."
            )
        return updated
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-run scenario analysis: {str(e)}"
        )
