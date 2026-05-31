# Invoice-Receipt (FR)

## What it is

The Invoice-Receipt (FR) is **an invoice and a receipt in one document**: it bills the sale **and** acknowledges payment at the same time. It is the right document when the client **pays on the spot**.

- Very common for **services** (consultations, freelancers, independent professionals)
- Avoids issuing an FT and then a separate RC
- Client identification: can include NIF, name only, or be anonymous

## Example

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, Payment, TaxCategory, VendusClient

client = VendusClient.from_env()

# An FR records payment on issue, so you must say HOW it was paid.
# Payment-method ids are account-specific — look them up once.
cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

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
    payments=[Payment(method_id=cash.id, amount=Decimal("90.00"))],
    external_reference="FR-2026-001",
)

print(fr.number)  # "FR 2026/12"
print(fr.atcud)
```

## Scenarios

```python
# 1. With NIF
client.documents.create_invoice_receipt(
    register_id=1, items=[...], payments=[...],
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
)

# 2. Name only (client did not provide NIF)
client.documents.create_invoice_receipt(
    register_id=1, items=[...], payments=[...],
    client=ClientData(name="João Silva"),
)

# 3. Final consumer (anonymous)
client.documents.create_invoice_receipt(register_id=1, items=[...], payments=[...])
```

## Async variant

```python
fr = await client.documents.create_invoice_receipt_async(
    register_id=1,
    items=[...],
    payments=[...],
)
```

## FT vs FR

| | Invoice (FT) | Invoice-Receipt (FR) |
|---|---|---|
| Bills the sale | ✅ | ✅ |
| Acknowledges payment | ❌ (needs a separate RC) | ✅ |
| When to use | Client pays later (on credit, net 30) | Client pays **on the spot** |

## Notes

1. **Immediate payment:** FR assumes payment happens at issue time, so `payments` is **required** — get the account's method ids from `list_payment_methods()`. If you bill on credit, use `create_invoice` (FT) instead.
2. **Cancellation:** an FR **cannot be cancelled** — reverse it with a credit note (`create_credit_note(reference_document_id=fr.id, reason=...)`).
3. **Credit note:** crediting an FR uses the same `create_credit_note` — it fetches the FR and credits its lines.
