"""Inline client payload for document creation.

In v0.1.0 there is no separate Clients service. Clients are upserted by
`fiscal_id` (NIF) when a document is created.

To invoice a final consumer ("consumidor final"), omit the client entirely
from create_invoice — do NOT pass fiscal_id="999999990" (R7/R15).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ClientData(BaseModel):
    """Inline client data sent with a document.

    Two valid shapes:
    - With NIF: `ClientData(name="Acme Lda", fiscal_id="123456789")`
    - Name only: `ClientData(name="João Silva")` — for clients that did not
      provide a fiscal_id. Accepted by Vendus on FT and FR.

    To invoice a final consumer with NO identification at all, omit the
    `client` argument entirely from create_invoice / create_invoice_receipt.

    Vendus upserts by `fiscal_id` when present. The API does NOT return the
    client object in the document response.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., description="Client name or company name. Always required.")
    fiscal_id: Optional[str] = Field(
        default=None,
        description=(
            "NIF/NIPC. 9 digits for Portuguese clients. Optional — omit when "
            "the client did not provide one."
        ),
    )
    address: Optional[str] = None
    postalcode: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code (e.g. 'PT', 'ES').",
    )
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    billing_email: Optional[str] = None
    notes: Optional[str] = None
    external_reference: Optional[str] = None
    irs_retention: Optional[bool] = None
