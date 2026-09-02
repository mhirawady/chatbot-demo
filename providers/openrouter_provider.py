"""OpenRouter (OpenAI-compatible) API adapter."""

import json
from typing import Any

import requests

from config import MAX_TOKENS, OPENROUTER_BASE_URL, REQUEST_TIMEOUT_SECONDS
from providers.base import (
    LLMProvider,
    Message,
    ProviderError,
    ProviderResponse,
    Role,
    ToolCall,
    ToolSchema,
)


class OpenRouterProvider(LLMProvider):
    """Talks to Claude through OpenRouter's OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str = OPENROUTER_BASE_URL) -> None:
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}/chat/completions"

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema],
        system: str,
        model: str,
    ) -> ProviderResponse:
        payload = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "messages": [
                self._build_system_message(system),
                *self._to_wire_messages(messages),
            ],
            "tools": [self._to_tool_param(tool) for tool in tools],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with requests.post(
                self._url,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                response.raise_for_status()
                body = response.json()
        except requests.RequestException as exc:
            raise ProviderError(f"OpenRouter request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError("OpenRouter returned a non-JSON response") from exc

        return self._to_provider_response(body)

    @staticmethod
    def _build_system_message(system: str) -> dict[str, Any]:
        # cache_control pass-through to Claude is best-effort here; OpenRouter may
        # ignore it, which costs cache savings but changes nothing functionally.
        return {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }

    @staticmethod
    def _to_tool_param(tool: ToolSchema) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    @staticmethod
    def _to_wire_messages(messages: list[Message]) -> list[dict[str, Any]]:
        wire: list[dict[str, Any]] = []
        for message in messages:
            if message.tool_results:
                wire.extend(
                    {
                        "role": "tool",
                        "tool_call_id": result.tool_call_id,
                        "content": json.dumps(result.content),
                    }
                    for result in message.tool_results
                )
                continue

            if message.role is Role.ASSISTANT:
                entry: dict[str, Any] = {
                    "role": "assistant",
                    "content": message.text or "",
                }
                if message.tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments),
                            },
                        }
                        for call in message.tool_calls
                    ]
                wire.append(entry)
            elif message.text:
                wire.append({"role": "user", "content": message.text})
        return wire

    @staticmethod
    def _to_provider_response(body: dict[str, Any]) -> ProviderResponse:
        choices = body.get("choices")
        if not choices:
            raise ProviderError("OpenRouter response contained no choices")

        message = choices[0].get("message", {})
        text = message.get("content") or None
        tool_calls: list[ToolCall] = []

        for raw_call in message.get("tool_calls") or []:
            function = raw_call.get("function", {})
            raw_arguments = function.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            tool_calls.append(
                ToolCall(
                    id=raw_call.get("id", ""),
                    name=function.get("name", ""),
                    arguments=arguments,
                )
            )

        return ProviderResponse(text=text, tool_calls=tuple(tool_calls))
