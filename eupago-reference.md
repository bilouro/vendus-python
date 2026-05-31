# eupago-python — Reference for building a sibling Python SDK

This document captures the principles, architecture and discipline used to
build [eupago-python](https://github.com/bilouro/eupago-python) — an
unofficial-but-production-grade Python SDK for the eupago Portuguese
payment gateway. Use it as the playbook for similar SDKs (e.g. Vendus,
another Portuguese API).

The point is **not** to copy code — Vendus and eupago have different
domains. The point is to copy the *patterns, conventions and discipline*
that made eupago-python pleasant to use, easy to maintain, and trustworthy
enough for production adoption.

---

## 0. Identity & philosophy

- **Community SDK, professional quality.** Not affiliated with the vendor.
  But every line should pass for code a paying customer would expect.
- **Stripe / Mollie as the north star.** When in doubt about API shape,
  ergonomics, or docs, ask "what would Stripe do?" — they have spent more
  on developer experience than anyone in this space.
- **Pythonic, fully typed, IDE-friendly.** `mypy --strict`, `py.typed`
  marker, type-hinted everything. Autocomplete is part of the product.
- **Hide the upstream mess.** Upstream APIs often have legacy quirks
  (inconsistent field names, mixed languages, two generations of
  endpoints). The SDK normalizes everything to a clean, consistent,
  English vocabulary. The user should *never* see raw upstream names.

---

## 1. Architecture — Stripe-inspired client with service mixins

```
Client (the one thing users instantiate)
  └── PaymentMethodService (lazy-loaded via @property)
        ├── _request()          ← sync, auth injected by base
        └── _request_async()    ← async variant
              └── HttpTransport ← httpx wrapper: retry, timeout, audit, UA
                    └── Auth strategy: ApiKey / OAuth / StaticBearer
```

### Key properties of this layout
- **One client class** the user instantiates with credentials. No factory
  ceremony.
- **One service per resource/payment method.** Lazy-loaded via property so
  startup is fast and unused services cost nothing.
- **BaseService** centralizes auth injection, error handling, sync/async
  parity. Concrete services just declare their endpoints and shape the
  body.
- **HttpTransport** wraps httpx and lives once per client. Adds: retry
  with exponential backoff + jitter (GET only), audit hook, User-Agent,
  request-level Content-Type override.
- **Auth as a strategy.** Multiple auth mechanisms (header API key, body
  API key, OAuth bearer, static bearer) implementing the same
  `apply_header` / `apply_body` surface so services don't care which
  they're using.

### File structure

```
src/<sdk>/
├── __init__.py          ← Public API: Client, models, exceptions, __version__
├── _client.py           ← The one class users instantiate
├── _http.py             ← HttpTransport — httpx sync+async, retry, audit, UA
├── _auth.py             ← Auth strategies — ApiKey, OAuth, StaticBearer
├── _config.py           ← URLs, prefixes, defaults — no magic, all constants
├── _logging.py          ← PII redaction filter
├── exceptions.py        ← Exception hierarchy (public API)
├── models/              ← Pydantic v2 models (public API)
│   ├── payment.py
│   ├── customer.py
│   └── webhook.py
├── services/            ← One module per resource/payment method
│   ├── _base.py         ← BaseService with _request/_request_async + auth
│   └── mbway.py         ← Reference implementation
├── webhooks/
│   ├── __init__.py      ← parse_webhook() — public entry point
│   ├── _parser.py
│   └── _signature.py    ← HMAC verify, AES decrypt
└── py.typed             ← PEP 561 marker
```

### Underscore convention
- `_filename.py` = **internal**, not in the public API.
- `filename.py` = **public**, exported in `__init__.py`.
- Public functions/classes have docstrings; internal ones may not.

---

## 2. The eleven rules (R1–R11)

These are the rules we apply when adding or modifying anything. Most
generalise to any payment / financial SDK.

### R1 — Naming: the unified vocabulary

The upstream API will have inconsistent names across endpoints, payment
methods, or generations. Map *everything* to a single English vocabulary
and never expose raw upstream names to the user.

Build a table early. Example from eupago:

| Concept | SDK name | upstream legacy | upstream v1.02 |
|---|---|---|---|
| Amount | `amount` | `valor` | `payment.amount.value` |
| Order ID | `order_id` | `id` | `payment.identifier` |
| Reference | `reference` | `referencia` | `reference` |
| Phone | `phone_number` | (alias) | `payment.customerPhone` |

When you add a new concept, **extend the table first**, then use it
consistently across services. Never branch.

### R2 — Money is `Decimal`, never `float`

```python
# CORRECT
amount = Decimal("49.90")

# WRONG — float will burn you on 49.8999... bugs
amount = 49.90
```

All money fields in models are `Decimal`. Convert with `float(amount)`
only at the serialization boundary (inside the service method when
building the wire body), never in models.

### R3 — POST never retries

Payment gateways typically have no idempotency keys. Retrying a POST can
duplicate a payment. The transport enforces this:
- **GET**: retry up to `max_retries` with exponential backoff + jitter.
- **POST/PUT/DELETE**: never retry. Fail immediately.

This is non-negotiable.

### R4 — Auth is per-endpoint, not global

Real-world APIs use multiple auth methods (header API key, body API key,
OAuth bearer, …). Each service declares its default:

```python
class SomeService(BaseService):
    _default_auth = "header"  # or "body" or "oauth"

    def some_method(self):
        # method can override per-call: auth="oauth"
        return self._request("POST", PATH, json=body)
```

The user never thinks about auth — it's injected transparently.

### R5 — Every method has sync + async variants

Convention: **`_async` suffix** on the method name (not a separate client
class).

```python
class SomeService(BaseService):
    def create_payment(self, ...) -> PaymentResult:
        body = _build_request_body(...)
        response = self._request("POST", PATH, json=body)
        return _parse_response(response.json(), ...)

    async def create_payment_async(self, ...) -> PaymentResult:
        body = _build_request_body(...)
        response = await self._request_async("POST", PATH, json=body)
        return _parse_response(response.json(), ...)
```

- Shared logic → module-level functions (`_build_request_body`,
  `_parse_response`).
- Sync and async are near-identical: only `self._request` vs
  `await self._request_async`.

### R6 — No PII in logs

Phone numbers, emails, NIF/tax IDs, full card PANs — automatically
redacted by a logging filter. Never add log statements that bypass the
SDK logger. Never include PII in exception messages that could be
displayed to end users.

### R7 — Validate before calling the API

Catch obvious errors locally; don't waste an API call on something the
upstream will obviously reject.

```python
if amount <= 0 or amount > _MAX_AMOUNT:
    raise ValidationError(f"Amount must be between 0.01 and {_MAX_AMOUNT}")
```

Use the SDK's `ValidationError`, not `ValueError`. Keep validations
**minimal** — only validate constraints documented by the upstream; do
not invent extra ones.

### R8 — Status normalization

Users never see raw upstream status codes. All services convert to a
single enum:

```python
class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ERROR = "error"
    DECLINED = "declined"
```

A central `normalize_status()` / `normalize_method()` lives in
`models/payment.py`. New status codes go there, used by everyone.

### R9 — Raw response always available

Every result model includes `raw_response: dict` — the unparsed upstream
JSON. This is the escape hatch for fields the SDK doesn't model yet
(forward-compat). **Never remove it.**

```python
return PaymentResult(
    transaction_id=...,
    amount=...,
    raw_response=data,  # always
)
```

### R10 — Examples show the recommended path, not every parameter

"The API supports it" ≠ "the example should show it."

Examples must show what a developer would do in a **real app** — the
simplest, most correct path. Advanced/optional parameters go in a
separate "Advanced" section or in the API reference, not in the main
example.

Checklist before writing an example:
1. Remove every parameter that has a sensible default or is configured
   elsewhere.
2. Add inline comments explaining **what each parameter does**, not just
   its name.
3. Read the example as a developer seeing the SDK for the first time —
   is it clear?
4. Compare with how Stripe/Mollie present the same flow.

### R11 — Research UX, not just API

Before implementing a feature, study how **top SDKs present that feature
to developers**, not just the raw API endpoints. The upstream tells you
what's possible; the best SDKs tell you what's recommended.

For each new feature, check:
1. How does Stripe handle this?
2. What does the developer journey look like? (setup → first call →
   webhook → done)
3. Which parameters are "configure once" vs "pass every time"?

---

## 3. Adding a new resource/payment method — the recipe

1. **Create the service module** — `src/<sdk>/services/<resource>.py`.
2. **Structure it like the reference implementation:**

   ```python
   from __future__ import annotations

   from decimal import Decimal
   from typing import Any

   from <sdk>._config import API_PREFIX
   from <sdk>.exceptions import ValidationError
   from <sdk>.models.payment import PaymentResult, PaymentStatus
   from <sdk>.services._base import BaseService

   _MAX_AMOUNT = Decimal("99999")
   _PATH_CREATE = f"{API_PREFIX}/{resource}/create"


   def _build_request_body(...) -> dict[str, Any]:
       """Build the upstream request body. Validates inputs."""
       ...

   def _parse_response(data: dict[str, Any], ...) -> PaymentResult:
       """Convert raw upstream response to PaymentResult."""
       ...


   class SomeService(BaseService):
       # For legacy/body-auth endpoints:
       # _default_auth = "body"

       def create_payment(self, ...) -> PaymentResult:
           body = _build_request_body(...)
           response = self._request("POST", _PATH_CREATE, json=body)
           return _parse_response(response.json(), ...)

       async def create_payment_async(self, ...) -> PaymentResult:
           body = _build_request_body(...)
           response = await self._request_async("POST", _PATH_CREATE, json=body)
           return _parse_response(response.json(), ...)
   ```

3. **Register on the client** — a lazy property in `_client.py`:

   ```python
   @property
   def new_method(self) -> NewMethodService:
       return self._get_service("new_method", NewMethodService)
   ```

4. **Export in `__init__.py`** only if the service exposes new public
   models.
5. **Add tests** (see §4).
6. **Update `services/__init__.py`** with the import.
7. **Add an example** (see §6).
8. **Add a doc page** (see §6).

---

## 4. Testing discipline — the most important section

This is what separates an SDK that *looks* tested from one that *is*.

### Two layers

| Layer | Tool | Runs on | Purpose |
|---|---|---|---|
| Unit | `pytest` + `respx` (mock httpx) | Every commit, CI | Guard the wire shape, validation, sync/async parity |
| Live | `pytest -m integration` | Manually / on demand | Prove the SDK actually works against the real sandbox end-to-end |

### Unit tests (the safety net)

- One `tests/unit/test_<service>.py` per service.
- **Assert the exact wire body**, not just behaviour. The eupago SDK had
  three latent bugs precisely because old unit tests only checked the
  return value, not what we sent on the wire. Example:
  ```python
  body = json.loads(route.calls[0].request.content)
  assert body == {"payment": {"value": 49.90, "currency": "EUR"}}
  ```
- **Mock with `respx`**, never call the real API.
- Cover: success path, validation errors, API error handling, async
  variant, edge cases.
- Coverage gate: **≥85%** (enforced in `pytest --cov-fail-under=85`).

### Live integration tests (the truth)

- Live tests go in `tests/integration/`.
- Marked `@pytest.mark.integration` — **excluded by default** from `pytest`.
- Each live test is **skipped automatically** when required env vars are
  missing (no false failures on machines without sandbox creds).
- **Each operation should have one live test** that exercises the full
  loop: SDK → upstream → webhook (if applicable) → SDK parses webhook.
- Use a **real webhook receiver** (we ran a Terraform-managed Lambda +
  API Gateway + DynamoDB infra) so webhooks are captured and asserted
  against.

### The honesty rule

When a live test can't complete end-to-end because the upstream channel
doesn't have a feature provisioned, **skip with a clear reason** — don't
let the test pass silently:

```python
try:
    return client.foo.bar(...)
except ApiError as e:
    if e.error_code == "BAD_REQUEST":
        pytest.skip(
            "Channel does not have <feature> enabled (upstream returned BAD_REQUEST). "
            "The SDK body shape was sent but the endpoint refuses the channel — "
            "re-run on a channel with <feature> provisioned."
        )
    raise
```

This way: you exercised the SDK code, validated the wire body, **and**
documented why the live assertion couldn't complete. Anyone reading the
test result understands immediately.

### The honesty rule — status reporting

Same discipline applies to the README/CHANGELOG/roadmap. **Per-operation
matrix**, not per-service:

| Operation | Unit | Live |
|---|:-:|---|
| `service.create_payment` | ✅ | ✅ Backoffice mark-paid → webhook PAID |
| `service.authorize` | ✅ | ⚠️ Endpoint requires channel feature; live test skips on demo channel |
| `service.capture` | ✅ | ⚠️ Same — gated by feature |

Never write "service.* live-validated" when only `create_payment` was.
Three operations failing to live-test is honest and fine; calling them
all "Done" is a trap.

### Live-validate as discovery

Live tests routinely reveal SDK bugs that unit tests miss:
- Wrong field name (`value` vs `amount`)
- Missing required field (`countryCode`)
- Wrong content-type (form-urlencoded vs JSON)
- Wrong status code expected

When you find one: **fix the SDK, write a unit test that asserts the
correct wire body**, then the live test passes. This is how the SDK
becomes by-the-book against the real API rather than against the docs.

---

## 5. Quality standards

All four checks must pass before any commit:

```bash
ruff check .          # zero warnings
ruff format --check . # fully formatted
mypy src/ --strict    # zero errors
pytest                # all pass, coverage ≥85%
```

- Python ≥3.9 compatibility — use `from __future__ import annotations`,
  never `match/case` or bare `X | Y` at runtime.
- Every public function has type annotations.
- `py.typed` marker present — IDEs get full autocomplete.
- Pre-commit hooks installed and running.

---

## 6. Docs philosophy

### What to write
- **README** — short, status table, quickstart, link to docs site.
- **Docs site** — `mkdocs` + Material theme, bilingual (EN + PT) via
  `mkdocs-static-i18n` plugin.
- **One docs page per resource** — what it is, flow diagram (Mermaid),
  example, parameters table, async variant, notes.
- **One example file per operation** — runnable Python script in
  `examples/` showing the full lifecycle.
- **CHANGELOG** — Keep a Changelog format, every wire-level change with
  the upstream error code it fixes.
- **`CLAUDE.md` at the repo root** — playbook for AI assistants working
  in the repo. The rules from §2 live there, with concrete code paths.

### What NOT to write
- No "Why we built this" hagiography.
- No exhaustive API references that duplicate the docstrings — let
  `mkdocstrings` generate them.
- No examples that show every optional parameter (R10).
- No status claims that aren't backed by a live test or a documented
  skip reason.

### `mkdocs --strict`
Must pass on every commit. CI deploys to GitHub Pages on each push to
`main`.

### Bilingual via suffix
- `payments/foo.md` — English (default).
- `payments/foo.pt.md` — Portuguese.
- `mkdocs.yml` has `nav_translations` mapping section names.

---

## 7. Webhooks

If the upstream sends webhooks:

- **One namespace on the client:** `client.webhooks.parse(body, headers)`
  — Stripe-style.
- **Verify signatures by default.** HMAC-SHA256, constant-time
  comparison. The secret is configured once on the client constructor.
- **Support both cleartext and encrypted payloads** if upstream offers
  them. Auto-detect from headers (e.g. presence of an IV header). Decryption
  is an optional `extra` (`pip install <sdk>[crypto]`).
- **The webhook event model is its own type** (`WebhookEvent`), not a
  `PaymentResult` — different fields, different lifecycle.
- **`parse_webhook(...)` as the module-level escape hatch** for multi-
  channel cases that need to pick a secret per call.

---

## 8. Lessons from eupago that generalise

These are mistakes we made (or nearly made) that you can avoid up front:

1. **The upstream's reference docs lie sometimes.** Always live-validate
   the wire shape against the real sandbox before claiming "done". Eupago
   had endpoints whose documented body returned `AMOUNT_MISSING` /
   `BAD_REQUEST` until you sent the *actually-required* fields.

2. **Two coexisting API generations is a real thing.** Don't expose them.
   Pick one vocabulary, map both into it. Use the unified-vocabulary
   table (R1) as the source of truth.

3. **A channel-level feature flag will silently block your test.** If
   the upstream gates features per merchant account, your test channel
   might not have everything enabled. Detect, skip with reason, document
   what needs to be activated.

4. **OAuth credentials are often hand-issued by support.** Document the
   process, add a `Test escape hatch` showing how to inject a Bearer
   directly (`management_bearer=...` pattern) so a developer can move
   forward while waiting.

5. **Response field names diverge across endpoints.** The same concept
   can be `transactionID` in one place and `subscriptionID` in another.
   Your parser should accept both:
   ```python
   transaction_id = data.get("transactionID") or data.get("subscriptionID")
   ```

6. **Two identifiers for the same thing.** An integer "management ID"
   and a hex "token" both exist for the same resource, used by different
   endpoints. Document the distinction; do **not** silently pick one and
   hope.

7. **Form-encoded bodies sneak into "modern" REST APIs.** Don't hardcode
   `Content-Type: application/json` in the transport. Allow a per-request
   `data=` (form) parameter that overrides Content-Type.

8. **Refund body shapes change per endpoint.** Don't assume `value` /
   `currency` from payment endpoints applies to refund. Always check the
   reference, then live-validate.

9. **Some operations don't fire webhooks.** Eupago's refund endpoint
   does not — verify via the response only. Document the asymmetry
   loudly in the docs.

10. **The integer ID may not be in the list response.** This is a real
    UX gap on eupago. Document it; don't paper over with magic scans.

---

## 9. Roadmap discipline

Treat the roadmap as a contract:

```
| Version | Scope | Status |
|---|---|---|
| **v0.1.0** | <core resource> + webhooks + core | **Done** |
| **v0.2.0** | <second resource> | **Done** |
| **v0.3.0** | <auth/capture etc.> | **Done** |
| v0.4.0 | <next feature> | — |
| v1.0.0 | Stable API, full docs | — |
```

- Don't mark "Done" until live-validated (or live-test-with-skip
  documented).
- Bump version + tag a release for each "Done" row when it ships.
- Keep `[Unreleased]` in the CHANGELOG; promote on release.

---

## 10. TL;DR — the spirit

1. **One way to do each thing.** No alternates, no aliases, no "or you
   could also..." — pick the best shape and commit.
2. **Live-validate, don't trust docs.** If you didn't run it against the
   sandbox, it isn't done.
3. **Honesty in the README.** Per-operation matrix. Skip-with-reason.
4. **Stripe is the reference for UX, not just code.** Read their docs
   before designing yours.
5. **No PII in logs, no float for money, no retry on POST.** Three
   non-negotiables.
6. **`mypy --strict`, `ruff check`, `pytest` — every commit.**
7. **`CLAUDE.md` is your colleague's onboarding doc.** Keep it current.
