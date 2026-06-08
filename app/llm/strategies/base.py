from abc import ABC, abstractmethod
from typing import Any

from app.tools.base import ToolDefinition

MockDecision = dict[str, Any]


def tool_call_decision(tool: str, args: dict[str, Any], cost: float) -> MockDecision:
    return {
        "type": "tool_call",
        "tool": tool,
        "args": args,
        "cost": cost,
    }


def final_decision(content: str, cost: float = 0.001) -> MockDecision:
    return {
        "type": "final",
        "content": content,
        "cost": cost,
    }


class MockStrategy(ABC):
    @abstractmethod
    def matches(self, goal: str) -> bool:
        """Return true when this strategy should handle the goal."""

    @abstractmethod
    def decide(
        self,
        goal: str,
        past_steps: list[dict[str, Any]],
        candidate_tools: list[ToolDefinition],
    ) -> MockDecision:
        """Return the next deterministic mock LLM decision."""
