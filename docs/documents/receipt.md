---
description: "Issue a Vendus receipt (Recibo, RG) from Python — acknowledge payment of one or more invoices, referenced by document number."
---

# Receipt (RG)

## What it is

A **Recibo (RG)** acknowledges payment of one or more previously-issued invoices (e.g. an
[FT](invoice.md)). It references the invoices by their **document number** and records the `payments` —
it carries no line items of its own. Use it when you issued an unpaid invoice (FT) and the
client pays afterwards.

## Example

```python
from decimal import Decimal
from vendus import Payment, VendusClient

client = VendusClient.from_env()
cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

receipt = client.documents.create_receipt(
    register_id=1,
    invoice_numbers=["FT 2026/123"],   # the invoice(s) being paid
    payments=[Payment(method_id=cash.id, amount=Decimal("100.00"))],
)
print(receipt.number)  # "RG 2026/1"
```

## Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `register_id` | `int` | Yes | POS register id |
| `invoice_numbers` | `list[str]` | Yes | document numbers of the invoices being paid |
| `payments` | `list[Payment]` | Yes | how the payment was made |
| `external_reference` | `str` | No | enables safe POST retries |
| `mode` | `DocumentMode \| None` | No | `TESTS` for a non-fiscal test document |

## Notes

- **FT vs FR vs RG:** an **FT** bills the sale (may be unpaid); an **RG** is the receipt
  issued when it is paid; an **FR** combines both at once.
- Unlike invoices, a **receipt can be cancelled** — `client.documents.cancel(receipt.id)`
  (verified live).
