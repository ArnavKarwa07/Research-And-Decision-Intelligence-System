from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.claim import ClaimResponse
from app.models.claim import Claim
from app.dependencies import get_db

router = APIRouter(tags=['claims'])

@router.get('/queries/{query_id}/claims', response_model=List[ClaimResponse])
async def get_query_claims(query_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all claims for a specific query."""
    from app.models.query import Query
    result = await db.execute(select(Query).where(Query.id == query_id))
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
        
    result = await db.execute(select(Claim).where(Claim.query_id == query_id))
    claims = result.scalars().all()
    return claims

@router.post('/queries/{query_id}/claims/extract', response_model=List[ClaimResponse])
async def extract_claims(query_id: UUID, db: AsyncSession = Depends(get_db)):
    """Manually trigger claim extraction for a query."""
    # Placeholder for explicit claim extraction logic
    return []

@router.post('/queries/{query_id}/claims/{claim_id}/verify', response_model=ClaimResponse)
async def verify_claim(query_id: UUID, claim_id: UUID, db: AsyncSession = Depends(get_db)):
    """Manually trigger fact-checking for a specific claim."""
    result = await db.execute(select(Claim).where(Claim.id == claim_id, Claim.query_id == query_id))
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    claim.status = "verified"
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    
    return claim
