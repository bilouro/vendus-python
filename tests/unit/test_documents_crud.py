"""Tests for get/list/cancel (sync + async) and credit_note async."""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
import respx

from vendus import (
    CreditLine,
    DocumentItem,
    DocumentMode,
    DocumentType,
    NotFoundError,
    TaxCategory,
    ValidationError,
    VendusClient,
)

_BASE = "https://www.vendus.pt/ws"


@pytest.fixture
def vendus() -> VendusClient:
    return VendusClient(api_key="test-key", base_url=_BASE, max_retries=0)


@pytest.fixture
def items() -> list[DocumentItem]:
    return [
        DocumentItem(
            description="x",
            quantity=Decimal("1"),
            unit_price=Decimal("10"),
            tax_category=TaxCategory.NORMAL,
        ),
    ]


def _doc(doc_id: int = 1, doc_type: str = "FT") -> dict[str, object]:
    return {
        "id": doc_id,
        "type": doc_type,
        "number": f"{doc_type} 2026/{doc_id}",
        "amount_gross": "10.00",
        "amount_net": "8.13",
    }


class TestGet:
    def test_get_sync(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/5").mock(return_value=httpx.Response(200, json=_doc(5)))
            doc = vendus.documents.get(5)
        assert doc.id == 5

    async def test_get_async(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/5").mock(return_value=httpx.Response(200, json=_doc(5)))
            doc = await vendus.documents.get_async(5)
        assert doc.id == 5


class TestList:
    def test_list_sync_with_filters(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            route = router.get("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=[_doc(1), _doc(2)])
            )
            docs = vendus.documents.list(
                type=DocumentType.INVOICE,
                date_from="2026-01-01",
                date_to="2026-12-31",
                limit=10,
            )
        assert len(docs) == 2
        params = dict(route.calls.last.request.url.params)
        assert params["type"] == "FT"
        assert params["date_start"] == "2026-01-01"
        assert params["date_end"] == "2026-12-31"
        assert params["per_page"] == "10"

    def test_list_sync_no_filters(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents").mock(
                return_value=httpx.Response(200, json={"data": [_doc(1)]})
            )
            docs = vendus.documents.list()
        assert len(docs) == 1

    async def test_list_async(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents").mock(return_value=httpx.Response(200, json=[_doc(1)]))
            docs = await vendus.documents.list_async(type=DocumentType.CREDIT_NOTE)
        assert len(docs) == 1


class TestCancel:
    def test_cancel_sync(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            # cancel() first GETs the document to check its type.
            router.get("/v1.1/documents/9").mock(
                return_value=httpx.Response(200, json=_doc(9, "OR"))
            )
            route = router.patch("/v1.1/documents/9").mock(
                return_value=httpx.Response(200, json=_doc(9, "OR"))
            )
            doc = vendus.documents.cancel(9)
        assert doc.id == 9
        # Wire shape: only status is sent — Vendus rejects `notes` on this endpoint.
        body = route.calls.last.request.content.decode()
        assert '"status":"A"' in body or '"status": "A"' in body
        assert "notes" not in body

    def test_cancel_rejects_fiscal_invoice(self, vendus: VendusClient) -> None:
        # FT/FR/NC cannot be cancelled — the SDK refuses before any change.
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/7").mock(
                return_value=httpx.Response(200, json=_doc(7, "FT"))
            )
            with pytest.raises(ValidationError, match="credit note"):
                vendus.documents.cancel(7)

    async def test_cancel_async(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/9").mock(
                return_value=httpx.Response(200, json=_doc(9, "OR"))
            )
            router.patch("/v1.1/documents/9").mock(
                return_value=httpx.Response(200, json=_doc(9, "OR"))
            )
            doc = await vendus.documents.cancel_async(9)
        assert doc.id == 9


# A GET /documents/{id} response shape (subset) the credit-note builder reads.
_ORIGINAL = {
    "id": 1,
    "type": "FT",
    "number": "FT 2026/1",
    "register_id": 1,
    "amount_gross": "10.00",
    "amount_net": "8.13",
    "client": {"name": "Acme", "fiscal_id": "123456789"},
    "items": [
        {
            "id": 50,
            "title": "x",
            "qty": 1,
            "qty_nc": 1,
            "amounts": {"gross_unit": "10.00"},
            "tax": {"id": "NOR"},
        }
    ],
}


class TestCreditNote:
    def test_create_credit_note_credits_original(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/1").mock(return_value=httpx.Response(200, json=_ORIGINAL))
            route = router.post("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=_doc(2, "NC"))
            )
            doc = vendus.documents.create_credit_note(reference_document_id=1, reason="Return")
        assert doc.type == DocumentType.CREDIT_NOTE
        body = json.loads(route.calls.last.request.content)
        assert body["type"] == "NC"
        ref = body["items"][0]["reference_document"]
        assert ref == {"document_number": "FT 2026/1", "document_row": 1}
        assert "reference_document_id" not in body  # the old, rejected field

    async def test_create_credit_note_async(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/1").mock(return_value=httpx.Response(200, json=_ORIGINAL))
            router.post("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=_doc(2, "NC"))
            )
            doc = await vendus.documents.create_credit_note_async(
                reference_document_id=1, reason="Return"
            )
        assert doc.type == DocumentType.CREDIT_NOTE

    def test_partial_credit_sends_only_selected_rows(self, vendus: VendusClient) -> None:
        original = {
            "id": 1,
            "type": "FT",
            "number": "FT 2026/1",
            "register_id": 1,
            "client": {"name": "Acme", "fiscal_id": "123456789"},
            "items": [
                {"id": 10, "qty_nc": 1, "amounts": {"gross_unit": "1"}, "tax": {"id": "NOR"}},
                {"id": 20, "qty_nc": 1, "amounts": {"gross_unit": "1"}, "tax": {"id": "NOR"}},
            ],
        }
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/1").mock(return_value=httpx.Response(200, json=original))
            route = router.post("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=_doc(2, "NC"))
            )
            vendus.documents.create_credit_note(
                reference_document_id=1, reason="x", lines=[CreditLine(row=2)]
            )
        body = json.loads(route.calls.last.request.content)
        assert len(body["items"]) == 1
        assert body["items"][0]["reference_document"]["document_row"] == 2

    def test_credit_note_not_found_gives_hint(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.1/documents/999").mock(
                return_value=httpx.Response(
                    404, json={"errors": [{"code": "A001", "message": "No data"}]}
                )
            )
            with pytest.raises(NotFoundError, match="real, retrievable"):
                vendus.documents.create_credit_note(reference_document_id=999, reason="x")


class TestPaymentMethods:
    def test_list_payment_methods(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.0/payments").mock(
                return_value=httpx.Response(
                    200,
                    json=[{"id": 1, "title": "Dinheiro", "type": "NU", "status": "on", "x": 1}],
                )
            )
            methods = vendus.documents.list_payment_methods()
        assert methods[0].id == 1
        assert methods[0].type == "NU"

    async def test_list_payment_methods_async(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.get("/v1.0/payments").mock(
                return_value=httpx.Response(200, json=[{"id": 2, "title": "MB", "type": "CD"}])
            )
            methods = await vendus.documents.list_payment_methods_async()
        assert methods[0].id == 2


class TestDefaultMode:
    """A client-level default_mode is applied when a call omits `mode`."""

    def test_default_mode_applied(self, items: list[DocumentItem]) -> None:
        client = VendusClient(
            api_key="k", base_url=_BASE, max_retries=0, default_mode=DocumentMode.NORMAL
        )
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=_doc(1, "FT"))
            )
            client.documents.create_invoice(register_id=1, items=items)
        body = json.loads(route.calls.last.request.content)
        assert body["mode"] == "normal"

    def test_per_call_mode_overrides_default(self, items: list[DocumentItem]) -> None:
        client = VendusClient(
            api_key="k", base_url=_BASE, max_retries=0, default_mode=DocumentMode.NORMAL
        )
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=_doc(1, "FT"))
            )
            client.documents.create_invoice(register_id=1, items=items, mode=DocumentMode.TESTS)
        body = json.loads(route.calls.last.request.content)
        assert body["mode"] == "tests"

    def test_no_default_omits_mode(self, items: list[DocumentItem]) -> None:
        client = VendusClient(api_key="k", base_url=_BASE, max_retries=0)
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=_doc(1, "FT"))
            )
            client.documents.create_invoice(register_id=1, items=items)
        body = json.loads(route.calls.last.request.content)
        assert "mode" not in body
