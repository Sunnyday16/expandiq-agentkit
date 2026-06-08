from typing import Any

from app.llm.strategies.base import MockDecision, MockStrategy, final_decision, tool_call_decision
from app.llm.strategies.helpers import has_tool
from app.tools.base import ToolDefinition


class TransientMockStrategy(MockStrategy):
    def matches(self, goal: str) -> bool:
        return "transient" in goal.lower()

    def decide(
        self,
        goal: str,
        past_steps: list[dict[str, Any]],
        candidate_tools: list[ToolDefinition],
    ) -> MockDecision:
        del goal, candidate_tools
        if not has_tool(past_steps, "web_search"):
            return tool_call_decision("web_search", {"q": "transient agent runtime search"}, 0.002)
        return final_decision("Web search recovered after a transient failure.")
