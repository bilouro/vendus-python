---
description: "Install the vendus Python SDK and issue your first Vendus invoice in minutes — API key setup, configuration and a working create_invoice example."
---

# Installation & Quickstart

## Installation

```bash
pip install vendus      # or: uv add vendus
```

- **PyPI:** <https://pypi.org/project/vendus/>
- **Python:** 3.9 – 3.13
- **Dependencies:** [httpx](https://www.python-httpx.org/) and [Pydantic v2](https://docs.pydantic.dev/) — nothing else
- **Typed:** ships a `py.typed` marker (PEP 561) — full autocomplete and `mypy` support

## Get your API key

1. Sign in at [www.vendus.pt](https://www.vendus.pt)
2. **Settings → Access → API**
3. Create/copy the API key

The API key identifies the user in Vendus — every document issued via API is attributed to that user.

## Configure credentials

Recommended: environment variable or `.env` file.

```bash
export VENDUS_API_KEY="your-key"
```

```python
from vendus import VendusClient

client = VendusClient.from_env()         # reads VENDUS_API_KEY
# or
client = VendusClient(api_key="...")
```

!!! danger "Never commit API keys"
    Add `.env` to `.gitignore`. Do not pass API keys as URL parameters or log them.

## First invoice

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient.from_env()

invoice = client.documents.create_invoice(
    register_id=1,                       # POS register ID configured in Vendus
    client=ClientData(
        name="Acme Lda",
        fiscal_id="123456789",
    ),
    items=[
        DocumentItem(
            description="Consulting",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"), # gross, includes VAT
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    external_reference="ORD-2026-001",   # enables safe POST retries
)

print(f"Invoice {invoice.number}")
print(f"Total: {invoice.gross_amount} EUR")
print(f"ATCUD: {invoice.atcud}")
print(f"QR: {invoice.qrcode}")
```

!!! warning "Test mode by default"
    New Vendus accounts have their register in **test mode**, so documents are non-fiscal
    until you switch to real mode. Pass `VendusClient(api_key=..., default_mode=DocumentMode.NORMAL)`
    (or `mode=` per call) for real documents. See [Configuration](configuration.md#default-document-mode).

## Reversing a document

Fiscal documents (FT/FR/NC) **cannot be cancelled** — `cancel()` rejects them. To reverse
an invoice, issue a credit note that credits it:

```python
client.documents.create_credit_note(
    reference_document_id=invoice.id,
    reason="Issued in error",
)
```

## Next steps

- [Configuration](configuration.md) — all `VendusClient` options
- [Which document type to choose?](../documents/index.md)
- [Invoice (FT)](../documents/invoice.md), [Invoice-Receipt (FR)](../documents/invoice-receipt.md), [Credit Note (NC)](../documents/credit-note.md)
