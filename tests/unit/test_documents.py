"""Tests for DocumentsService body building and response parsing.

Transport-level tests come once HttpTransport is implemented (currently stubbed).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from vendus import (
    ClientData,
    Document,
    DocumentItem,
    DocumentMode,
    DocumentType,
    TaxCategory,
    ValidationError,
)
from vendus.services.documents import (
    _build_credit_note_body,
    _build_invoice_body,
    _build_invoice_receipt_body,
    _parse_document,
)


@pytest.fixture
def items() -> list[DocumentItem]:
    return [
        DocumentItem(
            description="Consulting hours",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ]


@pytest.fixture
def client_data() -> ClientData:
    return ClientData(fiscal_id="123456789", name="Acme Lda")


class TestBuildInvoiceBody:
    def test_minimal(self, items: list[DocumentItem]) -> None:
        body = _build_invoice_body(1, items, None, None)
        assert body["type"] == "FT"
        assert body["register_id"] == 1
        assert "client" not in body
        assert "external_reference" not in body
        assert len(body["items"]) == 1
        assert body["items"][0]["title"] == "Consulting hours"
        # Wire shape: Vendus wants a tax category id, never a numeric tax_rate.
        assert body["items"][0]["tax_id"] == "NOR"
        assert "tax_rate" not in body["items"][0]

    def test_with_client(self, items: list[DocumentItem], client_data: ClientData) -> None:
        body = _build_invoice_body(1, items, client_data, None)
        assert body["client"]["fiscal_id"] == "123456789"
        assert body["client"]["name"] == "Acme Lda"

    def test_with_external_reference(self, items: list[DocumentItem]) -> None:
        body = _build_invoice_body(1, items, None, "order-42")
        assert body["external_reference"] == "order-42"

    def test_rejects_final_consumer_nif(self, items: list[DocumentItem]) -> None:
        bad_client = ClientData(fiscal_id="999999990", name="Anyone")
        with pytest.raises(ValidationError, match="999999990"):
            _build_invoice_body(1, items, bad_client, None)

    def test_rejects_invalid_pt_nif(self, items: list[DocumentItem]) -> None:
        bad_client = ClientData(fiscal_id="123456788", name="Wrong checksum")
        with pytest.raises(ValidationError, match="Invalid Portuguese NIF"):
            _build_invoice_body(1, items, bad_client, None)

    def test_rejects_empty_items(self) -> None:
        with pytest.raises(ValidationError, match="At least one item"):
            _build_invoice_body(1, [], None, None)


class TestBuildCreditNoteBody:
    def test_minimal(self, items: list[DocumentItem]) -> None:
        body = _build_credit_note_body(1, 999, "Return", items, None, None)
        assert body["type"] == "NC"
        assert body["reference_document_id"] == 999
        assert body["notes"] == "Return"

    def test_requires_reason(self, items: list[DocumentItem]) -> None:
        with pytest.raises(ValidationError, match="reason"):
            _build_credit_note_body(1, 999, "", items, None, None)

    def test_requires_reason_not_whitespace(self, items: list[DocumentItem]) -> None:
        with pytest.raises(ValidationError, match="reason"):
            _build_credit_note_body(1, 999, "   ", items, None, None)


class TestMode:
    """The `mode` field controls fiscal vs. test (non-fiscal) documents."""

    def test_omitted_by_default(self, items: list[DocumentItem]) -> None:
        # Omitting mode lets Vendus use the register's configured mode.
        assert "mode" not in _build_invoice_body(1, items, None, None)
        assert "mode" not in _build_invoice_receipt_body(1, items, None, None)
        assert "mode" not in _build_credit_note_body(1, 9, "r", items, None, None)

    def test_tests_mode_on_wire(self, items: list[DocumentItem]) -> None:
        body = _build_invoice_body(1, items, None, None, mode=DocumentMode.TESTS)
        assert body["mode"] == "tests"

    def test_normal_mode_on_wire(self, items: list[DocumentItem]) -> None:
        body = _build_invoice_receipt_body(1, items, None, None, mode=DocumentMode.NORMAL)
        assert body["mode"] == "normal"

    def test_credit_note_mode_on_wire(self, items: list[DocumentItem]) -> None:
        body = _build_credit_note_body(1, 9, "Return", items, None, None, mode=DocumentMode.TESTS)
        assert body["mode"] == "tests"


class TestParseDocument:
    def test_parses_invoice_response(self, load_fixture: Any) -> None:
        data = load_fixture("invoice_created.json")
        doc: Document = _parse_document(data)
        assert doc.id == 12345
        assert doc.type == DocumentType.INVOICE
        assert doc.number == "FT 2026/123"
        assert doc.gross_amount == Decimal("92.25")
        assert doc.atcud == "AAAAAAAA-123"
        # Fixture has no tax_authority_id → not communicated to the AT.
        assert doc.tax_authority_id is None
        assert doc.raw_response == data

    def test_parses_tax_authority_id_when_present(self, load_fixture: Any) -> None:
        data = {**load_fixture("invoice_created.json"), "tax_authority_id": "AT-987654"}
        doc = _parse_document(data)
        assert doc.tax_authority_id == "AT-987654"

    def test_parses_credit_note_response(self, load_fixture: Any) -> None:
        data = load_fixture("credit_note_created.json")
        doc = _parse_document(data)
        assert doc.type == DocumentType.CREDIT_NOTE
        assert doc.gross_amount == Decimal("18.45")
