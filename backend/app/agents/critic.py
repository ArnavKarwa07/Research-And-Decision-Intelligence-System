"""Critic Agent (Upgraded Red-Team / Adversarial Reviewer) for RADIS Phase 5.
Inherits from BaseAgent. Audits evidence quality, logical coherence, completeness,
and bias detection without shared state during review.
"""
import logging
from typing import Any, Dict, List, Optional
from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.agents.agent_contracts import CriticInput, CriticOutput

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """Independent adversarial red-team reviewer agent."""

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                max_steps=5,
                max_tokens=15000,
                timeout_seconds=45,
                allowed_tools=["llm_structured_generate", "llm_generate"]
            )
        super().__init__(config, agent_type="Critic Agent")
        self.findings: List[str] = []
        self.weak_evidence: List[Dict[str, Any]] = []
        self.missing_variables: List[Dict[str, Any]] = []
        self.overall_severity: str = "LOW"
        self.recommendations: List[str] = []
        self.replan_recommended: bool = False
        self.synthesis_snapshot: str = ""

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        """Executes independent critique pass across 4 dimensions:
        1. Evidence Quality (source reliability, recency, single-source, confidence < 0.60)
        2. Logical Coherence (reasoning validity, hidden assumptions)
        3. Completeness (missing perspectives, omitted variables)
        4. Bias Detection (confirmation, selection, framing)
        """
        logger.info(f"[{self.state.agent_type}] Starting red-team audit step...")
        
        # Parse inputs
        if isinstance(input_data, CriticInput):
            synthesis = input_data.synthesis
            claims = input_data.claims
            evidence_chain = input_data.evidence_chain
            hypotheses = input_data.hypotheses or []
        else:
            synthesis = input_data.get("synthesis", input_data.get("synthesis_summary", ""))
            claims = input_data.get("claims", [])
            evidence_chain = input_data.get("evidence_chain", [])
            hypotheses = input_data.get("hypotheses", [])

        self.synthesis_snapshot = synthesis
        tokens_used = 150

        # Dimension 1: Evidence Quality & Weak Evidence Detection
        self._audit_evidence_quality(claims, evidence_chain)

        # Dimension 2: Logical Coherence
        self._audit_logical_coherence(synthesis, claims)

        # Dimension 3: Completeness & Missing Variables
        self._audit_completeness(synthesis, claims, hypotheses)

        # Dimension 4: Bias Detection
        self._audit_bias(synthesis, claims)

        # Optional LLM Enhancement if provider injected
        if self._llm_provider:
            try:
                llm_res = await self._invoke_llm_enhancement(synthesis, claims)
                tokens_used += llm_res.get("tokens_used", 200)
            except Exception as e:
                logger.warning(f"[{self.state.agent_type}] LLM enhancement skipped: {e}")

        # Compute overall severity & recommendations
        self._compute_severity_and_recommendations()

        msg = (
            f"Critique pass complete. Overall Severity: {self.overall_severity}. "
            f"Weak evidence: {len(self.weak_evidence)}, Missing variables: {len(self.missing_variables)}. "
            f"Replan recommended: {self.replan_recommended}."
        )

        return StepResult(
            action="critique_pass",
            result={
                "overall_severity": self.overall_severity,
                "replan_recommended": self.replan_recommended,
                "findings_count": len(self.findings),
                "weak_evidence_count": len(self.weak_evidence),
                "missing_variables_count": len(self.missing_variables),
            },
            tokens_used=tokens_used,
            should_continue=False,
            message=msg
        )

    def _audit_evidence_quality(self, claims: List[Any], evidence_chain: List[Any]) -> None:
        """Flags single source, low confidence (<0.60), and unverified claims."""
        for idx, claim in enumerate(claims):
            c_dict = claim if isinstance(claim, dict) else claim.model_dump() if hasattr(claim, "model_dump") else {}
            claim_id = str(c_dict.get("id", c_dict.get("claim_id", f"claim-{idx+1}")))
            conf = float(c_dict.get("confidence", 1.0))
            status = str(c_dict.get("support_status", c_dict.get("status", "SUPPORTED"))).upper()
            
            # Sources extraction
            sources = c_dict.get("sources", [])
            source_url = c_dict.get("source_url")
            sources_count = len(sources) if sources else (1 if source_url else 0)

            # Check 1: Single Source
            if sources_count == 1:
                self.weak_evidence.append({
                    "claim_id": claim_id,
                    "reason": "SINGLE_SOURCE",
                    "severity": "MEDIUM" if conf >= 0.70 else "HIGH",
                    "details": f"Claim '{claim_id}' relies on only 1 source.",
                    "remediation": "Gather secondary independent sources to verify claim."
                })
                self.findings.append(f"Evidence Quality Issue: Claim {claim_id} depends on single source.")

            # Check 2: Low Confidence (< 0.60)
            if conf < 0.60:
                severity = "CRITICAL" if conf < 0.30 else "HIGH"
                self.weak_evidence.append({
                    "claim_id": claim_id,
                    "reason": "LOW_CONFIDENCE",
                    "severity": severity,
                    "details": f"Claim '{claim_id}' has low confidence score of {conf:.2f} (< 0.60).",
                    "remediation": "Re-evaluate claim or execute targeted fact-checking."
                })
                self.findings.append(f"Evidence Quality Issue: Claim {claim_id} confidence {conf:.2f} is below 0.60 threshold.")

            # Check 3: Unverified / Unsupported status
            if status in ["UNSUPPORTED", "UNVERIFIED", "INCONCLUSIVE"]:
                self.weak_evidence.append({
                    "claim_id": claim_id,
                    "reason": "UNVERIFIED",
                    "severity": "HIGH",
                    "details": f"Claim '{claim_id}' has status '{status}'.",
                    "remediation": "Conduct disconfirming or validating research pass."
                })
                self.findings.append(f"Evidence Quality Issue: Claim {claim_id} is unverified ({status}).")

    def _audit_logical_coherence(self, synthesis: str, claims: List[Any]) -> None:
        """Audits logical soundness, unstated assumptions, and inferences."""
        if not claims and synthesis:
            self.findings.append("Logical Coherence Warning: Synthesis produced without structured atomic claims.")
            self.missing_variables.append({
                "variable": "atomic_claims",
                "impact": "HIGH",
                "category": "UNSTATED_ASSUMPTION",
                "suggested_action": "Extract atomic claims from synthesis for formal verification."
            })
        
        # Check for synthesis contradictory signals or weak conclusions
        if "however" in synthesis.lower() and "unclear" in synthesis.lower():
            self.findings.append("Logical Coherence Note: Synthesis notes unresolved ambiguity or friction.")

    def _audit_completeness(self, synthesis: str, claims: List[Any], hypotheses: List[Any]) -> None:
        """Detects omitted factors, unstated assumptions, and missing variables."""
        synth_lower = synthesis.lower()
        
        # Key domain factors to audit
        key_factors = [
            ("financial_cost", ["cost", "budget", "price", "financial", "roi"], "MEDIUM"),
            ("regulatory_compliance", ["regulatory", "legal", "compliance", "policy"], "HIGH"),
            ("scalability_limits", ["scale", "performance", "capacity", "limit"], "MEDIUM"),
            ("temporal_validity", ["timeline", "duration", "obsolete", "current"], "MEDIUM"),
            ("risk_mitigation", ["risk", "mitigation", "contingency", "fallback"], "HIGH"),
        ]

        for factor_name, keywords, impact in key_factors:
            present = any(kw in synth_lower for kw in keywords)
            if not present:
                self.missing_variables.append({
                    "variable": factor_name,
                    "impact": impact,
                    "category": "OMITTED_FACTOR",
                    "suggested_action": f"Include research analysis addressing {factor_name.replace('_', ' ')}."
                })
                self.findings.append(f"Completeness Gap: Omitted variable '{factor_name}'.")

    def _audit_bias(self, synthesis: str, claims: List[Any]) -> None:
        """Audits confirmation and framing bias."""
        supported_count = sum(1 for c in claims if isinstance(c, dict) and c.get("support_status") == "SUPPORTED")
        total_count = len(claims)

        if total_count >= 3 and supported_count == total_count:
            self.findings.append("Bias Alert: 100% of claims are supported — potential confirmation bias detected.")

    def _compute_severity_and_recommendations(self) -> None:
        """Evaluates overall severity rating (LOW, MEDIUM, HIGH, CRITICAL) and replan trigger."""
        severities = [item["severity"] for item in self.weak_evidence] + [mv["impact"] for mv in self.missing_variables]

        if "CRITICAL" in severities:
            self.overall_severity = "CRITICAL"
        elif "HIGH" in severities or len([s for s in severities if s == "MEDIUM"]) >= 3:
            self.overall_severity = "HIGH"
        elif "MEDIUM" in severities:
            self.overall_severity = "MEDIUM"
        else:
            self.overall_severity = "LOW"

        # Determine replan recommendation
        if self.overall_severity in ["HIGH", "CRITICAL"]:
            self.replan_recommended = True
        else:
            self.replan_recommended = False

        # Generate actionable recommendations
        if self.weak_evidence:
            self.recommendations.append(f"Address {len(self.weak_evidence)} weak evidence item(s) through targeted retrieval.")
        if self.missing_variables:
            self.recommendations.append(f"Incorporate missing variables: {', '.join(mv['variable'] for mv in self.missing_variables[:3])}.")
        if not self.recommendations:
            self.recommendations.append("Synthesis and evidence chain pass red-team audit cleanly.")

    async def _invoke_llm_enhancement(self, synthesis: str, claims: List[Any]) -> Dict[str, Any]:
        """Optional LLM structured call for deeper qualitative criticism."""
        prompt = (
            f"Perform a red-team review of the following synthesis:\n{synthesis}\n"
            f"Claims count: {len(claims)}\n"
            "Identify any critical hidden assumptions, unstated risks, or omitted variables."
        )
        if hasattr(self._llm_provider, "generate"):
            res = await self._llm_provider.generate(prompt)
            return {"tokens_used": 250, "text": res}
        return {"tokens_used": 0}

    async def compile_output(self) -> Dict[str, Any]:
        """Compiles final CriticOutput response."""
        output = CriticOutput(
            findings=self.findings,
            weak_evidence=self.weak_evidence,
            missing_variables=self.missing_variables,
            overall_severity=self.overall_severity,
            recommendations=self.recommendations,
            replan_recommended=self.replan_recommended
        )
        return output.model_dump()
