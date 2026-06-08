from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.entities.run import Run
from app.exceptions import RunNotFoundError
from app.llm.mock_llm import mock_llm
from app.models.runs import CreateRunRequest
from app.repositories import runs as run_repository
from app.services.agent_runtime import MockLLM, execute_agent_loop

logger = get_logger(__name__)


async def create_and_schedule_run(
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    background_tasks: BackgroundTasks,
    request: CreateRunRequest,
    *,
    llm: MockLLM = mock_llm,
) -> Run:
    run = await run_repository.create_run(session, request)
    logger.info(
        "Created run run_id=%s max_steps=%s max_cost_usd=%.3f",
        run.id,
        request.max_steps,
        request.max_cost_usd,
    )
    background_tasks.add_task(execute_agent_loop, sessionmaker, run.id, request, llm=llm)
    logger.info("Scheduled agent runtime run_id=%s", run.id)
    return run


async def list_runs(session: AsyncSession, *, limit: int, offset: int) -> list[Run]:
    runs = await run_repository.list_recent_runs(session, limit=limit, offset=offset)
    logger.info("Listed runs count=%s limit=%s offset=%s", len(runs), limit, offset)
    return runs


async def get_run_details(session: AsyncSession, run_id: str) -> Run:
    run = await run_repository.get_run_with_steps(session, run_id)
    if run is None:
        logger.info("Run lookup failed run_id=%s", run_id)
        raise RunNotFoundError(run_id)
    logger.info("Fetched run run_id=%s status=%s reason=%s steps=%s", run.id, run.status, run.reason, len(run.steps))
    return run
