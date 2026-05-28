"""Unofficial Python SDK for the Vendus invoicing API (Portugal)."""

from __future__ import annotations

from vendus._client import VendusClient
from vendus._version import __version__
from vendus.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    TransportError,
    ValidationError,
    VendusError,
)
from vendus.models import (
    ClientData,
    Document,
    DocumentItem,
    DocumentStatus,
    DocumentType,
    TaxExemption,
)

__all__ = [
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "ClientData",
    "Document",
    "DocumentItem",
    "DocumentStatus",
    "DocumentType",
    "NotFoundError",
    "RateLimitError",
    "TaxExemption",
    "TransportError",
    "ValidationError",
    "VendusClient",
    "VendusError",
    "__version__",
]
