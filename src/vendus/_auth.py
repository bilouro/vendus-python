"""Authentication. Vendus uses HTTP Basic Auth with api_key as username."""

from __future__ import annotations

import httpx


def basic_auth(api_key: str) -> httpx.BasicAuth:
    """Return an httpx BasicAuth using api_key as username and empty password."""
    if not api_key:
        raise ValueError("api_key must be a non-empty string")
    return httpx.BasicAuth(username=api_key, password="")
