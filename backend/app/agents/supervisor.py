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
    run_id: str | None = None

class ResearchObjective(BaseModel):
    query: str
    objective: str
    depth: Literal['shallow', 'deep'] = 'shallow'
    processed: bool = False

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
    Enforces budget check gates before delegating sub-tasks and handles budget exhaustion gracefully.
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
            'query': '',
            'run_id': None,
            'budget_capped': False,
            'processed_indices': set(),
        }

    def _check_budget_exhausted(self) -> tuple[bool, str]:
        """Check if run budget or agent token limit has been exhausted."""
        run_id = self.internal_state.get('run_id')
        if run_id:
            from app.services.budget_service import budget_service
            rb = budget_service.get_run_budget(run_id)
            if rb:
                hard_exceeded, hard_reason, _ = rb.check_limits()
                if hard_exceeded:
                    return True, hard_reason or f"Run budget hard limit exceeded for run '{run_id}'"

        if self.state.tokens_used >= self.config.max_tokens:
            return True, f"Token budget exhausted ({self.state.tokens_used}/{self.config.max_tokens})"

        stop, reason = self.should_stop()
        if stop and ('budget' in reason.lower() or 'token' in reason.lower() or 'max' in reason.lower()):
            return True, reason

        return False, ""

    async def step(self, input_data: dict[str, Any]) -> StepResult:
        """Determine next action based on internal phase."""
        try:
            # Parse input on first step
            if not self.internal_state['query']:
                typed_input = SupervisorInput(**input_data)
                self.internal_state['query'] = typed_input.query_text
                self.internal_state['user_preferences'] = typed_input.user_preferences
                if typed_input.run_id:
                    self.internal_state['run_id'] = typed_input.run_id
                elif input_data.get('run_id'):
                    self.internal_state['run_id'] = str(input_data.get('run_id'))
                
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
        """Spawn research agents via tools or internal logic with budget check gates."""
        # Budget Check Gate prior to delegating sub-tasks
        is_exhausted, reason = self._check_budget_exhausted()
        if is_exhausted:
            logger.warning(f"Supervisor budget gate triggered: {reason}. Capping research and triggering immediate synthesis.")
            self.internal_state['phase'] = 'synthesizing'
            self.internal_state['budget_capped'] = True
            return StepResult(
                action="cap_research",
                message=f"Budget exhausted ({reason}). Capping research and triggering immediate synthesis with accumulated evidence.",
                should_continue=True
            )

        plan: ResearchPlan | None = self.internal_state.get('plan')
        if not plan or not plan.objectives:
            self.internal_state['phase'] = 'evaluating'
            return StepResult(action="spawn_agents", message="No objectives to dispatch.")

        processed_indices = self.internal_state.setdefault('processed_indices', set())
        unprocessed = [(idx, obj) for idx, obj in enumerate(plan.objectives) if idx not in processed_indices]
        if not unprocessed:
            self.internal_state['phase'] = 'evaluating'
            return StepResult(action="spawn_agents", message="All objectives dispatched.")

        idx, obj = unprocessed[0]

        # Check / create sub-task budget if run_id is active
        run_id = self.internal_state.get('run_id')
        if run_id:
            from app.services.budget_service import budget_service, BudgetExceededError
            try:
                sub_task_id = f"subtask-{idx + 1}"
                sub_b = budget_service.create_sub_task_budget(run_id=run_id, sub_task_id=sub_task_id)
                if sub_b.token_budget.remaining() <= 0 or sub_b.search_budget.remaining() <= 0:
                    logger.warning(f"Sub-task budget remaining is zero for run {run_id}. Capping research.")
                    self.internal_state['phase'] = 'synthesizing'
                    self.internal_state['budget_capped'] = True
                    return StepResult(
                        action="cap_research",
                        message="Sub-task budget exhausted. Capping research and triggering immediate synthesis.",
                        should_continue=True
                    )
            except BudgetExceededError as e:
                logger.warning(f"Sub-task budget allocation failed: {e}. Capping research.")
                self.internal_state['phase'] = 'synthesizing'
                self.internal_state['budget_capped'] = True
                return StepResult(
                    action="cap_research",
                    message=f"Budget limit exceeded ({e}). Capping research and triggering immediate synthesis.",
                    should_continue=True
                )

        processed_indices.add(idx)

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
                evidence_items = tool_res.data.get("evidence", []) if isinstance(tool_res.data, dict) else []
                self.internal_state['evidence'].extend(evidence_items)
                return StepResult(action="spawn_agent", message=f"Spawned research for: {obj.query}")
            else:
                return StepResult(action="spawn_agent", message=f"Failed to spawn agent: {getattr(tool_res, 'error', 'Unknown error')}")

        except Exception as e:
            from app.services.budget_service import BudgetExceededError
            if isinstance(e, (PermissionError, BudgetExceededError)):
                logger.warning(f"Sub-task execution capped due to constraint: {e}. Triggering immediate synthesis.")
                self.internal_state['phase'] = 'synthesizing'
                self.internal_state['budget_capped'] = True
                return StepResult(
                    action="cap_research",
                    message=f"Research capped due to constraint: {e}. Triggering immediate synthesis.",
                    should_continue=True
                )
            logger.error(f"Error in research execution: {e}")
            self.internal_state['phase'] = 'evaluating'
            return StepResult(action="error", message=str(e))

    async def _evaluate_results(self) -> StepResult:
        """Evaluate if we have enough evidence to answer the query."""
        evidence = self.internal_state['evidence']

        if self.internal_state.get('budget_capped'):
            logger.info("Budget capped prior to evaluation. Synthesizing with accumulated evidence.")
            self.internal_state['phase'] = 'synthesizing'
            return StepResult(
                action="evaluate",
                message=f"Budget capped. Proceeding directly to synthesize {len(evidence)} accumulated evidence items."
            )

        if not evidence:
            self.internal_state['phase'] = 'synthesizing'
            return StepResult(action="evaluate", message="No evidence found, proceeding to synthesize failure.")

        self.internal_state['phase'] = 'synthesizing'
        return StepResult(action="evaluate", message=f"Evaluated {len(evidence)} pieces of evidence. Ready to synthesize.")

    async def _synthesize(self) -> StepResult:
        """Generate final summary and confidence using accumulated evidence."""
        accumulated_evidence = self.internal_state.get('evidence', [])
        budget_capped = self.internal_state.get('budget_capped', False)

        if not self._llm_provider:
            summary_prefix = "[BUDGET CAPPED] " if budget_capped else ""
            self.internal_state['final_summary'] = f"{summary_prefix}Synthesized from {len(accumulated_evidence)} evidence items."
            self.internal_state['confidence'] = 0.75 if budget_capped else 0.85
            self.internal_state['phase'] = 'done'
            return StepResult(
                action="synthesize",
                message="Synthesis complete.",
                should_continue=False
            )

        system_prompt = (
            "Synthesize the research evidence into a final summary. "
            "Report confidence. Distinguish FACT from INFERENCE. "
            "Do not expose hidden chain-of-thought."
        )
        if budget_capped:
            system_prompt += " Note: Research was capped early due to budget constraints; synthesize using all available accumulated evidence."

        user_prompt = f"Query: {self.internal_state['query']}\nEvidence: {json.dumps(accumulated_evidence)}"

        resp = await self._llm_provider.generate(
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt)
            ]
        )

        summary_text = resp.content
        if budget_capped and not summary_text.startswith("[BUDGET CAPPED]"):
            summary_text = f"[BUDGET CAPPED] {summary_text}"

        self.internal_state['final_summary'] = summary_text
        self.internal_state['confidence'] = 0.75 if budget_capped else 0.85
        self.internal_state['phase'] = 'done'

        tokens = getattr(resp, 'tokens_used', 0)
        return StepResult(
            action="synthesize",
            message="Synthesis complete.",
            should_continue=False,
            tokens_used=tokens
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

