import asyncio
from typing import Any, AsyncGenerator
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
import uuid

class StreamEvent(BaseModel):
    event_type: str  # 'step', 'evidence', 'status', 'complete', 'error'
    data: dict[str, Any]
    timestamp: datetime

class StreamService:
    """Manages SSE event streams for active queries with event history replay."""
    
    def __init__(self):
        self._queues: dict[UUID, dict[str, asyncio.Queue]] = {}
        self._history: dict[UUID, list[StreamEvent]] = {}

    def publish(self, query_id: UUID, event: StreamEvent) -> None:
        if query_id not in self._history:
            self._history[query_id] = []
        self._history[query_id].append(event)

        if query_id in self._queues:
            for queue in self._queues[query_id].values():
                queue.put_nowait(event)

    async def subscribe(self, query_id: UUID) -> tuple[str, AsyncGenerator[StreamEvent, None]]:
        subscriber_id = str(uuid.uuid4())
        
        if query_id not in self._queues:
            self._queues[query_id] = {}
            
        queue: asyncio.Queue = asyncio.Queue()
        
        # Replay past events for this query if available
        if query_id in self._history:
            for past_event in self._history[query_id]:
                queue.put_nowait(past_event)

        self._queues[query_id][subscriber_id] = queue
        
        async def event_generator() -> AsyncGenerator[StreamEvent, None]:
            try:
                while True:
                    event = await queue.get()
                    yield event
            finally:
                self.unsubscribe(query_id, subscriber_id)
                
        return subscriber_id, event_generator()

    def unsubscribe(self, query_id: UUID, subscriber_id: str) -> None:
        if query_id in self._queues and subscriber_id in self._queues[query_id]:
            del self._queues[query_id][subscriber_id]

    def cleanup(self, query_id: UUID) -> None:
        if query_id in self._queues:
            del self._queues[query_id]
        if query_id in self._history:
            del self._history[query_id]

# Singleton instance
stream_service = StreamService()
