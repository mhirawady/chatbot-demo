"""Decorator-based registry for LLM-callable tools."""

from collections.abc import Callable
from typing import Any

from providers.base import ToolSchema

ToolHandler = Callable[..., dict[str, Any]]

_HANDLERS: dict[str, ToolHandler] = {}
_SCHEMAS: dict[str, ToolSchema] = {}


def register_tool(
    name: str, schema: dict[str, Any], extra_description: str = ""
) -> Callable[[ToolHandler], ToolHandler]:
    """Register a handler under `name` with its JSON input schema.

    `extra_description` is appended after the handler's docstring, useful for
    API terminology or formatting notes that don't belong in the docstring
    itself.
    """

    def decorator(handler: ToolHandler) -> ToolHandler:
        if name in _HANDLERS:
            raise ValueError(f"Tool already registered: {name}")
        description = (handler.__doc__ or "").strip()
        if not description:
            raise ValueError(f"Tool {name} needs a docstring for its description")
        if extra_description:
            description = f"{description}\n\n{extra_description}"
        _HANDLERS[name] = handler
        _SCHEMAS[name] = ToolSchema(
            name=name, description=description, input_schema=schema
        )
        return handler

    return decorator


def get_tool_schemas() -> list[ToolSchema]:
    """Return schemas for every registered tool."""
    return list(_SCHEMAS.values())


def dispatch(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Invoke a registered tool, returning a JSON-serializable payload."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"status": "error", "message": f"Unknown tool: {name}"}
    try:
        return handler(**arguments)
    except TypeError as exc:
        return {
            "status": "invalid_input",
            "message": f"Bad arguments for {name}: {exc}",
        }
