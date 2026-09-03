"""Self-Challenge API endpoints for RADIS Phase 5."""
import logging
from uuid import UUID
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.hypothesis import SelfChallengeRequest, SelfChallengeResponse
from app.services.self_challenge_service import SelfChallengeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queries", tags=["self-challenge"])


@router.post("/{query_id}/self-challenge", response_model=SelfChallengeResponse, status_code=status.HTTP_200_OK)
async def run_self_challenge(
    query_id: UUID,
    body: Optional[SelfChallengeRequest] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Execute full self-challenge pipeline:
    1. Alternative hypothesis generation (3-7 competing hypotheses)
    2. Falsification per hypothesis with disconfirming query execution
    3. Evidence mapping & confidence recalculation
    4. Red-team critic audit pass
    5. Dynamic replanning check & circuit breaker (max 3 replan iterations)
    6. Finalization with caveats if circuit breaker trips.
    """
    logger.info(f"Received self-challenge trigger for query_id={query_id}")
    try:
        service = SelfChallengeService(db=db)
        if body and body.max_replan_iterations:
            service.max_replan_iterations = body.max_replan_iterations
        if body and body.confidence_threshold:
            service.confidence_threshold = body.confidence_threshold

        result = await service.run_self_challenge(query_id=query_id)
        return result
    except Exception as e:
        logger.error(f"Error during self-challenge execution for query {query_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Self-challenge pipeline failed: {str(e)}"
        )
