"""End-to-end DocumentsService tests through the real transport (HTTP mocked with respx)."""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
import respx

from vendus import (
    ClientData,
    Document,
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
            description="Consulting hours",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ]


@pytest.fixture
def invoice_response() -> dict[str, object]:
    return {
        "id": 12345,
        "type": "FT",
        "subtype": "FT",
        "number": "FT 2026/123",
        "amount_gross": "92.25",
        "amount_net": "75.00",
        "atcud": "AAAAAAAA-123",
        "qrcode": "A:...",
    }


def test_create_invoice_end_to_end(
    vendus: VendusClient,
    items: list[DocumentItem],
    invoice_response: dict[str, object],
) -> None:
    with respx.mock(base_url=_BASE) as router:
        route = router.post("/v1.1/documents").mock(
            return_value=httpx.Response(200, json=invoice_response)
        )
        doc: Document = vendus.documents.create_invoice(
            register_id=1,
            items=items,
            client=ClientData(fiscal_id="123456789", name="Acme Lda"),
        )

    assert doc.id == 12345
    assert doc.type == DocumentType.INVOICE
    assert doc.atcud == "AAAAAAAA-123"

    # Verify the request body shape
    sent = route.calls.last.request
    body = sent.content.decode()
    assert '"type":"FT"' in body or '"type": "FT"' in body
    assert "123456789" in body
    assert "Consulting hours" in body


def test_create_credit_note_end_to_end(vendus: VendusClient) -> None:
    # create_credit_note GETs the original, then credits each of its lines.
    original = {
        "id": 12345,
        "type": "FT",
        "number": "FT 2026/1",
        "register_id": 1,
        "amount_gross": "18.45",
        "amount_net": "15.00",
        "client": {"name": "Acme", "fiscal_id": "123456789"},
        "items": [
            {
                "id": 7,
                "title": "x",
                "qty": 1,
                "qty_nc": 1,
                "amounts": {"gross_unit": "18.45"},
                "tax": {"id": "NOR"},
            }
        ],
    }
    response = {
        "id": 999,
        "type": "NC",
        "number": "NC 2026/1",
        "amount_gross": "18.45",
        "amount_net": "15.00",
        "atcud": "X-1",
    }
    with respx.mock(base_url=_BASE) as router:
        router.get("/v1.1/documents/12345").mock(return_value=httpx.Response(200, json=original))
        route = router.post("/v1.1/documents").mock(return_value=httpx.Response(200, json=response))
        doc = vendus.documents.create_credit_note(
            reference_document_id=12345, reason="Customer return"
        )

    assert doc.type == DocumentType.CREDIT_NOTE
    assert doc.id == 999
    body = json.loads(route.calls.last.request.content)
    assert body["items"][0]["id"] == 7
    assert body["items"][0]["reference_document"]["document_number"] == "FT 2026/1"


async def test_create_invoice_async_end_to_end(
    vendus: VendusClient,
    items: list[DocumentItem],
    invoice_response: dict[str, object],
) -> None:
    with respx.mock(base_url=_BASE) as router:
        router.post("/v1.1/documents").mock(return_value=httpx.Response(200, json=invoice_response))
        doc = await vendus.documents.create_invoice_async(
            register_id=1,
            items=items,
            client=ClientData(fiscal_id="123456789", name="Acme Lda"),
        )

    assert doc.id == 12345
