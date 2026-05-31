# vendus

[![PyPI version](https://img.shields.io/pypi/v/vendus)](https://pypi.org/project/vendus/)
[![Python versions](https://img.shields.io/pypi/pyversions/vendus)](https://pypi.org/project/vendus/)
[![CI](https://github.com/bilouro/vendus-python/actions/workflows/test.yml/badge.svg)](https://github.com/bilouro/vendus-python/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-mypy--strict-blue)](https://mypy.readthedocs.io/)
[![Docs](https://img.shields.io/badge/docs-bilouro.github.io-blue)](https://bilouro.github.io/vendus-python/)

The first Python SDK for [Vendus](https://www.vendus.pt), Portugal's AT-certified invoicing & POS platform.
Issue invoices, invoice-receipts, and credit notes — in 5 lines of Python.

**Documentation: [English](https://bilouro.github.io/vendus-python/) · [Português](https://bilouro.github.io/vendus-python/pt/)** | [Examples](examples/) | [API Reference](https://bilouro.github.io/vendus-python/api/)

> **Community SDK** — not affiliated with or endorsed by Vendus.
> For official integrations, visit [vendus.pt](https://www.vendus.pt).

## Installation

```bash
pip install vendus
```

Requires Python 3.9+. No additional dependencies beyond [httpx](https://www.python-httpx.org/) and [Pydantic v2](https://docs.pydantic.dev/).

## Quick Start

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient(api_key="your-api-key")

# Issue an invoice (FT)
invoice = client.documents.create_invoice(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Consulting hours",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"),  # gross (includes tax)
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    external_reference="ORD-2026-001",   # enables safe POST retries
)

print(invoice.number)   # "FT 2026/123"
print(invoice.atcud)    # AT communication code
print(invoice.qrcode)   # AT QR code payload
```

## Async Support

Every method has an async variant — same client, `_async` suffix:

```python
invoice = await client.documents.create_invoice_async(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[...],
)
```

## Three client shapes (one API)

The same `create_invoice` / `create_invoice_receipt` handles all three cases:

```python
# 1. Client with NIF (typical B2B)
client.documents.create_invoice(
    register_id=1, items=[...],
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
)

# 2. Client without NIF (B2C, customer gave name only)
client.documents.create_invoice(
    register_id=1, items=[...],
    client=ClientData(name="João Silva"),
)

# 3. Final consumer (anonymous, no identification at all)
client.documents.create_invoice(register_id=1, items=[...])
```

Do NOT pass `fiscal_id="999999990"` — the SDK rejects it. For final consumer, omit `client`.

## Credit Notes

A credit note (NC) credits a previously issued invoice. It is also the only way
to reverse a fiscal invoice — FT/FR **cannot be cancelled**. The SDK fetches the
original and credits its full set of lines, so you pass only the id and a reason:

```python
credit_note = client.documents.create_credit_note(
    reference_document_id=invoice.id,
    reason="Customer return",
    external_reference="REFUND-2026-001",
)
```

## Error Handling

All errors inherit from `VendusError` with typed subclasses:

```python
from vendus import (
    VendusClient,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    APIError,
    TransportError,
)

try:
    invoice = client.documents.create_invoice(...)
except ValidationError as e:
    # Local validation — invalid NIF, missing items, forbidden 999999990
    print(e)
except AuthenticationError:
    # API key rejected (401)
    ...
except RateLimitError:
    # 429 — back off
    ...
except APIError as e:
    # Other Vendus errors — inspect e.status_code and e.response_body
    ...
except TransportError:
    # Network failure — timeout, DNS, connection refused
    ...
```

## Configuration

```python
client = VendusClient(
    api_key="your-api-key",
    base_url="https://www.vendus.pt/ws",  # production (default)
    timeout=30.0,                          # seconds
    max_retries=3,                         # GET retries; POST only if external_reference present
)

# Or load from VENDUS_API_KEY
client = VendusClient.from_env()
```

## Supported Documents

| Document | Code | Method | Status |
|---|---|---|---|
| Fatura | FT | `client.documents.create_invoice` | ✅ |
| Fatura Simplificada | FS | `client.documents.create_simplified_invoice` | ✅ |
| Fatura-Recibo | FR | `client.documents.create_invoice_receipt` | ✅ |
| Recibo | RG | `client.documents.create_receipt` | ✅ |
| Nota de Crédito | NC | `client.documents.create_credit_note` | ✅ |
| Orçamento | OT | — | roadmap |
| Guia de Transporte | GT | — | roadmap |
| Nota de Débito | ND | — | roadmap |

### Validation status

The wire format of every operation is asserted by unit tests (respx mocks), and validated against the real Vendus API — in **test mode** (`mode=tests`, non-fiscal) where possible, and once in real mode for the operations that test mode can't reach:

| Operation | Unit | Live |
|---|:-:|---|
| `create_invoice` (FT) | ✅ | ✅ test + real |
| `create_simplified_invoice` (FS) | ✅ | ✅ test + real (credited by NC) |
| `create_invoice_receipt` (FR) | ✅ | ✅ test + real (+ payment variations) |
| `create_receipt` (RG) | ✅ | ✅ test + real (references an invoice) |
| `create_credit_note` (NC) | ✅ | ✅ real (full + partial; credits FT/FR/FS) |
| `cancel` | ✅ | ✅ refuses FT/FR/NC; cancels a receipt (RG) |
| `list_payment_methods` / `list_registers` / `list` / `get` | ✅ | ✅ read-only |

> Test-mode documents ("Modo de Formação") are non-fiscal and never reported to the AT, but Vendus stores them in a separate space — they can't be retrieved or credited via `/documents/{id}`, so credit notes are validated in real mode. Fiscal invoices (FT/FR/NC) can't be cancelled (reverse them with a credit note); a **receipt (RG) can** — both paths are live-verified.

## Why This SDK

- **Fully typed** — `mypy --strict` passes, `py.typed` marker included. Full autocomplete in VS Code and PyCharm.
- **Sync + Async** — one client, no separate packages. httpx powers both.
- **Decimal amounts** — no floating-point surprises with money. `Decimal("49.90")`, not `49.8999...`. Cent-precision matters for AT.
- **Safe retries** — GET retries with exponential backoff + jitter. POST retries only when `external_reference` is set (Vendus's deduplication anchor). Without it, POST fails immediately to avoid duplicate fiscal documents.
- **PII redaction** — fiscal_id, email, phone, address are automatically redacted from logs.
- **NIF validation** — Portuguese NIF check digit verified locally before any API call.
- **Exception hierarchy** — catch `ValidationError` for local issues, `AuthenticationError` for bad keys, `RateLimitError` for 429s, or `VendusError` for everything.
- **AT communication is opaque** — Vendus is the certified party. Hash, ATCUD, and QR code come ready from Vendus; the SDK never talks to AT directly.

## Development

```bash
git clone https://github.com/bilouro/vendus-python.git
cd vendus-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

Run checks (all must pass before a PR):

```bash
ruff check .          # lint
ruff format --check . # formatting
mypy src/             # type check (strict)
pytest                # unit tests + coverage (≥85% enforced)
```

**Live integration tests** hit the real Vendus API; they're excluded from `pytest` and
auto-skip without credentials. Run them in test mode against a demo account:

```bash
export VENDUS_API_KEY=... VENDUS_REGISTER_ID=...
pytest -m integration --no-cov
```

Full developer guide — testing, the live-validation discipline, and how to add a document
type — is on the [Contributing](https://bilouro.github.io/vendus-python/contributing/)
page, alongside `CLAUDE.md` and `TODO.md`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome — especially for new document types.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open public issues for security bugs.

## License

[MIT](LICENSE) — use it however you want.
