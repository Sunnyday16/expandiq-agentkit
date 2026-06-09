# AgentKit Report

## Method

I built a deterministic agent-runtime service that accepts a user goal, creates a persisted run, executes the agent loop in the background, and exposes polling endpoints for the current run state and step timeline.

The core flow is:

1. `POST /runs` validates the request and creates a `running` run.
2. The run service schedules the agent loop as a FastAPI background task.
3. The runtime retrieves top-K candidate tools before each mock LLM decision.
4. The mock LLM selects either a tool call or a final answer.
5. The runtime dispatches the selected tool, persists the step, updates cost and evaluates guards.
6. `GET /runs/{run_id}` returns the persisted run and ordered steps for polling.

The mock LLM is intentionally deterministic so reviewer tests can assert exact behavior without depending on external providers.

## Engineering Design

The backend is separated into small layers:

- `api`: HTTP route handlers.
- `services`: run orchestration and agent runtime logic.
- `repositories`: database access.
- `runtime`: agent runtime guardrails.
- `models`: Pydantic request and response shapes.
- `entities`: SQLAlchemy persistence entities.
- `mappers`: conversion from entities to API responses.
- `llm`: deterministic mock LLM, strategy registry and mock strategies.
- `tools`: tool registry, retrieval, metadata and handlers.
- `exceptions`: application-specific exceptions.
- `core`: shared logging configuration.

This follows the same layered architecture I would use in a Spring Boot-based microservice backend: controller, service, repository, model/entity and exception handling. The implementation remains small because the assignment is a prototype rather than a production platform.

I chose SQLite for this prototype because it keeps local setup simple and lets reviewers run the service without Docker or a managed database. It still satisfies the assignment requirement for persisted `runs` and `steps`. In production, I would use PostgreSQL or another managed relational database with migrations, stronger concurrency controls, indexing, backups and operational monitoring.

`POST /runs` supports an optional `Idempotency-Key` header. The service stores the key, a stable hash of the request body and the created `run_id` in a separate `idempotency_keys` table. Replaying the same key with the same body returns the original run instead of creating duplicate work; reusing the key with a different body returns `409 Conflict`.

The mock LLM uses a lightweight Strategy pattern. Each `MockStrategy` owns one deterministic behavior, such as stuck-loop testing, transient-error recovery, email handling or revenue-summary retrieval. The thin `mock_llm` entry point selects a registered strategy and delegates the decision. Adding a new behavior means adding a strategy module and registering it, without changing the orchestration logic or existing strategy classes.

Tool retrieval uses a small dependency-free BM25-style ranker over tool names and descriptions. I chose BM25 over plain keyword overlap because it is still deterministic and local, but handles noisy tool descriptions better through inverse document frequency and length normalization. A small direct-name boost keeps tools such as `send_email` high when the user's goal explicitly says "send email".

For a larger production registry, I would likely move to hybrid retrieval: BM25 for exact keyword/tool-name matches and semantic embeddings for intent matching. I would combine scores or ranks, then evaluate tool-selection accuracy offline before shipping the retrieval changes.

Application logging is configured centrally and records the main runtime lifecycle: run creation, scheduling, tool retrieval, tool dispatch, retry decisions and terminal guard reasons. This keeps the API response focused on persisted state while still giving operators useful log lines during a run.

For this prototype, FastAPI `BackgroundTasks` is enough because each run is local, deterministic and small. In production, I would likely move agent execution to an event-driven worker architecture: `POST /runs` would persist the run and publish a `RunRequested` event to Kafka, worker services would consume that event, execute the agent loop, persist step events and update run status. The frontend could continue polling or receive updates through SSE/WebSockets. Kafka would help scale workers horizontally, retry failed processing and decouple request handling from long-running agent execution.

## Error Handling

The service distinguishes normal agent outcomes from application errors:

- Normal guard outcomes are persisted as terminal run reasons: `step_cap`, `cost_cap`, `stuck` and `timeout`.
- Tool-level failures are returned through `ToolResult.error` and persisted in the step timeline.
- Recoverable tool failures are retried before the final result is persisted.
- Missing runs raise `RunNotFoundError` and are translated to HTTP 404 by the FastAPI exception handler.
- Unexpected worker exceptions are logged and persisted as `reason="error"`.

This keeps the UI and API useful for debugging because failed agent behavior remains visible as run state and timeline data.

## Scenario Coverage

The test suite covers:

- Happy path Q3 revenue retrieval.
- Recent run listing and pagination.
- Transient tool failure recovery.
- Semantic email error correction.
- Stuck detection.
- Cost cap termination.
- Step cap termination.
- `POST /runs` idempotency replay and conflict handling.
- Unexpected runtime error termination.
- Tool retrieval ranking.
- Guard behavior.

## Interpretation

The assignment specifies `/runs` endpoints, so the implementation keeps those exact paths. API versioning such as `/api/v1/runs` is listed as a future enhancement rather than changing the required contract.

The frontend uses a Vite proxy with `/api/runs` during local development, but the backend still exposes the required `/runs` endpoints.

## Use of Coding Assistants and GenAI Tools

I used an AI coding assistant as a pair-programming aid for implementation, testing, refactoring and documentation. I drove the architecture decisions, including the clean controller/service/repository/entity/model separation, the choice to keep `/runs` as the required API contract, and the decision to represent guard outcomes as persisted run states rather than exceptions.

The assistant helped accelerate code drafting and review, but I inspected the behavior, asked follow-up questions, corrected bugs found during manual testing and kept the final scope intentionally aligned with the assignment requirements.
