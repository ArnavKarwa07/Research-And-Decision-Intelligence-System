"""Hypothesis API endpoints for RADIS."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.hypothesis import (
    HypothesisResponse,
    HypothesisUpdate,
)
from app.services.hypothesis_service import hypothesis_service

router = APIRouter(tags=['hypotheses'])


@router.post('/queries/{query_id}/hypotheses/generate', response_model=list[HypothesisResponse], status_code=status.HTTP_201_CREATED)
async def generate_hypotheses(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate competing hypotheses for a given query."""
    try:
        hypotheses = await hypothesis_service.generate_hypotheses(db, query_id)
        return hypotheses
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate hypotheses: {e!s}")


@router.get('/queries/{query_id}/hypotheses', response_model=list[HypothesisResponse])
async def get_query_hypotheses(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all hypotheses associated with a specific query."""
    hypotheses = await hypothesis_service.get_hypotheses(db, query_id)
    return hypotheses


@router.get('/hypotheses/{hypothesis_id}', response_model=HypothesisResponse)
async def get_hypothesis(
    hypothesis_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific hypothesis by ID."""
    hypothesis = await hypothesis_service.get_hypothesis_by_id(db, hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hypothesis {hypothesis_id} not found")
    return hypothesis


@router.patch('/hypotheses/{hypothesis_id}', response_model=HypothesisResponse)
async def update_hypothesis(
    hypothesis_id: UUID,
    updates: HypothesisUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a hypothesis by ID."""
    try:
        update_data = updates.model_dump(exclude_unset=True)
        hypothesis = await hypothesis_service.update_hypothesis(db, hypothesis_id, update_data)
        return hypothesis
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update hypothesis: {e!s}")


@router.post('/hypotheses/{hypothesis_id}/falsify', response_model=dict[str, Any])
async def trigger_falsification(
    hypothesis_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Trigger disconfirming query falsification workflow for a hypothesis."""
    try:
        result = await hypothesis_service.run_falsification(db, hypothesis_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Falsification failed: {e!s}")
