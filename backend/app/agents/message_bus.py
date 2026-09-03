import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class AgentMessage(BaseModel):
    """Message schema for inter-agent communication."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str
    to_agent: str | None = None  # None indicates broadcast message
    message_type: str            # e.g., 'result', 'request', 'status', 'progress'
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageBus:
    """
    In-memory async message bus for inter-agent communication.
    Allows point-to-point and broadcast messaging.
    """
    
    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}
        self._history: dict[str, list[AgentMessage]] = {}
        self._broadcast_history: list[AgentMessage] = []

    def subscribe(self, agent_id: str) -> None:
        """Create a mailbox for an agent if it doesn't exist."""
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
            self._history[agent_id] = []
            logger.info(f"Agent {agent_id} subscribed to MessageBus")

    async def send(self, message: AgentMessage) -> None:
        """Send a message to a specific agent."""
        if not message.to_agent:
            raise ValueError("Message must have a to_agent for point-to-point send. Use broadcast() instead.")
            
        target = message.to_agent
        if target not in self._queues:
            self.subscribe(target)
            
        self._history[target].append(message)
        await self._queues[target].put(message)
        logger.debug(f"Message {message.id} sent from {message.from_agent} to {target}")

    async def broadcast(self, message: AgentMessage) -> None:
        """Send a message to all subscribed agents."""
        if message.to_agent is not None:
            logger.warning("Broadcast message has to_agent set; clearing it.")
            message.to_agent = None
            
        self._broadcast_history.append(message)
        
        for agent_id, queue in self._queues.items():
            if agent_id != message.from_agent:
                self._history[agent_id].append(message)
                await queue.put(message)
                
        logger.debug(f"Message {message.id} broadcasted from {message.from_agent}")

    async def receive(self, agent_id: str, timeout: float = 5.0) -> AgentMessage | None:
        """
        Wait for a message addressed to the agent.
        Returns None if timeout occurs.
        """
        if agent_id not in self._queues:
            self.subscribe(agent_id)
            
        try:
            message = await asyncio.wait_for(self._queues[agent_id].get(), timeout=timeout)
            return message
        except asyncio.TimeoutError:
            return None

    def get_history(self, agent_id: str) -> list[AgentMessage]:
        """Retrieve all messages sent to an agent (including broadcasts)."""
        return self._history.get(agent_id, [])
