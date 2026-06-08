import re
from typing import Any

BAD_EMAIL_PATTERN = re.compile(r"\bbad\s+email\s+(?P<name>[a-z][a-z0-9_-]*)", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\bemail\s+(?P<name>[a-z][a-z0-9_-]*)", re.IGNORECASE)


def has_tool(past_steps: list[dict[str, Any]], tool_name: str) -> bool:
    return any(step["tool_name"] == tool_name for step in past_steps)


def last_tool_failed(past_steps: list[dict[str, Any]], code: str) -> bool:
    if not past_steps:
        return False
    error = past_steps[-1].get("result", {}).get("error")
    return bool(error and error.get("code") == code)


def bad_email_recipient(goal: str) -> tuple[str, str]:
    match = BAD_EMAIL_PATTERN.search(goal)
    name = match.group("name") if match else "recipient"
    return name.capitalize(), f"{name.lower()}@example.com"


def email_recipient(goal: str) -> tuple[str, str]:
    match = EMAIL_PATTERN.search(goal)
    name = match.group("name") if match else "alex"
    return name.capitalize(), f"{name.lower()}@example.com"
