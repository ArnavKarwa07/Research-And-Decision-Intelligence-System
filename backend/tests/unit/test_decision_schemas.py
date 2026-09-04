"""Unit tests for decision schemas validation."""
import pytest
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.decision import (
    DecisionCriterion,
    AlternativeOptionInput,
    AlternativeOptionScored,
    ScenarioDefinition,
    DecisionCreateRequest,
    DecisionResponse,
)


def test_decision_criterion_validation():
    crit = DecisionCriterion(id="c1", name="Cost", weight=0.7)
    assert crit.weight == 0.7

    with pytest.raises(ValidationError):
        DecisionCriterion(id="c1", name="Cost", weight=1.5)  # Weight > 1.0

    with pytest.raises(ValidationError):
        DecisionCriterion(id="c1", name="Cost", weight=-0.2)  # Weight < 0.0


def test_scenario_definition_validation():
    sc = ScenarioDefinition(name="Best", probability=0.25)
    assert sc.probability == 0.25

    with pytest.raises(ValidationError):
        ScenarioDefinition(name="Invalid", probability=2.0)


def test_decision_create_request():
    req = DecisionCreateRequest(
        query_id=uuid4(),
        alternatives=[AlternativeOptionInput(id="a1", name="Option A")],
        criteria=[DecisionCriterion(id="c1", name="Cost", weight=1.0)]
    )
    assert len(req.alternatives) == 1
    assert req.criteria[0].name == "Cost"
