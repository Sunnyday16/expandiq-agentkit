import json

from app.entities.run import Run
from app.models.runs import RunListItem, RunResponse, StepResponse


def to_run_response(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id,
        goal=run.goal,
        status=run.status,
        reason=run.reason,
        total_cost=run.total_cost,
        started_at=run.started_at,
        finished_at=run.finished_at,
        steps=[
            StepResponse(
                step_number=step.step_number,
                tool_name=step.tool_name,
                args=json.loads(step.args_json),
                result=json.loads(step.result_json),
                cost=step.cost,
                created_at=step.created_at,
            )
            for step in run.steps
        ],
    )


def to_run_list_item(run: Run) -> RunListItem:
    return RunListItem(
        id=run.id,
        goal=run.goal,
        status=run.status,
        reason=run.reason,
        total_cost=run.total_cost,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
