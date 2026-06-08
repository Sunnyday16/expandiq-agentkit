import math
import re
from collections import Counter

from app.tools.base import ToolDefinition

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
BM25_K1 = 1.5
BM25_B = 0.75


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def tool_search_text(tool: ToolDefinition) -> str:
    return f"{tool.name.replace('_', ' ')} {tool.description.replace('_', ' ')}"


def bm25_score(
    query_tokens: list[str],
    document_tokens: list[str],
    document_frequency: dict[str, int],
    *,
    document_count: int,
    average_document_length: float,
) -> float:
    if not query_tokens or not document_tokens:
        return 0.0

    token_counts = Counter(document_tokens)
    document_length = len(document_tokens)
    score = 0.0
    for token in set(query_tokens):
        term_frequency = token_counts[token]
        if term_frequency == 0:
            continue

        inverse_document_frequency = math.log(
            1 + ((document_count - document_frequency[token] + 0.5) / (document_frequency[token] + 0.5))
        )
        length_normalizer = 1 - BM25_B + (BM25_B * document_length / average_document_length)
        score += inverse_document_frequency * (
            (term_frequency * (BM25_K1 + 1)) / (term_frequency + (BM25_K1 * length_normalizer))
        )
    return score


def tool_name_boost(goal_tokens: list[str], tool: ToolDefinition) -> float:
    name_tokens = set(tokenize(tool.name.replace("_", " ")))
    return 0.5 * len(set(goal_tokens) & name_tokens)


def retrieve_tools(
    goal: str,
    registry: dict[str, ToolDefinition],
    *,
    top_k: int = 5,
) -> list[ToolDefinition]:
    goal_tokens = tokenize(goal)
    documents = {tool.name: tokenize(tool_search_text(tool)) for tool in registry.values()}
    document_count = len(documents)
    average_document_length = sum(len(tokens) for tokens in documents.values()) / document_count
    document_frequency: dict[str, int] = {}
    for token in {token for tokens in documents.values() for token in set(tokens)}:
        document_frequency[token] = sum(1 for tokens in documents.values() if token in tokens)

    scored: list[tuple[float, str, ToolDefinition]] = []
    for tool in registry.values():
        score = bm25_score(
            goal_tokens,
            documents[tool.name],
            document_frequency,
            document_count=document_count,
            average_document_length=average_document_length,
        )
        score += tool_name_boost(goal_tokens, tool)
        scored.append((score, tool.name, tool))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [tool for score, _, tool in scored[:top_k] if score > 0] or list(registry.values())[:top_k]
