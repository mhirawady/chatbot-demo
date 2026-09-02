"""Tool schema and handler tests."""

from typing import Any

import pytest

import tools
from tools import dispatch, get_tool_schemas
from tools.end_conversation import TOOL_NAME as END_CONVERSATION_TOOL

EXPECTED_TOOLS = {"get_booking", "get_flight_status", END_CONVERSATION_TOOL}


@pytest.fixture(scope="module")
def schemas() -> dict[str, Any]:
    return {schema.name: schema for schema in get_tool_schemas()}


def test_all_tools_registered(schemas: dict[str, Any]) -> None:
    assert set(schemas) == EXPECTED_TOOLS


@pytest.mark.parametrize("name", sorted(EXPECTED_TOOLS))
def test_schema_shape(schemas: dict[str, Any], name: str) -> None:
    schema = schemas[name]
    assert schema.description
    assert schema.input_schema["type"] == "object"
    assert "properties" in schema.input_schema


def test_get_booking_schema_requires_code_and_name(
    schemas: dict[str, Any],
) -> None:
    required = schemas["get_booking"].input_schema["required"]
    assert set(required) == {"booking_code", "last_name"}


def test_get_booking_description_includes_terminology_note(
    schemas: dict[str, Any],
) -> None:
    assert "booking code" in schemas["get_booking"].description
    assert "reservation code" in schemas["get_booking"].description


def test_get_flight_status_schema_requires_number_and_date(
    schemas: dict[str, Any],
) -> None:
    required = schemas["get_flight_status"].input_schema["required"]
    assert set(required) == {"flight_number", "date"}


def test_end_conversation_takes_no_arguments(schemas: dict[str, Any]) -> None:
    assert schemas[END_CONVERSATION_TOOL].input_schema["properties"] == {}


def test_dispatch_get_booking_found() -> None:
    result = dispatch("get_booking", {"booking_code": "gh7x2p", "last_name": "webb"})
    assert result["status"] == "found"
    assert result["record"]["booking_code"] == "GH7X2P"


def test_dispatch_get_booking_not_found() -> None:
    result = dispatch("get_booking", {"booking_code": "ZZ9999", "last_name": "Nobody"})
    assert result["status"] == "not_found"
    assert "record" not in result


def test_dispatch_get_booking_invalid_code() -> None:
    result = dispatch("get_booking", {"booking_code": "??", "last_name": "Webb"})
    assert result["status"] == "invalid_input"


def test_dispatch_get_flight_status_found() -> None:
    result = dispatch(
        "get_flight_status", {"flight_number": "sh412", "date": "2026-07-09"}
    )
    assert result["status"] == "found"
    assert result["record"]["status"] == "CANCELLED"


def test_dispatch_get_flight_status_rejects_bad_date() -> None:
    result = dispatch(
        "get_flight_status", {"flight_number": "SH412", "date": "09/07/2026"}
    )
    assert result["status"] == "invalid_input"


def test_dispatch_end_conversation() -> None:
    assert dispatch(END_CONVERSATION_TOOL, {}) == {"status": "ended"}


def test_dispatch_unknown_tool() -> None:
    result = dispatch("nope", {})
    assert result["status"] == "error"


def test_dispatch_rejects_bad_arguments() -> None:
    result = dispatch("get_booking", {"unexpected": "value"})
    assert result["status"] == "invalid_input"


def test_duplicate_registration_rejected() -> None:
    with pytest.raises(ValueError, match="already registered"):

        @tools.register_tool("get_booking", {"type": "object", "properties": {}})
        def _duplicate() -> dict[str, Any]:
            """Duplicate registration."""
            return {}
