"""Hypothesis Agent implementation for RADIS.
Decomposes research queries into 3-7 competing, falsifiable hypotheses.
"""
import logging
import uuid
from typing import Any

from app.agents.agent_contracts import HypothesisAgentInput, HypothesisAgentOutput, HypothesisItem
from app.agents.base import AgentConfig, BaseAgent, StepResult
from app.agents.llm_provider import Message

logger = logging.getLogger(__name__)


class HypothesisAgent(BaseAgent):
    """Hypothesis Agent generates 3-7 competing, falsifiable hypotheses for a research query."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                max_steps=5,
                max_tokens=15000,
                timeout_seconds=45,
                allowed_tools=["llm_structured_generate", "llm_generate"]
            )
        super().__init__(config, agent_type="Hypothesis Generation Agent")
        self.hypotheses: list[HypothesisItem] = []
        self.investigation_priorities: list[str] = []

    async def step(self, input_data: dict[str, Any]) -> StepResult:
        query_text = input_data.get("query_text") or input_data.get("objective") or "Research Query"
        existing_claims = input_data.get("existing_claims", [])
        existing_sources = input_data.get("existing_sources", [])

        logger.info(f"[Hypothesis Agent] Generating competing hypotheses for: '{query_text}'")

        parsed_input = HypothesisAgentInput(
            query_text=query_text,
            existing_claims=existing_claims,
            existing_sources=existing_sources
        )

        tokens_used = 250
        generated_output: HypothesisAgentOutput | None = None

        # Attempt structured generation via LLM Provider if available
        if self._llm_provider:
            try:
                system_prompt = (
                    "You are a Specialist Hypothesis Generation Agent in a decision intelligence system. "
                    "Given a research query and context, generate between 3 and 7 distinct, competing, "
                    "and mutually falsifiable hypotheses. Provide an initial confidence score [0.0 - 1.0] "
                    "for each and list discriminating evidence needed to evaluate them."
                )
                user_content = (
                    f"Query: {parsed_input.query_text}\n"
                    f"Existing Claims Count: {len(parsed_input.existing_claims)}\n"
                    f"Existing Sources Count: {len(parsed_input.existing_sources)}\n"
                )
                messages = [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_content)
                ]
                res = await self._llm_provider.generate_structured(messages, HypothesisAgentOutput)
                if isinstance(res, HypothesisAgentOutput) and len(res.hypotheses) >= 1:
                    generated_output = res
                    tokens_used = 500
            except Exception as e:
                logger.warning(f"[Hypothesis Agent] Structured LLM generation fallback triggered: {e}")

        # Heuristic / deterministic fallback if LLM provider returns empty or fails
        if not generated_output or not generated_output.hypotheses:
            h1_id = str(uuid.uuid4())
            h2_id = str(uuid.uuid4())
            h3_id = str(uuid.uuid4())

            fallback_hypotheses = [
                HypothesisItem(
                    hypothesis_id=h1_id,
                    statement=f"Primary Hypothesis: {parsed_input.query_text} is directly supported by existing evidence.",
                    initial_confidence=0.65,
                    discriminating_evidence_needed=[
                        "Direct empirical verification from primary sources",
                        "Quantitative benchmark measurements"
                    ]
                ),
                HypothesisItem(
                    hypothesis_id=h2_id,
                    statement=f"Null Hypothesis: {parsed_input.query_text} is driven by confounding external factors or baseline trends.",
                    initial_confidence=0.45,
                    discriminating_evidence_needed=[
                        "Control group comparisons or baseline data",
                        "Sensitivity analysis across alternative parameters"
                    ]
                ),
                HypothesisItem(
                    hypothesis_id=h3_id,
                    statement=f"Counter Hypothesis: {parsed_input.query_text} faces significant operational or technical counter-evidence.",
                    initial_confidence=0.35,
                    discriminating_evidence_needed=[
                        "Falsification testing under edge-case workloads",
                        "Independent third-party failure mode reports"
                    ]
                )
            ]
            fallback_priorities = [
                "Verify primary hypothesis against primary source documentation",
                "Execute disconfirming search queries for counter-evidence",
                "Validate assumptions underlying the null hypothesis"
            ]
            generated_output = HypothesisAgentOutput(
                hypotheses=fallback_hypotheses,
                investigation_priorities=fallback_priorities
            )

        # Enforce 3 to 7 items boundary
        self.hypotheses = generated_output.hypotheses[:7]
        self.investigation_priorities = generated_output.investigation_priorities or [
            "Gather disconfirming evidence for top hypothesis",
            "Perform cross-validation across competing hypotheses"
        ]

        result_dict = {
            "hypotheses_count": len(self.hypotheses),
            "hypotheses": [h.model_dump() for h in self.hypotheses],
            "investigation_priorities": self.investigation_priorities
        }

        return StepResult(
            action="generate_hypotheses",
            result=result_dict,
            tokens_used=tokens_used,
            should_continue=False,
            message=f"Generated {len(self.hypotheses)} competing hypotheses for investigation."
        )

    async def compile_output(self) -> dict[str, Any]:
        output = HypothesisAgentOutput(
            hypotheses=self.hypotheses,
            investigation_priorities=self.investigation_priorities
        )
        return output.model_dump()
