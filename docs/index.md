# vendus Python SDK

[![PyPI version](https://img.shields.io/pypi/v/vendus)](https://pypi.org/project/vendus/)
[![Python versions](https://img.shields.io/pypi/pyversions/vendus)](https://pypi.org/project/vendus/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/bilouro/vendus-python/blob/main/LICENSE)

Python SDK for [Vendus](https://www.vendus.pt), Portugal's AT-certified invoicing & POS platform.

!!! warning "Community SDK"
    This is an independent open-source project, not affiliated with or endorsed by Vendus.

## Quickstart

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient(api_key="your-api-key")

invoice = client.documents.create_invoice(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Consulting hours",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ],
)

print(invoice.number)   # "FT 2026/123"
print(invoice.atcud)    # AT communication code
print(invoice.qrcode)   # AT QR code payload
```

## Supported document types

| Document | Code | Method | Status |
|---|---|---|---|
| [**Invoice**](documents/invoice.md) | FT | `client.documents.create_invoice` | ✅ |
| [**Simplified Invoice**](documents/simplified-invoice.md) | FS | `client.documents.create_simplified_invoice` | ✅ |
| [**Invoice-Receipt**](documents/invoice-receipt.md) | FR | `client.documents.create_invoice_receipt` | ✅ |
| [**Receipt**](documents/receipt.md) | RG | `client.documents.create_receipt` | ✅ |
| [**Credit Note**](documents/credit-note.md) | NC | `client.documents.create_credit_note` | ✅ |

## Why this SDK?

- **Sync + Async** — same client, `_async` suffix for async variants
- **Fully typed** — `mypy --strict`, full IDE autocomplete
- **`Decimal` for money** — never `float`. Cent precision required by AT
- **Safe retries** — GET auto-retries; POST only when `external_reference` is present (prevents duplicate fiscal documents)
- **NIF validated locally** — mod 11 algorithm, fails before hitting the API
- **PII redaction in logs** — `fiscal_id`, email, phone, address
- **AT is opaque** — Vendus communicates with AT; the SDK never talks to AT directly

## Next steps

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Installation**

    ---

    Install and configure in 2 minutes

    [:octicons-arrow-right-24: Get started](getting-started/index.md)

-   :material-file-document:{ .lg .middle } **Documents**

    ---

    Which type to use? Decision guide

    [:octicons-arrow-right-24: Documents](documents/index.md)

-   :material-flask:{ .lg .middle } **Recipes**

    ---

    Guides for FastAPI, Flask, Django

    [:octicons-arrow-right-24: Recipes](recipes/index.md)

-   :material-alert-circle:{ .lg .middle } **Errors**

    ---

    Exception hierarchy and handling

    [:octicons-arrow-right-24: Errors](errors/index.md)

</div>
