# AI-Assist Log

## Tooling

- Coding assistant: Codex.
- Local stack: Python 3.12, FastAPI, async SQLAlchemy, SQLite, pytest, ruff, mypy, Vite, React and TypeScript.
- Runtime design: deterministic mock LLM only. No real LLM provider keys or external APIs are required.
- Project-specific agent setup: `AGENTS.md` captures the repo-level Codex guidance used for continuing work on this assignment. No hooks, MCP servers or external model-provider configuration were added to this repository.

## How I Used the Assistant

I used Codex as a pair-programming assistant while keeping the architecture and scope decisions under my control. I worked in small reviewable slices, checked behavior after each slice, and redirected the design when a suggestion was too broad, too generic or less aligned with the assignment.

The most useful assistant work was:

- Drafting focused implementation slices after I had decided the boundary.
- Generating test scaffolding for guard, retry and integration scenarios.
- Helping inspect possible bugs during manual scenario testing.
- Refactoring code into the package structure I wanted.
- Tightening README and report wording after the implementation was working.

## Responsibility Split

My role:

- Chose the layered backend architecture and module boundaries.
- Chose SQLite for the prototype and documented the production database trade-off.
- Chose to keep the required `/runs` API contract instead of adding versioned routes.
- Chose to keep guard outcomes as persisted run states rather than exceptions.
- Identified manual-test issues such as hardcoded email recipients and noisy retrieval scoring.
- Decided when to refactor into `MockStrategy`, when to move guardrails into `runtime`, and when to keep stretch goals as future work.
- Ran and reviewed the final validation checks before considering the work complete.

Codex-assisted work:

- Drafted implementation slices after I defined the boundary.
- Helped generate focused tests for guardrails, retry behavior, integration flow and API errors.
- Helped inspect the code for duplicated logic and possible missing edge cases.
- Helped with documentation wording after the design and behavior were already reviewed.

Reworked after assistant drafts:

- Refined the package structure to match my layered microservice style.
- Replaced plain keyword overlap with BM25-style retrieval after discussing ranking weaknesses.
- Split the mock LLM into separate strategy modules to better support maintainability and SOLID principles.
- Tightened the AI-assist log to clearly reflect architecture ownership and review decisions.

## How I Framed the Task

I used the assistant to break the work into reviewable implementation checkpoints instead of asking for one complete generated solution. The project progressed through small, verifiable steps:

- confirm the required API contract;
- build one working persisted run;
- add the agent loop pieces one at a time;
- cover guard and error scenarios with tests;
- add the frontend after the backend behavior was stable;
- refactor the structure only after the core flow was working;
- finish with documentation and final requirement review.

This helped me keep each decision reviewable. It also made it easier to catch issues during testing, such as the hardcoded email-recipient behavior, instead of hiding them inside a large generated implementation.

## Architecture Decisions I Drove

I chose a small layered architecture, similar to how I would structure a Spring Boot-based microservice backend. The goal was to keep the FastAPI project easy to explain while still separating HTTP handling, business workflow, persistence and response mapping:

- `api`: thin controller layer for HTTP concerns.
- `services`: business workflow and agent-runtime orchestration.
- `repositories`: database access.
- `runtime`: agent guardrails such as step cap, cost cap, stuck detection and timeout.
- `entities`: SQLAlchemy persistence models.
- `models`: Pydantic request and response models.
- `mappers`: conversion from persistence entities to API responses.
- `exceptions`: small application exception layer.
- `tools`: deterministic tool registry and tool handlers.

I deliberately kept this structure lightweight. I wanted separation of concerns without adding a dependency-injection framework or extra abstractions that the assignment did not require.

I also made these design calls:

- Keep the required backend endpoints exactly as `/runs`, not `/api/v1/runs`, because the assignment specifies those paths.
- Use SQLite with async SQLAlchemy because it satisfies persistence requirements without Docker or external services.
- Use deterministic BM25-style retrieval instead of embeddings so the reviewer can replay and reason about each run while getting better ranking behavior than plain keyword overlap.
- Add optional `Idempotency-Key` support for `POST /runs` as a small stretch goal, using a separate table to replay duplicate create requests and reject conflicting payloads.
- Treat guard outcomes as persisted run states instead of exceptions, because the UI and API should show why the agent stopped.
- Use structured `ToolResult` errors for tool failures so semantic and recoverable errors are visible in the timeline.
- Add a Spring-like exception style only for application errors such as missing runs, keeping agent-loop outcomes separate.
- Use a lightweight `MockStrategy` package in the mock LLM so each deterministic behavior lives in its own module instead of one large conditional file.

## Prompt History Summary

The work was driven through incremental prompts and review checkpoints:

1. Clarify the required `/runs` API contract, persistence expectations and success criteria before writing code.
2. Build the first backend slice: `POST /runs`, `GET /runs/{id}` and persisted steps.
3. Replace the initial stub with the real runtime pieces: tool registry, retrieval, mock LLM and loop.
4. Add `GET /runs` for recent run listing.
5. Move execution into a background task and add the unexpected-error termination path.
6. Add mypy, ruff and focused tests.
7. Build the React single-page UI with goal input, polling, timeline, final answer and past runs.
8. Review the assignment scenarios and manually test happy, negative and guard paths.
9. Refactor the backend into the clean controller/service/repository/entity/model/mapper structure.
10. Add the lightweight exception-handling style and central logging.
11. Refactor the lengthy mock LLM file into a lightweight Strategy package so each deterministic mock behavior has one main reason to change, and new behaviors can be added by creating a strategy module and registering it.
12. Find and fix email-recipient bugs discovered during manual testing.
13. Finalize README, report and AI-assist documentation.
14. Add optional `POST /runs` idempotency support after reviewing the stretch-goal trade-off.

## Review and Corrections

I used the assistant to help review behavior, but I made the final calls on what to fix. Examples:

- During manual testing, I noticed an email goal could route to the wrong hardcoded recipient. I documented the issue, fixed the mock LLM behavior and added regression coverage.
- I questioned whether API versioning should be added. I decided not to change the required `/runs` contract and documented versioning as future work instead.
- I asked whether a Spring-like exception structure would be too much for Python. I kept only a small application exception layer so it improved clarity without over-engineering the prototype.
- I requested a final requirement pass against the assignment and added missing timeout coverage plus an explicit AI-assist log.

## Ownership

The architecture, scope boundaries and final trade-offs are mine. Codex helped with drafting and implementation speed, but I reviewed the code, ran the checks, asked for corrections when behavior did not match the requirement, and kept the design aligned with the assignment.

I am responsible for the final code and documentation submitted in this repository.
