"""Search API Routes for RADIS Phase 4 (Internal Knowledge + RAG).
Provides endpoints for hybrid, semantic, and keyword searches over internal session document chunks.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field

from app.agents.agent_contracts import DocumentChunk
from app.rag.search.hybrid_search import hybrid_search_engine
from app.rag.search.bm25_engine import bm25_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    top_k: int = Field(default=5, ge=1, le=50, description="Max document chunks to return")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Dense vs Sparse weight alpha (1.0 = Dense only, 0.0 = BM25 only)")
    enable_reranking: bool = Field(default=True, description="Enable cross-encoder reranking")
    chunks: Optional[List[DocumentChunk]] = Field(default=None, description="Optional ad-hoc chunk corpus override")


class SearchResponse(BaseModel):
    session_id: str
    query: str
    search_type: str
    total_results: int
    chunks: List[DocumentChunk]


@router.post("/sessions/{session_id}/search/hybrid", response_model=SearchResponse)
async def hybrid_search_endpoint(
    session_id: str = Path(..., description="Session identifier"),
    req: SearchRequest = ...
) -> SearchResponse:
    """Execute Hybrid Search combining Dense + BM25 Sparse Search via Reciprocal Rank Fusion (RRF) and Cross-Encoder Reranking."""
    try:
        results = await hybrid_search_engine.search(
            session_id=session_id,
            query=req.query,
            top_k=req.top_k,
            alpha=req.alpha,
            enable_reranking=req.enable_reranking,
            chunks_override=req.chunks
        )
        return SearchResponse(
            session_id=session_id,
            query=req.query,
            search_type="hybrid",
            total_results=len(results),
            chunks=results
        )
    except Exception as e:
        logger.error(f"[Search API] Hybrid search failed for session '{session_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid search failed: {str(e)}"
        )


@router.post("/sessions/{session_id}/search/semantic", response_model=SearchResponse)
async def semantic_search_endpoint(
    session_id: str = Path(..., description="Session identifier"),
    req: SearchRequest = ...
) -> SearchResponse:
    """Execute Dense Vector Search only."""
    try:
        results = await hybrid_search_engine.search(
            session_id=session_id,
            query=req.query,
            top_k=req.top_k,
            alpha=1.0,
            enable_reranking=req.enable_reranking,
            chunks_override=req.chunks
        )
        return SearchResponse(
            session_id=session_id,
            query=req.query,
            search_type="semantic",
            total_results=len(results),
            chunks=results
        )
    except Exception as e:
        logger.error(f"[Search API] Semantic search failed for session '{session_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.post("/sessions/{session_id}/search/keyword", response_model=SearchResponse)
async def keyword_search_endpoint(
    session_id: str = Path(..., description="Session identifier"),
    req: SearchRequest = ...
) -> SearchResponse:
    """Execute BM25 Keyword Search only."""
    try:
        raw_results = bm25_engine.search(
            session_id=session_id,
            query=req.query,
            top_k=req.top_k,
            chunks_override=req.chunks
        )
        chunks = []
        for chunk, score in raw_results:
            c_copy = chunk.model_copy()
            c_copy.score = score
            chunks.append(c_copy)

        return SearchResponse(
            session_id=session_id,
            query=req.query,
            search_type="keyword",
            total_results=len(chunks),
            chunks=chunks
        )
    except Exception as e:
        logger.error(f"[Search API] Keyword search failed for session '{session_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Keyword search failed: {str(e)}"
        )
