from typing import Any, Literal

from app.llm.strategies.base import MockDecision
from app.llm.strategies.registry import MOCK_STRATEGIES
from app.tools.base import ToolDefinition

MockLLMType = Literal["tool_call", "final"]


def mock_llm(
    goal: str,
    past_steps: list[dict[str, Any]],
    candidate_tools: list[ToolDefinition],
) -> MockDecision:
    for strategy in MOCK_STRATEGIES:
        if strategy.matches(goal):
            return strategy.decide(goal, past_steps, candidate_tools)
    raise RuntimeError("No mock strategy matched the goal.")
