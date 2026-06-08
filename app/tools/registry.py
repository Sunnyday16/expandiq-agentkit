from typing import Any

from app.tools.base import ToolDefinition, ToolError, ToolResult

_transient_attempts_by_key: dict[str, int] = {}


def reset_tool_state() -> None:
    _transient_attempts_by_key.clear()


async def search_docs(args: dict[str, Any]) -> ToolResult:
    query = str(args.get("q", "")).strip()
    if not query:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_argument",
                message="search_docs requires a non-empty q argument.",
                recoverable=False,
            ),
        )
    return ToolResult(
        ok=True,
        data={
            "matches": [
                {"id": "doc-q3", "title": "Q3 revenue summary"},
                {"id": "doc-runbook", "title": "AgentKit operating notes"},
            ]
        },
    )


async def fetch_doc(args: dict[str, Any]) -> ToolResult:
    doc_id = str(args.get("id", "")).strip()
    docs = {
        "doc-q3": "Q3 revenue increased due to enterprise expansion and lower churn.",
        "doc-runbook": "AgentKit runs are bounded by step, cost, timeout and stuck guards.",
    }
    if doc_id not in docs:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="not_found",
                message=f"Document {doc_id or '<empty>'} was not found.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data={"id": doc_id, "content": docs[doc_id]})


async def send_email(args: dict[str, Any]) -> ToolResult:
    if not args.get("idempotency_key"):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="missing_idempotency_key",
                message="send_email requires an idempotency_key because it is non-idempotent.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data={"message_id": "msg-001", "status": "queued"})


async def create_calendar_event(args: dict[str, Any]) -> ToolResult:
    title = str(args.get("title", "")).strip()
    if not title:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_argument",
                message="create_calendar_event requires a title.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data={"event_id": "evt-001", "title": title})


async def query_sql(args: dict[str, Any]) -> ToolResult:
    query = str(args.get("query", "")).strip()
    if not query.lower().startswith("select"):
        return ToolResult(
            ok=False,
            error=ToolError(
                code="unsafe_query",
                message="Only SELECT queries are allowed in the mock SQL tool.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data={"rows": [{"customer_count": 42, "plan": "enterprise"}]})


async def summarise_text(args: dict[str, Any]) -> ToolResult:
    text = str(args.get("text", "")).strip()
    if not text:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_argument",
                message="summarise_text requires text.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data={"summary": text[:120]})


async def translate(args: dict[str, Any]) -> ToolResult:
    text = str(args.get("text", "")).strip()
    target_language = str(args.get("target_language", "")).strip()
    if not text or not target_language:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_argument",
                message="translate requires text and target_language.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data={"translated_text": f"{text} [{target_language}]"})


async def fetch_weather(args: dict[str, Any]) -> ToolResult:
    city = str(args.get("city", "")).strip()
    if not city:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_argument",
                message="fetch_weather requires city.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data={"city": city, "forecast": "mild and clear"})


async def lookup_contact(args: dict[str, Any]) -> ToolResult:
    name = str(args.get("name", "")).strip().lower()
    contacts = {
        "alex": {"email": "alex@example.com", "name": "Alex"},
        "riley": {"email": "riley@example.com", "name": "Riley"},
        "sunny": {"email": "sunny@example.com", "name": "Sunny"},
    }
    if name not in contacts:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="not_found",
                message=f"Contact {name or '<empty>'} was not found.",
                recoverable=False,
            ),
        )
    return ToolResult(ok=True, data=contacts[name])


async def web_search(args: dict[str, Any]) -> ToolResult:
    query = str(args.get("q", "")).strip()
    if not query:
        return ToolResult(
            ok=False,
            error=ToolError(
                code="invalid_argument",
                message="web_search requires q.",
                recoverable=False,
            ),
        )
    if "transient" in query.lower():
        attempts = _transient_attempts_by_key.get(query, 0) + 1
        _transient_attempts_by_key[query] = attempts
        if attempts == 1:
            return ToolResult(
                ok=False,
                error=ToolError(
                    code="transient_network",
                    message="Temporary search backend failure.",
                    recoverable=True,
                ),
            )
    return ToolResult(ok=True, data={"results": [{"title": "Mock result", "url": "https://example.test"}]})


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "search_docs": ToolDefinition(
        name="search_docs",
        description="Search internal docs by keyword for reports, runbooks and policy text.",
        parallel_safe=True,
        idempotent=True,
        handler=search_docs,
    ),
    "fetch_doc": ToolDefinition(
        name="fetch_doc",
        description="Fetch a full internal document by id after a document search.",
        parallel_safe=True,
        idempotent=True,
        handler=fetch_doc,
    ),
    "send_email": ToolDefinition(
        name="send_email",
        description="Send an email to a contact. Requires recipient, subject and idempotency key.",
        parallel_safe=False,
        idempotent=False,
        handler=send_email,
    ),
    "create_calendar_event": ToolDefinition(
        name="create_calendar_event",
        description="Schedule a calendar event with a title, attendee and time.",
        parallel_safe=False,
        idempotent=False,
        handler=create_calendar_event,
    ),
    "query_sql": ToolDefinition(
        name="query_sql",
        description="Run a safe SELECT query against a mock customer database.",
        parallel_safe=True,
        idempotent=True,
        handler=query_sql,
    ),
    "summarise_text": ToolDefinition(
        name="summarise_text",
        description="Summarise a passage of text into a short answer.",
        parallel_safe=True,
        idempotent=True,
        handler=summarise_text,
    ),
    "translate": ToolDefinition(
        name="translate",
        description="Translate text between languages.",
        parallel_safe=True,
        idempotent=True,
        handler=translate,
    ),
    "fetch_weather": ToolDefinition(
        name="fetch_weather",
        description="Get the current weather forecast for a city.",
        parallel_safe=True,
        idempotent=True,
        handler=fetch_weather,
    ),
    "lookup_contact": ToolDefinition(
        name="lookup_contact",
        description="Find a contact by name before sending email or scheduling meetings.",
        parallel_safe=True,
        idempotent=True,
        handler=lookup_contact,
    ),
    "web_search": ToolDefinition(
        name="web_search",
        description="Search the web for public information and current-looking references.",
        parallel_safe=True,
        idempotent=True,
        handler=web_search,
    ),
}
