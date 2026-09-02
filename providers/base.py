"""Provider-agnostic LLM interface and message types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    """Author of a transcript message."""

    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """The outcome of a tool invocation, returned to the model."""

    tool_call_id: str
    name: str
    content: dict[str, Any]


@dataclass(frozen=True)
class Message:
    """One transcript entry.

    An assistant message may carry text, tool calls, or both. A user message
    carries either text typed by the passenger or results from tool calls.
    """

    role: Role
    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(frozen=True)
class ToolSchema:
    """Provider-agnostic description of a callable tool."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ProviderResponse:
    """Normalized model response."""

    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class ProviderError(RuntimeError):
    """Raised when a provider request fails or returns an unusable response."""


class LLMProvider(ABC):
    """Contract every LLM backend must satisfy."""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema],
        system: str,
        model: str,
    ) -> ProviderResponse:
        """Send a conversation turn and return the normalized response."""
