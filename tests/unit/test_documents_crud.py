"""Tests for get/list/cancel (sync + async) and credit_note async."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from vendus import (
    ClientData,
    DocumentItem,
    DocumentType,
    TaxCategory,
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
            route = router.patch("/v1.1/documents/9").mock(
                return_value=httpx.Response(200, json=_doc(9))
            )
            doc = vendus.documents.cancel(9)
        assert doc.id == 9
        # Wire shape: only status is sent — Vendus rejects `notes` on this endpoint.
        body = route.calls.last.request.content.decode()
        assert '"status":"A"' in body or '"status": "A"' in body
        assert "notes" not in body

    async def test_cancel_async(self, vendus: VendusClient) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.patch("/v1.1/documents/9").mock(return_value=httpx.Response(200, json=_doc(9)))
            doc = await vendus.documents.cancel_async(9)
        assert doc.id == 9


class TestCreditNoteAsync:
    async def test_create_credit_note_async(
        self, vendus: VendusClient, items: list[DocumentItem]
    ) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.post("/v1.1/documents").mock(
                return_value=httpx.Response(200, json=_doc(2, "NC"))
            )
            doc = await vendus.documents.create_credit_note_async(
                register_id=1,
                reference_document_id=1,
                reason="Return",
                items=items,
                client=ClientData(fiscal_id="123456789", name="Acme"),
            )
        assert doc.type == DocumentType.CREDIT_NOTE
