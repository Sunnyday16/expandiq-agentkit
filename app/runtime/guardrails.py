import json
from datetime import UTC, datetime
from typing import Any

from app.entities.run import Run

RUN_TIMEOUT_SECONDS = 60
STUCK_REPEAT_THRESHOLD = 3


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def args_hash(args: dict[str, Any]) -> str:
    return json.dumps(args, sort_keys=True, separators=(",", ":"))


def timeout_exceeded(started_at: datetime) -> bool:
    return (utc_now() - started_at).total_seconds() >= RUN_TIMEOUT_SECONDS


def cost_cap_exceeded(total_cost: float, max_cost_usd: float) -> bool:
    return total_cost > max_cost_usd


def mark_terminated(run: Run, reason: str) -> None:
    run.status = "terminated"
    run.reason = reason
    run.finished_at = utc_now()


class StuckDetector:
    def __init__(self, threshold: int = STUCK_REPEAT_THRESHOLD) -> None:
        self.threshold = threshold
        self._repeated_calls: dict[tuple[str, str], int] = {}

    def record(self, tool_name: str, args: dict[str, Any]) -> bool:
        call_key = (tool_name, args_hash(args))
        self._repeated_calls[call_key] = self._repeated_calls.get(call_key, 0) + 1
        return self._repeated_calls[call_key] >= self.threshold
