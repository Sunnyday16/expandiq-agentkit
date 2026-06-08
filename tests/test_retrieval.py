from typing import Any

from app.tools.base import ToolDefinition, ToolResult
from app.tools.registry import TOOL_REGISTRY
from app.tools.retrieval import retrieve_tools, tokenize, tool_search_text


async def noop_handler(_: dict[str, Any]) -> ToolResult:
    return ToolResult(ok=True, data={})


def test_retrieval_ranks_goal_relevant_tools() -> None:
    tools = retrieve_tools("send an email to Alex", TOOL_REGISTRY, top_k=3)

    names = [tool.name for tool in tools]
    assert "send_email" in names
    assert "lookup_contact" in names
    assert names[0] == "send_email"


def test_retrieval_resists_noisy_description_overlap() -> None:
    registry = {
        "send_email": ToolDefinition(
            name="send_email",
            description="Send an email to a contact. Requires recipient and idempotency key.",
            parallel_safe=False,
            idempotent=False,
            handler=noop_handler,
        ),
        "lookup_contact": ToolDefinition(
            name="lookup_contact",
            description="Find a contact before sending email update notes and routing send email work.",
            parallel_safe=True,
            idempotent=True,
            handler=noop_handler,
        ),
    }

    goal = "send email update"
    naive_scores = {
        name: len(set(tokenize(goal)) & set(tokenize(tool_search_text(tool))))
        for name, tool in registry.items()
    }
    tools = retrieve_tools(goal, registry, top_k=2)

    assert naive_scores["lookup_contact"] > naive_scores["send_email"]
    assert tools[0].name == "send_email"
