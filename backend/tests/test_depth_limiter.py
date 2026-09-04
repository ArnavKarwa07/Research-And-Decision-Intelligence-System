"""Unit tests for DepthLimiter agent nesting and parallel branch width enforcement."""

import pytest
from app.services.depth_limiter import (
    DepthLimiter,
    DepthLimitExceededError,
    WidthLimitExceededError,
)


def test_depth_limiter_root_and_nested_spawning():
    limiter = DepthLimiter(max_depth=3, max_width=3)

    # Root agent
    root = limiter.register_agent(agent_id="root", agent_type="supervisor")
    assert root.depth == 0
    assert root.parent_id is None

    # Depth 1
    child1 = limiter.register_agent(agent_id="child1", parent_id="root", agent_type="researcher")
    assert child1.depth == 1

    # Depth 2
    child2 = limiter.register_agent(agent_id="child2", parent_id="child1", agent_type="fact_checker")
    assert child2.depth == 2

    # Depth 3
    child3 = limiter.register_agent(agent_id="child3", parent_id="child2", agent_type="retrieval")
    assert child3.depth == 3

    # Exceeding depth 3 -> DepthLimitExceededError
    with pytest.raises(DepthLimitExceededError) as exc_info:
        limiter.register_agent(agent_id="child4", parent_id="child3", agent_type="sub_retrieval")
    assert exc_info.value.depth == 4
    assert exc_info.value.max_depth == 3


def test_depth_limiter_width_limit_enforcement():
    limiter = DepthLimiter(max_depth=3, max_width=2)
    limiter.register_agent("root")

    # Spawn 2 parallel children (max_width=2)
    c1 = limiter.register_agent("c1", parent_id="root")
    c2 = limiter.register_agent("c2", parent_id="root")
    assert limiter.get_active_width("root") == 2

    # Attempt 3rd parallel child -> WidthLimitExceededError
    with pytest.raises(WidthLimitExceededError) as exc_info:
        limiter.register_agent("c3", parent_id="root")
    assert exc_info.value.current_width == 3
    assert exc_info.value.max_width == 2

    # Complete child c1 -> active slot released
    limiter.complete_agent("c1")
    assert limiter.get_active_width("root") == 1

    # Now spawning 3rd child succeeds
    c3 = limiter.register_agent("c3", parent_id="root")
    assert c3.depth == 1
    assert limiter.get_active_width("root") == 2


def test_can_spawn_child_check():
    limiter = DepthLimiter(max_depth=2, max_width=1)
    limiter.register_agent("root")

    allowed, reason = limiter.can_spawn_child("root")
    assert allowed is True
    assert reason is None

    limiter.register_agent("c1", parent_id="root")

    # Width limit hit
    allowed, reason = limiter.can_spawn_child("root")
    assert allowed is False
    assert "reaches max_width" in reason

    # Depth check
    limiter.register_agent("c1_child", parent_id="c1")  # depth 2
    allowed, reason = limiter.can_spawn_child("c1_child")
    assert allowed is False
    assert "exceeds max_depth" in reason


def test_get_tree_and_reset():
    limiter = DepthLimiter(max_depth=3, max_width=5)
    limiter.register_agent("root", agent_type="supervisor")
    limiter.register_agent("child1", parent_id="root", agent_type="sub_1")
    limiter.register_agent("child2", parent_id="root", agent_type="sub_2")

    tree = limiter.get_tree("root")
    assert tree["agent_id"] == "root"
    assert len(tree["children"]) == 2
    assert tree["children"][0]["agent_id"] == "child1"

    limiter.reset()
    assert limiter.get_agent("root") is None
