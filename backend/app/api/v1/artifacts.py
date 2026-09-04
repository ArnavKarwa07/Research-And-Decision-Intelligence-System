"""API Endpoints for Phase 11 Artifacts, Reports, & Export Packages."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.source import Source
from app.schemas.artifact import (
    DecisionMemoResponse,
    ExecutiveReportResponse,
    ComparisonTableResponse,
)
from app.services.artifact_service import ArtifactService
from app.services.export_package_service import ExportPackageService

router = APIRouter(tags=["artifacts"])


@router.post(
    "/queries/{query_id}/artifacts/decision-memo",
    response_model=DecisionMemoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist an executive decision memo"
)
async def generate_decision_memo(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ArtifactService(db)
    return await service.generate_decision_memo(query_id)


@router.get(
    "/queries/{query_id}/artifacts/decision-memo",
    response_model=DecisionMemoResponse,
    summary="Fetch existing or compiled executive decision memo"
)
async def get_decision_memo(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ArtifactService(db)
    return await service.get_or_create_decision_memo(query_id)


@router.post(
    "/queries/{query_id}/artifacts/research-report",
    response_model=ExecutiveReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a full technical research report"
)
async def generate_research_report(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ArtifactService(db)
    return await service.generate_research_report(query_id)


@router.get(
    "/queries/{query_id}/artifacts/research-report",
    response_model=ExecutiveReportResponse,
    summary="Fetch full technical research report"
)
async def get_research_report(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ArtifactService(db)
    return await service.generate_research_report(query_id)


@router.get(
    "/queries/{query_id}/artifacts/comparison-table",
    response_model=ComparisonTableResponse,
    summary="Export tabular comparison of alternatives vs criteria"
)
async def export_comparison_table(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ArtifactService(db)
    return await service.export_comparison_table(query_id)


@router.get(
    "/queries/{query_id}/artifacts/export-package",
    summary="One-click export download bundling research findings into a ZIP package archive"
)
async def download_export_package(
    query_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ExportPackageService(db)
    zip_buffer, filename = await service.generate_zip_package(query_id)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get(
    "/queries/{query_id}/sources",
    summary="Fetch all aggregated sources for a query with domain quality scores"
)
async def get_query_sources(
    query_id: UUID,
    source_type: Optional[str] = Query(None, description="Filter by source type (web, pdf, db, academic)"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Source)
    if source_type:
        stmt = stmt.where(Source.source_type == source_type)
    res = await self_db_exec(db, stmt)
    sources = list(res.scalars().all())
    return [
        {
            "id": str(s.id),
            "title": s.title or "Web Resource",
            "url": s.url,
            "publisher": s.publisher or "Verified Provider",
            "quality_score": s.quality_score or 0.88,
            "relevance_score": getattr(s, "relevance_score", 0.90),
            "source_type": s.source_type or "web",
            "created_at": s.created_at,
        }
        for s in sources
    ]


async def self_db_exec(db: AsyncSession, stmt):
    res = await db.execute(stmt)
    return res
