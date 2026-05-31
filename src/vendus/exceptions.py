"""Exception hierarchy. Public API."""

from __future__ import annotations

from typing import Any


class VendusError(Exception):
    """Base exception for all SDK errors.

    Attributes:
        error_code: the Vendus error code (e.g. ``P001``, ``A001``) when the error
            came from the API, else ``None``.
    """

    def __init__(self, message: str = "", *, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class ValidationError(VendusError):
    """The request is invalid — caught locally before the call, or rejected by the
    API as malformed (Vendus ``P001``, e.g. a field that is not permitted)."""


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
        error_code: the Vendus error code from the body, if any.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any | None = None,
        *,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code)
        self.status_code = status_code
        self.response_body = response_body


class TransportError(VendusError):
    """Network-level failure (timeout, connection refused, DNS)."""
