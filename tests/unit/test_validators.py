"""Tests for NIF validation."""

from __future__ import annotations

import pytest

from vendus._validators import validate_nif_pt


@pytest.mark.parametrize(
    "nif",
    [
        "123456789",  # Valid example
        "501964843",  # Real-shape NIPC (valid checksum)
    ],
)
def test_valid_nif(nif: str) -> None:
    assert validate_nif_pt(nif) is True


@pytest.mark.parametrize(
    "nif",
    [
        "",
        "12345678",
        "1234567890",
        "abcdefghi",
        "499999990",  # Invalid prefix
        "123456788",  # Wrong check digit
    ],
)
def test_invalid_nif(nif: str) -> None:
    assert validate_nif_pt(nif) is False
