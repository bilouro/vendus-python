"""Base class for resource services."""

from __future__ import annotations

from typing import Any

import httpx

from vendus._http import HttpTransport
from vendus.models.document import DocumentMode


class BaseService:
    """Shared plumbing for all resource services.

    Each subclass calls self._request / self._request_async; auth and base URL
    are injected by HttpTransport.
    """

    def __init__(self, transport: HttpTransport, default_mode: DocumentMode | None = None) -> None:
        self._transport = transport
        self._default_mode = default_mode

    def _effective_mode(self, mode: DocumentMode | None) -> DocumentMode | None:
        """Resolve the working mode: a per-call ``mode`` wins; otherwise fall back
        to the client's ``default_mode`` (and finally to None → the register's mode)."""
        return mode if mode is not None else self._default_mode

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return self._transport.request(method, path, json=json, params=params)

    async def _request_async(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return await self._transport.request_async(method, path, json=json, params=params)
