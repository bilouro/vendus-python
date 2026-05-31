"""All six invoicing scenarios (FT/FS x with-NIF/name-only/final-consumer)."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from vendus import (
    ClientData,
    DocumentItem,
    DocumentType,
    Payment,
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


@pytest.fixture
def payments() -> list[Payment]:
    return [Payment(method_id=191432483, amount=Decimal("10"))]


def _ok(doc_type: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": 1,
            "type": doc_type,
            "number": f"{doc_type} 2026/1",
            "amount_gross": "10.00",
            "amount_net": "8.13",
        },
    )


# ---------------------------------------------------------------------------
# Fatura (FT) — three scenarios
# ---------------------------------------------------------------------------


class TestInvoiceScenarios:
    def test_ft_with_nif(self, vendus: VendusClient, items: list[DocumentItem]) -> None:
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(return_value=_ok("FT"))
            doc = vendus.documents.create_invoice(
                register_id=1,
                items=items,
                client=ClientData(name="Acme Lda", fiscal_id="123456789"),
            )
        assert doc.type == DocumentType.INVOICE
        body = route.calls.last.request.content.decode()
        assert "123456789" in body
        assert "Acme Lda" in body

    def test_ft_name_only(self, vendus: VendusClient, items: list[DocumentItem]) -> None:
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(return_value=_ok("FT"))
            doc = vendus.documents.create_invoice(
                register_id=1,
                items=items,
                client=ClientData(name="João Silva"),
            )
        assert doc.type == DocumentType.INVOICE
        body = route.calls.last.request.content.decode()
        assert "João Silva" in body
        assert "fiscal_id" not in body  # omitted entirely

    def test_ft_final_consumer(self, vendus: VendusClient, items: list[DocumentItem]) -> None:
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(return_value=_ok("FT"))
            doc = vendus.documents.create_invoice(register_id=1, items=items)
        assert doc.type == DocumentType.INVOICE
        body = route.calls.last.request.content.decode()
        assert "client" not in body


# ---------------------------------------------------------------------------
# Fatura-Recibo (FR) — three scenarios
# ---------------------------------------------------------------------------


class TestInvoiceReceiptScenarios:
    def test_fr_with_nif(
        self, vendus: VendusClient, items: list[DocumentItem], payments: list[Payment]
    ) -> None:
        with respx.mock(base_url=_BASE) as router:
            route = router.post("/v1.1/documents").mock(return_value=_ok("FR"))
            doc = vendus.documents.create_invoice_receipt(
                register_id=1,
                items=items,
                payments=payments,
                client=ClientData(name="Acme Lda", fiscal_id="123456789"),
            )
        assert doc.type == DocumentType.INVOICE_RECEIPT
        body = route.calls.last.request.content.decode()
        assert '"type":"FR"' in body or '"type": "FR"' in body
        assert "payments" in body  # an FR must carry payment(s)

    def test_fr_name_only(
        self, vendus: VendusClient, items: list[DocumentItem], payments: list[Payment]
    ) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.post("/v1.1/documents").mock(return_value=_ok("FR"))
            doc = vendus.documents.create_invoice_receipt(
                register_id=1,
                items=items,
                payments=payments,
                client=ClientData(name="João Silva"),
            )
        assert doc.type == DocumentType.INVOICE_RECEIPT

    def test_fr_final_consumer(
        self, vendus: VendusClient, items: list[DocumentItem], payments: list[Payment]
    ) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.post("/v1.1/documents").mock(return_value=_ok("FR"))
            doc = vendus.documents.create_invoice_receipt(
                register_id=1, items=items, payments=payments
            )
        assert doc.type == DocumentType.INVOICE_RECEIPT

    def test_fr_requires_payment(self, vendus: VendusClient, items: list[DocumentItem]) -> None:
        with pytest.raises(ValidationError, match="payment"):
            vendus.documents.create_invoice_receipt(register_id=1, items=items, payments=[])

    async def test_fr_async(
        self, vendus: VendusClient, items: list[DocumentItem], payments: list[Payment]
    ) -> None:
        with respx.mock(base_url=_BASE) as router:
            router.post("/v1.1/documents").mock(return_value=_ok("FR"))
            doc = await vendus.documents.create_invoice_receipt_async(
                register_id=1, items=items, payments=payments
            )
        assert doc.type == DocumentType.INVOICE_RECEIPT


# ---------------------------------------------------------------------------
# Validation still rejects bad data
# ---------------------------------------------------------------------------


class TestValidationStillApplies:
    def test_rejects_999999990_on_ft(self, vendus: VendusClient, items: list[DocumentItem]) -> None:
        bad = ClientData(name="Anyone", fiscal_id="999999990")
        with pytest.raises(ValidationError, match="999999990"):
            vendus.documents.create_invoice(register_id=1, items=items, client=bad)

    def test_rejects_999999990_on_fr(
        self, vendus: VendusClient, items: list[DocumentItem], payments: list[Payment]
    ) -> None:
        bad = ClientData(name="Anyone", fiscal_id="999999990")
        with pytest.raises(ValidationError, match="999999990"):
            vendus.documents.create_invoice_receipt(
                register_id=1, items=items, payments=payments, client=bad
            )

    def test_rejects_invalid_pt_nif(self, vendus: VendusClient, items: list[DocumentItem]) -> None:
        bad = ClientData(name="X", fiscal_id="123456788")  # wrong check digit
        with pytest.raises(ValidationError, match="Invalid Portuguese NIF"):
            vendus.documents.create_invoice(register_id=1, items=items, client=bad)

    def test_name_required_when_client_passed(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            ClientData(fiscal_id="123456789")  # type: ignore[call-arg]
