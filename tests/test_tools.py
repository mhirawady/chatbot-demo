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


def test_get_booking_schema_requires_reference_and_name(
    schemas: dict[str, Any],
) -> None:
    required = schemas["get_booking"].input_schema["required"]
    assert set(required) == {"booking_reference", "last_name"}


def test_get_flight_status_schema_requires_number_and_date(
    schemas: dict[str, Any],
) -> None:
    required = schemas["get_flight_status"].input_schema["required"]
    assert set(required) == {"flight_number", "date"}


def test_end_conversation_takes_no_arguments(schemas: dict[str, Any]) -> None:
    assert schemas[END_CONVERSATION_TOOL].input_schema["properties"] == {}


def test_dispatch_get_booking_found() -> None:
    result = dispatch(
        "get_booking", {"booking_reference": "mr7qx2", "last_name": "alvarez"}
    )
    assert result["status"] == "found"
    assert result["record"]["fare_type"] == "Main Economy"


def test_dispatch_get_booking_not_found() -> None:
    result = dispatch(
        "get_booking", {"booking_reference": "ZZ9999", "last_name": "Nobody"}
    )
    assert result["status"] == "not_found"
    assert "record" not in result


def test_dispatch_get_booking_invalid_reference() -> None:
    result = dispatch(
        "get_booking", {"booking_reference": "??", "last_name": "Alvarez"}
    )
    assert result["status"] == "invalid_input"


def test_dispatch_get_flight_status_found() -> None:
    result = dispatch(
        "get_flight_status", {"flight_number": "mr226", "date": "2026-09-02"}
    )
    assert result["status"] == "found"
    assert result["record"]["status"] == "delayed"


def test_dispatch_get_flight_status_rejects_bad_date() -> None:
    result = dispatch(
        "get_flight_status", {"flight_number": "MR226", "date": "02/09/2026"}
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
