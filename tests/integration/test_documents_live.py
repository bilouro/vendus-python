"""Live integration tests against the real Vendus API.

Excluded from the default ``pytest`` run (``integration`` marker) and auto-skip
when credentials are absent, so they never run by accident.

What is and isn't live-validated here, and why:

- ``create_invoice`` (FT) and ``create_invoice_receipt`` (FR) run in TEST MODE
  (``mode=tests``) — non-fiscal documents Vendus never reports to the AT. Vendus
  stores these "Modo de Formação" documents in a SEPARATE space: they are not
  retrievable or cancellable via ``/documents/{id}`` (both return "não existe"),
  so these tests cannot clean up after themselves — the documents are non-fiscal,
  not listed, and harmless.
- ``list_payment_methods``, ``list`` and ``get`` are validated read-only.
- ``create_credit_note`` (NC) is NOT in this automated suite: it must GET a real
  (retrievable) original to credit, so it cannot run in test mode, and crediting a
  real invoice creates real fiscal documents. It was validated manually once in
  real mode (NC 01P2026/9 credited FR 01P2026/2170); its body shape is covered by
  unit tests.
- ``cancel`` is NOT live-validated: FT/FR/NC cannot be cancelled (the SDK refuses
  them), and cancelling any other real document is destructive. Covered by unit
  tests.

Run with (``--no-cov`` so a subset run does not trip the coverage gate):

    VENDUS_API_KEY=... VENDUS_REGISTER_ID=... pytest -m integration --no-cov
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from vendus import (
    APIError,
    DocumentItem,
    DocumentMode,
    DocumentType,
    Payment,
    TaxCategory,
    VendusClient,
)

pytestmark = pytest.mark.integration

_API_KEY = os.environ.get("VENDUS_API_KEY")
_REGISTER_ID = os.environ.get("VENDUS_REGISTER_ID")

requires_creds = pytest.mark.skipif(
    not _API_KEY or not _REGISTER_ID,
    reason="set VENDUS_API_KEY and VENDUS_REGISTER_ID to run live tests",
)


@pytest.fixture
def client() -> VendusClient:
    assert _API_KEY  # guaranteed by requires_creds
    return VendusClient(api_key=_API_KEY)


@pytest.fixture
def register_id() -> int:
    assert _REGISTER_ID  # guaranteed by requires_creds
    return int(_REGISTER_ID)


@pytest.fixture
def items() -> list[DocumentItem]:
    return [
        DocumentItem(
            description="vendus-python integration test",
            quantity=Decimal("1"),
            unit_price=Decimal("1.23"),
            tax_category=TaxCategory.NORMAL,
        ),
    ]


@requires_creds
def test_invoice_in_test_mode_is_not_reported_to_at(
    client: VendusClient,
    register_id: int,
    items: list[DocumentItem],
) -> None:
    """Issue an FT in test mode and prove it never reached the AT.

    Test-mode documents cannot be cancelled via the API (they are not in the
    /documents space), so there is nothing to clean up — the document is
    non-fiscal and not listed.
    """
    try:
        invoice = client.documents.create_invoice(
            register_id=register_id,
            items=items,
            external_reference="vendus-python-itest-ft",
            mode=DocumentMode.TESTS,
        )
    except APIError as exc:
        # Honesty rule (eupago-reference §4/§8.3): if the account itself is not
        # provisioned for AT invoicing series, skip with a clear reason instead of
        # failing — the SDK request was accepted, the blocker is account setup.
        body = exc.response_body if isinstance(exc.response_body, dict) else {}
        if body.get("code") == "A001" and "Autoridade Tribut" in str(body.get("message", "")):
            pytest.skip(
                "Vendus account is not configured for AT invoicing series (error A001): "
                "configure the AT access data in the Vendus backoffice so series/ATCUD can "
                "be registered, then re-run."
            )
        raise

    assert invoice.id > 0
    assert invoice.type == DocumentType.INVOICE
    assert invoice.number  # Vendus assigns a number even in test mode

    # A test document has no AT id. (This is necessary but not sufficient proof
    # of non-fiscality: real documents also come back with an empty
    # tax_authority_id at create time — the series prefix "T" is the real tell,
    # e.g. "FT T01P2026/…" vs "FT 01P2026/…". We rely on mode=tests + the
    # register being in test mode for the actual guarantee.)
    assert not invoice.tax_authority_id


@requires_creds
def test_list_and_get_documents_live(client: VendusClient) -> None:
    """list() returns real documents and get() fetches one by id (read-only)."""
    docs = client.documents.list(limit=5)
    assert isinstance(docs, list)
    if not docs:
        pytest.skip("account has no documents to validate list/get against")

    first = docs[0]
    assert first.id > 0
    assert first.number

    fetched = client.documents.get(first.id)
    assert fetched.id == first.id
    assert isinstance(fetched.type, DocumentType)


@requires_creds
def test_list_payment_methods_live(client: VendusClient) -> None:
    """list_payment_methods() returns the account's configured methods (read-only)."""
    methods = client.documents.list_payment_methods()
    assert methods, "account should have at least one payment method"
    assert all(m.id and m.type for m in methods)


