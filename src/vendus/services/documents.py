"""DocumentsService — invoices, invoice-receipts, and credit notes.

v0.1.0 MVP scope:
- create_invoice (FT)
- create_invoice_receipt (FR)
- create_credit_note (NC)
- get / list / cancel

Each method has a sync and async variant (R5).

Client identification — all three create_* methods accept the same client shapes:
- client=ClientData(name="...", fiscal_id="...")  → identified client with NIF
- client=ClientData(name="...")                   → identified, no NIF given
- client=None (omit argument)                     → final consumer (anonymous)
"""

from __future__ import annotations

import builtins
from decimal import Decimal
from typing import Any

from vendus._config import (
    API_VERSION_DOCUMENTS,
    FINAL_CONSUMER_FORBIDDEN_NIF,
    PATH_DOCUMENTS,
)
from vendus._validators import validate_nif_pt
from vendus.exceptions import ValidationError
from vendus.models.client import ClientData
from vendus.models.document import Document, DocumentItem, DocumentMode, DocumentType
from vendus.services._base import BaseService

_PATH = f"/{API_VERSION_DOCUMENTS}{PATH_DOCUMENTS}"


# ---------------------------------------------------------------------------
# Request body builders
# ---------------------------------------------------------------------------


def _serialize_client(client: ClientData | None) -> dict[str, Any] | None:
    """Convert ClientData to the dict shape Vendus expects.

    R7/R15: reject 999999990. To invoice a final consumer with no identification,
    pass client=None.
    """
    if client is None:
        return None
    fiscal_id = client.fiscal_id
    if fiscal_id is not None:
        if fiscal_id == FINAL_CONSUMER_FORBIDDEN_NIF:
            raise ValidationError(
                "Do not pass fiscal_id='999999990' for final consumer invoices. "
                "Omit the client argument entirely."
            )
        if fiscal_id.isdigit() and len(fiscal_id) == 9 and not validate_nif_pt(fiscal_id):
            raise ValidationError(f"Invalid Portuguese NIF: {fiscal_id}")
    return client.model_dump(exclude_none=True)


def _serialize_items(items: list[DocumentItem]) -> list[dict[str, Any]]:
    if not items:
        raise ValidationError("At least one item is required")
    return [
        {
            "title": item.description,
            "qty": float(item.quantity),
            "gross_price": float(item.unit_price),
            # Vendus models VAT by category code (tax_id), not a numeric rate.
            "tax_id": item.tax_category.value,
            **(
                {"tax_exemption": item.tax_exemption.value}
                if item.tax_exemption is not None
                else {}
            ),
            # `discount` is a percentage (0-100) -> Vendus `discount_percentage`.
            **({"discount_percentage": float(item.discount)} if item.discount is not None else {}),
            # `product_id` references an existing Vendus product -> `id`.
            # (not yet live-verified; serialized per the documented field list.)
            **({"id": item.product_id} if item.product_id is not None else {}),
            **({"reference": item.reference} if item.reference is not None else {}),
        }
        for item in items
    ]


def _apply_optional(
    body: dict[str, Any],
    client: ClientData | None,
    external_reference: str | None,
    mode: DocumentMode | None,
) -> None:
    """Attach the fields shared by every create call, only when provided."""
    serialized_client = _serialize_client(client)
    if serialized_client is not None:
        body["client"] = serialized_client
    if external_reference is not None:
        body["external_reference"] = external_reference
    # Omit `mode` to let Vendus fall back to the register's configured mode.
    if mode is not None:
        body["mode"] = mode.value


def _build_invoice_body(
    register_id: int,
    items: list[DocumentItem],
    client: ClientData | None,
    external_reference: str | None,
    mode: DocumentMode | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": DocumentType.INVOICE.value,
        "register_id": register_id,
        "items": _serialize_items(items),
    }
    _apply_optional(body, client, external_reference, mode)
    return body


def _build_invoice_receipt_body(
    register_id: int,
    items: list[DocumentItem],
    client: ClientData | None,
    external_reference: str | None,
    mode: DocumentMode | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": DocumentType.INVOICE_RECEIPT.value,
        "register_id": register_id,
        "items": _serialize_items(items),
    }
    _apply_optional(body, client, external_reference, mode)
    return body


