"""Conversation control tool."""

from typing import Any

from tools.registry import register_tool

TOOL_NAME = "end_conversation"

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


@register_tool(TOOL_NAME, SCHEMA)
def end_conversation() -> dict[str, Any]:
    """End the current conversation and start a fresh one.

    Call this when the passenger says they are done, wants to start over, or
    wants to talk about something entirely unrelated.
    """
    # Orchestration intercepts this call; the payload is never sent back.
    return {"status": "ended"}
