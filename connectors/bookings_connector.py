"""Mock booking lookup API."""

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import BOOKINGS_PATH
from connectors.base import (
    LookupResult,
    LookupStatus,
    humanize_record,
    load_json_records,
    rename_key,
)

_BOOKING_CODE_PATTERN = re.compile(r"^[A-Z0-9]{5,8}$")


class BookingsConnector:
    """Looks up passenger bookings, independent of the backing store."""

    def __init__(self, path: Path) -> None:
        self._records: list[dict[str, Any]] = load_json_records(path, "bookings")

    def find(self, booking_code: str, last_name: str) -> LookupResult:
        """Find a booking by booking code and a passenger's last name."""
        code = booking_code.strip().upper()
        surname = last_name.strip()

        if not _BOOKING_CODE_PATTERN.match(code):
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message=(
                    f"Booking code must be 5-8 letters or digits, got {booking_code!r}."
                ),
            )
        if not surname:
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message="Last name must not be empty.",
            )

        for record in self._records:
            same_code = record["pnr"].upper() == code
            has_passenger = any(
                passenger["last_name"].casefold() == surname.casefold()
                for passenger in record["passengers"]
            )
            if same_code and has_passenger:
                # PNR is internal jargon; the passenger-facing tool result
                # calls it a booking code, and every date/time is humanized.
                presentable = rename_key(record, "pnr", "booking_code")
                return LookupResult(
                    status=LookupStatus.FOUND, record=humanize_record(presentable)
                )

        return LookupResult(
            status=LookupStatus.NOT_FOUND,
            message="No booking matches that booking code and last name.",
            details={"booking_code": code, "last_name": surname},
        )


@lru_cache(maxsize=1)
def get_bookings_connector() -> BookingsConnector:
    """Return the process-wide bookings connector singleton."""
    return BookingsConnector(BOOKINGS_PATH)
