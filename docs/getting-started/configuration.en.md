# Configuration

## `VendusClient` options

```python
from vendus import VendusClient

client = VendusClient(
    api_key="your-key",
    base_url="https://www.vendus.pt/ws",  # production (default)
    timeout=30.0,                          # seconds
    max_retries=3,                         # GETs retry; POST only with external_reference
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | — | Vendus API key (required) |
| `base_url` | `str` | `https://www.vendus.pt/ws` | API base. For Spain: `https://www.vendus.es/ws` |
| `timeout` | `float` | `30.0` | HTTP timeout in seconds |
| `max_retries` | `int` | `3` | Max retry attempts on eligible requests |

## From environment

```python
client = VendusClient.from_env()             # reads VENDUS_API_KEY
client = VendusClient.from_env(env_var="X")  # custom variable
```

## Retry policy

| Method | Retries? | When |
|---|---|---|
| GET | ✅ Always | 408, 429, 5xx, timeout |
| POST / PUT / PATCH | Conditional | Only if body contains `external_reference` |
| DELETE | ❌ Never | Cancellation must be explicitly idempotent on the app side |

The rule exists because Vendus **does not offer idempotency keys**. Without `external_reference`, a retried POST could create two fiscal documents (and burn two serial numbers). The `external_reference` parameter is the deduplication anchor Vendus accepts.

**Recommendation:** always pass `external_reference` when issuing documents.

```python
invoice = client.documents.create_invoice(
    register_id=1,
    items=[...],
    external_reference="ORD-2026-001",  # idempotency
)
```

## Logging

The SDK uses the `vendus` logger with an automatic PII redaction filter for `fiscal_id`, `email`, `phone`, `mobile`, `address`, `postalcode`, `billing_email`.

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("vendus").setLevel(logging.DEBUG)
```

!!! warning "Never bypass the logger"
    Don't print payloads directly with `print(json)` or another logger. Always use `logging.getLogger("vendus")` so redaction applies.

## Sandbox

Vendus **does not have a publicly documented sandbox environment**. Every authenticated call hits production and may create real fiscal documents with AT-reporting implications.

Recommended strategies:

1. **Dedicated test account** — Vendus accepts creating commercial demo accounts
2. **Dedicated series** — configure a document series exclusively for tests ("FT-TEST") on the production account
3. **Cancel immediately** — every test document should be cancelled via `client.documents.cancel(id, reason="test")`
4. **Mocks in unit tests** — use `respx` to fake responses and avoid real API calls entirely
