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
- [ ] **`mode=tests` override on a `normal` register.** Unverified whether a per-request
  `mode=tests` produces a non-fiscal document on a register configured as `normal`.
  Our register is in `tests` mode, so we never exercised the override direction.
- [ ] **FR payment variations.** Only validated with cash (type `NU`). Not tested:
  other methods (MB/MBWAY/CC…), multiple `payments`, and deferred `date_due`.

## SDK gaps / decisions to revisit

- [x] **Client-level default `mode` (footgun).** Done: `VendusClient(api_key=...,
  default_mode=DocumentMode.NORMAL)` (and `from_env(default_mode=...)`) is applied to
  every create that omits `mode`; a per-call `mode` still overrides. Verified live
  (`default_mode=TESTS` → `FT T01P2026/12` without passing `mode`). This removes the
  footgun where the register's `tests` default silently produced test documents.
- [x] **Partial credit notes.** Done: `create_credit_note(..., lines=[CreditLine(row=,
  qty=)])` credits only the selected rows/quantities; a full credit skips already-credited
  lines. Verified live (partial credit of line 1 of a 2-line FT → `qty_nc` `[1,1]`→`[0,1]`).
- [ ] **`cancel` for non-FT/FR/NC types.** The SDK blocks the three fiscal types we
  know are non-cancellable (FT verified; FR/NC by rule). Which other types Vendus
  actually lets you cancel is unverified — do not expand the block list without
  checking. Consider also translating Vendus's "não é permitido cancelar" error as a
  backstop.
- [ ] **`DocumentType` enum vs the authoritative `documents/types` list.** The enum
  still has `OR` and `RC`, which are absent from the reference list
  (FT/FS/NC/FR/FG/ND/GA/GD/GR/GT/DC/PF/OT/EC). The live account also returns `RG`,
  which is in *no* list. Decide: align the enum to the reference (likely `QUOTE` →
  `OT`, add the missing codes) and how to model `RG`. Unknown codes already fall back
  to `DocumentType.UNKNOWN`, so this is correctness/ergonomics, not a crash risk.

## Robustness / correctness

- [ ] **Error mapping by code, not just HTTP status.** Vendus returns HTTP 403 for some
  validation errors (e.g. `P001`) and 400 for others. The transport maps 403 →
  `AuthorizationError`, which is misleading for a field-validation error. Map known
  error codes (P001, A001, …) to clearer exceptions.
- [ ] **Stronger non-fiscal assertion in the FR/FT integration tests.** `tax_authority_id`
  is empty in the POST response even for *real* fiscal documents, so it is necessary
  but not sufficient proof of non-fiscality. The real discriminator is the series
  prefix (`FT T01P…` test vs `FT 01P…` real) — consider asserting on it.

## Docs

- [ ] **Document `list_payment_methods` and the `Payment` model** on a dedicated docs
  page (currently only shown inline in the FR examples).
- [ ] **Mention the cancel restriction prominently** in the getting-started flow (FT/FR
  can't be cancelled → credit note), not only on the per-document pages.
