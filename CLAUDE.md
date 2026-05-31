# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Unofficial Python SDK for the [Vendus](https://www.vendus.pt) invoicing API (Portugal). Published as `vendus` on PyPI. Community-driven, open-source, designed for **professional adoption** — companies should be able to trust this SDK in production.

Vendus is an AT-certified (Autoridade Tributária) invoicing/POS SaaS. The Vendus backend handles all communication with the AT (SAF-T, ATCUD, QR code, document hash). This SDK talks to Vendus; Vendus talks to AT. The SDK never communicates with the AT directly.

## Working Principle: Always Honest, Never Assume (non-negotiable)

This rule overrides convenience. It applies to code, comments, docs, commit messages, and every reply to the user.

- **State only what is verified.** If something is not confirmed, say so explicitly and label it as an assumption or unknown — never present a guess or general knowledge as established fact.
- **Cite the source for any claim about the Vendus API or AT behavior.** No source → mark it `TBD` in the code/docs and flag it for verification. Do not write unsourced assertions into user-facing docs.
- **When asked "how do we know X?"**, if there is no verified source, say so plainly instead of rationalizing after the fact.
- **When uncertain, verify or ask before acting.** Don't fill gaps with plausible-sounding details.
- **No contradictions between artifacts.** If the docs claim something the code/CLAUDE.md still lists as `TBD`, that is a bug — resolve it, don't paper over it.

> Origin: the docs once stated "Vendus has no public sandbox" as fact, with no cited source, while CLAUDE.md still listed sandbox as `TBD — investigate`. That unsourced assertion is exactly what this rule forbids.

## Build Disciplines (non-negotiable)

R1–R16 are the rules. The two disciplines below are called out separately because they are
not encoded as numbered rules and this project has already been bitten by their absence.

### Live-validation discipline — non-negotiable

Two test layers, both required:

| Layer | Tool | Runs | Purpose |
|---|---|---|---|
| Unit | `pytest` + `respx` | every commit / CI | guard the **exact wire body**, validation, sync/async parity |
| Live | `pytest -m integration` | on demand | prove the SDK works against the **real Vendus API** end-to-end |

- Unit tests **assert the exact JSON sent on the wire**, not just the return value — that is how latent field-name/shape bugs are caught (`body = json.loads(route.calls[0].request.content); assert body == {...}`).
- Live tests live in `tests/integration/`, are marked `@pytest.mark.integration` (excluded from the default `pytest` run), and **auto-skip** when `VENDUS_API_KEY` is absent — no false failures on machines without creds.
- **One live test per operation**, exercising the full loop (SDK → Vendus → parse). Run them against the **test-mode register configured in `.env`** (`VENDUS_REGISTER_ID`, a register whose `mode` is `tests`) so live tests issue **non-fiscal** documents that are never reported to the AT.
- **"If you didn't run it against the real Vendus API, it isn't done."** The Vendus `.doc` reference pages describe what *should* happen; verify the actual wire shape live before claiming an operation works. This is the operational form of the *Always Honest, Never Assume* rule above.

### Honesty in status reporting

- README / CHANGELOG / roadmap use a **per-operation matrix** (Unit ✅ / Live ✅), never a blanket "service done".
- Never mark a row **Done** without a live test — or a live test that **skips with a documented reason**. A skipped-with-reason test is honest; a green test that never hit the API is a trap.
- When the upstream docs turn out wrong or incomplete: fix the SDK, add a unit test asserting the **corrected** wire body, then the live test passes — and record the divergence (with the Vendus error it fixed) in the CHANGELOG.

## Scope (v0.1.0 — MVP)

- Issue invoices (FT)
- Issue invoice-receipts (FR)
- Issue credit notes (NC) referencing an original document
- Inline client upsert by `fiscal_id` (NIF) — **no separate clients service in v0.1.0**
- Client shapes supported in `create_invoice` / `create_invoice_receipt`:
  - `ClientData(name=..., fiscal_id=...)` — identified with NIF
  - `ClientData(name=...)` — identified by name only (fiscal_id optional)
  - `client=None` (omit) — final consumer (anonymous)
- Get / list / cancel documents
- Sync + async API

Everything else is roadmap.

## Commands

