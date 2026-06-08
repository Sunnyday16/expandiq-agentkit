from typing import Any

from app.llm.strategies.base import MockDecision, MockStrategy, final_decision, tool_call_decision
from app.llm.strategies.helpers import has_tool
from app.tools.base import ToolDefinition


class RevenueSummaryMockStrategy(MockStrategy):
    def matches(self, goal: str) -> bool:
        del goal
        return True

    def decide(
        self,
        goal: str,
        past_steps: list[dict[str, Any]],
        candidate_tools: list[ToolDefinition],
    ) -> MockDecision:
        del candidate_tools
        if not has_tool(past_steps, "search_docs"):
            return tool_call_decision("search_docs", {"q": goal}, 0.002)
        if not has_tool(past_steps, "fetch_doc"):
            return tool_call_decision("fetch_doc", {"id": "doc-q3"}, 0.002)
        if not has_tool(past_steps, "summarise_text"):
            return tool_call_decision(
                "summarise_text",
                {"text": "Q3 revenue increased due to enterprise expansion and lower churn."},
                0.002,
            )
        return final_decision("Q3 revenue increased due to enterprise expansion and lower churn.")
