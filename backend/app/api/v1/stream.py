from fastapi import APIRouter, Request, Depends
from uuid import UUID
from sse_starlette.sse import EventSourceResponse
import asyncio

from app.services.stream_service import stream_service
from app.dependencies import get_db

router = APIRouter(tags=['stream'])

@router.get('/queries/{query_id}/stream')
async def stream_query(query_id: UUID, request: Request, db=Depends(get_db)):
    """SSE endpoint for real-time query progress."""
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.query import Query
    
    result = await db.execute(select(Query).where(Query.id == query_id))
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
        
    subscriber_id, event_generator = await stream_service.subscribe(query_id)
    
    async def sse_generator():
        yield {"comment": "stream connected"}
        try:
            async for event in event_generator:
                if event.event_type == "ping":
                    yield {"comment": "ping"}
                    continue
                yield {
                    "event": event.event_type,
                    "data": event.model_dump_json()
                }
                if event.event_type in ("complete", "error"):
                    await asyncio.sleep(0.5)
                    break
        except (asyncio.CancelledError, Exception):
            pass
        finally:
            stream_service.unsubscribe(query_id, subscriber_id)
            
    return EventSourceResponse(
        sse_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
