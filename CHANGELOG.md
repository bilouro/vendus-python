# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `mode` parameter (`DocumentMode` enum: `NORMAL` / `TESTS`) on `create_invoice`,
  `create_invoice_receipt`, `create_credit_note` (sync + async) — issue non-fiscal
  test-mode documents that Vendus does not communicate to the AT
- `default_mode` on `VendusClient` / `from_env` — applied to every create that omits
  `mode`, so the intended mode is set once (a per-call `mode` still overrides it).
  `mode` otherwise inherits the register's mode, which is `tests` on new accounts
- `Document.tax_authority_id` — the AT-generated id, empty until Vendus reports the
  document to the AT (lets you confirm a test document was not reported)
- `TaxCategory` enum (`NORMAL`/`INTERMEDIATE`/`REDUCED`/`EXEMPT`/`OTHER`) for line-item VAT
- `Payment` model and `list_payment_methods()` (sync + async) — a Fatura-Recibo now
  takes `payments=[Payment(method_id=..., amount=...)]`; method ids are account-specific
- `PaymentMethod` model returned by `list_payment_methods()`
- `CreditLine` model + `lines` argument on `create_credit_note` — credit only specific
  rows/quantities (partial credit); omit for a full credit, which now skips lines that
  are already fully credited. Verified live on a real multi-line invoice
- `error_code` attribute on every exception (the Vendus error code, e.g. `P001`)
- `DocumentType` now covers the full `documents/types` reference (`FG`, `GA`, `GD`, `GR`,
  `DC`, `PF`, `OT`, `EC`) plus `RG` (observed live)
- Docs: a dedicated **Payment methods** page (`list_payment_methods`, the `Payment` model,
  split payments, `date_due`), all live-validated
- `list_registers()` (sync + async) and the `Register` model — read the account's
  registers (caixas) to discover a `register_id` and its working mode. Registers are
  read-only via the API (configured in the Vendus backoffice)
- `DocumentType.UNKNOWN` — forward-compat sentinel so the SDK does not crash on type
  codes the API returns but the enum does not model (e.g. `RG`); the raw code stays in
  `raw_response`
- Live integration tests (`tests/integration/`, excluded by default): FT and FR in test
  mode, plus read-only `list_payment_methods`/`list`/`get` against real documents
- Initial project skeleton
- `VendusClient` with HTTP Basic Auth
- `DocumentsService.create_invoice` (sync + async)
- `DocumentsService.create_invoice_receipt` (sync + async)
- `DocumentsService.create_credit_note` (sync + async)
- `get` / `list` / `cancel` (sync + async)
- `ClientData` supports three shapes: with NIF, name-only, or omitted (final consumer)
- Pydantic v2 models for documents, items, taxes, inline client data
- Portuguese NIF validation
- PII redaction filter for logging
- HttpTransport with conditional POST retries (R3)
- 93 unit tests with `respx` mocks (95% coverage), plus live integration tests
- Bilingual documentation (PT/EN) with mkdocs-material + i18n
- 10 runnable examples, including an all-scenarios reference
- CI workflow (ruff, mypy --strict, pytest on Python 3.9–3.13)
- Docs auto-deploy to GitHub Pages
- Issue/PR templates and Dependabot config

### Changed
- A Vendus `P001` (field-validation error, returned with HTTP 403) now raises
  `ValidationError` instead of the misleading `AuthorizationError`.
- `DocumentType.QUOTE` is now `"OT"` (was the incorrect `"OR"`) and `DocumentType.RECEIPT`
  is `"RG"` (observed live; was the unverified `"RC"`), aligning with the Vendus reference.
- **Breaking:** `DocumentItem.tax_rate` (a `Decimal` percentage) is now `tax_category`
  (a `TaxCategory` enum). Vendus classifies line-item VAT by category (`tax_id`:
  NOR/INT/RED/ISE/OUT), not by a numeric rate — the rate is defined by the category in
  the merchant's Vendus configuration.
- **Breaking:** `cancel(document_id)` no longer takes a `reason` — the Vendus document
  PATCH endpoint has no field for a cancellation reason. It now also fetches the document
  and **refuses to cancel FT/FR/NC** (fiscal documents cannot be cancelled; reverse them
  with a credit note), raising `ValidationError` with that guidance.
- **Breaking:** `create_credit_note(reference_document_id, reason, ...)` no longer takes
  `register_id`/`items`/`client`. It fetches the original and credits its full set of
  lines (the original must be a real, retrievable document). The previous signature never
  worked: Vendus rejected the old top-level `reference_document_id` field.
- **Breaking:** `create_invoice_receipt(...)` now requires `payments` — an FR records
  payment on issue and Vendus rejects it otherwise.
- Docs: replaced the "Sandbox" section with a sourced "Testing" section. Vendus has
  no separate sandbox host; testing is done via document-level test mode. Corrects a
  prior unsourced claim that every call creates real fiscal documents.

### Fixed
- Line items now send the field names the real Vendus API actually accepts — found by
  live validation, which returned `P001` for the old names: `tax_id` (was `tax_rate`),
  `discount_percentage` (was `discount`), `id` (was `product_id`). `create_invoice` had
  never succeeded against the live API before this.
- `cancel` no longer sends `notes` (rejected by the document PATCH endpoint, which
  accepts only `status`/`mode`).
- Credit notes now build the wire body Vendus accepts — found live: each credit line
  references the original via `reference_document` (number + row) and the original line
  id, instead of the rejected top-level `reference_document_id`.
- `_parse_document` tolerates unknown document type codes instead of raising
  (the live account returned `RG`, which is absent from the documents/types reference).
- `create_credit_note` raises a clearer `NotFoundError` when the original can't be read
  (e.g. a test-mode document), explaining it must be a real, retrievable document.
- Error-message extraction for the `{"errors": [{"code", "message"}]}` body shape — the
  message (not the raw dict) is now used for the exception text.

### Quality
- `mypy --strict` passes with zero errors
- `ruff check` / `ruff format` clean

[Unreleased]: https://github.com/bilouro/vendus-python/compare/main...HEAD
