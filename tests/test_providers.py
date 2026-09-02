"""Provider adapter tests against fixture responses. No live API calls."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from providers.anthropic_provider import AnthropicProvider
from providers.base import (
    Message,
    ProviderError,
    Role,
    ToolCall,
    ToolResult,
    ToolSchema,
)
from providers.openrouter_provider import OpenRouterProvider

SYSTEM = "You are Avery."
MODEL = "claude-sonnet-5"

TOOLS = [
    ToolSchema(
        name="get_booking",
        description="Look up a booking.",
        input_schema={
            "type": "object",
            "properties": {"booking_reference": {"type": "string"}},
            "required": ["booking_reference"],
        },
    )
]

TRANSCRIPT = [
    Message(role=Role.USER, text="Where is booking MR7QX2?"),
    Message(
        role=Role.ASSISTANT,
        text="Checking now.",
        tool_calls=(
            ToolCall(id="call_1", name="get_booking", arguments={"ref": "MR7QX2"}),
        ),
    ),
    Message(
        role=Role.USER,
        tool_results=(
            ToolResult(
                tool_call_id="call_1", name="get_booking", content={"status": "found"}
            ),
        ),
    ),
]


def _to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


class _StubMessages:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.last_kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        response = _to_namespace(self._payload)
        # tool_use inputs stay plain dicts on the real SDK.
        for block, raw in zip(response.content, self._payload["content"], strict=True):
            if raw.get("type") == "tool_use":
                block.input = raw["input"]
        return response


def _anthropic_with(payload: dict[str, Any]) -> tuple[AnthropicProvider, _StubMessages]:
    provider = AnthropicProvider.__new__(AnthropicProvider)
    stub = _StubMessages(payload)
    provider._client = SimpleNamespace(messages=stub)  # type: ignore[assignment]
    return provider, stub


class _StubResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_StubResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_anthropic_parses_text_response(load_fixture: Any) -> None:
    provider, _ = _anthropic_with(load_fixture("anthropic_text_response.json"))
    response = provider.chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    assert response.text is not None
    assert "no change fee" in response.text
    assert not response.has_tool_calls


def test_anthropic_parses_tool_use_response(load_fixture: Any) -> None:
    provider, _ = _anthropic_with(load_fixture("anthropic_tool_use_response.json"))
    response = provider.chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    assert response.has_tool_calls
    call = response.tool_calls[0]
    assert call.name == "get_booking"
    assert call.arguments["booking_reference"] == "MR7QX2"


def test_anthropic_sends_cached_system_blocks(load_fixture: Any) -> None:
    provider, stub = _anthropic_with(load_fixture("anthropic_text_response.json"))
    provider.chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    system = stub.last_kwargs["system"]
    assert system[0]["text"] == SYSTEM
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_anthropic_translates_transcript_blocks(load_fixture: Any) -> None:
    provider, stub = _anthropic_with(load_fixture("anthropic_text_response.json"))
    provider.chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    sent = stub.last_kwargs["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[1]["content"][1]["type"] == "tool_use"
    assert sent[2]["content"][0]["type"] == "tool_result"


def test_anthropic_tool_schema_uses_input_schema(load_fixture: Any) -> None:
    provider, stub = _anthropic_with(load_fixture("anthropic_text_response.json"))
    provider.chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    tool = stub.last_kwargs["tools"][0]
    assert tool["name"] == "get_booking"
    assert tool["input_schema"]["required"] == ["booking_reference"]


def test_openrouter_parses_text_response(
    monkeypatch: pytest.MonkeyPatch, load_fixture: Any
) -> None:
    payload = load_fixture("openrouter_text_response.json")
    monkeypatch.setattr(
        "providers.openrouter_provider.requests.post",
        lambda *a, **kw: _StubResponse(payload),
    )
    response = OpenRouterProvider(api_key="test").chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    assert response.text is not None
    assert not response.has_tool_calls


def test_openrouter_parses_tool_call_response(
    monkeypatch: pytest.MonkeyPatch, load_fixture: Any
) -> None:
    payload = load_fixture("openrouter_tool_call_response.json")
    monkeypatch.setattr(
        "providers.openrouter_provider.requests.post",
        lambda *a, **kw: _StubResponse(payload),
    )
    response = OpenRouterProvider(api_key="test").chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    call = response.tool_calls[0]
    assert call.id == "call_01ABC"
    assert call.arguments["last_name"] == "Alvarez"


def test_openrouter_builds_openai_shaped_request(
    monkeypatch: pytest.MonkeyPatch, load_fixture: Any
) -> None:
    payload = load_fixture("openrouter_text_response.json")
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _StubResponse:
        captured["url"] = url
        captured["json"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return _StubResponse(payload)

    monkeypatch.setattr("providers.openrouter_provider.requests.post", fake_post)
    OpenRouterProvider(api_key="test-key").chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    body = captured["json"]
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert body["messages"][0]["role"] == "system"
    assert [m["role"] for m in body["messages"][1:]] == ["user", "assistant", "tool"]
    assert body["tools"][0]["type"] == "function"
    assert body["tools"][0]["function"]["parameters"]["required"] == [
        "booking_reference"
    ]


def test_openrouter_serializes_tool_call_arguments(
    monkeypatch: pytest.MonkeyPatch, load_fixture: Any
) -> None:
    payload = load_fixture("openrouter_text_response.json")
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _StubResponse:
        captured["json"] = kwargs["json"]
        return _StubResponse(payload)

    monkeypatch.setattr("providers.openrouter_provider.requests.post", fake_post)
    OpenRouterProvider(api_key="test").chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)

    assistant = captured["json"]["messages"][2]
    arguments = assistant["tool_calls"][0]["function"]["arguments"]
    assert json.loads(arguments) == {"ref": "MR7QX2"}


def test_openrouter_raises_on_empty_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "providers.openrouter_provider.requests.post",
        lambda *a, **kw: _StubResponse({"choices": []}),
    )
    with pytest.raises(ProviderError, match="no choices"):
        OpenRouterProvider(api_key="test").chat(TRANSCRIPT, TOOLS, SYSTEM, MODEL)
