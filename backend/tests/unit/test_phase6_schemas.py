"""Unit tests for Phase 6 Pydantic schemas (Decision Intelligence)."""
import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas.decision import (
    DecisionCriterion,
    AlternativeOptionInput,
    AlternativeOptionScored,
    ScenarioDefinition,
    ScenarioOutcome,
    SensitivitySwitchPoint,
    DecisionTrigger,
    DecisionCreateRequest,
    DecisionResponse,
    DecisionListResponse,
    SensitivityRequest,
    ScenarioRequest,
)
from app.models.decision import Decision


def test_decision_criterion_validation():
    """Test DecisionCriterion valid data and weight boundary constraints."""
    crit = DecisionCriterion(
        id="c1",
        name="Operational Cost",
        weight=0.35,
        description="Total annual operational expense"
    )
    assert crit.id == "c1"
    assert crit.name == "Operational Cost"
    assert crit.weight == 0.35
    assert crit.description == "Total annual operational expense"

    # Weight > 1.0 should fail
    with pytest.raises(ValidationError):
        DecisionCriterion(id="c2", name="Risk", weight=1.2)

    # Weight < 0.0 should fail
    with pytest.raises(ValidationError):
        DecisionCriterion(id="c3", name="Speed", weight=-0.05)


def test_alternative_option_schemas():
    """Test AlternativeOptionInput and AlternativeOptionScored."""
    opt_in = AlternativeOptionInput(
        id="opt-a",
        name="Microservices Architecture",
        description="Distributed containerized services",
        pros=["Independent deployments", "Technology flexibility"],
        cons=["Distributed complexity"]
    )
    assert opt_in.id == "opt-a"
    assert len(opt_in.pros) == 2
    assert len(opt_in.cons) == 1

    scored = AlternativeOptionScored(
        id="opt-a",
        name="Microservices Architecture",
        scores={"c1": 0.8, "c2": 0.6},
        weighted_score=0.74,
        risks=["Network latency overhead"]
    )
    assert scored.id == "opt-a"
    assert scored.scores["c1"] == 0.8
    assert scored.weighted_score == 0.74
    assert len(scored.risks) == 1
    assert scored.pros == []
    assert scored.cons == []


def test_scenario_schemas():
    """Test ScenarioDefinition and ScenarioOutcome."""
    scen = ScenarioDefinition(
        name="recession",
        probability=0.25,
        description="Downturn scenario with reduced budget"
    )
    assert scen.name == "recession"
    assert scen.probability == 0.25

    # Probability bounds
    with pytest.raises(ValidationError):
        ScenarioDefinition(name="invalid", probability=1.5)

    with pytest.raises(ValidationError):
        ScenarioDefinition(name="invalid", probability=-0.1)

    outcome = ScenarioOutcome(
        scenario_name="recession",
        alternative_id="opt-a",
        projected_value=65.0,
        notes="Tight budget dampens migration"
    )
    assert outcome.scenario_name == "recession"
    assert outcome.alternative_id == "opt-a"
    assert outcome.projected_value == 65.0


def test_sensitivity_schemas():
    """Test SensitivitySwitchPoint and SensitivityRequest."""
    sp = SensitivitySwitchPoint(
        criterion_id="c1",
        criterion_name="Cost",
        original_weight=0.3,
        threshold_weight=0.52,
        switches_from="opt-a",
        switches_to="opt-b",
        notes="Option B becomes superior if cost weight exceeds 52%"
    )
    assert sp.criterion_id == "c1"
    assert sp.original_weight == 0.3
    assert sp.threshold_weight == 0.52
    assert sp.switches_from == "opt-a"
    assert sp.switches_to == "opt-b"

    req_default = SensitivityRequest()
    assert req_default.weight_delta == 0.05
    assert req_default.target_criteria is None

    req_custom = SensitivityRequest(weight_delta=0.1, target_criteria=["c1", "c2"])
    assert req_custom.weight_delta == 0.1
    assert req_custom.target_criteria == ["c1", "c2"]


def test_decision_trigger_schema():
    """Test DecisionTrigger validation and default severity."""
    trig = DecisionTrigger(
        condition="Vendor API latency > 500ms for 3 consecutive days",
        threshold="500ms",
        action="Trigger failover to secondary provider"
    )
    assert trig.severity == "medium"
    assert trig.threshold == "500ms"

    trig_high = DecisionTrigger(
        condition="Budget exceeded",
        threshold="$100k",
        action="Halt expansion",
        severity="critical"
    )
    assert trig_high.severity == "critical"


def test_decision_create_and_scenario_request():
    """Test DecisionCreateRequest and ScenarioRequest."""
    qid = uuid.uuid4()
    crit = DecisionCriterion(id="c1", name="Security", weight=1.0)
    opt = AlternativeOptionInput(id="opt1", name="Option 1")
    scen = ScenarioDefinition(name="base", probability=1.0)

    req = DecisionCreateRequest(
        query_id=qid,
        alternatives=[opt],
        criteria=[crit],
        scenarios=[scen]
    )
    assert req.query_id == qid
    assert len(req.alternatives) == 1
    assert len(req.criteria) == 1
    assert len(req.scenarios) == 1

    scen_req = ScenarioRequest(scenarios=[scen])
    assert len(scen_req.scenarios) == 1


def test_decision_response_from_orm():
    """Test DecisionResponse populates correctly from SQLAlchemy model."""
    qid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    dec = Decision(
        query_id=qid,
        recommendation="Adopt Architecture A",
        confidence=0.9,
        rationale="Superior security and performance profile",
        alternatives=[{"id": "a1", "name": "Arch A", "weighted_score": 0.85}],
        criteria=[{"id": "c1", "name": "Security", "weight": 0.6}],
        weighted_matrix={"a1": {"c1": 0.85}},
        scenarios={"base": {"probability": 1.0}},
        sensitivity_analysis={"switch_points": []},
        expected_values={"a1": 85.0},
        key_risks=["Initial migration cost"],
        assumptions=["Staff has Kubernetes skills"],
        decision_triggers=[{"condition": "Migration delay > 2 months", "action": "Hire contractors"}],
        metadata={"generated_by": "DecisionAgent"}
    )
    dec.created_at = now
    dec.updated_at = now

    resp = DecisionResponse.model_validate(dec)
    assert resp.id == dec.id
    assert resp.query_id == qid
    assert resp.recommendation == "Adopt Architecture A"
    assert resp.confidence == 0.9
    assert resp.rationale == "Superior security and performance profile"
    assert len(resp.alternatives) == 1
    assert len(resp.criteria) == 1
    assert resp.metadata == {"generated_by": "DecisionAgent"}
    assert resp.created_at == now

    dumped = resp.model_dump(by_alias=True)
    assert "metadata" in dumped
    assert dumped["metadata"]["generated_by"] == "DecisionAgent"


def test_decision_list_response():
    """Test DecisionListResponse schema."""
    qid = uuid.uuid4()
    resp = DecisionResponse(
        id=uuid.uuid4(),
        query_id=qid,
        recommendation="Rec A",
        confidence=0.8
    )
    list_resp = DecisionListResponse(decisions=[resp], total=1)
    assert list_resp.total == 1
    assert len(list_resp.decisions) == 1
