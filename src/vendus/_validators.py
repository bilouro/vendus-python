"""Local validators. Catch errors before wasting an API call."""

from __future__ import annotations

# Valid first digits for Portuguese NIFs
_VALID_NIF_PREFIXES = ("1", "2", "3", "5", "6", "8", "9")


def validate_nif_pt(nif: str) -> bool:
    """Validate a Portuguese fiscal_id (NIF/NIPC).

    9 digits, valid prefix, check digit (mod 11) matches.
    """
    if not nif or len(nif) != 9 or not nif.isdigit():
        return False
    if nif[0] not in _VALID_NIF_PREFIXES:
        return False

    total = sum(int(nif[i]) * (9 - i) for i in range(8))
    remainder = total % 11
    check = 0 if remainder < 2 else 11 - remainder
    return check == int(nif[8])
