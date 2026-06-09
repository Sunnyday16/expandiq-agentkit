from fastapi import APIRouter, BackgroundTasks, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.session import SessionDependency
from app.mappers.runs import to_run_list_item, to_run_response
from app.models.runs import (
    CreateRunRequest,
    CreateRunResponse,
    RunListResponse,
    RunResponse,
)
from app.services.agent_runtime import MockLLM
from app.services.run_service import create_and_schedule_run, get_run_details, list_runs as list_runs_service

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=CreateRunResponse, status_code=201)
async def create_run(
    payload: CreateRunRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response,
    session: SessionDependency,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CreateRunResponse:
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    llm: MockLLM = request.app.state.llm
    created_run = await create_and_schedule_run(
        session,
        sessionmaker,
        background_tasks,
        payload,
        idempotency_key=idempotency_key,
        llm=llm,
    )
    if created_run.replayed:
        response.status_code = 200
    return CreateRunResponse(run_id=created_run.run.id)


@router.get("", response_model=RunListResponse)
async def list_runs(
    session: SessionDependency,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> RunListResponse:
    runs = await list_runs_service(session, limit=limit, offset=offset)
    return RunListResponse(
        items=[to_run_list_item(run) for run in runs],
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, session: SessionDependency) -> RunResponse:
    run = await get_run_details(session, run_id)
    return to_run_response(run)
