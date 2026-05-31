# Contributing

Thanks for your interest in improving `vendus`. This project follows a strict quality
bar — read `CLAUDE.md` first; it documents the rules (R1–R16) that apply to every change.
The full developer guide is on the docs site:
<https://bilouro.github.io/vendus-python/contributing/>.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Quality gate (all must pass before a PR)

```bash
ruff check .
ruff format --check .
mypy src/
pytest                  # coverage ≥85% enforced
mkdocs build --strict   # if you touched docs
```

## Tests

- **Unit** (`tests/unit/`, `respx` mocks) run by default and assert the **exact wire
  body**, not just the return value.
- **Live integration** (`tests/integration/`) hit the real Vendus API. They are excluded
  from `pytest` and auto-skip without credentials:

  ```bash
  export VENDUS_API_KEY=...      # a test/demo account key
  export VENDUS_REGISTER_ID=...  # GET /v1.1/registers/ or the Vendus backoffice
  pytest -m integration --no-cov
  ```

  They run in test mode (non-fiscal documents). Use a dedicated test/demo account.

## Live-validation discipline

Validate the wire shape against the real API **before** claiming an operation works — the
Vendus reference docs can be incomplete. The hard-won facts are in `CLAUDE.md` R16 (e.g.
an FR needs `payments`, an NC credits a real original, FT/FR/NC can't be cancelled, and
`mode` inherits the register's mode — `tests` on new accounts).

## What to read first

- `CLAUDE.md` — architecture, rules (R1–R16), document types, vocabulary, live-verified facts
- `src/vendus/services/documents.py` — reference implementation
- `tests/unit/test_documents.py` — wire-body test pattern
- `TODO.md` — known gaps and follow-ups

## Adding a new document type

See the [docs guide](https://bilouro.github.io/vendus-python/contributing/): enum →
`_build_X_body` → `create_X` / `create_X_async` (thread `self._effective_mode(mode)`) →
**live-validate** → unit tests (wire body) → example → doc page (EN + PT) →
`CHANGELOG.md` / `CLAUDE.md`.

## Scope

Anything outside the current roadmap (see `CLAUDE.md`) needs an issue first.
