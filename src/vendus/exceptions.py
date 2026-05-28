"""Exception hierarchy. Public API."""

from __future__ import annotations

from typing import Any


class VendusError(Exception):
    """Base exception for all SDK errors."""


class ValidationError(VendusError):
    """Local validation failed before any API call."""


class AuthenticationError(VendusError):
    """API key was rejected by Vendus (HTTP 401)."""


class AuthorizationError(VendusError):
    """Authenticated but not authorized for the requested action (HTTP 403)."""


class NotFoundError(VendusError):
    """Requested resource does not exist (HTTP 404)."""


class RateLimitError(VendusError):
    """Vendus rate limit hit (HTTP 429)."""


class APIError(VendusError):
    """Vendus returned an error response.

    Attributes:
        status_code: HTTP status code from the API.
        response_body: Parsed JSON body if available, else raw text.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TransportError(VendusError):
    """Network-level failure (timeout, connection refused, DNS)."""
