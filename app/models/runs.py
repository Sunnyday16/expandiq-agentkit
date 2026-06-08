from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


RunStatus = Literal["running", "succeeded", "terminated"]
RunReason = Literal["step_cap", "cost_cap", "stuck", "timeout", "error", "succeeded"]


class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=1)
    max_steps: int = Field(default=20, ge=1, le=100)
    max_cost_usd: float = Field(default=0.50, gt=0)


class CreateRunResponse(BaseModel):
    run_id: str


class RunListItem(BaseModel):
    id: str
    goal: str
    status: RunStatus
    reason: RunReason | None
    total_cost: float
    started_at: datetime
    finished_at: datetime | None


class RunListResponse(BaseModel):
    items: list[RunListItem]
    limit: int
    offset: int


class StepResponse(BaseModel):
    step_number: int
    tool_name: str
    args: dict[str, Any]
    result: dict[str, Any]
    cost: float
    created_at: datetime


class RunResponse(BaseModel):
    id: str
    goal: str
    status: RunStatus
    reason: RunReason | None
    total_cost: float
    started_at: datetime
    finished_at: datetime | None
    steps: list[StepResponse]