```bash
# Development setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Run checks (must all pass before commit)
ruff check .                        # lint
ruff format .                       # auto-format
mypy src/                           # strict type checking
pytest                              # tests with coverage (≥85% enforced)

# Run specific tests
pytest tests/unit/test_documents.py
pytest -k "test_create_invoice"
pytest -m "not integration"         # skip sandbox tests
```

---

## Architecture

### Pattern: Stripe-inspired client with Mollie-style mixins

```
VendusClient (lazy-loads services via properties)
  └── DocumentsService(BaseService)
        ├── _request()             ← sync, auth injected by BaseService
        └── _request_async()       ← async variant
              └── HttpTransport    ← httpx wrapper with retry, timeout, audit hook
                    └── BasicAuth  ← api_key as Basic Auth username
```

### File Structure

```
src/vendus/
├── __init__.py          ← Public API: VendusClient, models, exceptions, __version__
├── _client.py           ← VendusClient — the only thing users instantiate
├── _http.py             ← HttpTransport — httpx sync+async, retry, timeout, User-Agent
├── _auth.py             ← BasicAuth (api_key as username, empty password)
├── _config.py           ← URLs, prefixes, defaults — no magic, all constants
├── _logging.py          ← PII redaction filter (fiscal_id, email, address, phone)
├── _validators.py       ← validate_nif_pt, etc.
├── exceptions.py        ← Exception hierarchy (public API)
├── models/              ← Pydantic v2 models (public API)
│   ├── document.py      ← Document, DocumentItem, DocumentType, DocumentStatus
│   ├── client.py        ← ClientData (inline payload only — no persistent Client in v0.1)
│   └── tax.py           ← Tax, TaxExemption (codes M01–M99)
├── services/            ← One module per resource
│   ├── _base.py         ← BaseService with _request/_request_async + auth injection
│   └── documents.py     ← DocumentsService (invoices + credit notes)
├── webhooks/            ← Stub for v0.4
└── py.typed             ← PEP 561 marker
```

### Underscore convention

- `_filename.py` = internal module, not part of public API
- `filename.py` = public module, exported in `__init__.py`

---

## Rules for Development

### R1: Naming Convention — The Unified Vocabulary

The Vendus API uses Portuguese-influenced naming (`fiscal_id`, `amount_gross`). The SDK normalizes to a single English vocabulary. **Never invent SDK names that don't match Vendus when there's no good reason to differ** — but DO normalize where the Vendus name is ambiguous or domain-specific.

| Concept | SDK name | Vendus API | Python type |
|---|---|---|---|
| Fiscal ID (NIF) | `fiscal_id` | `fiscal_id` | `str` |
| Client name | `name` | `name` | `str` |
| Document ID | `id` | `id` | `int` |
| Document number | `number` | `number` | `str` |
| Document type | `type` | `type` | `DocumentType` enum |
| Subtype | `subtype` | `subtype` | `str` |
| Working mode | `mode` | `mode` | `DocumentMode` enum |
| Date issued | `date` | `date` | `datetime` |
| Local time | `local_time` | `local_time` | `datetime` |
| System time | `system_time` | `system_time` | `datetime` |
| Gross amount | `gross_amount` | `amount_gross` | `Decimal` |
| Net amount | `net_amount` | `amount_net` | `Decimal` |
| Tax amount | `tax_amount` | (derived) | `Decimal` |
| AT hash | `hash` | `hash` | `str` |
| ATCUD | `atcud` | `atcud` | `str` |
| AT document ID | `tax_authority_id` | `tax_authority_id` | `str` |
| QR code data | `qrcode` | `qrcode` | `str` |
| External reference | `external_reference` | `external_reference` | `str` |
| Reference document | `reference_document_id` | (credit note ref) | `int` |
| Item description | `description` | `title` | `str` |
| Item quantity | `quantity` | `qty` | `Decimal` |
| Item unit price | `unit_price` | `gross_price` | `Decimal` |
| Item discount % | `discount` | `discount_percentage` | `Decimal` |
| Product id | `product_id` | `id` | `int` |
| Tax category | `tax_category` | `tax_id` | `TaxCategory` enum |
| Tax exemption | `tax_exemption` | `tax_exemption` | `TaxExemption` enum |

