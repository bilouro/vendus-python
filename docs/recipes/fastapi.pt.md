# FastAPI

Endpoint async que recebe um pedido de fatura e devolve o documento emitido.

```python
# main.py
from decimal import Decimal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from vendus import (
    VendusClient, ClientData, DocumentItem,
    ValidationError, RateLimitError, APIError, TransportError,
)

app = FastAPI()
vendus = VendusClient.from_env()


class InvoiceItemIn(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal


class InvoiceIn(BaseModel):
    register_id: int
    fiscal_id: str | None = None
    client_name: str | None = None
    items: list[InvoiceItemIn]
    external_reference: str


@app.post("/invoices")
async def create_invoice(payload: InvoiceIn):
    client_data = None
    if payload.client_name:
        client_data = ClientData(name=payload.client_name, fiscal_id=payload.fiscal_id)

    items = [
        DocumentItem(
            description=i.description,
            quantity=i.quantity,
            unit_price=i.unit_price,
            tax_rate=i.tax_rate,
        )
        for i in payload.items
    ]

    try:
        invoice = await vendus.documents.create_invoice_async(
            register_id=payload.register_id,
            client=client_data,
            items=items,
            external_reference=payload.external_reference,
        )
    except ValidationError as e:
        raise HTTPException(400, detail=str(e))
    except RateLimitError:
        raise HTTPException(429, detail="rate limited")
    except (APIError, TransportError) as e:
        raise HTTPException(502, detail=str(e))

    return {
        "id": invoice.id,
        "number": invoice.number,
        "atcud": invoice.atcud,
        "qrcode": invoice.qrcode,
        "gross_amount": str(invoice.gross_amount),
    }
```

Notas:

- `VendusClient` é seguro para reutilizar entre requests
- `external_reference` deve vir do cliente HTTP (ex: order id) para garantir idempotência ponta-a-ponta
- Erros são mapeados para HTTP status apropriados
