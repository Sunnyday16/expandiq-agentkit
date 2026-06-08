import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.entities.run import Run, Step
from app.llm.mock_llm import mock_llm
from app.models.runs import CreateRunRequest
from app.repositories import runs as run_repository
from app.runtime.guardrails import (
    StuckDetector,
    cost_cap_exceeded,
    mark_terminated,
    timeout_exceeded,
    utc_now,
)
from app.tools.base import ToolError, ToolResult
from app.tools.registry import TOOL_REGISTRY
from app.tools.retrieval import retrieve_tools

MockLLM = Callable[[str, list[dict[str, Any]], list[Any]], dict[str, Any]]
logger = get_logger(__name__)


def persistable_step(step: Step) -> dict[str, Any]:
    return {
        "tool_name": step.tool_name,
        "args": json.loads(step.args_json),
        "result": json.loads(step.result_json),
    }


def is_transient_error(result: ToolResult) -> bool:
    return bool(result.error and result.error.recoverable)


def format_log_context(context: dict[str, Any]) -> str:
    return " ".join(f"{key}={value}" for key, value in context.items())


async def terminate_run(
    session: AsyncSession,
    run: Run,
    reason: str,
    **log_context: Any,
) -> None:
    mark_terminated(run, reason)
    await session.commit()
    logger.info(
        "Terminated run run_id=%s reason=%s %s",
        run.id,
        reason,
        format_log_context(log_context),
    )


async def terminate_for_cost_cap_if_needed(
    session: AsyncSession,
    run: Run,
    max_cost_usd: float,
) -> bool:
    if not cost_cap_exceeded(run.total_cost, max_cost_usd):
        return False

    await terminate_run(
        session,
        run,
        "cost_cap",
        total_cost=f"{run.total_cost:.3f}",
        max_cost_usd=f"{max_cost_usd:.3f}",
    )
    return True


async def dispatch_tool(tool_name: str, args: dict[str, Any], *, max_retries: int = 2) -> ToolResult:
    if tool_name not in TOOL_REGISTRY:
        logger.info("Tool dispatch rejected unknown_tool=%s", tool_name)
        return ToolResult(
            ok=False,
            error=ToolError(
                code="unknown_tool",
                message=f"Tool {tool_name} is not registered.",
                recoverable=False,
            ),
        )

    tool = TOOL_REGISTRY[tool_name]
    attempt = 0
    while True:
        result = await tool.handler(args)
        if result.ok or not is_transient_error(result) or attempt >= max_retries:
            logger.info(
                "Tool dispatch completed tool=%s ok=%s attempts=%s error_code=%s",
                tool_name,
                result.ok,
                attempt + 1,
                result.error.code if result.error else None,
            )
            return result
        logger.info(
            "Retrying recoverable tool error tool=%s attempt=%s error_code=%s",
            tool_name,
            attempt + 1,
            result.error.code if result.error else None,
        )
        attempt += 1


async def execute_agent_loop(
    sessionmaker: async_sessionmaker[AsyncSession],
    run_id: str,
    request: CreateRunRequest,
    *,
    llm: MockLLM = mock_llm,
) -> None:
    async with sessionmaker() as session:
        run = await run_repository.get_run(session, run_id)
        if run is None:
            logger.info("Skipping agent runtime for missing run run_id=%s", run_id)
            return
        try:
            logger.info("Starting agent runtime run_id=%s", run_id)
            await _execute_agent_loop(session, run, request, llm=llm)
        except Exception:
            logger.exception("Unexpected agent runtime error run_id=%s", run_id)
            await session.rollback()
            run = await run_repository.get_run(session, run_id)
            if run is not None:
                await terminate_run(session, run, "error")


async def _execute_agent_loop(
    session: AsyncSession,
    run: Run,
    request: CreateRunRequest,
    *,
    llm: MockLLM = mock_llm,
) -> None:
    started_at = run.started_at
    past_steps: list[dict[str, Any]] = []
    stuck_detector = StuckDetector()

    for step_number in range(1, request.max_steps + 1):
        if timeout_exceeded(started_at):
            await terminate_run(session, run, "timeout", step_number=step_number)
            break

        candidate_tools = retrieve_tools(request.goal, TOOL_REGISTRY, top_k=5)
        logger.info(
            "Retrieved candidate tools run_id=%s step_number=%s tools=%s",
            run.id,
            step_number,
            [tool.name for tool in candidate_tools],
        )
        decision = llm(request.goal, past_steps, candidate_tools)
        cost = float(decision["cost"])

        if decision["type"] == "final":
            step = Step(
                run_id=run.id,
                step_number=step_number,
                tool_name="final_answer",
                args_json=json.dumps({}),
                result_json=json.dumps({"type": "final", "content": decision["content"]}),
                cost=cost,
                created_at=utc_now(),
            )
            session.add(step)
            past_steps.append(persistable_step(step))
            run.total_cost += cost
            if await terminate_for_cost_cap_if_needed(session, run, request.max_cost_usd):
                break
            run.status = "succeeded"
            run.reason = "succeeded"
            run.finished_at = utc_now()
            logger.info(
                "Completed run run_id=%s status=succeeded total_cost=%.3f steps=%s",
                run.id,
                run.total_cost,
                step_number,
            )
            await session.commit()
            break

        tool_name = str(decision["tool"])
        args = dict(decision["args"])
        result = await dispatch_tool(tool_name, args)

        step = Step(
            run_id=run.id,
            step_number=step_number,
            tool_name=tool_name,
            args_json=json.dumps(args),
            result_json=json.dumps(result.to_dict()),
            cost=cost,
            created_at=utc_now(),
        )
        session.add(step)
        past_steps.append(persistable_step(step))
        run.total_cost += cost
        logger.info(
            "Persisted tool step run_id=%s step_number=%s tool=%s ok=%s cost=%.3f total_cost=%.3f",
            run.id,
            step_number,
            tool_name,
            result.ok,
            cost,
            run.total_cost,
        )

        if stuck_detector.record(tool_name, args):
            await terminate_run(session, run, "stuck", step_number=step_number)
            break
        if await terminate_for_cost_cap_if_needed(session, run, request.max_cost_usd):
            break
        await session.commit()

    if run.status == "running":
        await terminate_run(session, run, "step_cap", max_steps=request.max_steps)
