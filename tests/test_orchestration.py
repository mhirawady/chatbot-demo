"""Orchestration loop tests using a scripted provider."""

from config import CLOSING_LINE, MAX_TOOL_ROUNDTRIPS, TOOL_LIMIT_MESSAGE
from orchestration import Orchestrator, TurnOutcome
from providers.base import (
    LLMProvider,
    Message,
    ProviderError,
    ProviderResponse,
    ToolCall,
    ToolSchema,
)


class ScriptedProvider(LLMProvider):
    """Returns queued responses in order, recording what it was sent."""

    def __init__(self, *responses: ProviderResponse | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[list[Message]] = []

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema],
        system: str,
        model: str,
    ) -> ProviderResponse:
        self.calls.append(list(messages))
        item = self._responses.pop(0) if self._responses else ProviderResponse(text="")
        if isinstance(item, Exception):
            raise item
        return item


def _booking_call(call_id: str = "c1") -> ToolCall:
    return ToolCall(
        id=call_id,
        name="get_booking",
        arguments={"booking_code": "GH7X2P", "last_name": "Webb"},
    )


def _orchestrator(*responses: ProviderResponse | Exception) -> Orchestrator:
    return Orchestrator(ScriptedProvider(*responses), model="test-model")


def test_plain_reply_continues_conversation() -> None:
    orchestrator = _orchestrator(ProviderResponse(text="Happy to help."))
    result = orchestrator.handle_input("What are the baggage fees?")

    assert result.outcome is TurnOutcome.CONTINUE
    assert result.reply == "Happy to help."


def test_exit_command_short_circuits_provider() -> None:
    provider = ScriptedProvider()
    orchestrator = Orchestrator(provider, model="test-model")

    result = orchestrator.handle_input("exit")

    assert result.outcome is TurnOutcome.EXIT
    assert provider.calls == []


def test_keyword_fallback_resets_without_provider_call() -> None:
    provider = ScriptedProvider()
    orchestrator = Orchestrator(provider, model="test-model")
    orchestrator.session.add_user_text("earlier turn")

    result = orchestrator.handle_input("I want to talk about something else")

    assert result.outcome is TurnOutcome.RESET
    assert result.reply == CLOSING_LINE
    assert provider.calls == []
    assert orchestrator.session.messages == []


def test_end_conversation_tool_resets_transcript() -> None:
    orchestrator = _orchestrator(
        ProviderResponse(
            tool_calls=(ToolCall(id="c1", name="end_conversation", arguments={}),)
        )
    )
    orchestrator.handle_input("Thanks, that's all for now")

    assert orchestrator.session.messages == []


def test_end_conversation_returns_closing_line() -> None:
    orchestrator = _orchestrator(
        ProviderResponse(
            tool_calls=(ToolCall(id="c1", name="end_conversation", arguments={}),)
        )
    )
    result = orchestrator.handle_input("Thanks, that's all for now")

    assert result.outcome is TurnOutcome.RESET
    assert result.reply == CLOSING_LINE


def test_end_conversation_takes_priority_over_other_tool_calls() -> None:
    provider = ScriptedProvider(
        ProviderResponse(
            tool_calls=(
                _booking_call(),
                ToolCall(id="c2", name="end_conversation", arguments={}),
            )
        ),
        ProviderResponse(text="should never be reached"),
    )
    orchestrator = Orchestrator(provider, model="test-model")

    result = orchestrator.handle_input("Check GH7X2P, then never mind")

    assert result.outcome is TurnOutcome.RESET
    assert len(provider.calls) == 1


def test_tool_result_is_fed_back_to_provider() -> None:
    provider = ScriptedProvider(
        ProviderResponse(tool_calls=(_booking_call(),)),
        ProviderResponse(text="You're on SH412 to SFO."),
    )
    orchestrator = Orchestrator(provider, model="test-model")

    result = orchestrator.handle_input("Look up GH7X2P for Webb")

    assert result.reply == "You're on SH412 to SFO."
    tool_results = provider.calls[1][-1].tool_results
    assert tool_results[0].content["status"] == "found"


def test_turn_aborts_after_max_roundtrips() -> None:
    looping = [ProviderResponse(tool_calls=(_booking_call(),))] * MAX_TOOL_ROUNDTRIPS
    provider = ScriptedProvider(*looping)
    orchestrator = Orchestrator(provider, model="test-model")

    result = orchestrator.handle_input("Look up GH7X2P for Webb")

    assert result.reply == TOOL_LIMIT_MESSAGE
    assert result.outcome is TurnOutcome.CONTINUE
    assert len(provider.calls) == MAX_TOOL_ROUNDTRIPS


def test_provider_error_is_surfaced_not_raised() -> None:
    orchestrator = _orchestrator(ProviderError("upstream is down"))

    result = orchestrator.handle_input("Are you there?")

    assert result.outcome is TurnOutcome.CONTINUE
    assert result.reply is not None
    assert "upstream is down" in result.reply


def test_reset_clears_history_between_conversations() -> None:
    provider = ScriptedProvider(
        ProviderResponse(text="First answer."),
        ProviderResponse(text="Second answer."),
    )
    orchestrator = Orchestrator(provider, model="test-model")

    orchestrator.handle_input("First question")
    orchestrator.reset()
    orchestrator.handle_input("Second question")

    second_transcript = provider.calls[1]
    assert len(second_transcript) == 1
    assert second_transcript[0].text == "Second question"


def test_system_prompt_is_stable_across_resets() -> None:
    provider = ScriptedProvider(
        ProviderResponse(text="one"), ProviderResponse(text="two")
    )
    orchestrator = Orchestrator(provider, model="test-model")
    systems: list[str] = []

    original_chat = provider.chat

    def capture(
        messages: list[Message], tools: list[ToolSchema], system: str, model: str
    ) -> ProviderResponse:
        systems.append(system)
        return original_chat(messages, tools, system, model)

    provider.chat = capture  # type: ignore[method-assign]

    orchestrator.handle_input("first")
    orchestrator.reset()
    orchestrator.handle_input("second")

    assert systems[0] == systems[1]
