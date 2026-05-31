"""FastAPI endpoint that issues invoices.

Run: uvicorn 09_fastapi_integration:app
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from vendus import (
    APIError,
    ClientData,
    DocumentItem,
    RateLimitError,
    TaxCategory,
    TransportError,
    ValidationError,
    VendusClient,
)

app = FastAPI()
vendus = VendusClient.from_env()


class ItemIn(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_category: TaxCategory


class InvoiceRequest(BaseModel):
    register_id: int
    fiscal_id: str | None = None
    client_name: str | None = None
    items: list[ItemIn]
    external_reference: str


@app.post("/invoices")
async def create_invoice(req: InvoiceRequest) -> dict[str, object]:
    client = None
    if req.client_name:
        client = ClientData(name=req.client_name, fiscal_id=req.fiscal_id)

    items = [
        DocumentItem(
            description=i.description,
            quantity=i.quantity,
            unit_price=i.unit_price,
            tax_category=i.tax_category,
        )
        for i in req.items
    ]

    try:
        invoice = await vendus.documents.create_invoice_async(
            register_id=req.register_id,
            client=client,
            items=items,
            external_reference=req.external_reference,
        )
    except ValidationError as e:
        raise HTTPException(400, detail=str(e)) from e
    except RateLimitError as e:
        raise HTTPException(429, detail="rate limited") from e
    except (APIError, TransportError) as e:
        raise HTTPException(502, detail=str(e)) from e

    return {
        "id": invoice.id,
        "number": invoice.number,
        "atcud": invoice.atcud,
        "qrcode": invoice.qrcode,
        "gross_amount": str(invoice.gross_amount),
    }
