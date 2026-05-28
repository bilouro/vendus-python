# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- 69 tests with `respx` mocks (93% coverage)
- Bilingual documentation (PT/EN) with mkdocs-material + i18n
- 10 runnable examples, including an all-scenarios reference
- CI workflow (ruff, mypy --strict, pytest on Python 3.9–3.13)
- Docs auto-deploy to GitHub Pages
- Issue/PR templates and Dependabot config

### Quality
- `mypy --strict` passes with zero errors
- `ruff check` / `ruff format` clean

[Unreleased]: https://github.com/bilouro/vendus-python/compare/main...HEAD
