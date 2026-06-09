from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.runs import CreateRunRequest
from app.repositories import runs as run_repository
from app.runtime.guardrails import utc_now
from app.services.agent_runtime import _execute_agent_loop


def test_create_and_fetch_completed_run(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        create_response = client.post(
            "/runs",
            json={"goal": "Find the Q3 revenue summary", "max_steps": 20, "max_cost_usd": 0.50},
        )

        assert create_response.status_code == 201
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["id"] == run_id
    assert body["goal"] == "Find the Q3 revenue summary"
    assert body["status"] == "succeeded"
    assert body["reason"] == "succeeded"
    assert body["total_cost"] == 0.007
    assert len(body["steps"]) == 4
    assert body["steps"][0]["tool_name"] == "search_docs"
    assert body["steps"][0]["args"] == {"q": "Find the Q3 revenue summary"}
    assert body["steps"][1]["tool_name"] == "fetch_doc"
    assert body["steps"][2]["tool_name"] == "summarise_text"
    assert body["steps"][3]["tool_name"] == "final_answer"


def test_create_run_without_idempotency_key_creates_new_runs(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        first_response = client.post("/runs", json={"goal": "Find the Q3 revenue summary"})
        second_response = client.post("/runs", json={"goal": "Find the Q3 revenue summary"})

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["run_id"] != second_response.json()["run_id"]


def test_create_run_replays_same_idempotency_key_and_body(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)
    payload = {"goal": "Find the Q3 revenue summary"}
    headers = {"Idempotency-Key": "test-key-001"}

    with TestClient(app) as client:
        first_response = client.post("/runs", json=payload, headers=headers)
        second_response = client.post("/runs", json=payload, headers=headers)
        list_response = client.get("/runs")

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["run_id"] == second_response.json()["run_id"]
    assert len(list_response.json()["items"]) == 1


def test_create_run_rejects_idempotency_key_with_different_body(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)
    headers = {"Idempotency-Key": "test-key-002"}

    with TestClient(app) as client:
        client.post("/runs", json={"goal": "Find the Q3 revenue summary"}, headers=headers)
        conflict_response = client.post(
            "/runs",
            json={"goal": "Test transient web search recovery"},
            headers=headers,
        )

    assert conflict_response.status_code == 409
    assert conflict_response.json() == {
        "error": {
            "code": "idempotency_key_conflict",
            "message": "Idempotency key test-key-002 was already used with a different request.",
            "status_code": 409,
        }
    }


def test_get_missing_run_returns_404(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        response = client.get("/runs/missing-run")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "run_not_found",
            "message": "Run not found: missing-run",
            "status_code": 404,
        }
    }


def test_list_runs_returns_recent_runs_newest_first(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        first_response = client.post("/runs", json={"goal": "Find the Q3 revenue summary"})
        second_response = client.post("/runs", json={"goal": "Test transient web search recovery"})

        list_response = client.get("/runs?limit=10&offset=0")

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert [item["id"] for item in body["items"]] == [
        second_response.json()["run_id"],
        first_response.json()["run_id"],
    ]
    assert "steps" not in body["items"][0]


def test_list_runs_supports_pagination(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        client.post("/runs", json={"goal": "Find the Q3 revenue summary"})
        second_response = client.post("/runs", json={"goal": "Test transient web search recovery"})
        client.post("/runs", json={"goal": "Make the agent stuck"})

        list_response = client.get("/runs?limit=1&offset=1")

    assert list_response.status_code == 200
    body = list_response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == second_response.json()["run_id"]


def test_create_and_fetch_transient_error_run(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        create_response = client.post(
            "/runs",
            json={"goal": "Test transient web search recovery"},
        )
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "succeeded"
    assert body["reason"] == "succeeded"
    assert body["steps"][0]["tool_name"] == "web_search"
    assert body["steps"][0]["result"]["ok"] is True
    assert body["steps"][1]["tool_name"] == "final_answer"


def test_bad_email_goal_uses_requested_recipient_after_semantic_error(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        create_response = client.post("/runs", json={"goal": "bad email Sunny"})
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    body = get_response.json()
    assert body["status"] == "succeeded"
    assert body["reason"] == "succeeded"
    assert body["steps"][0]["tool_name"] == "send_email"
    assert body["steps"][0]["args"]["to"] == "sunny@example.com"
    assert body["steps"][0]["result"]["ok"] is False
    assert body["steps"][0]["result"]["error"]["code"] == "missing_idempotency_key"
    assert body["steps"][1]["tool_name"] == "send_email"
    assert body["steps"][1]["args"]["to"] == "sunny@example.com"
    assert body["steps"][1]["result"]["ok"] is True
    assert body["steps"][2]["result"]["content"] == "Email error was corrected and queued for Sunny."


def test_email_goal_uses_requested_recipient(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        create_response = client.post("/runs", json={"goal": "email Sunny an AgentKit update"})
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    body = get_response.json()
    assert body["status"] == "succeeded"
    assert body["steps"][0]["tool_name"] == "lookup_contact"
    assert body["steps"][0]["args"]["name"] == "Sunny"
    assert body["steps"][1]["tool_name"] == "send_email"
    assert body["steps"][1]["args"]["to"] == "sunny@example.com"
    assert body["steps"][2]["result"]["content"] == "Email queued for Sunny."


def test_stuck_run_terminates_with_reason(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        create_response = client.post("/runs", json={"goal": "Make the agent stuck"})
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    body = get_response.json()
    assert body["status"] == "terminated"
    assert body["reason"] == "stuck"
    assert len(body["steps"]) == 3


def test_cost_cap_terminates_with_reason(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        create_response = client.post(
            "/runs",
            json={"goal": "Find the Q3 revenue summary", "max_cost_usd": 0.003},
        )
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    body = get_response.json()
    assert body["status"] == "terminated"
    assert body["reason"] == "cost_cap"
    assert body["total_cost"] > 0.003


def test_step_cap_terminates_with_reason(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        create_response = client.post(
            "/runs",
            json={"goal": "Find the Q3 revenue summary", "max_steps": 2},
        )
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    body = get_response.json()
    assert body["status"] == "terminated"
    assert body["reason"] == "step_cap"
    assert len(body["steps"]) == 2


def test_unexpected_worker_error_marks_run_as_error(tmp_path: Path) -> None:
    def broken_llm(
        goal: str,
        past_steps: list[dict[str, Any]],
        candidate_tools: list[Any],
    ) -> dict[str, Any]:
        raise RuntimeError("forced test failure")

    database_url = f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}"
    app = create_app(database_url=database_url, llm=broken_llm)

    with TestClient(app) as client:
        create_response = client.post("/runs", json={"goal": "Trigger an unexpected error"})
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/runs/{run_id}")

    body = get_response.json()
    assert body["status"] == "terminated"
    assert body["reason"] == "error"


@pytest.mark.asyncio
async def test_timeout_guard_terminates_with_reason(tmp_path: Path) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.database.session import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'agentkit-test.db'}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    request = CreateRunRequest(goal="Find the Q3 revenue summary")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with sessionmaker() as session:
        run = await run_repository.create_run(session, request)
        run.started_at = utc_now().replace(year=2000)
        await session.commit()

        await _execute_agent_loop(session, run, request)

        refreshed = await run_repository.get_run_with_steps(session, run.id)

    await engine.dispose()

    assert refreshed is not None
    assert refreshed.status == "terminated"
    assert refreshed.reason == "timeout"
    assert refreshed.steps == []
