# Contributing & Development

Thanks for your interest in `vendus`. This project aims at production quality — the
guiding rules and conventions are summarized below; read them before any substantial
change.

## Setup

```bash
git clone https://github.com/bilouro/vendus-python.git
cd vendus-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Quality gate (must pass before every PR)

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy src/               # strict type checking
pytest                  # unit tests + coverage (≥85% enforced)
```

If you touched docs, also build them strictly:

```bash
mkdocs build --strict
```

## Testing — two layers

The SDK is validated in two layers, and the second is what keeps it honest against the
real API.

### 1. Unit tests (every commit)

- `tests/unit/`, mocked with [`respx`](https://lundberg.github.io/respx/) — they never
  touch the network.
- They **assert the exact wire body**, not just the return value. That is how
  field-name / shape bugs are caught.
- Coverage gate: ≥85% (`pytest` fails below it).

```bash
pytest                              # all unit tests + coverage
pytest tests/unit/test_documents.py
pytest -k create_invoice
```

### 2. Live integration tests (on demand)

- `tests/integration/`, marked `@pytest.mark.integration` and **excluded from the
  default `pytest` run**. They hit the **real Vendus API**.
- They auto-skip unless `VENDUS_API_KEY` and `VENDUS_REGISTER_ID` are set, so they never
  fail in CI or on a machine without credentials.
- They run in **test mode** (`mode=tests`) where possible — non-fiscal documents that
  Vendus never reports to the AT.

```bash
export VENDUS_API_KEY=...         # an API key from a test/demo account
export VENDUS_REGISTER_ID=...     # see below
pytest -m integration --no-cov    # --no-cov: a subset run would otherwise trip the coverage gate
```

**Getting the ids you need:**

- `register_id` — `client.documents.list_registers()` (or the Vendus backoffice). Each
  register has an `id` and a `mode`.
- Payment-method ids (for a Fatura-Recibo) — `client.documents.list_payment_methods()`.

!!! warning "Use a dedicated test/demo account"
    Vendus has no separate sandbox host; "testing" is a document-level **test mode**.
    New accounts default their register to test mode, so live tests issue non-fiscal
    documents. See [Configuration → Testing](getting-started/configuration.md#testing).
    Test-mode documents are **not** retrievable or cancellable, so a live test cannot
    clean up after itself — they are inert. Anything you create in **real** mode is a
    permanent fiscal record; reverse an invoice with a credit note (see below).

## The live-validation discipline

The Vendus reference docs are not always complete — **validate the wire shape against
the real API before claiming an operation works.** Several real bugs were caught only
this way (the SDK's `create_invoice` never actually worked until live validation fixed
the line-item fields). The live-verified facts a contributor must respect:

- **Line items** send `tax_id` (a `TaxCategory` code: NOR/INT/RED/ISE/OUT), not
  `tax_rate`; `discount_percentage`, not `discount`; `id` for a product line, not
  `product_id`. Wrong names → the API returns `P001`.
- **Fatura-Recibo (FR)** requires `payments` — `[Payment(method_id=..., amount=...)]`,
  with account-specific method ids from `list_payment_methods()`.
- **Credit notes (NC)** credit a **real** original: the SDK GETs it and references each
  line by `reference_document` (number + row) + the original line id. An NC **cannot** be
  created in test mode (the test original isn't retrievable).
- **FT / FR / NC cannot be cancelled** — `cancel()` refuses them; reverse an invoice with
  a credit note.
- **`mode` inherits the register's mode** (test on new accounts). Set
  `VendusClient(default_mode=DocumentMode.NORMAL)` for real documents, or pass `mode=`
  per call. Forgetting it silently produces a test document.
- **Unknown document type codes** map to `DocumentType.UNKNOWN` (the raw code stays in
  `raw_response`) — never crash on a type the enum does not model.

## Architecture (orientation)

```
VendusClient            # the one class users instantiate; lazy-loads services
  └── DocumentsService  # create_*, get, list, cancel, list_payment_methods
        └── _request / _request_async    (auth + base URL injected by HttpTransport)
              └── HttpTransport           # httpx sync+async, retry, timeout, User-Agent
```

- `_filename.py` = internal; `filename.py` = public (exported in `__init__.py`).
- Money is `Decimal` everywhere; convert with `float()` only at the wire boundary.
- Every method has a sync and an `_async` variant.

## Adding a new document type

Use `services/documents.py::create_invoice` as the reference.

1. Add the code to the `DocumentType` enum in `models/document.py`.
2. Add a `_build_X_body(...)` builder in `services/documents.py`.
3. Add `create_X` and `create_X_async` to `DocumentsService`. Thread
   `self._effective_mode(mode)` for the `mode` argument so the client-level
   `default_mode` applies.
4. **Live-validate the wire body** against the real API before claiming it works — the
   reference docs may be incomplete (an FR needs `payments`; an NC needs per-line
   `reference_document`).
5. Add unit tests that assert the exact wire body (`tests/unit/`), with response
   fixtures in `tests/fixtures/`.
6. Add a runnable example in `examples/` and a doc page `docs/documents/X.md` (+ the
   Portuguese `X.pt.md`).
7. Update `CHANGELOG.md`.

## Pull Requests

- **One feature or fix per PR** — don't mix unrelated changes.
- **Include tests** for new code — minimum 85% coverage, asserting the exact wire body.
- **Update `CHANGELOG.md`** in the `[Unreleased]` section.
- **All CI checks must pass** — lint, types, tests (Python 3.9–3.13).
- **Live-validate** anything that hits the API before claiming it works (see above).
- Describe what changed and why in the PR body.

### Typical workflow

```bash
# 1. Create a branch
git checkout -b feature/debit-note

# 2. Develop and test
pytest tests/unit/test_documents.py

# 3. Check everything
ruff check . && ruff format --check . && mypy src/ && pytest

# 4. Commit and push
git add .
git commit -m "Add debit note (ND) support"
git push -u origin feature/debit-note

# 5. Open a PR on GitHub
```

## Code conventions

- **Python ≥3.9** — use `from __future__ import annotations`; never `match/case`, and use
  `Optional[...]` (not `X | None`) at runtime in Pydantic models.
- **`Decimal` for money** — never `float`; convert with `float()` only at the wire boundary.
- **Type annotations** on every public function (`mypy --strict` passes).
- **Google-style docstrings** on public functions.
- **`_filename.py`** = internal module, **`filename.py`** = public API (exported in `__init__.py`).
- **Never log PII** — `fiscal_id`, email, phone, and address are redacted automatically.
- **One method per document type**, each with a sync and an `_async` variant.
