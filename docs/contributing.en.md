# Contributing

Thanks for your interest. This project follows strict standards — read `CLAUDE.md` in the repository before proposing changes.

## Setup

```bash
git clone https://github.com/bilouro/vendus-python.git
cd vendus-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Before opening a PR

All must pass:

```bash
ruff check .
ruff format --check .
mypy src/
pytest
```

Minimum coverage: 85%.

## What to read first

- `CLAUDE.md` — architecture, rules (R1–R15), document types, vocabulary
- `src/vendus/services/documents.py` — reference implementation
- `tests/unit/test_invoice_scenarios.py` — test pattern for new document types

## Scope

Anything outside the current roadmap (see `CLAUDE.md`) should be discussed in an issue first.

## Adding a new document type

1. Add to the `DocumentType` enum in `models/document.py`
2. Create `_build_X_body` in `services/documents.py`
3. Create `create_X` and `create_X_async` methods on `DocumentsService`
4. Add tests in `tests/unit/test_X.py` with fixtures in `tests/fixtures/`
5. Create an example in `examples/`
6. Create page in `docs/documents/X.md` (PT) and `X.en.md` (EN)
7. Update `CLAUDE.md` (roadmap) and `CHANGELOG.md`
