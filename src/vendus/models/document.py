"""Document models: invoices, credit notes, line items, status/type enums."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from vendus.models.tax import TaxCategory, TaxExemption


class DocumentType(str, Enum):
    """Vendus document types (AT-defined codes)."""

    INVOICE = "FT"
    SIMPLIFIED_INVOICE = "FS"
    INVOICE_RECEIPT = "FR"
    CREDIT_NOTE = "NC"
    DEBIT_NOTE = "ND"
    RECEIPT = "RC"
    QUOTE = "OR"
    DELIVERY_NOTE = "GT"


class DocumentMode(str, Enum):
    """Working mode for a document (Vendus ``mode`` field).

    NORMAL issues a real fiscal document that Vendus communicates to the AT.
    TESTS issues a non-fiscal "Modo de Formação/Testes" document that is **not**
    communicated to the AT (no fiscal validity) — the safe way to test.

    When omitted on a create call, Vendus uses the register's configured mode.
    """

    NORMAL = "normal"
    TESTS = "tests"


class DocumentStatus(str, Enum):
    """Normalized status. Mapped from Vendus raw strings by normalize_status()."""

    DRAFT = "draft"
    ISSUED = "issued"
    CANCELLED = "cancelled"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"


# Vendus raw status -> SDK enum
_STATUS_MAP: dict[str, DocumentStatus] = {
    "N": DocumentStatus.ISSUED,
    "A": DocumentStatus.CANCELLED,
    "draft": DocumentStatus.DRAFT,
    "paid": DocumentStatus.PAID,
    "partial": DocumentStatus.PARTIALLY_PAID,
}


def normalize_status(raw: str | None) -> DocumentStatus:
    """Map a Vendus raw status to the SDK enum. Unknown values default to ISSUED."""
    if raw is None:
        return DocumentStatus.ISSUED
    return _STATUS_MAP.get(raw, DocumentStatus.ISSUED)


class DocumentItem(BaseModel):
    """A line item on a document."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(..., description="Description shown on the document line.")
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, description="Gross unit price including tax.")
    tax_category: TaxCategory = Field(
        ...,
        description="VAT category. Maps to Vendus tax_id (e.g. NORMAL -> 'NOR').",
    )
    tax_exemption: Optional[TaxExemption] = Field(
        default=None,
        description="Required by AT when tax_category is EXEMPT. Use an M01-M99 code.",
    )
    discount: Optional[Decimal] = Field(default=None, ge=0, le=100)
    product_id: Optional[int] = None
    reference: Optional[str] = None


class Document(BaseModel):
    """A document returned by Vendus after creation or lookup."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    id: int
    type: DocumentType
    subtype: Optional[str] = None
    number: str
    date: Optional[datetime] = None
    local_time: Optional[datetime] = None
    system_time: Optional[datetime] = None
    gross_amount: Decimal
    net_amount: Decimal
    tax_amount: Optional[Decimal] = None
    hash: Optional[str] = None
    atcud: Optional[str] = None
    tax_authority_id: Optional[str] = Field(
        default=None,
        description=(
            "AT-generated document id. Only set once Vendus has communicated the "
            "document to the AT; empty for test-mode (non-fiscal) documents."
        ),
    )
    qrcode: Optional[str] = Field(default=None, description="AT QR code payload.")
    output: Optional[str] = None
    output_data: Optional[str] = None
    status: DocumentStatus = DocumentStatus.ISSUED

    # Escape hatch (R9) — unparsed JSON from Vendus.
    raw_response: dict[str, Any] = Field(default_factory=dict)
