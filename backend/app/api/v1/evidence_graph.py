from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.claim import Claim
from app.models.contradiction import Contradiction
from app.models.source import Source
from app.dependencies import get_db

router = APIRouter(tags=['evidence'])

@router.get('/queries/{query_id}/evidence-graph')
async def get_evidence_graph(query_id: UUID, db: AsyncSession = Depends(get_db)):
    """Returns graph JSON with nodes (claims, sources), edges (support links, contradiction links), and stats summary."""
    from app.models.query import Query
    result = await db.execute(select(Query).where(Query.id == query_id))
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
        
    claims_res = await db.execute(select(Claim).where(Claim.query_id == query_id))
    claims = claims_res.scalars().all()
    
    contradictions_res = await db.execute(select(Contradiction).where(Contradiction.query_id == query_id))
    contradictions = contradictions_res.scalars().all()
    
    # Placeholder for actual source and evidence link models
    sources = []
    support_links = []
    
    nodes = []
    edges = []
    
    for c in claims:
        nodes.append({
            "id": str(c.id),
            "type": "claim",
            "data": {
                "content": c.content,
                "status": c.status,
                "confidence_score": c.confidence_score
            }
        })
        
    for src in sources:
        nodes.append({
            "id": str(src.id),
            "type": "source",
            "data": {
                "url": src.url,
                "credibility_score": getattr(src, 'credibility_score', 0.5)
            }
        })
        
    for contra in contradictions:
        edges.append({
            "id": str(contra.id),
            "source": str(contra.claim_a_id),
            "target": str(contra.claim_b_id),
            "type": "contradicts",
            "data": {
                "status": contra.resolution_status
            }
        })
        
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_claims": len(claims),
            "total_sources": len(sources),
            "total_contradictions": len(contradictions)
        }
    }
