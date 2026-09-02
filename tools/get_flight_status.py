"""Flight status lookup tool."""

from typing import Any

from connectors import get_flights_connector
from tools.registry import register_tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "flight_number": {
            "type": "string",
            "description": "Flight number including the airline code, e.g. MR418.",
        },
        "date": {
            "type": "string",
            "description": "Date of departure in YYYY-MM-DD format.",
        },
    },
    "required": ["flight_number", "date"],
    "additionalProperties": False,
}


@register_tool("get_flight_status", SCHEMA)
def get_flight_status(flight_number: str, date: str) -> dict[str, Any]:
    """Look up the status of a Meridian flight by flight number and date.

    Returns scheduled and estimated times, gate, terminal, and any delay.
    """
    result = get_flights_connector().find(flight_number, date)
    return result.to_payload()
