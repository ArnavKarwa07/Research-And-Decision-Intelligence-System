"""
Gatekeeper & Clarification Specialist Agent (Phase 8).
Responsible for identifying task ambiguities, raising clarification prompts, evaluating tool execution risks, and managing approval gate states.
"""

import logging
from typing import Dict, Any, List
from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class GatekeeperAgent(BaseAgent):
    def __init__(self, config: AgentConfig = None):
        if not config:
            config = AgentConfig(
                max_steps=10,
                max_tokens=10000,
                timeout_seconds=30,
                allowed_tools=["create_gate", "request_clarification"],
            )
        super().__init__(config, agent_type="gatekeeper_agent")
        self.last_analysis: Dict[str, Any] = {}

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        query_text = input_data.get("query_text", "")
        tool_name = input_data.get("tool_name", None)
        agent_role = input_data.get("agent_role", "research")

        needs_clarification = False
        clarification_prompt = ""
        suggested_options: List[str] = []

        # Analyze query for critical ambiguity or underspecified inputs
        ambiguous_keywords = ["do whatever", "any option", "choose for me", "unknown dataset", "all data"]
        if any(kw in query_text.lower() for kw in ambiguous_keywords) or len(query_text.strip()) < 10:
            needs_clarification = True
            clarification_prompt = f"The research objective '{query_text}' is ambiguous or underspecified. Please clarify target scope or constraints."
            suggested_options = ["Focus on financial metrics", "Focus on technical architecture", "Focus on market analysis"]

        # Check tool risk gate
        requires_gate = False
        risk_level = "low"
        if tool_name:
            perm_allowed, req_approval, _ = SecurityService.check_tool_permission(agent_role, tool_name)
            if req_approval:
                requires_gate = True
                risk_level = "high" if tool_name in ["python_sandbox", "execute_sql_query"] else "medium"

        self.last_analysis = {
            "needs_clarification": needs_clarification,
            "clarification_prompt": clarification_prompt,
            "suggested_options": suggested_options,
            "requires_approval_gate": requires_gate,
            "risk_level": risk_level,
            "gate_tool_name": tool_name,
            "timeout_seconds": 300,  # 5-minute auto-kill timeout
        }

        return StepResult(
            action="gatekeeper_analysis_complete",
            result=self.last_analysis,
            tokens_used=100,
            should_continue=False,
            message=f"Gatekeeper analysis complete. Clarification: {needs_clarification}, Gate needed: {requires_gate}",
        )

    async def compile_output(self) -> Dict[str, Any]:
        return self.last_analysis
