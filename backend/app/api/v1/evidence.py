from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.evidence import EvidenceResponse
from app.dependencies import get_db, get_settings
from app.services.query_service import QueryService

router = APIRouter(tags=['evidence'])

@router.get('/queries/{query_id}/evidence', response_model=list[EvidenceResponse])
async def get_evidence(query_id: UUID, db: AsyncSession = Depends(get_db), settings = Depends(get_settings)):
    """Get all evidence for a query."""
    query_service = QueryService(db, settings)
    query = await query_service.get_query(query_id)
    
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
        
    evidence = await query_service.get_evidence_for_query(query_id)
    return evidence
