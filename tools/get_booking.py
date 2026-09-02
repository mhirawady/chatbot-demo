"""Booking lookup tool."""

from typing import Any

from connectors import get_bookings_connector
from connectors.base import API_TERMINOLOGY_NOTE
from tools.registry import register_tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "booking_code": {
            "type": "string",
            "description": "The passenger-facing booking code, e.g. GH7X2P.",
        },
        "last_name": {
            "type": "string",
            "description": "Last name of a passenger on the booking.",
        },
    },
    "required": ["booking_code", "last_name"],
    "additionalProperties": False,
}


@register_tool("get_booking", SCHEMA, extra_description=API_TERMINOLOGY_NOTE)
def get_booking(booking_code: str, last_name: str) -> dict[str, Any]:
    """Look up a passenger booking by booking code and passenger last name.

    Returns the itinerary, passengers, contact info, and segment statuses.
    """
    result = get_bookings_connector().find(booking_code, last_name)
    return result.to_payload()
