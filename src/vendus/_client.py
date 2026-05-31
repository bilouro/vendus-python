"""VendusClient — the single entry point users instantiate."""

from __future__ import annotations

import os
from typing import TypeVar

from vendus._auth import basic_auth
from vendus._config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    PRODUCTION_BASE_URL,
)
from vendus._http import HttpTransport
from vendus._version import __version__
from vendus.models.document import DocumentMode
from vendus.services._base import BaseService
from vendus.services.documents import DocumentsService

_S = TypeVar("_S", bound=BaseService)


class VendusClient:
    """Top-level client. Services are lazy-loaded via properties.

    Example:
        client = VendusClient(api_key="...")
        invoice = client.documents.create_invoice(...)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = PRODUCTION_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_mode: DocumentMode | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._transport = HttpTransport(
            auth=basic_auth(api_key),
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            sdk_version=__version__,
        )
        # Applied to every create_* call that does not pass `mode` explicitly.
        # Set DocumentMode.NORMAL once if your register defaults to test mode.
        self._default_mode = default_mode
        self._services: dict[str, BaseService] = {}

    @classmethod
    def from_env(
        cls,
        *,
        env_var: str = "VENDUS_API_KEY",
        default_mode: DocumentMode | None = None,
    ) -> VendusClient:
        """Construct from an environment variable."""
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} is not set")
        return cls(api_key=api_key, default_mode=default_mode)

    def _get_service(self, name: str, factory: type[_S]) -> _S:
        if name not in self._services:
            self._services[name] = factory(self._transport, self._default_mode)
        return self._services[name]  # type: ignore[return-value]

    @property
    def documents(self) -> DocumentsService:
        return self._get_service("documents", DocumentsService)
