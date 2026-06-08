from typing import Any

from app.llm.strategies.base import MockDecision, MockStrategy, final_decision, tool_call_decision
from app.llm.strategies.helpers import bad_email_recipient, has_tool, last_tool_failed
from app.tools.base import ToolDefinition


class BadEmailMockStrategy(MockStrategy):
    def matches(self, goal: str) -> bool:
        return "bad email" in goal.lower()

    def decide(
        self,
        goal: str,
        past_steps: list[dict[str, Any]],
        candidate_tools: list[ToolDefinition],
    ) -> MockDecision:
        del candidate_tools
        recipient_name, recipient_email = bad_email_recipient(goal)
        if not has_tool(past_steps, "send_email"):
            return tool_call_decision(
                "send_email",
                {"to": recipient_email, "subject": "Missing key"},
                0.002,
            )
        if last_tool_failed(past_steps, "missing_idempotency_key"):
            return tool_call_decision(
                "send_email",
                {
                    "to": recipient_email,
                    "subject": "Fixed key",
                    "body": "Retry with key.",
                    "idempotency_key": "agentkit-email-002",
                },
                0.002,
            )
        return final_decision(f"Email error was corrected and queued for {recipient_name}.")
