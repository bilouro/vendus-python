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
| `default_mode` | `DocumentMode \| None` | `None` | Mode applied to every create that omits `mode` (see below) |

## Default document mode

`mode` defaults to the **register's** configured mode. New Vendus accounts default their register to **test** mode, so a create that omits `mode` silently issues a *test* (non-fiscal) document. Set `default_mode` once so every document is issued in the mode you intend:

```python
from vendus import DocumentMode, VendusClient

client = VendusClient(api_key="...", default_mode=DocumentMode.NORMAL)
# every create_* now issues a real document unless you pass mode= explicitly
```

A per-call `mode=` always overrides the client default.

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

## Testing

Vendus has **no separate sandbox host** — there is no test URL; every request goes to `www.vendus.pt`. What Vendus does have is a document-level **test mode** ("Modo de Formação/Testes"): documents issued in test mode have **no fiscal validity** and are **never communicated to the AT**.

Test mode is controlled two ways:

1. **Per register (caixa).** Each register has a working mode (`normal` or `tests`), set in the Vendus backoffice (*Configuração → Definições → Lojas e Caixas*). **New accounts default to `tests`** — a fresh account issues non-fiscal documents until you switch it to `normal`.
2. **Per request.** Pass `mode` to any create method:

```python
from vendus import DocumentMode

invoice = client.documents.create_invoice(
    register_id=1,
    items=[...],
    mode=DocumentMode.TESTS,   # non-fiscal — not reported to the AT
)
```

Omit `mode` and Vendus uses the register's configured mode. A test document still gets a `number` and prints with a "sem validade fiscal" note. You can confirm a document was **not** reported to the AT because its `tax_authority_id` is empty (that field is only set once Vendus communicates the document to the AT).

!!! note "What's verified, and what isn't"
    The behaviour above is taken from the official docs: the `mode` field ([documents.doc](https://www.vendus.pt/ws/v1.1/documents.doc)), the per-register mode ([registers.doc](https://www.vendus.pt/ws/v1.1/registers.doc)), and the help page [Modo de Formação/Testes](https://www.vendus.cv/ajuda/modo-formacao-testes/). What we have **not** yet confirmed against the live API is whether a per-request `mode=tests` is honoured on a register configured as `normal`. The reliable, verified path is to use a register that is itself in `tests` mode.

### Recommended setup

- **Unit tests** — mock with `respx`; never hit the real API.
- **Integration tests** — run against a register in `tests` mode, assert `tax_authority_id` is empty, and cancel what you create (see `tests/integration/`).
