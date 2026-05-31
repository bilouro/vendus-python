"""Payment models — input for receipt-type documents, output for method listing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Payment(BaseModel):
    """A payment to attach to a receipt-type document (e.g. Fatura-Recibo).

    A Fatura-Recibo (FR) records payment at the moment of issue, so Vendus
    requires at least one payment whose amounts cover the document total.

    ``method_id`` is the **account-specific** id of a configured payment method
    (list them with ``client.documents.list_payment_methods()``). ``amount`` is
    gross (the value paid by this method).
    """

    model_config = ConfigDict(extra="forbid")

    method_id: int = Field(..., description="Account payment-method id (see list_payment_methods).")
    amount: Decimal = Field(..., gt=0, description="Gross amount paid by this method.")
    date_due: Optional[date] = Field(default=None, description="Due date for deferred payments.")


class PaymentMethod(BaseModel):
    """A payment method configured on the Vendus account."""

    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    type: str = Field(..., description="Vendus method type code, e.g. NU, MB, CC, MBWAY.")
    status: Optional[str] = None
