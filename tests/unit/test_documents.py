"""Tests for DocumentsService body building and response parsing.

Transport-level tests come once HttpTransport is implemented (currently stubbed).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from vendus import (
    ClientData,
    CreditLine,
    Document,
    DocumentItem,
    DocumentMode,
    DocumentType,
    Payment,
    TaxCategory,
    ValidationError,
)
from vendus.services.documents import (
    _build_credit_note_body,
    _build_invoice_body,
    _build_invoice_receipt_body,
    _build_receipt_body,
    _build_simplified_invoice_body,
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


# Shape of a GET /documents/{id} response, as observed live — the credit-note
# builder reads its lines from here.
_ORIGINAL_FT: dict[str, object] = {
    "number": "FT 2026/1",
    "register_id": 1,
    "client": {"name": "Acme Lda", "fiscal_id": "123456789", "ignored": "x"},
    "items": [
        {
            "id": 555,
            "title": "Consulting",
            "qty": 1,
            "qty_nc": 1,
            "amounts": {"gross_unit": "92.25"},
            "tax": {"id": "NOR"},
        },
    ],
}

# A two-line original, to exercise multi-line and partial credit.
_ORIGINAL_2LINE: dict[str, object] = {
    "number": "FT 2026/9",
    "register_id": 1,
    "items": [
        {
            "id": 10,
            "title": "A",
            "qty_nc": 1,
            "amounts": {"gross_unit": "1.00"},
            "tax": {"id": "NOR"},
        },
        {
            "id": 20,
            "title": "B",
            "qty_nc": 1,
            "amounts": {"gross_unit": "2.00"},
            "tax": {"id": "NOR"},
        },
    ],
}


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
    def test_credits_full_original(self) -> None:
        body = _build_credit_note_body(_ORIGINAL_FT, "Return", None, None, None)
        assert body["type"] == "NC"
        assert body["register_id"] == 1
        assert body["notes"] == "Return"
        # client is taken from the original, slimmed to name + fiscal_id
        assert body["client"] == {"name": "Acme Lda", "fiscal_id": "123456789"}
        line = body["items"][0]
        assert line["id"] == 555
        assert line["tax_id"] == "NOR"
        assert line["gross_price"] == 92.25
        assert line["reference_document"] == {
            "document_number": "FT 2026/1",
            "document_row": 1,
        }
        # the old top-level field that Vendus rejected must be gone
        assert "reference_document_id" not in body

    def test_credits_all_lines_of_multiline_original(self) -> None:
        body = _build_credit_note_body(_ORIGINAL_2LINE, "Return", None, None, None)
        rows = [it["reference_document"]["document_row"] for it in body["items"]]
        assert rows == [1, 2]  # both lines, referenced by 1-based row
        assert [it["id"] for it in body["items"]] == [10, 20]

    def test_partial_credit_selects_rows(self) -> None:
        body = _build_credit_note_body(_ORIGINAL_2LINE, "Return", [CreditLine(row=2)], None, None)
        assert len(body["items"]) == 1
        assert body["items"][0]["reference_document"]["document_row"] == 2
        assert body["items"][0]["id"] == 20

    def test_partial_credit_overrides_qty(self) -> None:
        body = _build_credit_note_body(
            _ORIGINAL_2LINE, "Return", [CreditLine(row=1, qty=Decimal("1"))], None, None
        )
        assert body["items"][0]["qty"] == 1.0

    def test_partial_rejects_unknown_row(self) -> None:
        with pytest.raises(ValidationError, match="row 9 does not exist"):
            _build_credit_note_body(_ORIGINAL_2LINE, "Return", [CreditLine(row=9)], None, None)

    def test_full_credit_skips_already_credited_lines(self) -> None:
        original = {
            "number": "FT 2026/2",
            "register_id": 1,
            "items": [
                {"id": 1, "qty_nc": 0, "amounts": {"gross_unit": "1"}, "tax": {"id": "NOR"}},
                {"id": 2, "qty_nc": 1, "amounts": {"gross_unit": "1"}, "tax": {"id": "NOR"}},
            ],
        }
        body = _build_credit_note_body(original, "Return", None, None, None)
        assert [it["id"] for it in body["items"]] == [2]  # row 1 (qty_nc=0) skipped

    def test_rejects_when_nothing_creditable(self) -> None:
        original = {
            "number": "X",
            "register_id": 1,
            "items": [{"id": 1, "qty_nc": 0, "amounts": {"gross_unit": "1"}, "tax": {"id": "NOR"}}],
        }
        with pytest.raises(ValidationError, match="already fully credited"):
            _build_credit_note_body(original, "Return", None, None, None)

    def test_requires_reason(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            _build_credit_note_body(_ORIGINAL_FT, "", None, None, None)

    def test_requires_reason_not_whitespace(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            _build_credit_note_body(_ORIGINAL_FT, "   ", None, None, None)

    def test_rejects_original_without_lines(self) -> None:
        with pytest.raises(ValidationError, match="no lines"):
            _build_credit_note_body({"number": "X", "items": []}, "r", None, None, None)


class TestBuildSimplifiedAndReceipt:
    def test_simplified_invoice_body(self, items: list[DocumentItem]) -> None:
        pays = [Payment(method_id=1, amount=Decimal("1"))]
        body = _build_simplified_invoice_body(1, items, pays, None, None)
        assert body["type"] == "FS"
        assert "payments" in body
        assert body["items"][0]["tax_id"] == "NOR"

    def test_receipt_body(self) -> None:
        pays = [Payment(method_id=1, amount=Decimal("1"))]
        body = _build_receipt_body(1, ["FT 2026/1"], pays, None)
        assert body["type"] == "RG"
        assert body["invoices"] == [{"document_number": "FT 2026/1"}]
        assert "payments" in body
        assert "items" not in body  # a receipt carries no line items

    def test_receipt_requires_an_invoice(self) -> None:
        pays = [Payment(method_id=1, amount=Decimal("1"))]
        with pytest.raises(ValidationError, match="at least one invoice"):
            _build_receipt_body(1, [], pays, None)


class TestMode:
    """The `mode` field controls fiscal vs. test (non-fiscal) documents."""

    def test_omitted_by_default(self, items: list[DocumentItem]) -> None:
        # Omitting mode lets Vendus use the register's configured mode.
        pays = [Payment(method_id=1, amount=Decimal("10"))]
        assert "mode" not in _build_invoice_body(1, items, None, None)
        assert "mode" not in _build_invoice_receipt_body(1, items, pays, None, None)
        assert "mode" not in _build_credit_note_body(_ORIGINAL_FT, "r", None, None, None)

    def test_tests_mode_on_wire(self, items: list[DocumentItem]) -> None:
        body = _build_invoice_body(1, items, None, None, mode=DocumentMode.TESTS)
        assert body["mode"] == "tests"

    def test_normal_mode_on_wire(self, items: list[DocumentItem]) -> None:
        pays = [Payment(method_id=1, amount=Decimal("10"))]
        body = _build_invoice_receipt_body(1, items, pays, None, None, mode=DocumentMode.NORMAL)
        assert body["mode"] == "normal"

    def test_credit_note_mode_on_wire(self) -> None:
        body = _build_credit_note_body(_ORIGINAL_FT, "Return", None, None, DocumentMode.TESTS)
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

    def test_parses_authoritative_type_codes(self) -> None:
        for code, expected in [
            ("FG", DocumentType.GLOBAL_INVOICE),
            ("OT", DocumentType.QUOTE),
            ("RG", DocumentType.RECEIPT),
        ]:
            doc = _parse_document({"id": 1, "type": code, "amount_gross": "1", "amount_net": "1"})
            assert doc.type == expected

    def test_unknown_type_maps_to_unknown(self) -> None:
        # A code we do not model must not crash parsing, and the exact code stays
        # in raw_response.
        doc = _parse_document({"id": 1, "type": "ZZ", "amount_gross": "1", "amount_net": "1"})
        assert doc.type == DocumentType.UNKNOWN
        assert doc.raw_response["type"] == "ZZ"

    def test_parses_credit_note_response(self, load_fixture: Any) -> None:
        data = load_fixture("credit_note_created.json")
        doc = _parse_document(data)
        assert doc.type == DocumentType.CREDIT_NOTE
        assert doc.gross_amount == Decimal("18.45")
