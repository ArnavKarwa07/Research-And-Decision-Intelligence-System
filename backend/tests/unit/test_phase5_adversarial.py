"""Adversarial Review & Edge Case Audit Suite for Phase 5 (P5-17).
Aggressively tests edge cases, mathematical assumptions, division by zero, budget limits,
loop deadlocks, malformed inputs, and circuit breakers across Phase 5 components.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.hypothesis import Hypothesis
from app.models.critique_report import CritiqueReport
from app.schemas.hypothesis import HypothesisCreate, EvidenceMapEntry, EvidenceRelationship
from app.agents.hypothesis import HypothesisAgent
from app.agents.falsification import FalsificationAgent
from app.agents.critic import CriticAgent
from app.services.hypothesis_service import HypothesisService
from app.services.critique_service import CritiqueService
from app.services.self_challenge_service import SelfChallengeService


# --- 1. Mathematical Assumptions & Division by Zero Audits ---

def test_recalculate_confidence_division_by_zero_and_zero_weight():
    """Audit: recalculate_confidence must never raise ZeroDivisionError when total weight = 0."""
    service = HypothesisService()
    
    # Total weight = 0.0
    zero_weights = [
        {"relationship": "supports", "weight": 0.0},
        {"relationship": "falsifies", "weight": 0.0}
    ]
    res = service.recalculate_confidence(zero_weights)
    assert res == 0.5


def test_recalculate_confidence_malformed_and_extreme_inputs():
    """Audit: recalculate_confidence handles malformed, None, negative, and extreme weights without crashing."""
    service = HypothesisService()

    extreme_inputs = [
        None,  # Not a dict
        "invalid_string",  # Not a dict
        {"relationship": "supports", "weight": None},  # None weight
        {"relationship": "supports", "weight": "not_a_number"},  # String weight
        {"relationship": "supports", "weight": -99.9},  # Negative weight
        {"relationship": "falsifies", "weight": 1e9},  # Extremely large weight
        {"relationship": "unknown_rel", "weight": 1.0}  # Unknown relationship
    ]

    # Must not raise an exception
    res = service.recalculate_confidence(extreme_inputs)
    assert 0.0 <= res <= 1.0


def test_falsification_calculate_confidence_zero_weight():
    """Audit: FalsificationAgent.calculate_confidence handles zero total weight and empty items."""
    agent = FalsificationAgent()

    # Empty list -> returns initial
    assert agent.calculate_confidence(initial=0.45, evidence_items=[]) == 0.45

    # Zero weight items -> returns initial
    zero_items = [{"relationship": "SUPPORTS", "weight": 0.0}]
    assert agent.calculate_confidence(initial=0.45, evidence_items=zero_items) == 0.45


# --- 2. Loop Deadlocks & Budget Overrun Audits ---

@pytest.mark.asyncio
async def test_falsification_agent_loop_deadlock_prevention():
    """Audit: FalsificationAgent halts execution when max_falsification_attempts cap is reached."""
    agent = FalsificationAgent()
    agent.web_search_tool.search = AsyncMock(return_value=[])

    input_data = {
        "hypothesis": {
            "hypothesis_id": "hyp-deadlock-check",
            "statement": "Infinite attempt prevention check",
            "initial_confidence": 0.5,
            "max_falsification_attempts": 3
        }
    }

    # Run step 5 times (exceeding limit of 3)
    for _ in range(3):
        res = await agent.step(input_data)
        assert res.action == "falsify_search"

    # Step 4 must return action='stop'
    over_res = await agent.step(input_data)
    assert over_res.action == "stop"
    assert over_res.should_continue is False


@pytest.mark.asyncio
async def test_self_challenge_circuit_breaker_prevents_infinite_replanning():
    """Audit: SelfChallengeService circuit breaker unconditionally terminates after max 3 replan iterations."""
    service = SelfChallengeService(db=None)
    query_id = uuid.uuid4()

    # Force run_falsification_pass to always return falsified status
    async def mock_falsification(q_id, hyps, research_context):
        return [
            {"id": "h1", "statement": "Falsified hyp", "status": "falsified", "confidence": 0.1}
        ]

    service.run_falsification_pass = mock_falsification

    # Pipeline MUST break loop after 3 replan iterations
    res = await service.run_self_challenge(query_id)
    assert res["replan_count"] == 3
    assert res["finalized_with_caveats"] is True
    assert res["final_status"] == "finalized_with_caveats"


# --- 3. Missing Validation & Edge Case Audits ---

@pytest.mark.asyncio
async def test_hypothesis_agent_handles_empty_query():
    """Audit: HypothesisAgent generates fallback hypotheses gracefully when query_text is empty or None."""
    agent = HypothesisAgent()

    result = await agent.step({"query_text": "", "existing_claims": []})

    assert result.action == "generate_hypotheses"
    assert len(result.result["hypotheses"]) >= 3


@pytest.mark.asyncio
async def test_critic_agent_handles_empty_synthesis_and_claims():
    """Audit: CriticAgent handles completely empty synthesis and claims lists without crashing."""
    agent = CriticAgent()

    result = await agent.step({"synthesis": "", "claims": [], "evidence_chain": []})

    assert result.action == "critique_pass"
    output = await agent.compile_output()
    assert "overall_severity" in output
    assert output["overall_severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@pytest.mark.asyncio
async def test_all_falsified_hypotheses_scenario():
    """Audit: System behavior when all generated hypotheses are falsified."""
    service = SelfChallengeService(db=None)
    query_id = uuid.uuid4()

    hyps = [
        {"id": "h1", "statement": "Statement 1", "status": "falsified", "confidence": 0.1},
        {"id": "h2", "statement": "Statement 2", "status": "falsified", "confidence": 0.1}
    ]

    critique = await service.run_critic_pass(query_id, "Query text", hyps, iteration=1)

    assert critique["overall_severity"] == "HIGH"
    assert critique["replan_triggered"] is True
    assert len(critique["weak_evidence"]) >= 1
