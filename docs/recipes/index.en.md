# Recipes

Integration guides for popular Python frameworks.

- [FastAPI](fastapi.md) — async endpoint to issue invoices
- [Flask](flask.md) — sync issuance in a Flask route
- [Django](django.md) — view + service for issuance and local storage

Cross-cutting patterns:
- Load the API key from `VENDUS_API_KEY` or a `.env` file
- Store `invoice.id` in your local DB for future NCs
- Pass a unique `external_reference` per request for idempotency
