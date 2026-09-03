from typing import Any, Literal
from pydantic import BaseModel, Field
import json
import logging
from .base import BaseAgent, AgentConfig, StepResult, AgentStatus
from .llm_provider import Message

logger = logging.getLogger(__name__)

class SupervisorInput(BaseModel):
    query_text: str
    session_id: str
    user_preferences: dict[str, Any] = Field(default_factory=dict)

class ResearchObjective(BaseModel):
    query: str
    objective: str
    depth: Literal['shallow', 'deep'] = 'shallow'

class ResearchPlan(BaseModel):
    objectives: list[ResearchObjective]
    reasoning: str

class SupervisorOutput(BaseModel):
    plan: ResearchPlan | None = None
    evidence_list: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    confidence_score: float = 0.0

class SupervisorAgent(BaseAgent):
    """
    The Supervisor Agent per AGENT_CONTRACTS.md.
    Responsibilities:
    - Analyze query, plan
    - Spawn Research agent
    - Evaluate results (Synthesize or re-plan)
    Must follow dynamic planning (Rule 5) and evidence rules (Rule 6).
    """
    
    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                max_steps=50,
                max_tokens=100_000,
                timeout_seconds=600,
                allowed_tools=['spawn_agent', 'update_plan', 'evaluate_results']
            )
        super().__init__(config, agent_type="supervisor")
        self.internal_state = {
            'phase': 'planning',  # planning -> researching -> evaluating -> synthesizing -> done
            'plan': None,
            'evidence': [],
            'sub_agents': [],
            'query': ''
        }

    async def step(self, input_data: dict[str, Any]) -> StepResult:
        """Determine next action based on internal phase."""
        try:
            # Parse input on first step
            if not self.internal_state['query']:
                typed_input = SupervisorInput(**input_data)
                self.internal_state['query'] = typed_input.query_text
                self.internal_state['user_preferences'] = typed_input.user_preferences
                
            phase = self.internal_state['phase']
            logger.info(f"Supervisor (ID: {self.state.agent_id}) phase: {phase}")

            if phase == 'planning':
                return await self._plan_research()
            elif phase == 'researching':
                return await self._execute_research()
            elif phase == 'evaluating':
                return await self._evaluate_results()
            elif phase == 'synthesizing':
                return await self._synthesize()
            else:
                return StepResult(action="idle", should_continue=False, message="Unknown phase.")
                
        except Exception as e:
            logger.error(f"Supervisor error in step: {e}", exc_info=True)
            return StepResult(action="error", should_continue=False, message=str(e))

    async def _plan_research(self) -> StepResult:
        """Use LLM to generate a research plan based on the query."""
        if not self._llm_provider:
            raise RuntimeError("LLM provider missing")
            
        system_prompt = (
            "You are a Research Supervisor. Break down the user's query into specific research objectives. "
            "Follow dynamic planning rules: identify only necessary workstreams."
        )
        user_prompt = f"Query: {self.internal_state['query']}"
        
        plan = await self._llm_provider.generate_structured(
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt)
            ],
            response_schema=ResearchPlan
        )
        
        self.internal_state['plan'] = plan
        self.internal_state['phase'] = 'researching'
        
        return StepResult(
            action="plan_research",
            message=f"Created plan with {len(plan.objectives)} objectives.",
            tokens_used=150  # rough estimate if real usage isn't passed back from structured
        )

    async def _execute_research(self) -> StepResult:
        """Spawn research agents via tools or internal logic."""
        # Here we mock the 'spawn_agent' tool call, assuming tool_registry handles it.
        # For simplicity in this implementation, we will invoke the tool for the first objective.
        
        plan: ResearchPlan = self.internal_state['plan']
        
        # If we have unprocessed objectives, spawn a research agent for them
        unprocessed = [obj for obj in plan.objectives if not hasattr(obj, 'processed')]
        
        if not unprocessed:
            self.internal_state['phase'] = 'evaluating'
            return StepResult(action="spawn_agents", message="All objectives dispatched.")
            
        obj = unprocessed[0]
        setattr(obj, 'processed', True)
        
        try:
            tool_res = await self.call_tool("spawn_agent", {
                "agent_type": "research",
                "input": {
                    "search_queries": [obj.query],
                    "objectives": obj.objective,
                    "depth": obj.depth
                }
            })
            
            if tool_res.success:
                self.internal_state['evidence'].extend(tool_res.data.get("evidence", []))
                return StepResult(action="spawn_agent", message=f"Spawned research for: {obj.query}")
            else:
                return StepResult(action="spawn_agent", message=f"Failed to spawn agent: {tool_res.error}")
                
        except PermissionError as e:
            logger.error(str(e))
            self.internal_state['phase'] = 'evaluating' # Force evaluate on failure
            return StepResult(action="error", message=str(e))
            

    async def _evaluate_results(self) -> StepResult:
        """Evaluate if we have enough evidence to answer the query."""
        evidence = self.internal_state['evidence']
        
        if not evidence:
            self.internal_state['phase'] = 'synthesizing'
            return StepResult(action="evaluate", message="No evidence found, proceeding to synthesize failure.")
            
        # Simplified evaluation: just proceed to synthesis
        self.internal_state['phase'] = 'synthesizing'
        return StepResult(action="evaluate", message=f"Evaluated {len(evidence)} pieces of evidence. Ready to synthesize.")

    async def _synthesize(self) -> StepResult:
        """Generate final summary and confidence."""
        if not self._llm_provider:
            raise RuntimeError("LLM provider missing")
            
        system_prompt = (
            "Synthesize the research evidence into a final summary. "
            "Report confidence. Distinguish FACT from INFERENCE. "
            "Do not expose hidden chain-of-thought."
        )
        user_prompt = f"Query: {self.internal_state['query']}\nEvidence: {json.dumps(self.internal_state['evidence'])}"
        
        resp = await self._llm_provider.generate(
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt)
            ]
        )
        
        self.internal_state['final_summary'] = resp.content
        self.internal_state['confidence'] = 0.85 # Mock confidence computation
        self.internal_state['phase'] = 'done'
        
        return StepResult(
            action="synthesize", 
            message="Synthesis complete.", 
            should_continue=False,
            tokens_used=resp.tokens_used
        )

    async def compile_output(self) -> dict[str, Any]:
        """Return SupervisorOutput dumped to dict."""
        output = SupervisorOutput(
            plan=self.internal_state.get('plan'),
            evidence_list=self.internal_state.get('evidence', []),
            summary=self.internal_state.get('final_summary', ''),
            confidence_score=self.internal_state.get('confidence', 0.0)
        )
        return output.model_dump()
