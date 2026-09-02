"""Provider-agnostic conversation orchestration."""

from dataclasses import dataclass
from enum import StrEnum

from config import (
    CLOSING_LINE,
    EXIT_COMMANDS,
    MAX_TOOL_ROUNDTRIPS,
    RESET_PHRASES,
    TOOL_LIMIT_MESSAGE,
)
from knowledge_base import get_policy_kb
from prompt_loader import build_system_prompt, load_persona
from providers.base import (
    LLMProvider,
    ProviderError,
    ToolCall,
    ToolResult,
)
from session import Session, new_session
from tools import END_CONVERSATION_TOOL, dispatch, get_tool_schemas


class TurnOutcome(StrEnum):
    """What the CLI should do after a turn."""

    CONTINUE = "continue"
    RESET = "reset"
    EXIT = "exit"


@dataclass(frozen=True)
class TurnResult:
    """Reply to show the passenger, plus the resulting control action."""

    reply: str | None
    outcome: TurnOutcome


def is_exit_command(user_input: str) -> bool:
    """True when the passenger typed a literal command to quit the CLI."""
    return user_input.strip().casefold() in EXIT_COMMANDS


def wants_reset(user_input: str) -> bool:
    """Deterministic backstop for when the model doesn't call end_conversation."""
    normalized = user_input.casefold()
    return any(phrase in normalized for phrase in RESET_PHRASES)


class Orchestrator:
    """Runs conversation turns against any LLM provider."""

    def __init__(self, provider: LLMProvider, model: str) -> None:
        self._provider = provider
        self._model = model
        self._system = build_system_prompt(load_persona(), get_policy_kb().search())
        self._tools = get_tool_schemas()
        self._session = new_session()

    @property
    def session(self) -> Session:
        return self._session

    def reset(self) -> None:
        """Drop the transcript. Static assets and the system prompt are reused."""
        self._session = new_session()

    def handle_input(self, user_input: str) -> TurnResult:
        """Process one line of passenger input."""
        if is_exit_command(user_input):
            return TurnResult(reply=None, outcome=TurnOutcome.EXIT)

        if wants_reset(user_input):
            self.reset()
            return TurnResult(reply=CLOSING_LINE, outcome=TurnOutcome.RESET)

        self._session.add_user_text(user_input)
        return self._run_turn()

    def _run_turn(self) -> TurnResult:
        for _ in range(MAX_TOOL_ROUNDTRIPS):
            try:
                response = self._provider.chat(
                    messages=self._session.snapshot(),
                    tools=self._tools,
                    system=self._system,
                    model=self._model,
                )
            except ProviderError as exc:
                return TurnResult(reply=f"Sorry — {exc}", outcome=TurnOutcome.CONTINUE)

            self._session.add_assistant_turn(response.text, response.tool_calls)

            if not response.has_tool_calls:
                return TurnResult(reply=response.text, outcome=TurnOutcome.CONTINUE)

            if any(call.name == END_CONVERSATION_TOOL for call in response.tool_calls):
                self.reset()
                return TurnResult(reply=CLOSING_LINE, outcome=TurnOutcome.RESET)

            self._session.add_tool_results(self._run_tools(response.tool_calls))

        return TurnResult(reply=TOOL_LIMIT_MESSAGE, outcome=TurnOutcome.CONTINUE)

    @staticmethod
    def _run_tools(tool_calls: tuple[ToolCall, ...]) -> tuple[ToolResult, ...]:
        return tuple(
            ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=dispatch(call.name, call.arguments),
            )
            for call in tool_calls
        )
