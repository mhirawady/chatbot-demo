"""Tool registry. Importing this package registers every tool."""

from tools import (  # noqa: F401
    end_conversation,
    get_booking,
    get_flight_status,
    search_flights,
)
from tools.end_conversation import TOOL_NAME as END_CONVERSATION_TOOL
from tools.registry import dispatch, get_tool_schemas, register_tool

__all__ = [
    "END_CONVERSATION_TOOL",
    "dispatch",
    "get_tool_schemas",
    "register_tool",
]
