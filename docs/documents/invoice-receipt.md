# Invoice-Receipt (FR)

## What it is

The Invoice-Receipt (FR) is **an invoice and a receipt in one document**: it bills the sale **and** acknowledges payment at the same time. It is the right document when the client **pays on the spot**.

- Very common for **services** (consultations, freelancers, independent professionals)
- Avoids issuing an FT and then a separate RC
- Client identification: can include NIF, name only, or be anonymous

## Example

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient.from_env()

fr = client.documents.create_invoice_receipt(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Consulting session (paid on the spot)",
            quantity=Decimal("1"),
            unit_price=Decimal("90.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    external_reference="FR-2026-001",
)

print(fr.number)  # "FR 2026/12"
print(fr.atcud)
```

## Scenarios

```python
# 1. With NIF
client.documents.create_invoice_receipt(
    register_id=1, items=[...],
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
)

# 2. Name only (client did not provide NIF)
client.documents.create_invoice_receipt(
    register_id=1, items=[...],
    client=ClientData(name="João Silva"),
)

# 3. Final consumer (anonymous)
client.documents.create_invoice_receipt(register_id=1, items=[...])
```

## Async variant

```python
fr = await client.documents.create_invoice_receipt_async(
    register_id=1,
    items=[...],
)
```

## FT vs FR

| | Invoice (FT) | Invoice-Receipt (FR) |
|---|---|---|
| Bills the sale | ✅ | ✅ |
| Acknowledges payment | ❌ (needs a separate RC) | ✅ |
| When to use | Client pays later (on credit, net 30) | Client pays **on the spot** |

## Notes

1. **Immediate payment:** FR assumes payment happens at issue time. If you bill on credit, use `create_invoice` (FT) and issue the receipt (RC) when the client pays — RC comes in a future version.
2. **Cancellation:** same API (`client.documents.cancel(id)`).
3. **Credit note:** an FR can be credited via `create_credit_note` referencing the FR's `id`.
