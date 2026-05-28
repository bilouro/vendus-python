"""Base class for resource services."""

from __future__ import annotations

from typing import Any

import httpx

from vendus._http import HttpTransport


class BaseService:
    """Shared plumbing for all resource services.

    Each subclass calls self._request / self._request_async; auth and base URL
    are injected by HttpTransport.
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

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
