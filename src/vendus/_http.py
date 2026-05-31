"""HTTP transport. httpx wrapper with retry, timeout, and status-code mapping.

R3: GET always retries on transient failures (timeout, 5xx, 429).
POST/PUT/DELETE retry **only** when the body contains `external_reference`
(Vendus's idempotency anchor).
"""

from __future__ import annotations

import random
import time
from typing import Any

import httpx

from vendus._config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    PRODUCTION_BASE_URL,
    USER_AGENT_PREFIX,
)
from vendus._logging import get_logger
from vendus.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    TransportError,
    ValidationError,
)

_logger = get_logger()

# HTTP status codes that are transient (worth retrying)
_RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class HttpTransport:
    """Sync + async HTTP transport with retry policy."""

    def __init__(
        self,
        auth: httpx.Auth,
        base_url: str = PRODUCTION_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        sdk_version: str = "0.1.0",
    ) -> None:
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max(0, max_retries)
        self._backoff_factor = backoff_factor
        self._user_agent = f"{USER_AGENT_PREFIX}/{sdk_version}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = self._build_url(path)
        retryable = self._is_retryable(method, json)

        with httpx.Client(
            auth=self._auth, timeout=self._timeout, headers=self._default_headers()
        ) as http:
            attempt = 0
            while True:
                try:
                    response = http.request(method, url, json=json, params=params)
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if retryable and attempt < self._max_retries:
                        self._sleep_for_retry(attempt)
                        attempt += 1
                        continue
                    raise TransportError(str(exc)) from exc

                if (
                    response.status_code in _RETRYABLE_STATUS
                    and retryable
                    and attempt < self._max_retries
                ):
                    self._sleep_for_retry(attempt)
                    attempt += 1
                    continue

                self._raise_for_status(response)
                return response

    async def request_async(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = self._build_url(path)
        retryable = self._is_retryable(method, json)

        async with httpx.AsyncClient(
            auth=self._auth, timeout=self._timeout, headers=self._default_headers()
        ) as http:
            attempt = 0
            while True:
                try:
                    response = await http.request(method, url, json=json, params=params)
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if retryable and attempt < self._max_retries:
                        await self._async_sleep_for_retry(attempt)
                        attempt += 1
                        continue
                    raise TransportError(str(exc)) from exc

                if (
                    response.status_code in _RETRYABLE_STATUS
                    and retryable
                    and attempt < self._max_retries
                ):
                    await self._async_sleep_for_retry(attempt)
                    attempt += 1
                    continue

                self._raise_for_status(response)
                return response

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base_url}/{path.lstrip('/')}"

    def _default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _is_retryable(method: str, body: dict[str, Any] | None) -> bool:
        """R3 retry policy."""
        method = method.upper()
        if method == "GET":
            return True
        if method in ("POST", "PUT", "PATCH"):
            return bool(body and body.get("external_reference"))
        # DELETE: never auto-retry
        return False

    def _sleep_for_retry(self, attempt: int) -> None:
        time.sleep(self._compute_backoff(attempt))

    async def _async_sleep_for_retry(self, attempt: int) -> None:
        import asyncio

        await asyncio.sleep(self._compute_backoff(attempt))

    def _compute_backoff(self, attempt: int) -> float:
        # Exponential backoff with full jitter
        base = self._backoff_factor * (2**attempt)
        return random.uniform(0, base)  # noqa: S311

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return

        body: Any
        try:
            body = response.json()
        except ValueError:
            body = response.text

        message = _extract_error_message(body) or f"HTTP {status}"
        code = _extract_error_code(body)

        # `P001` is a request/field validation error. Vendus returns it with HTTP
        # 403, which would otherwise surface as a misleading AuthorizationError.
        if code == "P001":
            raise ValidationError(message, error_code=code)
        if status == 401:
            raise AuthenticationError(message, error_code=code)
        if status == 403:
            raise AuthorizationError(message, error_code=code)
        if status == 404:
            raise NotFoundError(message, error_code=code)
        if status == 429:
            raise RateLimitError(message, error_code=code)
        raise APIError(message, status_code=status, response_body=body, error_code=code)


def _first_error(body: Any) -> dict[str, Any] | None:
    """Return the first error object from a Vendus error body, if present.

    Vendus uses ``{"errors": [{"code": ..., "message": ...}]}``.
    """
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            return errors[0]
        err = body.get("error")
        if isinstance(err, dict):
            return err
    return None


def _extract_error_message(body: Any) -> str | None:
    """Best-effort extraction of a human-readable error from a Vendus body."""
    first = _first_error(body)
    if first is not None:
        msg = first.get("message") or first.get("detail")
        if isinstance(msg, str) and msg:
            return msg
    if isinstance(body, dict):
        for key in ("message", "detail", "error"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(body, str) and body:
        return body
    return None


def _extract_error_code(body: Any) -> str | None:
    """Extract the Vendus error code (e.g. ``P001``) from a body, if present."""
    first = _first_error(body)
    if first is not None:
        code = first.get("code")
        if isinstance(code, str):
            return code
    if isinstance(body, dict):
        code = body.get("code")
        if isinstance(code, str):
            return code
    return None
