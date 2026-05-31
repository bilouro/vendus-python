# Contributing & Development

Thanks for your interest in `vendus`. This project aims at production quality — the
guiding rules live in [`CLAUDE.md`](https://github.com/bilouro/vendus-python/blob/main/CLAUDE.md)
at the repo root; read it before any substantial change.

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

- `register_id` — find it in the Vendus backoffice, or call `GET /v1.1/registers/`
  (each register has an `id` and a `mode`).
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
the line-item fields). These are recorded as live-verified facts in `CLAUDE.md` (rule
R16). The ones a contributor must respect:

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

Full detail (rules R1–R16, the unified vocabulary, the playbook) is in `CLAUDE.md`.

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
7. Update `CHANGELOG.md`, and `CLAUDE.md` (roadmap, and the R1 vocabulary table if a new
   field appears).

## Known gaps

Open follow-ups and verification gaps are tracked in
[`TODO.md`](https://github.com/bilouro/vendus-python/blob/main/TODO.md) — check it before
starting related work, and keep it honest (tick an item only when actually verified).

## Scope

Anything outside the current roadmap (see `CLAUDE.md`) should be discussed in an issue
first.
