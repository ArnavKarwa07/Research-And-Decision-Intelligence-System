"""Unit tests for Phase 6 SQLAlchemy models (Decision)."""
import uuid
import pytest
from app.models.decision import Decision
from app.models.query import Query


def test_decision_model_defaults():
    """Test default values for Decision model."""
    query_id = uuid.uuid4()
    decision = Decision(
        query_id=query_id,
        recommendation="Proceed with Cloud Native architecture",
        confidence=0.88
    )

    assert decision.id is not None
    assert isinstance(decision.id, uuid.UUID)
    assert decision.query_id == query_id
    assert decision.recommendation == "Proceed with Cloud Native architecture"
    assert decision.confidence == 0.88
    assert decision.rationale is None
    assert decision.alternatives == []
    assert decision.criteria == []
    assert decision.weighted_matrix == {}
    assert decision.scenarios == {}
    assert decision.sensitivity_analysis == {}
    assert decision.expected_values == {}
    assert decision.key_risks == []
    assert decision.assumptions == []
    assert decision.decision_triggers == []
    assert decision.metadata_ == {}


def test_decision_model_custom_values():
    """Test Decision model with explicit custom values and metadata alias."""
    dec_id = uuid.uuid4()
    query_id = uuid.uuid4()
    decision = Decision(
        id=dec_id,
        query_id=query_id,
        recommendation="Hybrid Deployment",
        confidence=0.92,
        rationale="Balances operational cost and compliance requirements",
        alternatives=[{"id": "opt-1", "name": "Cloud Native"}, {"id": "opt-2", "name": "On-Prem"}],
        criteria=[{"id": "crit-1", "name": "Cost", "weight": 0.5}],
        weighted_matrix={"opt-1": {"crit-1": 0.85}},
        scenarios={"base": {"probability": 0.7}},
        sensitivity_analysis={"switch_points": []},
        expected_values={"opt-1": 82.5},
        key_risks=["Data sovereignty regulations"],
        assumptions=["Bandwidth is not bottlenecked"],
        decision_triggers=[{"condition": "Cloud egress cost > $5k/mo", "action": "Re-evaluate"}],
        metadata={"generated_by": "DecisionAgent", "version": "1.0"}
    )

    assert decision.id == dec_id
    assert decision.query_id == query_id
    assert decision.recommendation == "Hybrid Deployment"
    assert decision.confidence == 0.92
    assert decision.rationale == "Balances operational cost and compliance requirements"
    assert len(decision.alternatives) == 2
    assert len(decision.criteria) == 1
    assert decision.weighted_matrix["opt-1"]["crit-1"] == 0.85
    assert decision.scenarios["base"]["probability"] == 0.7
    assert decision.expected_values["opt-1"] == 82.5
    assert "Data sovereignty regulations" in decision.key_risks
    assert "Bandwidth is not bottlenecked" in decision.assumptions
    assert len(decision.decision_triggers) == 1
    assert decision.metadata_["generated_by"] == "DecisionAgent"


def test_query_decision_relationship():
    """Test Query model contains relationship collection for decisions."""
    query = Query(text="What is the best scaling strategy?")
    assert hasattr(query, "decisions")
