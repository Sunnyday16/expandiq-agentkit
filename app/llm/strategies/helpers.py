import re
from typing import Any

EMAIL_PATTERN = re.compile(r"\bemail\s+(?P<name>[a-z][a-z0-9_-]*)", re.IGNORECASE)


def has_tool(past_steps: list[dict[str, Any]], tool_name: str) -> bool:
    return any(step["tool_name"] == tool_name for step in past_steps)


def last_tool_failed(past_steps: list[dict[str, Any]], code: str) -> bool:
    if not past_steps:
        return False
    error = past_steps[-1].get("result", {}).get("error")
    return bool(error and error.get("code") == code)


def email_recipient(goal: str) -> tuple[str, str]:
    match = EMAIL_PATTERN.search(goal)
    name = match.group("name") if match else "alex"
    return name.capitalize(), f"{name.lower()}@example.com"
