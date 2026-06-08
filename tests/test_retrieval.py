from app.tools.registry import TOOL_REGISTRY
from app.tools.retrieval import retrieve_tools


def test_retrieval_ranks_goal_relevant_tools() -> None:
    tools = retrieve_tools("send an email to Alex", TOOL_REGISTRY, top_k=3)

    names = [tool.name for tool in tools]
    assert "send_email" in names
    assert "lookup_contact" in names
    assert names[0] == "send_email"
