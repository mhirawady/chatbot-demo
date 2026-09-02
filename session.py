"""In-memory transcript for a single conversation."""

from dataclasses import dataclass, field

from providers.base import Message, Role, ToolCall, ToolResult


@dataclass
class Session:
    """Holds one conversation's messages. Nothing survives a reset."""

    messages: list[Message] = field(default_factory=list)

    def add_user_text(self, text: str) -> None:
        self.messages.append(Message(role=Role.USER, text=text))

    def add_assistant_turn(
        self, text: str | None, tool_calls: tuple[ToolCall, ...] = ()
    ) -> None:
        self.messages.append(
            Message(role=Role.ASSISTANT, text=text, tool_calls=tool_calls)
        )

    def add_tool_results(self, results: tuple[ToolResult, ...]) -> None:
        self.messages.append(Message(role=Role.USER, tool_results=results))

    def snapshot(self) -> list[Message]:
        """Return a copy of the transcript for sending to a provider."""
        return list(self.messages)


def new_session() -> Session:
    """Start a fresh conversation with no prior history."""
    return Session()
