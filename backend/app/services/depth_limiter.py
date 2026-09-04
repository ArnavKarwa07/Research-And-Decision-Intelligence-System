"""Depth Limiter Service for Agent Nesting and Parallel Branch Width Enforcement.

Enforces maximum agent nesting/spawning depth limits and maximum parallel branch
width limits to prevent uncontrolled recursive loops or branch explosion.
"""
from dataclasses import dataclass, field
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class DepthLimitExceededError(Exception):
    """Raised when an agent attempts to spawn beyond the maximum allowed nesting depth."""

    def __init__(self, depth: int, max_depth: int, agent_id: str, parent_id: Optional[str] = None):
        self.depth = depth
        self.max_depth = max_depth
        self.agent_id = agent_id
        self.parent_id = parent_id
        parent_str = f" from parent {parent_id}" if parent_id else ""
        super().__init__(f"Agent depth limit exceeded{parent_str}: depth {depth} > max_depth {max_depth}")


class WidthLimitExceededError(Exception):
    """Raised when a parent agent attempts to spawn more parallel child branches than allowed."""

    def __init__(self, current_width: int, max_width: int, parent_id: str):
        self.current_width = current_width
        self.max_width = max_width
        self.parent_id = parent_id
        super().__init__(f"Parallel branch width limit exceeded for parent {parent_id}: {current_width} > max_width {max_width}")


@dataclass
class AgentNode:
    """Represents a node in the agent execution hierarchy tree."""
    agent_id: str
    parent_id: Optional[str] = None
    agent_type: str = ""
    depth: int = 0
    children: list[str] = field(default_factory=list)
    active_children: set[str] = field(default_factory=set)
    completed: bool = False


class DepthLimiter:
    """Service to enforce nesting depth and parallel width limits across agent hierarchies."""

    def __init__(self, max_depth: int = 3, max_width: int = 5):
        self.max_depth = max_depth
        self.max_width = max_width
        self._nodes: dict[str, AgentNode] = {}

    def register_agent(
        self,
        agent_id: str,
        parent_id: Optional[str] = None,
        agent_type: str = "",
    ) -> AgentNode:
        """
        Register a new agent in the hierarchy tree.
        Validates depth and width limits.
        Raises DepthLimitExceededError or WidthLimitExceededError if violated.
        """
        if agent_id in self._nodes:
            return self._nodes[agent_id]

        depth = 0
        if parent_id is not None:
            if parent_id not in self._nodes:
                raise ValueError(f"Parent agent '{parent_id}' is not registered in DepthLimiter.")

            parent = self._nodes[parent_id]
            depth = parent.depth + 1

            if depth > self.max_depth:
                raise DepthLimitExceededError(depth=depth, max_depth=self.max_depth, agent_id=agent_id, parent_id=parent_id)

            if len(parent.active_children) >= self.max_width:
                raise WidthLimitExceededError(
                    current_width=len(parent.active_children) + 1,
                    max_width=self.max_width,
                    parent_id=parent_id,
                )

            parent.children.append(agent_id)
            parent.active_children.add(agent_id)

        node = AgentNode(
            agent_id=agent_id,
            parent_id=parent_id,
            agent_type=agent_type,
            depth=depth,
        )
        self._nodes[agent_id] = node
        logger.info(f"Registered agent '{agent_id}' (type: {agent_type}) at depth {depth} under parent '{parent_id}'.")
        return node

    def can_spawn_child(self, parent_id: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Check whether a child can be spawned under parent_id without raising exceptions.
        Returns: (allowed: bool, reason: str | None)
        """
        if parent_id is None:
            return True, None

        if parent_id not in self._nodes:
            return False, f"Parent agent '{parent_id}' is not registered."

        parent = self._nodes[parent_id]
        child_depth = parent.depth + 1

        if child_depth > self.max_depth:
            return False, f"Child depth {child_depth} exceeds max_depth {self.max_depth}"

        if len(parent.active_children) >= self.max_width:
            return False, f"Parent active child count {len(parent.active_children)} reaches max_width {self.max_width}"

        return True, None

    def complete_agent(self, agent_id: str) -> None:
        """Mark an agent as completed and release active child slot from parent."""
        if agent_id not in self._nodes:
            return

        node = self._nodes[agent_id]
        node.completed = True

        if node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            parent.active_children.discard(agent_id)

        logger.info(f"Completed agent '{agent_id}', active child slot released from parent '{node.parent_id}'.")

    def get_agent(self, agent_id: str) -> Optional[AgentNode]:
        return self._nodes.get(agent_id)

    def get_depth(self, agent_id: str) -> int:
        node = self.get_agent(agent_id)
        return node.depth if node else 0

    def get_active_width(self, parent_id: str) -> int:
        parent = self.get_agent(parent_id)
        return len(parent.active_children) if parent else 0

    def get_tree(self, root_id: str) -> dict[str, Any]:
        """Build dictionary representation of agent tree starting from root_id."""
        if root_id not in self._nodes:
            return {}

        node = self._nodes[root_id]
        return {
            "agent_id": node.agent_id,
            "agent_type": node.agent_type,
            "depth": node.depth,
            "completed": node.completed,
            "children": [self.get_tree(child_id) for child_id in node.children],
        }

    def reset(self) -> None:
        """Clear all registered nodes."""
        self._nodes.clear()


# Default singleton instance
depth_limiter = DepthLimiter()
