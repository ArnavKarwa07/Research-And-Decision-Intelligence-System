from typing import Any, Callable, Awaitable
from pydantic import BaseModel
import time
import logging

logger = logging.getLogger(__name__)

class ToolDefinition(BaseModel):
    """Schema for tool definitions to enforce typing."""
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema representation

class ToolResult(BaseModel):
    """Standardized result wrapper for tool execution."""
    success: bool
    data: Any = None
    error: str | None = None
    latency_ms: float = 0.0

class ToolRegistry:
    """
    Central registry for tools.
    Agents request tools by name; registry enforces access, validation, and auditing.
    Follows Rule 9: Tool Rules.
    """
    
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {}
    
    def register(self, name: str, description: str, schema: dict[str, Any], handler: Callable[[dict[str, Any]], Awaitable[Any]]) -> None:
        """Register a new tool with its metadata and async handler."""
        if name in self._tools:
            logger.warning(f"Overwriting existing tool: {name}")
        
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=schema
        )
        self._handlers[name] = handler
        logger.info(f"Registered tool: {name}")

    def get_tools_for_agent(self, allowed_tools: list[str]) -> list[ToolDefinition]:
        """Return definitions for tools the agent is allowed to access."""
        return [self._tools[name] for name in allowed_tools if name in self._tools]

    async def call(self, name: str, input_data: dict[str, Any], agent_id: str) -> ToolResult:
        """
        Execute a tool, wrapping it in timing, error handling, and basic auditing.
        """
        if name not in self._handlers:
            msg = f"Tool not found: {name}"
            logger.error(msg)
            return ToolResult(success=False, error=msg)
            
        tool_def = self._tools[name]
        if tool_def.input_schema and 'required' in tool_def.input_schema:
            for req in tool_def.input_schema['required']:
                if req not in input_data:
                    raise ValueError(f"Missing required parameter: {req}")
            
        handler = self._handlers[name]
        start_time = time.time()
        
        logger.debug(f"Agent {agent_id} calling tool {name} with data: {input_data}")
        
        try:
            # Note: actual strict JSON schema validation of input_data could happen here
            result_data = await handler(input_data)
            latency = (time.time() - start_time) * 1000
            logger.info(f"Tool {name} executed successfully by {agent_id} in {latency:.2f}ms")
            return ToolResult(
                success=True,
                data=result_data,
                latency_ms=latency
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"Tool {name} failed for agent {agent_id}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e),
                latency_ms=latency
            )
