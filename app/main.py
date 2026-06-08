import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.runs import router as runs_router
from app.core.logging import configure_logging
from app.database.session import Base, make_engine
from app.exceptions import AgentKitError
from app.llm.mock_llm import mock_llm
from app.services.agent_runtime import MockLLM

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./agentkit.db"


def create_app(database_url: str | None = None, llm: MockLLM = mock_llm) -> FastAPI:
    configure_logging()
    resolved_database_url = database_url or os.getenv("AGENTKIT_DATABASE_URL")
    if resolved_database_url is None:
        resolved_database_url = DEFAULT_DATABASE_URL
    engine = make_engine(resolved_database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = engine
        app.state.sessionmaker = sessionmaker
        app.state.llm = llm
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(title="AgentKit", lifespan=lifespan)
    app.include_router(runs_router)

    @app.exception_handler(AgentKitError)
    async def agentkit_error_handler(_: Request, exc: AgentKitError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response())

    return app


app = create_app()
