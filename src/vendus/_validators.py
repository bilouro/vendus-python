"""Local validators. Catch errors before wasting an API call.

The NIF algorithm here is the production-tested one (see nif.md): módulo 11 with
weights 9..2 over the first 8 digits; `check = 11 - (sum % 11)`, and a `check >= 10`
becomes **0** (the AT rule — not 1, a historical bug that rejected ~9% of valid
NIFs ending in 0). Spaces and hyphens are ignored, and any first digit 1-9 is
accepted (4 and 7 are valid for some NIF ranges).
"""

from __future__ import annotations

import re


def nif_digits(nif: str | None) -> str:
    """Keep only the digits (NIFs are often written with spaces or hyphens)."""
    return re.sub(r"\D", "", str(nif or ""))


def nif_error(nif: str | None) -> str | None:
    """Return None if `nif` is a valid Portuguese NIF (NIF/NIPC), else a short reason."""
    if not nif or not str(nif).strip():
        return "missing NIF"
    s = nif_digits(nif)
    if len(s) != 9:
        return f"expected 9 digits, got {len(s)}"
    if s[0] not in "123456789":
        return f"invalid first digit ({s[0]})"
    total = sum(int(s[i]) * (9 - i) for i in range(8))
    check = 11 - (total % 11)
    if check >= 10:
        check = 0
    if int(s[8]) != check:
        return f"check digit mismatch (expected {check}, got {s[8]})"
    return None


def validate_nif_pt(nif: str | None) -> bool:
    """True if `nif` is a valid Portuguese NIF. Spaces/hyphens are ignored."""
    return nif_error(nif) is None


def is_pt_nif_candidate(fiscal_id: str) -> bool:
    """True if `fiscal_id` looks like a Portuguese NIF that should be validated:
    only digits with optional spaces/hyphens, and exactly 9 digits. A value with
    letters (e.g. a foreign tax id) is left for the API to judge."""
    if re.search(r"[A-Za-z]", fiscal_id):
        return False
    return len(nif_digits(fiscal_id)) == 9
