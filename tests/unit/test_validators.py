"""Tests for NIF validation (production-tested algorithm — see nif.md)."""

from __future__ import annotations

import pytest

from vendus._validators import is_pt_nif_candidate, nif_error, validate_nif_pt


@pytest.mark.parametrize(
    "nif",
    [
        "123456789",  # valid example
        "501964843",  # real NIPC (valid checksum)
        "450000001",  # first digit 4 — valid (the SDK used to wrongly reject 4/7)
        "700000003",  # first digit 7 — valid
        "101100000",  # check digit 0 (the historical bug case)
        "123 456 789",  # spaces are ignored
        "123-456-789",  # hyphens are ignored
    ],
)
def test_valid_nif(nif: str) -> None:
    assert validate_nif_pt(nif) is True
    assert nif_error(nif) is None


@pytest.mark.parametrize(
    "nif",
    [
        "",
        "12345678",  # 8 digits
        "1234567890",  # 10 digits
        "abcdefghi",  # no digits
        "499999990",  # valid first digit, wrong check digit
        "123456788",  # wrong check digit
    ],
)
def test_invalid_nif(nif: str) -> None:
    assert validate_nif_pt(nif) is False
    assert nif_error(nif) is not None


def test_is_pt_nif_candidate() -> None:
    assert is_pt_nif_candidate("123456789") is True
    assert is_pt_nif_candidate("123 456 789") is True
    assert is_pt_nif_candidate("GB123456789") is False  # has letters → foreign, skip
    assert is_pt_nif_candidate("12345") is False  # not 9 digits
