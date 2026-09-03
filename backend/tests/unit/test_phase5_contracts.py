import pytest
from app.agents.agent_contracts import (
    HypothesisItem,
    HypothesisAgentInput,
    HypothesisAgentOutput,
    FalsificationInput,
    FalsificationOutput,
    CriticInput,
    CriticOutput,
)

def test_hypothesis_contracts():
    h = HypothesisItem(hypothesis_id="h1", statement="Test statement", initial_confidence=0.6)
    inp = HypothesisAgentInput(query_text="Quantum Computing scalability")
    out = HypothesisAgentOutput(hypotheses=[h], investigation_priorities=["Priority 1"])

    assert out.hypotheses[0].hypothesis_id == "h1"
    assert out.investigation_priorities == ["Priority 1"]


def test_falsification_contracts():
    h = HypothesisItem(hypothesis_id="h1", statement="Test statement")
    f_inp = FalsificationInput(hypothesis=h, research_context="Context")
    f_out = FalsificationOutput(hypothesis_id="h1", updated_confidence=0.4)

    assert f_out.hypothesis_id == "h1"
    assert f_out.updated_confidence == 0.4


def test_critic_contracts():
    c_inp = CriticInput(synthesis="Synthesis text")
    c_out = CriticOutput(overall_severity="HIGH", replan_recommended=True)

    assert c_out.overall_severity == "HIGH"
    assert c_out.replan_recommended is True
