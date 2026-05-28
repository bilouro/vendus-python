# Contributing

Thanks for your interest in improving `vendus`. This project follows a strict quality bar — please read `CLAUDE.md` first; it documents the rules that apply to every change.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Before opening a PR

All four must pass:

```bash
ruff check .
ruff format --check .
mypy src/
pytest
```

## What to read first

- `CLAUDE.md` — architecture, rules (R1–R15), document types, vocabulary
- `src/vendus/services/documents.py` — reference implementation

## Scope

Anything outside the current roadmap (see `CLAUDE.md`) needs discussion in an issue first.
