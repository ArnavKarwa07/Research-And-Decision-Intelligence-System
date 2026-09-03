import enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any
import uuid
import time
import logging
import asyncio

logger = logging.getLogger(__name__)

class AgentStatus(str, enum.Enum):
    """Status states for an agent."""
    IDLE = 'idle'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    WAITING = 'waiting'

class AgentConfig(BaseModel):
    """Budget and constraints for an agent.
    Follows AGENTS.md rules for constraints and budgets.
    """
    max_steps: int
    max_tokens: int
    timeout_seconds: int
    allowed_tools: list[str]

class AgentState(BaseModel):
    """Observable, serializable agent state.
    Follows AGENTS.md rule 11 for state management.
    """
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: str = ''
    status: AgentStatus = AgentStatus.IDLE
    steps_taken: int = 0
    tokens_used: int = 0
    start_time: float | None = None
    elapsed_seconds: float = 0.0
    error: str | None = None
    progress_messages: list[str] = Field(default_factory=list)

class StepResult(BaseModel):
    """Result of a single agent step."""
    action: str
    result: Any = None
    tokens_used: int = 0
    should_continue: bool = True
    message: str = ''

class BaseAgent(ABC):
    """Abstract base class for all agents. 
    Enforces AGENTS.md rules including strict stop conditions, budget tracking,
    allowed tools enforcement, and state management.
    """
    
    def __init__(self, config: AgentConfig, agent_type: str = ''):
        self.config = config
        self.state = AgentState(agent_type=agent_type)
        self._tool_registry = None  # Set by orchestrator
        self._llm_provider = None   # Set by orchestrator
        self._message_bus = None    # Set by orchestrator for communication
    
    def set_tool_registry(self, registry: Any) -> None:
        """Inject tool registry."""
        self._tool_registry = registry

    def set_llm_provider(self, provider: Any) -> None:
        """Inject LLM provider."""
        self._llm_provider = provider
        
    def set_message_bus(self, message_bus: Any) -> None:
        """Inject message bus."""
        self._message_bus = message_bus
    
    def should_stop(self) -> tuple[bool, str]:
        """
        Check all stop conditions: steps, tokens, timeout. 
        Returns (should_stop, reason).
        Rule 13: Strict stop conditions.
        """
        if self.state.steps_taken >= self.config.max_steps:
            return True, f'Max steps reached ({self.config.max_steps})'
        if self.state.tokens_used >= self.config.max_tokens:
            return True, f'Token budget exhausted ({self.config.max_tokens})'
        if self.state.start_time:
            elapsed = time.time() - self.state.start_time
            if elapsed >= self.config.timeout_seconds:
                return True, f'Timeout ({self.config.timeout_seconds}s)'
        return False, ''
    
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Main execution loop with budget enforcement.
        Rule 16: Cost Discipline enforced here before/after each step.
        """
        self.state.status = AgentStatus.RUNNING
        self.state.start_time = time.time()
        logger.info(f"Starting agent {self.state.agent_type} (ID: {self.state.agent_id})")
        try:
            while True:
                stop, reason = self.should_stop()
                if stop:
                    self.state.status = AgentStatus.TIMEOUT if 'Timeout' in reason else AgentStatus.COMPLETED
                    self.state.error = reason
                    logger.warning(f"Agent {self.state.agent_id} stopping: {reason}")
                    break
                
                try:
                    remaining_time = max(1.0, self.config.timeout_seconds - (time.time() - self.state.start_time))
                    step_result = await asyncio.wait_for(self.step(input_data), timeout=remaining_time)
                except asyncio.TimeoutError:
                    self.state.status = AgentStatus.TIMEOUT
                    self.state.error = "Agent step timed out"
                    logger.warning(f"Agent {self.state.agent_id} stopping due to timeout.")
                    break
                
                self.state.steps_taken += 1
                self.state.tokens_used += step_result.tokens_used
                self.state.elapsed_seconds = time.time() - self.state.start_time
                self.state.progress_messages.append(step_result.message)
                
                logger.debug(f"Agent {self.state.agent_id} step {self.state.steps_taken}: {step_result.message}")
                
                if not step_result.should_continue:
                    self.state.status = AgentStatus.COMPLETED
                    break
            
            output = await self.compile_output()
            logger.info(f"Agent {self.state.agent_id} completed successfully.")
            return output
        except Exception as e:
            self.state.status = AgentStatus.FAILED
            self.state.error = str(e)
            logger.error(f"Agent {self.state.agent_id} failed: {e}", exc_info=True)
            raise
    
    @abstractmethod
    async def step(self, input_data: dict[str, Any]) -> StepResult:
        """Execute a single step. Must be implemented by subclasses."""
        ...
    
    @abstractmethod
    async def compile_output(self) -> dict[str, Any]:
        """Compile final output after all steps. Must be implemented by subclasses."""
        ...
    
    def get_state(self) -> AgentState:
        """Retrieve current agent state."""
        if self.state.start_time:
            self.state.elapsed_seconds = time.time() - self.state.start_time
        return self.state
    
    async def call_tool(self, tool_name: str, input_data: dict[str, Any]) -> Any:
        """
        Call a tool, enforcing the allowed_tools list.
        Rule 9: Tool rules applied.
        """
        if tool_name not in self.config.allowed_tools:
            logger.error(f"Agent {self.state.agent_type} attempted unauthorized tool: {tool_name}")
            raise PermissionError(f'Agent {self.state.agent_type} not allowed to call tool: {tool_name}')
        if not self._tool_registry:
            raise RuntimeError('No tool registry configured')
            
        return await self._tool_registry.call(tool_name, input_data, self.state.agent_id)
