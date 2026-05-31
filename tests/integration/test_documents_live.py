"""Live integration tests against the real Vendus API.

Excluded from the default ``pytest`` run (``integration`` marker) and auto-skip
when credentials are absent, so they never run by accident.

What is and isn't live-validated here, and why:

- ``create_invoice`` is exercised in TEST MODE (``mode=tests``) — a non-fiscal
  document Vendus never reports to the AT. Vendus stores these "Modo de Formação"
  documents in a SEPARATE space: they are not retrievable or cancellable via
  ``/documents/{id}`` (both return "não existe"). So this test cannot cancel its
  own output — the document is non-fiscal, not listed, and harmless.
- ``list`` and ``get`` are validated read-only against the account's REAL
  documents (no writes).
- ``cancel`` is NOT live-validated: it can only void a real fiscal document,
  which is destructive, and test-mode documents are not addressable. Its wire
  shape is covered by the unit tests.

Run with (``--no-cov`` so a subset run does not trip the coverage gate):

    VENDUS_API_KEY=... VENDUS_REGISTER_ID=... pytest -m integration --no-cov
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from vendus import APIError, DocumentItem, DocumentMode, DocumentType, TaxCategory, VendusClient

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

    # The honesty assertion: a test document is NOT communicated to the AT,
    # so its AT-generated id must be empty.
    assert not invoice.tax_authority_id, (
        "expected an empty tax_authority_id for a test-mode document, "
        f"got {invoice.tax_authority_id!r} — was the register really in test mode?"
    )


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
