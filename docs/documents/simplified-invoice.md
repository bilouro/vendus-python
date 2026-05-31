# Simplified Invoice (FS)

## What it is

A **Fatura Simplificada (FS)** is a simplified invoice for retail / final-consumer sales,
subject to AT amount limits (e.g. up to €1000 for a final consumer, €100 when a NIF is
given). Like a Fatura-Recibo, it is **paid on issue**, so `payments` is required; the
client is usually omitted (final consumer).

## Example

```python
from decimal import Decimal
from vendus import DocumentItem, Payment, TaxCategory, VendusClient

client = VendusClient.from_env()
cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

fs = client.documents.create_simplified_invoice(
    register_id=1,
    items=[
        DocumentItem(
            description="Coffee",
            quantity=Decimal("1"),
            unit_price=Decimal("2.50"),
            tax_category=TaxCategory.INTERMEDIATE,
        ),
    ],
    payments=[Payment(method_id=cash.id, amount=Decimal("2.50"))],
)
print(fs.number)  # "FS 2026/1"
```

## Parameters

Same shape as `create_invoice_receipt`: `register_id`, `items`, `payments` (**required**),
plus optional `client`, `external_reference`, `mode`. See [Payment methods](payment-methods.md).

## Notes

- Use it for quick retail sales. For a full invoice with a client NIF above the FS limit,
  use [`create_invoice`](invoice.md) (FT).
- An FS is an invoice, so it is reversed with a [credit note](credit-note.md), not cancelled.
