"""API tests for the FastAPI chat server (mocked orchestrator)."""

import pytest
from fastapi.testclient import TestClient

from orchestration import Orchestrator, TurnOutcome, TurnResult
from providers.base import LLMProvider, Message, ProviderResponse, ToolSchema
from server import app, create_orchestrator


class ScriptedProvider(LLMProvider):
    """Returns queued responses in order."""

    def __init__(self, *responses: ProviderResponse) -> None:
        self._responses = list(responses)

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema],
        system: str,
        model: str,
    ) -> ProviderResponse:
        return self._responses.pop(0) if self._responses else ProviderResponse(text="")


def test_start_session_returns_welcome(monkeypatch: pytest.MonkeyPatch) -> None:
    import server

    monkeypatch.setattr(
        server,
        "create_orchestrator",
        lambda: Orchestrator(ScriptedProvider(), model="test-model"),
    )
    client = TestClient(app)
    response = client.post("/api/session")
    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    assert "Sunny" in body["welcome"]


def test_chat_continues_with_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    import server

    monkeypatch.setattr(
        server,
        "create_orchestrator",
        lambda: Orchestrator(
            ScriptedProvider(ProviderResponse(text="Happy to help.")),
            model="test-model",
        ),
    )
    client = TestClient(app)
    session = client.post("/api/session").json()
    response = client.post(
        "/api/chat",
        json={"session_id": session["session_id"], "message": "Hi"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Happy to help."
    assert body["outcome"] == "continue"


def test_chat_unknown_session_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    import server

    monkeypatch.setattr(
        server,
        "create_orchestrator",
        lambda: Orchestrator(ScriptedProvider(), model="test-model"),
    )
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={"session_id": "missing", "message": "Hi"},
    )
    assert response.status_code == 404


def test_chat_reset_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    import server

    monkeypatch.setattr(
        server,
        "create_orchestrator",
        lambda: Orchestrator(ScriptedProvider(), model="test-model"),
    )
    client = TestClient(app)
    session = client.post("/api/session").json()
    response = client.post(
        "/api/chat",
        json={"session_id": session["session_id"], "message": "start over"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "reset"
    assert body["reply"] is not None


def test_index_serves_html(monkeypatch: pytest.MonkeyPatch) -> None:
    import server

    monkeypatch.setattr(server, "create_orchestrator", create_orchestrator)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "SkyHop" in response.text


def test_exit_resets_session_without_quitting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server

    class ExitOrchestrator(Orchestrator):
        def handle_input(self, user_input: str) -> TurnResult:
            return TurnResult(reply=None, outcome=TurnOutcome.EXIT)

    monkeypatch.setattr(
        server,
        "create_orchestrator",
        lambda: ExitOrchestrator(ScriptedProvider(), model="test-model"),
    )
    client = TestClient(app)
    session = client.post("/api/session").json()
    response = client.post(
        "/api/chat",
        json={"session_id": session["session_id"], "message": "exit"},
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "exit"
