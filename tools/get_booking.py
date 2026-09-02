"""Booking lookup tool."""

from typing import Any

from connectors import get_bookings_connector
from tools.registry import register_tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "booking_reference": {
            "type": "string",
            "description": "The 6-character booking reference, e.g. MR7QX2.",
        },
        "last_name": {
            "type": "string",
            "description": "Last name of the passenger who made the booking.",
        },
    },
    "required": ["booking_reference", "last_name"],
    "additionalProperties": False,
}


@register_tool("get_booking", SCHEMA)
def get_booking(booking_reference: str, last_name: str) -> dict[str, Any]:
    """Look up a passenger booking by booking reference and last name.

    Returns the itinerary, fare type, passengers, seats and booking status.
    """
    result = get_bookings_connector().find(booking_reference, last_name)
    return result.to_payload()
