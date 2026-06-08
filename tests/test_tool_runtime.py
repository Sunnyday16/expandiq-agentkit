import pytest

from app.services.agent_runtime import dispatch_tool, is_transient_error
from app.tools.base import ToolError, ToolResult
from app.tools.registry import reset_tool_state


def test_retry_classifier_detects_recoverable_errors() -> None:
    result = ToolResult(
        ok=False,
        error=ToolError(code="transient_network", message="temporary failure", recoverable=True),
    )

    assert is_transient_error(result)


def test_retry_classifier_rejects_semantic_errors() -> None:
    result = ToolResult(
        ok=False,
        error=ToolError(code="invalid_argument", message="missing arg", recoverable=False),
    )

    assert not is_transient_error(result)


@pytest.mark.asyncio
async def test_dispatch_retries_recoverable_tool_error() -> None:
    reset_tool_state()

    result = await dispatch_tool("web_search", {"q": "transient agent runtime search"})

    assert result.ok
    assert result.data == {
        "results": [{"title": "Mock result", "url": "https://example.test"}]
    }


@pytest.mark.asyncio
async def test_dispatch_surfaces_semantic_error_without_retry() -> None:
    result = await dispatch_tool("send_email", {"to": "alex@example.com"})

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "missing_idempotency_key"
