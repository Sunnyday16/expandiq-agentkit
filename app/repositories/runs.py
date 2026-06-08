from uuid import uuid4

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.entities.run import Run
from app.models.runs import CreateRunRequest
from app.runtime.guardrails import utc_now


async def create_run(session: AsyncSession, request: CreateRunRequest) -> Run:
    run = Run(
        id=str(uuid4()),
        goal=request.goal,
        status="running",
        reason=None,
        total_cost=0.0,
        started_at=utc_now(),
        finished_at=None,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def get_run(session: AsyncSession, run_id: str) -> Run | None:
    return await session.get(Run, run_id)


async def get_run_with_steps(session: AsyncSession, run_id: str) -> Run | None:
    statement: Select[tuple[Run]] = (
        select(Run).where(Run.id == run_id).options(selectinload(Run.steps))
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def list_recent_runs(session: AsyncSession, *, limit: int, offset: int) -> list[Run]:
    statement: Select[tuple[Run]] = (
        select(Run).order_by(Run.started_at.desc()).limit(limit).offset(offset)
    )
    return list((await session.execute(statement)).scalars().all())
