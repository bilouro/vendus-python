---
description: "Handle Vendus API errors in Python — the exception hierarchy, error codes like P001, local validation, retries and troubleshooting."
---

# Errors & Troubleshooting

## Exception hierarchy

All SDK exceptions inherit from `VendusError`. Catch specific exceptions first, general ones last.

```python
from vendus import (
    VendusError,            # base
    ValidationError,        # local validation (before API)
    AuthenticationError,    # 401
    AuthorizationError,     # 403
    NotFoundError,          # 404
    RateLimitError,         # 429
    APIError,               # other API errors (status_code + response_body)
    TransportError,         # network: timeout, DNS, connection refused
)
```

## Typical handling

```python
from vendus import VendusClient, ValidationError, RateLimitError, APIError, TransportError

client = VendusClient.from_env()

try:
    invoice = client.documents.create_invoice(...)
except ValidationError as e:
    # Invalid NIF, empty items, 999999990, etc.
    logger.warning("Validation failed: %s", e)
except RateLimitError:
    # Vendus is rate-limiting. Wait and retry.
    time.sleep(60)
except APIError as e:
    # Other Vendus-side error
    logger.error("Vendus API %s: %s", e.status_code, e.response_body)
except TransportError as e:
    # Network failed. GET retried automatically; POST without external_reference did NOT.
    logger.error("Network failed: %s", e)
```

## Common errors

### `ValidationError: Invalid Portuguese NIF`

NIF check digit does not match the mod 11 algorithm.

**Fix:** verify digits. If you believe it's a valid NIF the SDK rejects, open an issue.

### `ValidationError: Do not pass fiscal_id='999999990'`

You're trying to invoice a final consumer by passing the generic NIF. **Wrong** — in PT, final consumer = omit the `client` argument.

```python
# ❌ Wrong
client.documents.create_invoice(
    register_id=1, items=[...],
    client=ClientData(name="Anyone", fiscal_id="999999990"),
)

# ✅ Right
client.documents.create_invoice(register_id=1, items=[...])
```

### `ValidationError: Credit note requires reference_document_id`

The NC must reference the original document via `reference_document_id`.

### `AuthenticationError`

API key wrong, expired, or revoked. Check in **Vendus → Settings → Access → API**.

### `RateLimitError`

Vendus is throttling requests. The SDK already retries automatically on GETs. For POSTs, retries only with `external_reference`.

**Fix:** sleep (`time.sleep`) or implement a queue with exponential backoff.

### POST failed — how to safely retry?

If you passed `external_reference`, the SDK already retries automatically. If not:

1. **Don't retry blindly** — risk of creating a duplicate fiscal document
2. Check via `client.documents.list(date_from=..., date_to=...)` whether the original was actually created
3. If yes, discard. If not, retry with `external_reference` this time

General rule: **always pass `external_reference` when issuing.**

## Logging

The SDK logs requests/responses on the `vendus` logger. PII (NIF, email, phone, address) is redacted automatically.

```python
import logging
logging.getLogger("vendus").setLevel(logging.DEBUG)
```
