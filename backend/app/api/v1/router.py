from fastapi import APIRouter
from app.api.v1 import (
    sessions,
    queries,
    stream,
    evidence,
    contradictions,
    claims,
    evidence_graph,
    search,
    documents,
    critique,
    hypotheses,
    self_challenge,
    decisions,
    data_analysis,
    hitl,
    safety,
)



api_v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
api_v1_router.include_router(sessions.router)
api_v1_router.include_router(queries.router)
api_v1_router.include_router(stream.router)
api_v1_router.include_router(evidence.router)
api_v1_router.include_router(contradictions.router)
api_v1_router.include_router(claims.router)
api_v1_router.include_router(evidence_graph.router)
api_v1_router.include_router(search.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(critique.router)
api_v1_router.include_router(hypotheses.router)
api_v1_router.include_router(self_challenge.router)
api_v1_router.include_router(decisions.router)
api_v1_router.include_router(data_analysis.router)
api_v1_router.include_router(hitl.router)
api_v1_router.include_router(safety.router)



