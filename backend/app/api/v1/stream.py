from fastapi import APIRouter, Request
from uuid import UUID
from sse_starlette.sse import EventSourceResponse
import asyncio

from app.services.stream_service import stream_service

router = APIRouter(tags=['stream'])

@router.get('/queries/{query_id}/stream')
async def stream_query(query_id: UUID, request: Request):
    """SSE endpoint for real-time query progress."""
    subscriber_id, event_generator = await stream_service.subscribe(query_id)
    
    async def sse_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(anext(event_generator), timeout=1.0)
                    yield {
                        "event": event.event_type,
                        "data": event.model_dump_json()
                    }
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    continue
        finally:
            stream_service.unsubscribe(query_id, subscriber_id)
            
    return EventSourceResponse(sse_generator())
