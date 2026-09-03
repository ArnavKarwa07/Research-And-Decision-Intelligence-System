"""FastAPI routes for critique red-team operations."""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.hypothesis import CritiqueReportResponse
from app.services.critique_service import CritiqueService

router = APIRouter()
critique_service = CritiqueService()


@router.post("/queries/{query_id}/critique", response_model=CritiqueReportResponse, status_code=status.HTTP_201_CREATED)
async def run_critique(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Run an independent red-team critique pass on query synthesis."""
    try:
        report = await critique_service.run_critique(db, query_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run critique: {str(e)}")


@router.get("/queries/{query_id}/critique", response_model=List[CritiqueReportResponse])
async def get_critiques(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all critique reports for a research query."""
    from app.models.query import Query
    from sqlalchemy import select
    result = await db.execute(select(Query).where(Query.id == query_id))
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    reports = await critique_service.get_critiques_by_query(db, query_id)
    return reports

