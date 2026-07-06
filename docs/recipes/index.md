# Recipes

Integration guides for popular Python frameworks.

- [FastAPI](fastapi.md) — async endpoint to issue invoices
- [Flask](flask.md) — sync issuance in a Flask route
- [Django](django.md) — view + service for issuance and local storage
- [Persisting documents](persisting-documents.md) — reference DB schema (types & sizes), the write-ahead pattern, and reconciliation

Cross-cutting patterns:
- Load the API key from `VENDUS_API_KEY` or a `.env` file
- [Persist every issued document](persisting-documents.md) — store `id`, `number`, `hash` and `atcud` for reprints and future NCs
- Pass a unique `external_reference` per request for idempotency
