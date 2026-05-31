# TODO — known gaps & follow-ups

Running list of concrete follow-ups and known gaps, complementing the high-level
[Roadmap](CLAUDE.md#roadmap). Most items here were surfaced by **live-validating
the SDK against the real Vendus API** — they record what is *not* yet verified or
done, so nothing is silently assumed. Keep this honest: only check an item when it
is actually done/verified, not just coded.

## Live-validation gaps

- [x] **`create_credit_note` end-to-end live in REAL mode via the SDK.** Done: a real
  10-step flow (FR 01P2026/2171 → NC 01P2026/10) ran fully through the SDK. The
  original's `qty_nc` went 1 → 0 and `related_docs` linked the NC — functional proof
  the credit applied. `get`/`list`/`cancel`-guard also exercised on the real FR and NC.
- [x] **NC in test mode is verified impossible.** `create_credit_note` on a test-mode
  FT or FR fails with `NotFoundError` ("No data") because the original test document
  is not retrievable via `/documents/{id}`. NC only works on real, retrievable
  originals. (Verified live for both FT and FR.)
- [x] **Clearer error when crediting a non-retrievable original.** Done:
  `create_credit_note` wraps the GET's `NotFoundError` with a hint that the original
  must be a real, retrievable document (test-mode documents cannot be credited).
- [x] **Multi-line credit notes.** Done: verified live on a real 2-line FT
  (FT 01P2026/2) — rows 1 and 2 both credited correctly via `reference_document`
  (`qty_nc` `[1,1]`→`[0,1]`→`[0,0]`).
- [ ] **`mode=tests` override on a `normal` register.** Not testable in our setup — the
  only register is in `tests` mode. The other direction (`mode=normal` overriding a
  `tests` register) **is** verified (every real document was issued that way). Re-test if
  a `normal`-mode register becomes available.
- [x] **FR payment variations.** Done, live: Multibanco (`CD`), split across two methods
  (`NU` + `MBWAY`), and `date_due` all accepted (test mode); a real FR with Multibanco was
  issued and credited (`FR 01P2026/2172` → `NC 01P2026/13`).

## SDK gaps / decisions to revisit

- [x] **Client-level default `mode` (footgun).** Done: `VendusClient(api_key=...,
  default_mode=DocumentMode.NORMAL)` (and `from_env(default_mode=...)`) is applied to
  every create that omits `mode`; a per-call `mode` still overrides. Verified live
  (`default_mode=TESTS` → `FT T01P2026/12` without passing `mode`). This removes the
  footgun where the register's `tests` default silently produced test documents.
- [x] **Partial credit notes.** Done: `create_credit_note(..., lines=[CreditLine(row=,
  qty=)])` credits only the selected rows/quantities; a full credit skips already-credited
  lines. Verified live (partial credit of line 1 of a 2-line FT → `qty_nc` `[1,1]`→`[0,1]`).
- [ ] **`cancel` for non-FT/FR/NC types.** Not testable in v0.1 — the SDK only creates
  FT/FR/NC (all non-cancellable), so there is no cancellable document to exercise the
  PATCH happy path. The guard for FT/FR/NC is verified; the happy path is unit-only until
  a cancellable type (e.g. a quote) is supported.
- [x] **`DocumentType` enum vs the authoritative `documents/types` list.** Done: the enum
  now matches the reference (`QUOTE` = `OT`, added `FG`/`GA`/`GD`/`GR`/`DC`/`PF`/`EC`),
  `RECEIPT` = `RG` (observed live), and unknown codes fall back to `UNKNOWN`.

## Robustness / correctness

- [x] **Error mapping by code, not just HTTP status.** Done: `P001` (returned with 403)
  now raises `ValidationError` instead of `AuthorizationError`, every exception exposes
  `.error_code`, and the error message is parsed from the `{"errors": [...]}` shape.
- [x] **Stronger non-fiscal assertion in the FR/FT integration tests.** Resolved by
  documenting the limitation honestly: `tax_authority_id` empty is necessary but not
  sufficient, and the real tell (series prefix `T01P…`) is **account-specific**, so a hard
  assertion on it would be brittle. We rely on `mode=tests` + the register's mode instead.

## Docs

- [x] **Document `list_payment_methods` and the `Payment` model** on a dedicated docs
  page. Done: `docs/documents/payment-methods.md` (+ PT), in the nav.
- [x] **Mention the cancel restriction prominently** in the getting-started flow. Done:
  a "Reversing a document" section + a test-mode warning in `getting-started/index.md` (+ PT).
