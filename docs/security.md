---
description: "Security posture of the Vendus Python SDK: protecting the API key, the test/real mode boundary, PII redaction (R6), and keeping fiscal records tamper-evident."
---

# Security

What actually matters, security-wise, when you issue fiscal documents through Vendus
with this SDK. It is deliberately short — the SDK's attack surface is small: **one API
key, no webhooks, no card data.** Where a topic has more detail, it links there.

## The surface is small — know why

- **Auth is a single API key** over HTTPS Basic Auth (the key is the username, the
  password is empty — rule R4). There is no OAuth, no signed callback, no second secret.
- **No webhooks yet** (roadmap v0.5). Nothing arrives unsolicited, so there is no inbound
  event to forge or replay, and no "should I trust this?" decision to get wrong.
- **No card / payment data.** Vendus is invoicing — the SDK never touches a PAN.

So "keep it secure" reduces to four things: protect the key, respect the test/real
boundary, handle client PII, and keep your fiscal records intact.

## The API key is the whole of auth

| Credential | Unlocks | If it leaks |
|---|---|---|
| **`api_key`** | Issuing, reading, listing and cancelling documents **as you** | An attacker can issue **real** documents — reported to the AT in your name — that you then have to reverse with credit notes. A fiscal and financial mess, not just spam. |

Practical rules:

- The key lives in an **environment variable or a secrets manager** — never in code, the
  repo, the database, a URL, or a log line. The SDK reads it once at client
  construction; nothing else needs it. Keep `.env` in `.gitignore`.
- The SDK **never logs the key**. Don't defeat that by printing the client or the
  `Authorization` header yourself.
- If it leaks, **rotate it** in the Vendus backoffice. Test and production keys are
  different worlds — never let a production key into `.env.example`, a CI log, or a
  laptop's shell history.

## Test vs real mode is a safety boundary

`mode` **defaults to the register's configured mode** (R16). Omit it and you can
*silently* issue a **real, AT-reported fiscal document** — or a non-fiscal test one when
you needed a real invoice. A real document can't be un-issued (FT/FR/NC can't be
cancelled; you reverse it with a credit note), so getting this wrong has fiscal
consequences, not just a bad test.

Set it explicitly — once on the client or per call:

```python
from vendus import DocumentMode, VendusClient

client = VendusClient(api_key="...", default_mode=DocumentMode.NORMAL)  # or per call: mode=...
```

See [Configuration](getting-started/configuration.md) for the details.

## PII: the SDK redacts logs — don't undo it

- The `vendus` logger auto-redacts `fiscal_id`, `email`, `billing_email`, `phone`,
  `mobile`, `address` and `postalcode` from log records (R6). **Never route Vendus
  payloads through your own logger** "for convenience", and never put client PII in
  exception messages.
- The SDK does **not** expose a redactor in its public API. If you persist raw payloads (a `GET`
  response carries a client block), **redact them yourself on the way in** and pair that
  with bounded retention (a `purge_after` column). See the
  [Persisting documents](recipes/persisting-documents.md#security-pii-retention) recipe.
- **Minimize storage**: link a document to a person by `customer_id` into your own users
  table — don't copy the client's NIF / email / phone onto every document row.

## Fiscal records are integrity-critical

- A real document is AT-reported and **immutable**: never edit `hash`, `atcud`, `number`
  or `qrcode`, and never delete a fiscal row. Corrections are **new credit notes**, not
  edits.
- Make history **tamper-evident**: your application's DB role gets `INSERT` but not
  `UPDATE`/`DELETE` on the event log (enforce it with grants, not discipline).
- **Retention**: keep invoicing records (and the SAF-T that derives from them) for your
  legally required period — commonly cited as **10 years** in Portugal; confirm the
  current requirement with your accountant.

## Not yet in scope (being honest)

- **Webhooks / signature verification** — roadmap v0.5. Until then there is no
  inbound-event trust surface; when webhooks land, this page gets a signatures section.
- **Reporting a vulnerability** — see
  [SECURITY.md](https://github.com/bilouro/vendus-python/blob/main/SECURITY.md) for
  private disclosure. Do not open a public issue for a security bug.

## Checklist

- [ ] API key in env / secret manager; never in code, repo, logs or URLs
- [ ] `default_mode` (or a per-call `mode`) set explicitly — no silent real/test surprises
- [ ] Client PII never routed through your own logger, never in exception messages
- [ ] Persisted raw payloads redacted on the way in + bounded retention (`purge_after`)
- [ ] Documents linked to your customer table by id, not by copied PII
- [ ] Fiscal rows never edited or deleted; event log append-only by grant

---

Related: [Configuration](getting-started/configuration.md) ·
[Persisting documents](recipes/persisting-documents.md) ·
[Errors & Troubleshooting](errors/index.md)
