"""Mock booking lookup API."""

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import BOOKINGS_PATH
from connectors.base import LookupResult, LookupStatus, load_json_records

_BOOKING_REFERENCE_PATTERN = re.compile(r"^[A-Z0-9]{5,8}$")


class BookingsConnector:
    """Looks up passenger bookings, independent of the backing store."""

    def __init__(self, path: Path) -> None:
        self._records: list[dict[str, Any]] = load_json_records(path, "bookings")

    def find(self, booking_reference: str, last_name: str) -> LookupResult:
        """Find a booking by reference and passenger last name."""
        reference = booking_reference.strip().upper()
        surname = last_name.strip()

        if not _BOOKING_REFERENCE_PATTERN.match(reference):
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message=(
                    "Booking reference must be 5-8 letters or digits, "
                    f"got {booking_reference!r}."
                ),
            )
        if not surname:
            return LookupResult(
                status=LookupStatus.INVALID_INPUT,
                message="Last name must not be empty.",
            )

        for record in self._records:
            same_reference = record["booking_reference"].upper() == reference
            same_surname = record["last_name"].casefold() == surname.casefold()
            if same_reference and same_surname:
                return LookupResult(status=LookupStatus.FOUND, record=record)

        return LookupResult(
            status=LookupStatus.NOT_FOUND,
            message="No booking matches that reference and last name.",
            details={"booking_reference": reference, "last_name": surname},
        )


@lru_cache(maxsize=1)
def get_bookings_connector() -> BookingsConnector:
    """Return the process-wide bookings connector singleton."""
    return BookingsConnector(BOOKINGS_PATH)
