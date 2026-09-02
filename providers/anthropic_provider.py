"""Anthropic Messages API adapter."""

import json
from typing import Any

import anthropic
from anthropic.types import MessageParam, TextBlockParam, ToolParam

from config import MAX_TOKENS, REQUEST_TIMEOUT_SECONDS
from providers.base import (
    LLMProvider,
    Message,
    ProviderError,
    ProviderResponse,
    ToolCall,
    ToolSchema,
)


class AnthropicProvider(LLMProvider):
    """Talks to Claude through Anthropic's native Messages API."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS
        )

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema],
        system: str,
        model: str,
    ) -> ProviderResponse:
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=self._build_system(system),
                tools=[self._to_tool_param(tool) for tool in tools],
                messages=self._to_wire_messages(messages),
            )
        except anthropic.APIError as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc

        return self._to_provider_response(response)

    @staticmethod
    def _build_system(system: str) -> list[TextBlockParam]:
        # Cache hits are best-effort: Anthropic's ephemeral cache TTL is minutes,
        # so an idle CLI turn may miss it. Correctness never depends on a hit.
        return [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    @staticmethod
    def _to_tool_param(tool: ToolSchema) -> ToolParam:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }

    @staticmethod
    def _to_wire_messages(messages: list[Message]) -> list[MessageParam]:
        wire: list[MessageParam] = []
        for message in messages:
            blocks: list[Any] = []
            if message.text:
                blocks.append({"type": "text", "text": message.text})
            for call in message.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": call.arguments,
                    }
                )
            for result in message.tool_results:
                blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": result.tool_call_id,
                        "content": json.dumps(result.content),
                    }
                )
            if blocks:
                wire.append({"role": message.role.value, "content": blocks})
        return wire

    @staticmethod
    def _to_provider_response(response: Any) -> ProviderResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(block.text)
            elif block_type == "tool_use":
                arguments = block.input if isinstance(block.input, dict) else {}
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=arguments)
                )

        text = "\n".join(part for part in text_parts if part.strip()) or None
        return ProviderResponse(text=text, tool_calls=tuple(tool_calls))