def _build_credit_note_body(
    register_id: int,
    reference_document_id: int,
    reason: str,
    items: list[DocumentItem],
    client: ClientData | None,
    external_reference: str | None,
    mode: DocumentMode | None = None,
) -> dict[str, Any]:
    # R13: reference_document_id is a required argument (typed int) — the type
    # system enforces its presence. We only validate the reason here.
    if not reason or not reason.strip():
        raise ValidationError("Credit note requires a reason")

    body: dict[str, Any] = {
        "type": DocumentType.CREDIT_NOTE.value,
        "register_id": register_id,
        "reference_document_id": reference_document_id,
        "notes": reason,
        "items": _serialize_items(items),
    }
    _apply_optional(body, client, external_reference, mode)
    return body


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_document(data: dict[str, Any]) -> Document:
    """Convert raw Vendus JSON to Document."""
    return Document(
        id=int(data["id"]),
        type=DocumentType(data.get("type", "FT")),
        subtype=data.get("subtype"),
        number=data.get("number", ""),
        date=data.get("date"),
        local_time=data.get("local_time"),
        system_time=data.get("system_time"),
        gross_amount=Decimal(str(data.get("amount_gross", "0"))),
        net_amount=Decimal(str(data.get("amount_net", "0"))),
        hash=data.get("hash"),
        atcud=data.get("atcud"),
        tax_authority_id=data.get("tax_authority_id"),
        qrcode=data.get("qrcode"),
        output=data.get("output"),
        output_data=data.get("output_data"),
        raw_response=data,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DocumentsService(BaseService):
    """Issue and manage Vendus documents."""

    # ----- create_invoice ---------------------------------------------------

    def create_invoice(
        self,
        register_id: int,
        items: list[DocumentItem],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        """Issue an invoice (FT).

        Args:
            register_id: ID of the POS register configured in Vendus.
            items: Line items.
            client: Client data — upserted by fiscal_id. Omit for final consumer.
            external_reference: Your internal reference. Required to enable
                safe POST retries (R3).
            mode: Working mode. Pass ``DocumentMode.TESTS`` to issue a non-fiscal
                test document that is not reported to the AT. Omit to use the
                register's configured mode.
        """
        body = _build_invoice_body(register_id, items, client, external_reference, mode)
        response = self._request("POST", _PATH, json=body)
        return _parse_document(response.json())

    async def create_invoice_async(
        self,
        register_id: int,
        items: list[DocumentItem],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        body = _build_invoice_body(register_id, items, client, external_reference, mode)
        response = await self._request_async("POST", _PATH, json=body)
        return _parse_document(response.json())

    # ----- create_invoice_receipt -------------------------------------------

    def create_invoice_receipt(
        self,
        register_id: int,
        items: list[DocumentItem],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        """Issue a Fatura-Recibo (FR).

        An FR is an invoice and a receipt in a single document: it bills and
        acknowledges payment at once. Use it when the client pays immediately
        (typical for services and freelancers).

        Client can be omitted (final consumer) or passed with/without fiscal_id.
        Pass ``mode=DocumentMode.TESTS`` for a non-fiscal test document.
        """
        body = _build_invoice_receipt_body(register_id, items, client, external_reference, mode)
        response = self._request("POST", _PATH, json=body)
        return _parse_document(response.json())

    async def create_invoice_receipt_async(
        self,
        register_id: int,
        items: list[DocumentItem],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        body = _build_invoice_receipt_body(register_id, items, client, external_reference, mode)
        response = await self._request_async("POST", _PATH, json=body)
        return _parse_document(response.json())

    # ----- create_credit_note ----------------------------------------------

    def create_credit_note(
        self,
        register_id: int,
        reference_document_id: int,
        reason: str,
        items: list[DocumentItem],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        """Issue a credit note (NC) referencing a previously-issued document.

        Args:
            register_id: ID of the POS register configured in Vendus.
            reference_document_id: ID of the original invoice being credited (R13).
            reason: Free-text reason for the credit note. Required by AT.
            items: Line items to credit.
            client: Client data — should match the original invoice's client.
            external_reference: Your internal reference. Enables safe POST retries.
            mode: Working mode. ``DocumentMode.TESTS`` for a non-fiscal test
                document; omit to use the register's configured mode.
        """
        body = _build_credit_note_body(
            register_id, reference_document_id, reason, items, client, external_reference, mode
        )
        response = self._request("POST", _PATH, json=body)
        return _parse_document(response.json())

    async def create_credit_note_async(
        self,
        register_id: int,
        reference_document_id: int,
        reason: str,
        items: list[DocumentItem],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        body = _build_credit_note_body(
            register_id, reference_document_id, reason, items, client, external_reference, mode
        )
        response = await self._request_async("POST", _PATH, json=body)
        return _parse_document(response.json())

    # ----- get / list / cancel ---------------------------------------------

    def get(self, document_id: int) -> Document:
        response = self._request("GET", f"{_PATH}/{document_id}")
        return _parse_document(response.json())

    async def get_async(self, document_id: int) -> Document:
        response = await self._request_async("GET", f"{_PATH}/{document_id}")
        return _parse_document(response.json())

    def list(
        self,
        *,
        type: DocumentType | None = None,  # noqa: A002
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int | None = None,
    ) -> builtins.list[Document]:
        params: dict[str, Any] = {}
        if type is not None:
            params["type"] = type.value
        if date_from is not None:
            params["date_start"] = date_from
        if date_to is not None:
            params["date_end"] = date_to
        if limit is not None:
            params["per_page"] = limit
        response = self._request("GET", _PATH, params=params)
        data = response.json()
        items = data if isinstance(data, list) else data.get("data", [])
        return [_parse_document(item) for item in items]

    async def list_async(
        self,
        *,
        type: DocumentType | None = None,  # noqa: A002
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int | None = None,
    ) -> builtins.list[Document]:
        params: dict[str, Any] = {}
        if type is not None:
            params["type"] = type.value
        if date_from is not None:
            params["date_start"] = date_from
        if date_to is not None:
            params["date_end"] = date_to
        if limit is not None:
            params["per_page"] = limit
        response = await self._request_async("GET", _PATH, params=params)
        data = response.json()
        items = data if isinstance(data, list) else data.get("data", [])
        return [_parse_document(item) for item in items]

    def cancel(self, document_id: int) -> Document:
        """Cancel (void) a document by setting its status to cancelled (``A``).

        Vendus has no API field for a cancellation reason — the document PATCH
        endpoint accepts only ``status``/``mode`` — so the SDK sends none. Any
        AT-required justification is handled in the Vendus backoffice.
        """
        response = self._request("PATCH", f"{_PATH}/{document_id}", json={"status": "A"})
        return _parse_document(response.json())

    async def cancel_async(self, document_id: int) -> Document:
        response = await self._request_async(
            "PATCH", f"{_PATH}/{document_id}", json={"status": "A"}
        )
        return _parse_document(response.json())
