import re

from app.tools.base import ToolDefinition

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def tool_search_text(tool: ToolDefinition) -> str:
    return f"{tool.name.replace('_', ' ')} {tool.description.replace('_', ' ')}"


def retrieve_tools(
    goal: str,
    registry: dict[str, ToolDefinition],
    *,
    top_k: int = 5,
) -> list[ToolDefinition]:
    goal_tokens = set(tokenize(goal))
    scored: list[tuple[float, str, ToolDefinition]] = []
    for tool in registry.values():
        tool_tokens = set(tokenize(tool_search_text(tool)))
        score = float(len(goal_tokens & tool_tokens))
        scored.append((score, tool.name, tool))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [tool for score, _, tool in scored[:top_k] if score > 0] or list(registry.values())[:top_k]
