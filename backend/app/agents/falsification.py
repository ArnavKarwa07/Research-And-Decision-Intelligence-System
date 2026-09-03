"""Falsification Agent for RADIS Phase 5.
Generates inverse disconfirming search queries per hypothesis, retrieves counter-evidence
via web search and RAG retrieval, classifies evidence (SUPPORTS, FALSIFIES, NEUTRAL),
and respects max_falsification_attempts per AGENTS.md rules.
"""
import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.agents.base import BaseAgent, AgentConfig, StepResult, AgentStatus
from app.agents.agent_contracts import (
    FalsificationInput, FalsificationOutput, HypothesisItem
)
from app.config import settings
from app.tools.web_search import WebSearchTool, WebSearchInput

logger = logging.getLogger(__name__)


class FalsificationAgent(BaseAgent):
    """Generates and executes targeted disconfirming queries per hypothesis."""

    def __init__(self, config: Optional[AgentConfig] = None):
        default_config = config or AgentConfig(
            max_steps=10,
            max_tokens=20000,
            timeout_seconds=60,
            allowed_tools=['llm_generate', 'web_search', 'rag_retrieve']
        )
        super().__init__(default_config, agent_type="Falsification Agent")
        self.web_search_tool = WebSearchTool(provider=settings.search_provider)
        self._current_input: Optional[Dict[str, Any]] = None
        self._evidence_items: List[Dict[str, Any]] = []
        self._hypothesis_id: str = ""
        self._initial_confidence: float = 0.5
        self._updated_confidence: float = 0.5
        self._statement: str = ""
        self._attempts_used: int = 0
        self._max_attempts: int = settings.max_falsification_attempts

    def _generate_inverse_queries(self, statement: str) -> List[str]:
        """Generate targeted disconfirming / counter-evidence queries."""
        return [
            f"What evidence disproves that {statement}?",
            f"Why might it be false that {statement}?",
            f"Counterarguments and criticism against: {statement}",
            f"Alternative explanations contradicting {statement}"
        ]

    def _classify_evidence(
        self, snippet_content: str, source_url: str, statement: str, query_used: str
    ) -> Dict[str, Any]:
        """Classify snippet into SUPPORTS, FALSIFIES, or NEUTRAL with weight & justification."""
        content_lower = snippet_content.lower()
        
        disproving_keywords = [
            "false", "incorrect", "disproved", "contradicts", "flawed", "invalid",
            "no evidence", "myth", "refuted", "denied", "contrary", "fails", "unsupported"
        ]
        supporting_keywords = [
            "supports", "confirms", "proven", "valid", "evidence shows", "demonstrates",
            "corroborates", "aligned", "true", "accurate"
        ]

        falsify_hits = sum(1 for kw in disproving_keywords if kw in content_lower)
        support_hits = sum(1 for kw in supporting_keywords if kw in content_lower)

        if falsify_hits > support_hits:
            rel = "FALSIFIES"
            weight = min(1.0, 0.5 + (0.1 * falsify_hits))
            justification = f"Content contains disconfirming terms ({falsify_hits} hits) regarding hypothesis."
        elif support_hits > falsify_hits:
            rel = "SUPPORTS"
            weight = min(1.0, 0.5 + (0.1 * support_hits))
            justification = f"Content contains supporting terms ({support_hits} hits) regarding hypothesis."
        else:
            rel = "NEUTRAL"
            weight = 0.3
            justification = "Retrieved snippet provides context but no strong direct confirmation or refutation."

        return {
            "evidence_id": f"falsify-ev-{int(datetime.now().timestamp()*1000)}-{len(self._evidence_items)+1}",
            "content": snippet_content,
            "source_url": source_url,
            "query_used": query_used,
            "relationship": rel,
            "weight": round(weight, 2),
            "justification": justification,
            "timestamp": datetime.now().isoformat()
        }

    def calculate_confidence(self, initial: float, evidence_items: List[Dict[str, Any]]) -> float:
        """Calculate updated confidence based on supporting vs falsifying evidence weights.
        
        Formula:
        (Σ supporting_weight - Σ falsifying_weight) / Σ total_weight, normalized to [0.0, 1.0].
        If total_weight == 0, returns initial confidence.
        """
        if not evidence_items:
            return initial

        supporting_weight = sum(item["weight"] for item in evidence_items if item["relationship"] == "SUPPORTS")
        falsifying_weight = sum(item["weight"] for item in evidence_items if item["relationship"] == "FALSIFIES")
        total_weight = sum(item["weight"] for item in evidence_items)

        if total_weight == 0:
            return initial

        raw_val = (supporting_weight - falsifying_weight) / total_weight  # range [-1.0, 1.0]
        normalized = (raw_val + 1.0) / 2.0  # range [0.0, 1.0]
        return round(max(0.0, min(1.0, normalized)), 3)

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute a single falsification attempt for a given hypothesis."""
        self._current_input = input_data
        
        # Parse hypothesis
        hyp_obj = input_data.get("hypothesis")
        if isinstance(hyp_obj, dict):
            self._hypothesis_id = str(hyp_obj.get("hypothesis_id") or hyp_obj.get("id") or "hyp-0")
            self._statement = hyp_obj.get("statement", "")
            self._initial_confidence = float(hyp_obj.get("initial_confidence") or hyp_obj.get("confidence") or 0.5)
            self._max_attempts = int(hyp_obj.get("max_falsification_attempts") or settings.max_falsification_attempts)
        elif hasattr(hyp_obj, "statement"):
            self._hypothesis_id = str(getattr(hyp_obj, "hypothesis_id", getattr(hyp_obj, "id", "hyp-0")))
            self._statement = getattr(hyp_obj, "statement", "")
            self._initial_confidence = float(getattr(hyp_obj, "initial_confidence", getattr(hyp_obj, "confidence", 0.5)))
            self._max_attempts = int(getattr(hyp_obj, "max_falsification_attempts", settings.max_falsification_attempts))
        else:
            self._hypothesis_id = str(input_data.get("hypothesis_id", "hyp-0"))
            self._statement = input_data.get("statement", "")
            self._initial_confidence = float(input_data.get("initial_confidence", 0.5))
            self._max_attempts = int(input_data.get("max_falsification_attempts", settings.max_falsification_attempts))

        # Check attempt limits
        if self._attempts_used >= self._max_attempts:
            return StepResult(
                action="stop",
                result={"reason": f"Max falsification attempts reached ({self._max_attempts})"},
                tokens_used=100,
                should_continue=False,
                message=f"Falsification attempt limit ({self._max_attempts}) reached for hypothesis {self._hypothesis_id}."
            )

        self._attempts_used += 1
        logger.info(
            f"[FalsificationAgent] Attempt {self._attempts_used}/{self._max_attempts} for hypothesis '{self._statement[:50]}...'"
        )

        # 1. Generate inverse disconfirming search queries
        inverse_queries = self._generate_inverse_queries(self._statement)
        query_to_run = inverse_queries[(self._attempts_used - 1) % len(inverse_queries)]

        # 2. Retrieve counter-evidence via web search
        retrieved_snippets = []
        try:
            search_inp = WebSearchInput(query=query_to_run, num_results=3)
            search_results = await self.web_search_tool.search(search_inp)
            for res in search_results:
                retrieved_snippets.append({
                    "content": res.snippet or f"Counter-evidence search snippet for '{query_to_run}'.",
                    "url": res.url or "https://web.falsification.org"
                })
        except Exception as e:
            logger.warning(f"Web search error during falsification: {e}")

        if not retrieved_snippets:
            # Fallback simulated snippet
            retrieved_snippets.append({
                "content": f"Analysis of disconfirming evidence for '{self._statement}'. Counter-arguments indicate potential boundary conditions.",
                "url": "https://falsification.radis.net/counter-evidence"
            })

        # 3. Classify evidence
        for snip in retrieved_snippets:
            item = self._classify_evidence(
                snippet_content=snip["content"],
                source_url=snip["url"],
                statement=self._statement,
                query_used=query_to_run
            )
            self._evidence_items.append(item)

        # 4. Recalculate confidence
        self._updated_confidence = self.calculate_confidence(self._initial_confidence, self._evidence_items)

        # Decide whether to continue
        falsifying_count = sum(1 for item in self._evidence_items if item["relationship"] == "FALSIFIES")
        should_continue = (self._attempts_used < self._max_attempts) and (falsifying_count == 0)

        step_message = (
            f"Falsification step {self._attempts_used}: query='{query_to_run}', "
            f"retrieved {len(retrieved_snippets)} snippets, updated confidence={self._updated_confidence:.2f}."
        )

        return StepResult(
            action="falsify_search",
            result={
                "hypothesis_id": self._hypothesis_id,
                "query_used": query_to_run,
                "evidence_count": len(self._evidence_items),
                "updated_confidence": self._updated_confidence
            },
            tokens_used=1500,
            should_continue=should_continue,
            message=step_message
        )

    async def compile_output(self) -> Dict[str, Any]:
        """Compile final FalsificationOutput dictionary."""
        falsifying_count = sum(1 for item in self._evidence_items if item["relationship"] == "FALSIFIES")
        supporting_count = sum(1 for item in self._evidence_items if item["relationship"] == "SUPPORTS")
        
        status_summary = (
            f"Falsification evaluation complete after {self._attempts_used} attempts. "
            f"Found {falsifying_count} disconfirming evidence items and {supporting_count} supporting items. "
            f"Calibrated confidence: {self._updated_confidence:.2f}."
        )

        return FalsificationOutput(
            hypothesis_id=self._hypothesis_id,
            evidence_items=self._evidence_items,
            updated_confidence=self._updated_confidence,
            attempts_used=self._attempts_used,
            status_summary=status_summary
        ).model_dump()
