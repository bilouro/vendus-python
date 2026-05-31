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
    CreditLine,
    Document,
    DocumentItem,
    DocumentMode,
    DocumentStatus,
    DocumentType,
    Payment,
    PaymentMethod,
    TaxCategory,
    TaxExemption,
)

__all__ = [
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "ClientData",
    "CreditLine",
    "Document",
    "DocumentItem",
    "DocumentMode",
    "DocumentStatus",
    "DocumentType",
    "NotFoundError",
    "Payment",
    "PaymentMethod",
    "RateLimitError",
    "TaxCategory",
    "TaxExemption",
    "TransportError",
    "ValidationError",
    "VendusClient",
    "VendusError",
    "__version__",
]
