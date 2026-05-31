# Payment methods

A **Fatura-Recibo (FR)** records payment at the moment of issue, so it requires one or
more `payments`. Payment-method ids are **account-specific** — list them once and reuse
the ids you need.

## Listing the account's methods

```python
from vendus import VendusClient

client = VendusClient.from_env()
for m in client.documents.list_payment_methods():
    print(m.id, m.title, m.type)   # e.g. 191432483 Dinheiro NU
```

Each is a `PaymentMethod`:

| Field | Description |
|---|---|
| `id` | the id to pass as `Payment.method_id` |
| `title` | your own display name, configured in Vendus (e.g. "Dinheiro", "Multibanco") |
| `type` | the official Vendus code — e.g. `NU` (cash), `CC` (credit card), `CD` (debit card), `MB` (Multibanco reference), `MBWAY`, `TB` (bank transfer), `DNP` (current account). `title` and `type` are independent — an account may label a `CD` method "Multibanco" |
| `status` | `on` / `off` |

## Attaching payments to a receipt

```python
from decimal import Decimal
from vendus import Payment

cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

receipt = client.documents.create_invoice_receipt(
    register_id=1,
    items=[...],
    payments=[Payment(method_id=cash.id, amount=Decimal("90.00"))],
)
```

The payments must cover the document total.

### Split across several methods

```python
payments=[
    Payment(method_id=cash.id, amount=Decimal("50.00")),
    Payment(method_id=mbway.id, amount=Decimal("40.00")),
]
```

### Deferred payment

A `Payment` may carry a `date_due`:

```python
from datetime import date

Payment(method_id=transfer.id, amount=Decimal("90.00"), date_due=date(2026, 12, 31))
```

`Payment` fields: `method_id` (`int`, required), `amount` (`Decimal`, required, gross),
`date_due` (`date`, optional).

!!! note "Live-validated"
    A single method, multiple methods, split payments, and `date_due` are all validated
    against the real Vendus API.
