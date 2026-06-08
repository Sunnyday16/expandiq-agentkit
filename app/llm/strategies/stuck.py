from typing import Any

from app.llm.strategies.base import MockDecision, MockStrategy, tool_call_decision
from app.tools.base import ToolDefinition


class StuckMockStrategy(MockStrategy):
    def matches(self, goal: str) -> bool:
        return "stuck" in goal.lower()

    def decide(
        self,
        goal: str,
        past_steps: list[dict[str, Any]],
        candidate_tools: list[ToolDefinition],
    ) -> MockDecision:
        del goal, past_steps, candidate_tools
        return tool_call_decision("search_docs", {"q": "repeat forever"}, 0.002)
