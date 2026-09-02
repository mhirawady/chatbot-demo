"""Shared test fixtures."""

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture() -> Any:
    def _load(name: str) -> dict[str, Any]:
        with (FIXTURE_DIR / name).open(encoding="utf-8") as handle:
            data: dict[str, Any] = json.load(handle)
        return data

    return _load
