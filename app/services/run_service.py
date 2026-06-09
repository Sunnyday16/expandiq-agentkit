import hashlib
import json
from dataclasses import dataclass

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.entities.run import Run
from app.exceptions import IdempotencyKeyConflictError, RunNotFoundError
from app.llm.mock_llm import mock_llm
from app.models.runs import CreateRunRequest
from app.repositories import runs as run_repository
from app.services.agent_runtime import MockLLM, execute_agent_loop

logger = get_logger(__name__)


@dataclass(frozen=True)
class CreatedRun:
    run: Run
    replayed: bool


def request_hash(request: CreateRunRequest) -> str:
    payload = {
        "goal": request.goal,
        "max_steps": request.max_steps,
        "max_cost_usd": request.max_cost_usd,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


async def create_and_schedule_run(
    session: AsyncSession,
    sessionmaker: async_sessionmaker[AsyncSession],
    background_tasks: BackgroundTasks,
    request: CreateRunRequest,
    *,
    idempotency_key: str | None = None,
    llm: MockLLM = mock_llm,
) -> CreatedRun:
    if idempotency_key:
        hashed_request = request_hash(request)
        existing_key = await run_repository.get_idempotency_key(session, idempotency_key)
        if existing_key is not None:
            if existing_key.request_hash != hashed_request:
                logger.info("Idempotency key conflict key=%s", idempotency_key)
                raise IdempotencyKeyConflictError(idempotency_key)
            existing_run = await run_repository.get_run(session, existing_key.run_id)
            if existing_run is not None:
                logger.info(
                    "Replayed idempotent run key=%s run_id=%s",
                    idempotency_key,
                    existing_run.id,
                )
                return CreatedRun(run=existing_run, replayed=True)
            raise RunNotFoundError(existing_key.run_id)

        run = await run_repository.create_run_with_idempotency_key(
            session,
            request,
            idempotency_key=idempotency_key,
            request_hash=hashed_request,
        )
    else:
        run = await run_repository.create_run(session, request)

    logger.info(
        "Created run run_id=%s max_steps=%s max_cost_usd=%.3f",
        run.id,
        request.max_steps,
        request.max_cost_usd,
    )
    background_tasks.add_task(execute_agent_loop, sessionmaker, run.id, request, llm=llm)
    logger.info("Scheduled agent runtime run_id=%s", run.id)
    return CreatedRun(run=run, replayed=False)


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
