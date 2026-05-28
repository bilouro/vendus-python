"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from vendus import VendusClient

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def api_key() -> str:
    return "test-api-key"


@pytest.fixture
def client(api_key: str) -> VendusClient:
    return VendusClient(api_key=api_key)


@pytest.fixture
def load_fixture() -> Any:
    def _load(name: str) -> dict[str, Any]:
        path = _FIXTURES / name
        with path.open() as f:
            data: dict[str, Any] = json.load(f)
        return data

    return _load
