from typing import Any

from app.llm.strategies.base import MockDecision, MockStrategy, final_decision, tool_call_decision
from app.llm.strategies.helpers import email_recipient, has_tool
from app.tools.base import ToolDefinition


class EmailMockStrategy(MockStrategy):
    def matches(self, goal: str) -> bool:
        return "email" in goal.lower()

    def decide(
        self,
        goal: str,
        past_steps: list[dict[str, Any]],
        candidate_tools: list[ToolDefinition],
    ) -> MockDecision:
        del candidate_tools
        recipient_name, recipient_email = email_recipient(goal)
        if not has_tool(past_steps, "lookup_contact"):
            return tool_call_decision("lookup_contact", {"name": recipient_name}, 0.002)
        if not has_tool(past_steps, "send_email"):
            return tool_call_decision(
                "send_email",
                {
                    "to": recipient_email,
                    "subject": "AgentKit update",
                    "body": "The run completed.",
                    "idempotency_key": "agentkit-email-001",
                },
                0.003,
            )
        return final_decision(f"Email queued for {recipient_name}.")
