"""Application-specific exceptions for AgentKit."""


class AgentKitError(Exception):
    """Base class for expected application errors."""

    status_code = 500
    code = "agentkit_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_response(self) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "status_code": self.status_code,
            }
        }


class RunNotFoundError(AgentKitError):
    """Raised when a requested run does not exist."""

    status_code = 404
    code = "run_not_found"

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run not found: {run_id}")
        self.run_id = run_id


class IdempotencyKeyConflictError(AgentKitError):
    """Raised when an idempotency key is reused with a different request body."""

    status_code = 409
    code = "idempotency_key_conflict"

    def __init__(self, key: str) -> None:
        super().__init__(f"Idempotency key {key} was already used with a different request.")
        self.key = key