**When adding a new resource:** look at its API fields. Use the table. If a new concept appears, add it here and use it consistently.

### R2: Money is Decimal, Never Float

```python
# CORRECT
gross_amount=Decimal("49.90")

# WRONG — float causes 49.8999... bugs
gross_amount=49.90
```

All money fields in models are `Decimal`. Convert with `float(amount)` only at the serialization boundary (inside the service method, never in models). Fiscal compliance demands cent-precision.

### R3: POST Retries Are Conditional

Vendus does NOT have idempotency keys, but **accepts `external_reference`** as a deduplication anchor. The `HttpTransport` enforces:

- **GET**: retry up to `max_retries` with exponential backoff + jitter
- **POST/PUT/DELETE**: retry **only if** the body contains `external_reference`; otherwise fail immediately
- **DELETE on documents**: never retry (cancellation must be idempotent on the user's side)

This differs from the eupago SDK (where POST never retries). Document type-specific: a credit-note POST with `external_reference` is safe to retry; without it, it could duplicate a fiscal document.

### R4: Auth is Simple — One Method Only

Vendus uses **HTTP Basic Auth** with the API key as username and empty password:

```
Authorization: Basic base64(api_key + ":")
```

`_auth.py` wraps `httpx.BasicAuth(api_key, "")`. There is no OAuth, no header keys, no body keys. The user passes `api_key` once to `VendusClient` and never thinks about it again.

### R5: Every Method Has a Sync + Async Variant

```python
class DocumentsService(BaseService):
    def create_invoice(self, ...) -> Document:
        body = _build_invoice_body(...)
        response = self._request("POST", _PATH_DOCUMENTS, json=body)
        return _parse_document(response.json())

    async def create_invoice_async(self, ...) -> Document:
        body = _build_invoice_body(...)
        response = await self._request_async("POST", _PATH_DOCUMENTS, json=body)
        return _parse_document(response.json())
```

- Shared logic in module-level functions (`_build_*`, `_parse_*`)
- Sync/async near-identical — only `self._request` vs `await self._request_async`
- `_async` suffix is the convention (not a separate client class)

### R6: No PII in Logs

`fiscal_id`, `email`, `phone`, `mobile`, `address`, `postalcode` are redacted by `_logging.py`. Never bypass the `vendus` logger. Never include PII in exception messages.

### R7: Validate Before Calling the API

Catch obvious errors locally:

```python
if not validate_nif_pt(fiscal_id):
    raise ValidationError(f"Invalid Portuguese NIF: {fiscal_id}")

if fiscal_id == "999999990":
    raise ValidationError(
        "Do not use 999999990 as fiscal_id. "
        "For final consumer invoices, omit the client field entirely."
    )

if gross_amount <= 0:
    raise ValidationError("Amount must be positive")
```

Use `ValidationError` (not `ValueError`). Validate constraints documented by Vendus/AT — don't invent extras.

### R8: Status Normalization

The user never sees raw Vendus status strings. Convert to `DocumentStatus` enum:

```python
class DocumentStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    CANCELLED = "cancelled"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
```

Mapping in `models/document.py` — `normalize_status()`. New statuses → add to the map.

### R9: Raw Response Always Available

Every `Document` includes `raw_response: dict` — the unparsed JSON from Vendus. Escape hatch for fields the SDK doesn't model yet. Documented as escape hatch only — not the recommended path.

### R10: Examples Show the Recommended Path, Not Every Parameter

"The API supports it" ≠ "the example should show it."

Checklist before writing an example:
1. Remove every parameter that has a sensible default
2. Add inline comments explaining **what each parameter does**
3. Read as a developer seeing the SDK for the first time
4. Compare with Stripe/Mollie/InvoiceXpress examples

### R11: Research UX, Not Just API

Before implementing: study how top SDKs present the feature, not just the raw endpoints.

For each new feature:
1. How does Stripe / InvoiceXpress / Moloni handle this?
2. Developer journey (setup → first call → webhook → done)?
3. Which params are "configure once" vs "pass every time"?

### R12: Document Types Are Enums, One Method Per Type

Each document type has its own method, not a single `create(type=...)`:

```python
client.documents.create_invoice(...)             # FT
client.documents.create_simplified_invoice(...)  # FS
client.documents.create_invoice_receipt(...)     # FR
client.documents.create_receipt(...)             # RG (references invoices, no items)
client.documents.create_credit_note(...)         # NC
# (future)
client.documents.create_quote(...)               # OT
```

Reason: each type has different mandatory/forbidden fields. A credit note **requires** `reference_document_id`; an invoice doesn't. Type-checking and autocomplete are better with dedicated methods.

### R13: Credit Notes Credit a Real Original Document

`create_credit_note(reference_document_id, reason)` credits the **full** original. Vendus requires each credit line to reference an existing line of the original (`reference_document` = document number + 1-based row) and to carry that line's id, so the SDK **GETs the original** (FT/FR) and replicates its lines. Consequences:

- The original must be **retrievable** → a real document, not a test-mode one (test docs aren't addressable).
- No inline `items`/`client` — they come from the original.
- Partial credit is supported via `lines=[CreditLine(row=..., qty=...)]` (omit for full); a full credit skips lines already credited (`qty_nc == 0`). Verified live: a 2-line FT credited line-by-line, `qty_nc` `[1,1]`→`[0,1]`→`[0,0]`.
- There is **no** top-level `reference_document_id` on the wire — Vendus rejects it (`P001`); the link lives per item (`reference_document` = number + 1-based row + the original line id).

### R14: Inline Client Only (v0.1.0)

`create_invoice` and `create_credit_note` accept client data inline. Vendus upserts by `fiscal_id`. The SDK does NOT:
- Provide a `clients` service in v0.1.0
- Do any post-creation lookup to enrich the response with a client id
- Cache fiscal_id → client_id mapping

If the app needs to track Vendus client IDs locally, that is its responsibility. A future version may expose `client_id` as an alternative to inline data — this is a non-breaking addition.

### R15: Final Consumer is Implicit

In Portuguese invoicing, "consumidor final" (final consumer) is represented by omitting the client entirely, NOT by passing `fiscal_id=999999990`. R7 enforces this at validation time.

### R16: Live-verified Wire Facts (do not regress)

These were confirmed against the **real** Vendus API; changing them silently re-breaks the SDK. Each was a bug the respx mocks hid until live-validation caught it:

- **Line items** send `tax_id` (a `TaxCategory` code — `NOR`/`INT`/`RED`/`ISE`/`OUT`), not `tax_rate`; `discount_percentage`, not `discount`; `id` for a product line, not `product_id`. Wrong names → `P001`.
- **FR (Fatura-Recibo) requires `payments`** — `[{"id": <method_id>, "amount": <gross>}]`. `method_id` is **account-specific**; list it via `list_payment_methods()` (`GET /v1.0/payments`). Missing → "o pagamento deve ser realizado no ato".
- **Cancel** = `PATCH /documents/{id}` with `{"status":"A"}` only (no reason field). **FT/FR/NC cannot be cancelled** ("Não é permitido cancelar este tipo de documentos") — the SDK fetches the type and refuses, pointing to a credit note.
- **Test-mode documents** live in a separate space: not retrievable/cancellable via `/documents/{id}` (404 "não existe").
- **Unknown type codes** (e.g. `RG`, seen live, absent from documents/types) must not crash parsing → `DocumentType.UNKNOWN`, raw code kept in `raw_response`.
- `tax_authority_id` is **empty in the POST response even for real fiscal documents** (ATCUD/hash mark a doc fiscal), so it is not a reliable test-vs-real discriminator at create time — the series prefix is (`FT T01P…` test vs `FT 01P…` real).
- **`mode` defaults to the register's mode.** This account's register is in `tests`, so a create that omits `mode` silently produces a *test* document (a real-mode NC came out `NC T01P…` because `mode` was omitted). Fix: set it once with `VendusClient(default_mode=DocumentMode.NORMAL)` (a per-call `mode` still overrides), or pass `mode=DocumentMode.NORMAL` on every create. A NC also credits a real original correctly when the NC itself is test (it lands in the test space, leaving the real original's `qty_nc` untouched).
- **Vendus returns HTTP 403 for `P001`** (a field/request validation error). The SDK maps `P001` → `ValidationError` (not `AuthorizationError`) and exposes `.error_code` on every exception. The error body shape is `{"errors": [{"code", "message"}]}`.
- **FR payments** accept multiple methods (`NU`/`CD`/`MBWAY`/`CC`/`TB`…), split across several `payments`, and a `date_due` — all live-verified. Method ids are per-account.
- **FS (Fatura Simplificada)** is paid on issue like an FR — it **requires `payments`** ("o pagamento deve ser realizado no ato"). A NC credits an FS (verified live).
- **RG (Recibo)** references invoices via **`invoices: [{"document_number": ...}]`** (not `id`/`number` — `P001`) and **requires `payments`** ("Missing Payments"); it carries no line items.
- **A receipt (RG) CAN be cancelled** (`PATCH status=A` succeeded live) — unlike FT/FR/NC. So `cancel()`'s happy path is live-verified via an RG, and the guard correctly lets RG through.

---

## How to Add a New Document Type (Future Versions)

Follow `services/documents.py::create_invoice` as the reference. Steps:

### 1. Define type-specific build function
```python
def _build_receipt_body(
    items: list[DocumentItem],
    ...
) -> dict[str, Any]:
    ...
```

### 2. Add method pair to DocumentsService
```python
def create_receipt(self, ...) -> Document: ...
async def create_receipt_async(self, ...) -> Document: ...
```

### 3. Add tests
- `tests/unit/test_documents.py::TestReceipt`
- JSON fixtures in `tests/fixtures/`
- Mock with `respx`

### 4. Update CHANGELOG and docs

---

## Vendus API Reference (Quick Lookup)

### Base URLs
- Production: `https://www.vendus.pt/ws/`
- Spain: `https://www.vendus.es/ws/`
- Sandbox: **none.** Vendus has no separate sandbox host. Testing is done via a document-level test mode — pass `mode=tests` on a create call, or use a register configured in `tests` mode (new accounts default to this). Test documents are non-fiscal and not communicated to the AT (their `tax_authority_id` stays empty). Sources: [documents.doc](https://www.vendus.pt/ws/v1.1/documents.doc), [registers.doc](https://www.vendus.pt/ws/v1.1/registers.doc), [Modo de Formação/Testes](https://www.vendus.cv/ajuda/modo-formacao-testes/). Not yet live-verified: whether a per-request `mode=tests` overrides a `normal` register.

### Endpoint Versions
- Documents: `v1.1` (`/ws/v1.1/documents/`)
- Clients: `v1.0` (`/ws/v1.0/clients/`) — not used in v0.1.0
- Products: `v1.0`
- Receipts: `v1.1`

The SDK's `_config.py` keeps per-resource version mapping.

### Authentication
- HTTP Basic Auth: username = `api_key`, password = `""`

### Document Types (Vendus codes)
Aligned with the authoritative `documents/types` reference (`OT`, not `OR`; plus `FG`,
`GA`/`GD`/`GR`, `DC`, `PF`, `EC`). `RG` was observed live (a receipt code absent from the
reference). Any code not in this enum parses to `DocumentType.UNKNOWN` (raw code kept in
`raw_response`).

| Code | Name | SDK enum |
|---|---|---|
| FT | Fatura | `DocumentType.INVOICE` |
| FS | Fatura Simplificada | `DocumentType.SIMPLIFIED_INVOICE` |
| FR | Fatura-Recibo | `DocumentType.INVOICE_RECEIPT` |
| FG | Fatura Global | `DocumentType.GLOBAL_INVOICE` |
| NC | Nota de Crédito | `DocumentType.CREDIT_NOTE` |
| ND | Nota de Débito | `DocumentType.DEBIT_NOTE` |
| GA | Guia de Ativos Próprios | `DocumentType.OWN_ASSETS_GUIDE` |
| GD | Guia de Devolução | `DocumentType.RETURN_GUIDE` |
| GR | Guia de Remessa | `DocumentType.SHIPPING_GUIDE` |
| GT | Guia de Transporte | `DocumentType.DELIVERY_NOTE` |
| DC | Consulta de Mesa | `DocumentType.TABLE_BILL` |
| PF | Fatura Pró-Forma | `DocumentType.PROFORMA` |
| OT | Orçamento | `DocumentType.QUOTE` |
| EC | Encomenda | `DocumentType.ORDER` |
| RG | Recibo (observed live) | `DocumentType.RECEIPT` |
| — | unmodelled code | `DocumentType.UNKNOWN` |

### Tax Exemption Reasons (AT codes M01–M99)
Common ones:
- `M01` — Artigo 16.º, n.º 6 do CIVA
- `M07` — Isento Artigo 9.º do CIVA (saúde, educação)
- `M10` — Regime de IVA de caixa
- `M16` — Isento Artigo 14.º do RITI (intracomunitária)
- `M19` — Outras isenções
- `M99` — Não sujeito; não tributado

### Response: POST /documents
```json
{
  "id": 12345,
  "type": "FT",
  "subtype": "FT",
  "number": "FT 2026/123",
  "date": "2026-05-27",
  "system_time": "2026-05-27 14:30:00",
  "local_time": "2026-05-27 14:30:00",
  "amount_gross": "49.90",
  "amount_net": "40.57",
  "hash": "ABCD",
  "atcud": "AAAAAAAA-123",
  "qrcode": "A:...*B:...*C:...",
  "output": "FT 2026/123",
  "output_data": "..."
}
```

Note: the client object is NOT returned. If the SDK needs the client id, it must `GET /clients?fiscal_id=...` separately. v0.1.0 does not do this.

---

## Roadmap

| Version | Scope | Status |
|---|---|---|
| **v0.1.0** | FT + FS + FR + RG + NC (issue, partial credit, get/list/cancel, payments, registers) | In progress |
| v0.2.0 | Remaining document types (OT, ND, GT, FG, guias…) | — |
| v0.3.0 | Clients service + `client_id` support | — |
| v0.4.0 | Products + Stocks | — |
| v0.5.0 | Webhooks (Flask/FastAPI/Django adapters) | — |
| v0.6.0 | CLI tool + dry-run mode | — |
| v1.0.0 | Stable API, full docs | — |

---

## Releasing to PyPI

The package is published to PyPI as [`vendus`](https://pypi.org/project/vendus/) via
**Trusted Publishing (OIDC)** — there are **no API tokens or secrets** anywhere. Never put
a PyPI token in the repo, CI, or chat. A published version is **immutable** (you cannot
re-upload it — bump the version to fix a mistake).

Trusted-publisher config (set once on PyPI → the project's Publishing settings): owner
`bilouro`, repo `vendus-python`, workflow `release.yml`, environment `pypi`.

### Cutting a release

1. Make sure `main` is green — `ruff check .`, `ruff format --check .`, `mypy src/`,
   `pytest`, `mkdocs build --strict` — and everything is committed and pushed.
2. Bump the version in `pyproject.toml` (`version = "X.Y.Z"`). Semver: stay on `0.x` while
   the public API may still break (a minor bump can break); go `1.0.0` only when you commit
   to API stability. Adding a new document type is non-breaking → a minor bump.
3. Cut the CHANGELOG: move `[Unreleased]` into `## [X.Y.Z] - YYYY-MM-DD`, and update the
   compare / tag links at the bottom.
4. Commit (`docs: cut CHANGELOG X.Y.Z`) and push to `main`.
5. Publish a **GitHub Release** with tag `vX.Y.Z` on `main` — in the UI, or:
   `gh release create vX.Y.Z --target main --title vX.Y.Z --notes-file <changelog-section>`.
   This triggers `release.yml`, which builds, runs `twine check`, and publishes to PyPI via
   OIDC. No token step.
6. Verify: the **Release** workflow is green and `pip install vendus==X.Y.Z` works.

## Authoring & Attribution

Commits, PRs, changelogs, READMEs, and any other public artifact must NOT credit Claude. No `Co-Authored-By: Claude` lines, no "Generated with Claude Code" footers. The user is the sole author. Operate as an invisible agent.

## Quality Standards

- `ruff check .` — zero warnings
- `ruff format --check .` — fully formatted
- `mypy src/` with `--strict` — zero errors
- `pytest` — all pass, coverage ≥85%
- All four checks must pass before any commit
- Python ≥3.9 — use `from __future__ import annotations`, never `match/case` or bare `X | Y` at runtime
- Every public function has type annotations
- `py.typed` marker present — IDEs get full autocomplete