@requires_creds
def test_list_registers_live(client: VendusClient) -> None:
    """list_registers() returns the account's registers (read-only)."""
    registers = client.documents.list_registers()
    assert registers, "account should have at least one register"
    assert all(r.id and r.title for r in registers)
    assert all(r.mode in ("normal", "tests", "") for r in registers)


def _first_method_id(client: VendusClient) -> int:
    method = next((m for m in client.documents.list_payment_methods() if m.status == "on"), None)
    assert method is not None
    return method.id


@requires_creds
def test_simplified_invoice_in_test_mode(
    client: VendusClient, register_id: int, items: list[DocumentItem]
) -> None:
    """Issue an FS (simplified invoice) in test mode — requires a payment."""
    fs = client.documents.create_simplified_invoice(
        register_id=register_id,
        items=items,
        payments=[Payment(method_id=_first_method_id(client), amount=Decimal("1.23"))],
        mode=DocumentMode.TESTS,
        external_reference="vendus-python-itest-fs",
    )
    assert fs.type == DocumentType.SIMPLIFIED_INVOICE
    assert fs.number
    assert not fs.tax_authority_id


@requires_creds
def test_receipt_in_test_mode(
    client: VendusClient, register_id: int, items: list[DocumentItem]
) -> None:
    """Issue an RG (receipt) in test mode, referencing a test invoice."""
    invoice = client.documents.create_invoice(
        register_id=register_id,
        items=items,
        mode=DocumentMode.TESTS,
        external_reference="vendus-python-itest-rg-ft",
    )
    receipt = client.documents.create_receipt(
        register_id=register_id,
        invoice_numbers=[invoice.number],
        payments=[Payment(method_id=_first_method_id(client), amount=Decimal("1.23"))],
        mode=DocumentMode.TESTS,
        external_reference="vendus-python-itest-rg",
    )
    assert receipt.type == DocumentType.RECEIPT
    assert receipt.number


@requires_creds
def test_invoice_receipt_in_test_mode(
    client: VendusClient,
    register_id: int,
    items: list[DocumentItem],
) -> None:
    """Issue an FR in test mode — requires a payment, and is not reported to the AT."""
    methods = client.documents.list_payment_methods()
    method = next((m for m in methods if m.status == "on"), methods[0])

    receipt = client.documents.create_invoice_receipt(
        register_id=register_id,
        items=items,
        payments=[Payment(method_id=method.id, amount=Decimal("1.23"))],
        external_reference="vendus-python-itest-fr",
        mode=DocumentMode.TESTS,
    )

    assert receipt.id > 0
    assert receipt.type == DocumentType.INVOICE_RECEIPT
    assert receipt.number
    assert not receipt.tax_authority_id
