# AGENTS.md

## Setup Commands

- Install backend deps: `uv sync`
- Start backend: `uv run uvicorn app.main:app --reload`
- Install frontend deps: `cd frontend && npm install`
- Start frontend: `cd frontend && npm run dev`

## Validation Commands

- Run backend tests: `uv run pytest`
- Run backend lint: `uv run ruff check .`
- Run backend type check: `uv run mypy app tests`
- Run frontend build/type check: `cd frontend && npm run build`

## Code Style

- Python 3.12 with FastAPI and async SQLAlchemy.
- Keep FastAPI route handlers thin.
- Put business flow in services, persistence in repositories and database tables in entities.
- Use Pydantic models for API request and response schemas.
- Keep the mock LLM deterministic; do not add real LLM provider calls.
- Prefer small, reviewable changes over broad refactors.

## Project Boundaries

- Backend endpoints should remain the assignment-required `/runs` API.
- Runtime guard logic belongs in `app/runtime`.
- Tool definitions and retrieval belong in `app/tools`.
- Mock LLM strategies belong in `app/llm/strategies`.
- Frontend code belongs in `frontend/`.
- Document future production ideas in README or REPORT instead of adding unnecessary prototype complexity.
