"""FastAPI routes for critique red-team operations."""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.query import Query
from app.schemas.hypothesis import CritiqueReportResponse, CritiqueReportListResponse

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


@router.get("/queries/{query_id}/critique", response_model=CritiqueReportListResponse)
async def get_critiques(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all critique reports for a research query."""
    if isinstance(db, AsyncSession):
        from sqlalchemy import select
        res = await db.execute(select(Query).where(Query.id == query_id))
        query = res.scalar_one_or_none()
    else:
        query = db.query(Query).filter(Query.id == query_id).first()

    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    reports = critique_service.get_critiques_by_query(db, query_id)
    if hasattr(reports, "__await__"):
        reports = await reports
    return {"reports": reports, "total": len(reports)}
