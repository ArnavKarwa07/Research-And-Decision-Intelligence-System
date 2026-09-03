from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.contradiction import ContradictionResponse, ContradictionResolveRequest, ResolutionStatus
from app.models.contradiction import Contradiction
from app.models.claim import Claim
from app.dependencies import get_db

router = APIRouter(tags=['contradictions'])

@router.get('/queries/{query_id}/contradictions', response_model=List[ContradictionResponse])
async def get_query_contradictions(query_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all contradictions detected for a specific query."""
    from app.models.query import Query
    result = await db.execute(select(Query).where(Query.id == query_id))
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
        
    result = await db.execute(select(Contradiction).where(Contradiction.query_id == query_id))
    contradictions = result.scalars().all()
    return contradictions

@router.post('/contradictions/{contradiction_id}/resolve', response_model=ContradictionResponse)
async def resolve_contradiction(
    contradiction_id: UUID, 
    resolve_req: ContradictionResolveRequest,
    db: AsyncSession = Depends(get_db)
):
    """Manually resolve a contradiction."""
    result = await db.execute(select(Contradiction).where(Contradiction.id == contradiction_id))
    contradiction = result.scalar_one_or_none()
    
    if not contradiction:
        raise HTTPException(status_code=404, detail="Contradiction not found")
        
    contradiction.resolution_status = resolve_req.resolution_status.value
    contradiction.resolution_notes = resolve_req.resolution_notes
    
    # Update claim status based on resolution
    # E.g., marking one as disputed/refuted could go here, but for now just resolve the contradiction
    if resolve_req.resolution_status.value in ("resolved_a", "resolved_b", "resolved_both"):
        import datetime
        contradiction.resolved_at = datetime.datetime.now(datetime.timezone.utc)
        
        # We can set claim statuses based on who won
        claim_a_res = await db.execute(select(Claim).where(Claim.id == contradiction.claim_a_id))
        claim_b_res = await db.execute(select(Claim).where(Claim.id == contradiction.claim_b_id))
        claim_a = claim_a_res.scalar_one_or_none()
        claim_b = claim_b_res.scalar_one_or_none()
        
        if resolve_req.resolution_status.value == "resolved_a":
            if claim_a: claim_a.status = "verified"
            if claim_b: claim_b.status = "refuted"
        elif resolve_req.resolution_status.value == "resolved_b":
            if claim_a: claim_a.status = "refuted"
            if claim_b: claim_b.status = "verified"
        elif resolve_req.resolution_status.value == "resolved_both":
            if claim_a: claim_a.status = "verified"
            if claim_b: claim_b.status = "verified"
            
        if claim_a: db.add(claim_a)
        if claim_b: db.add(claim_b)
        
    elif resolve_req.resolution_status.value == "escalated":
        claim_a_res = await db.execute(select(Claim).where(Claim.id == contradiction.claim_a_id))
        claim_b_res = await db.execute(select(Claim).where(Claim.id == contradiction.claim_b_id))
        claim_a = claim_a_res.scalar_one_or_none()
        claim_b = claim_b_res.scalar_one_or_none()
        
        if claim_a:
            claim_a.status = "disputed"
            db.add(claim_a)
        if claim_b:
            claim_b.status = "disputed"
            db.add(claim_b)
            
    db.add(contradiction)
    await db.commit()
    await db.refresh(contradiction)
    
    return contradiction
