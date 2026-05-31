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
    API_VERSION_PAYMENTS,
    API_VERSION_REGISTERS,
    FINAL_CONSUMER_FORBIDDEN_NIF,
    PATH_DOCUMENTS,
    PATH_PAYMENTS,
    PATH_REGISTERS,
)
from vendus._validators import validate_nif_pt
from vendus.exceptions import NotFoundError, ValidationError
from vendus.models.client import ClientData
from vendus.models.document import (
    CreditLine,
    Document,
    DocumentItem,
    DocumentMode,
    DocumentType,
)
from vendus.models.payment import Payment, PaymentMethod
from vendus.models.register import Register
from vendus.services._base import BaseService

_PATH = f"/{API_VERSION_DOCUMENTS}{PATH_DOCUMENTS}"
_PATH_PAYMENTS = f"/{API_VERSION_PAYMENTS}{PATH_PAYMENTS}"
_PATH_REGISTERS = f"/{API_VERSION_REGISTERS}{PATH_REGISTERS}"

# Fiscal documents communicated to the AT cannot be cancelled — they are reversed
# with a credit note. Verified for FT (Vendus returns "Não é permitido cancelar
# este tipo de documentos"); applied to the fiscal invoice types the SDK issues.
_NON_CANCELLABLE = frozenset(
    {DocumentType.INVOICE, DocumentType.INVOICE_RECEIPT, DocumentType.CREDIT_NOTE}
)


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


def _serialize_payments(payments: list[Payment]) -> list[dict[str, Any]]:
    """Build the `payments` wire array. An FR is paid on the spot, so Vendus
    requires at least one payment (verified: it rejects an FR with no payment)."""
    if not payments:
        raise ValidationError(
            "A Fatura-Recibo requires at least one payment (it records payment on issue). "
            "List the account's payment-method ids with list_payment_methods()."
        )
    out: list[dict[str, Any]] = []
    for p in payments:
        entry: dict[str, Any] = {"id": p.method_id, "amount": float(p.amount)}
        if p.date_due is not None:
            entry["date_due"] = p.date_due.isoformat()
        out.append(entry)
    return out


def _ensure_cancellable(doc_type: DocumentType) -> None:
    """Refuse to cancel fiscal documents — they are reversed with a credit note."""
    if doc_type in _NON_CANCELLABLE:
        raise ValidationError(
            f"A {doc_type.value} cannot be cancelled. Fiscal documents communicated to "
            "the AT are reversed with a credit note, not cancelled — issue one with "
            "create_credit_note(reference_document_id=...) on the original document."
        )


def _build_paid_invoice_body(
    doc_type: DocumentType,
    register_id: int,
    items: list[DocumentItem],
    payments: list[Payment],
    client: ClientData | None,
    external_reference: str | None,
    mode: DocumentMode | None = None,
) -> dict[str, Any]:
    """Build a paid-on-issue invoice body (FR / FS) — both require `payments`."""
    body: dict[str, Any] = {
        "type": doc_type.value,
        "register_id": register_id,
        "items": _serialize_items(items),
        "payments": _serialize_payments(payments),
    }
    _apply_optional(body, client, external_reference, mode)
    return body


def _build_invoice_receipt_body(
    register_id: int,
    items: list[DocumentItem],
    payments: list[Payment],
    client: ClientData | None,
    external_reference: str | None,
    mode: DocumentMode | None = None,
) -> dict[str, Any]:
    return _build_paid_invoice_body(
        DocumentType.INVOICE_RECEIPT, register_id, items, payments, client, external_reference, mode
    )


def _build_simplified_invoice_body(
    register_id: int,
    items: list[DocumentItem],
    payments: list[Payment],
    client: ClientData | None,
    external_reference: str | None,
    mode: DocumentMode | None = None,
) -> dict[str, Any]:
    return _build_paid_invoice_body(
        DocumentType.SIMPLIFIED_INVOICE,
        register_id,
        items,
        payments,
        client,
        external_reference,
        mode,
    )


def _build_receipt_body(
    register_id: int,
    invoice_numbers: list[str],
    payments: list[Payment],
    external_reference: str | None,
    mode: DocumentMode | None = None,
) -> dict[str, Any]:
    """Build a Recibo (RG) body. It references invoices by document number and
    records the payment(s) — it carries no line items of its own."""
    if not invoice_numbers:
        raise ValidationError("A receipt (RG) must reference at least one invoice")
    body: dict[str, Any] = {
        "type": DocumentType.RECEIPT.value,
        "register_id": register_id,
        "invoices": [{"document_number": n} for n in invoice_numbers],
        "payments": _serialize_payments(payments),
    }
    if external_reference is not None:
        body["external_reference"] = external_reference
    if mode is not None:
        body["mode"] = mode.value
    return body


def _credit_not_found_msg(document_id: int) -> str:
    return (
        f"Document {document_id} could not be read to credit it. The original must be a "
        "real, retrievable document — test-mode documents cannot be credited."
    )


def _line_creditable_qty(line: dict[str, Any]) -> float:
    return float(line.get("qty_nc", line.get("qty", 0)) or 0)


def _credit_line_item(
    line: dict[str, Any], number: str, row: int, qty: Decimal | None = None
) -> dict[str, Any]:
    amounts = line.get("amounts") or {}
    tax = line.get("tax") or {}
    return {
        "id": line.get("id"),
        "title": line.get("title"),
        "qty": float(qty) if qty is not None else _line_creditable_qty(line),
        "gross_price": float(amounts.get("gross_unit", 0) or 0),
        "tax_id": tax.get("id"),
        "reference_document": {"document_number": number, "document_row": row},
    }


def _credit_note_items_from_original(
    original: dict[str, Any], lines: list[CreditLine] | None = None
) -> list[dict[str, Any]]:
    """Build the NC line items that credit the original document.

    Each credit line points at an existing line of the original via
    ``reference_document`` (document_number + 1-based row) and carries that line's
    id. Field paths (items[].id, .qty_nc, .amounts.gross_unit, .tax.id) are taken
    from a real GET response, not assumed.

    ``lines=None`` credits every line that still has creditable quantity, in full.
    Otherwise only the selected rows/quantities are credited (partial).
    """
    number = original.get("number", "")
    original_lines = original.get("items") or []
    if not original_lines:
        raise ValidationError("The referenced document has no lines to credit")
    by_row = dict(enumerate(original_lines, start=1))

    items: list[dict[str, Any]]
    if lines is None:
        items = [
            _credit_line_item(line, number, row)
            for row, line in by_row.items()
            if _line_creditable_qty(line) > 0
        ]
    else:
        items = []
        for cl in lines:
            if cl.row not in by_row:
                raise ValidationError(f"Document row {cl.row} does not exist on the original")
            items.append(_credit_line_item(by_row[cl.row], number, cl.row, cl.qty))

    if not items:
        raise ValidationError("Nothing to credit — the document is already fully credited")
    return items


def _build_credit_note_body(
    original: dict[str, Any],
    reason: str,
    lines: list[CreditLine] | None,
    external_reference: str | None,
    mode: DocumentMode | None,
) -> dict[str, Any]:
    if not reason or not reason.strip():
        raise ValidationError("Credit note requires a reason")
    body: dict[str, Any] = {
        "type": DocumentType.CREDIT_NOTE.value,
        "register_id": original.get("register_id"),
        "notes": reason,
        "items": _credit_note_items_from_original(original, lines),
    }
    client = original.get("client")
    if isinstance(client, dict):
        slim = {k: client[k] for k in ("name", "fiscal_id") if client.get(k)}
        if slim:
            body["client"] = slim
    if external_reference is not None:
        body["external_reference"] = external_reference
    if mode is not None:
        body["mode"] = mode.value
    return body


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_type(raw: Any) -> DocumentType:
    """Map a Vendus type code to the enum, tolerating codes we do not model yet."""
    try:
        return DocumentType(raw)
    except ValueError:
        return DocumentType.UNKNOWN


def _parse_document(data: dict[str, Any]) -> Document:
    """Convert raw Vendus JSON to Document."""
    return Document(
        id=int(data["id"]),
        type=_parse_type(data.get("type", "FT")),
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
        body = _build_invoice_body(
            register_id, items, client, external_reference, self._effective_mode(mode)
        )
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
        body = _build_invoice_body(
            register_id, items, client, external_reference, self._effective_mode(mode)
        )
        response = await self._request_async("POST", _PATH, json=body)
        return _parse_document(response.json())

    # ----- create_invoice_receipt -------------------------------------------

    def create_invoice_receipt(
        self,
        register_id: int,
        items: list[DocumentItem],
        payments: list[Payment],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        """Issue a Fatura-Recibo (FR).

        An FR is an invoice and a receipt in a single document: it bills and
        acknowledges payment at once. Use it when the client pays immediately
        (typical for services and freelancers).

        Args:
            register_id: ID of the POS register configured in Vendus.
            items: Line items.
            payments: How the document was paid. **Required** — an FR records
                payment on issue, and Vendus rejects it otherwise. Get the
                account's method ids from :meth:`list_payment_methods`.
            client: Client data — omit for final consumer.
            external_reference: Your internal reference. Enables safe POST retries.
            mode: ``DocumentMode.TESTS`` for a non-fiscal test document.
        """
        body = _build_invoice_receipt_body(
            register_id, items, payments, client, external_reference, self._effective_mode(mode)
        )
        response = self._request("POST", _PATH, json=body)
        return _parse_document(response.json())

    async def create_invoice_receipt_async(
        self,
        register_id: int,
        items: list[DocumentItem],
        payments: list[Payment],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        body = _build_invoice_receipt_body(
            register_id, items, payments, client, external_reference, self._effective_mode(mode)
        )
        response = await self._request_async("POST", _PATH, json=body)
        return _parse_document(response.json())

    # ----- create_simplified_invoice ----------------------------------------

    def create_simplified_invoice(
        self,
        register_id: int,
        items: list[DocumentItem],
        payments: list[Payment],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        """Issue a Fatura Simplificada (FS).

        A simplified invoice for retail / final-consumer sales (subject to AT
        amount limits). Like a Fatura-Recibo, it is paid on issue, so `payments`
        is **required**. The client is usually omitted (final consumer).
        """
        body = _build_simplified_invoice_body(
            register_id, items, payments, client, external_reference, self._effective_mode(mode)
        )
        response = self._request("POST", _PATH, json=body)
        return _parse_document(response.json())

    async def create_simplified_invoice_async(
        self,
        register_id: int,
        items: list[DocumentItem],
        payments: list[Payment],
        client: ClientData | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        body = _build_simplified_invoice_body(
            register_id, items, payments, client, external_reference, self._effective_mode(mode)
        )
        response = await self._request_async("POST", _PATH, json=body)
        return _parse_document(response.json())

    # ----- create_receipt ---------------------------------------------------

    def create_receipt(
        self,
        register_id: int,
        invoice_numbers: list[str],
        payments: list[Payment],
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        """Issue a Recibo (RG) acknowledging payment of one or more invoices.

        A receipt records payment for previously-issued invoices (e.g. an FT) and
        carries no line items of its own. Reference the invoices by their document
        number (e.g. ``"FT 2026/123"``) and provide the `payments`.

        Args:
            register_id: ID of the POS register configured in Vendus.
            invoice_numbers: document numbers of the invoices being paid.
            payments: how the payment was made (see :meth:`list_payment_methods`).
            external_reference: Your internal reference. Enables safe POST retries.
            mode: ``DocumentMode.TESTS`` for a non-fiscal test document.
        """
        body = _build_receipt_body(
            register_id, invoice_numbers, payments, external_reference, self._effective_mode(mode)
        )
        response = self._request("POST", _PATH, json=body)
        return _parse_document(response.json())

    async def create_receipt_async(
        self,
        register_id: int,
        invoice_numbers: list[str],
        payments: list[Payment],
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        body = _build_receipt_body(
            register_id, invoice_numbers, payments, external_reference, self._effective_mode(mode)
        )
        response = await self._request_async("POST", _PATH, json=body)
        return _parse_document(response.json())

    # ----- create_credit_note ----------------------------------------------

    def create_credit_note(
        self,
        reference_document_id: int,
        reason: str,
        lines: list[CreditLine] | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        """Issue a credit note (NC) crediting a previously-issued document.

        Vendus credits an invoice line by line: each credit line must reference an
        existing line of the original. The SDK fetches the original (FT/FR) and
        builds the credit lines from it — the client and amounts come from the
        original, so you usually pass only the document id and a reason.

        The original must be retrievable, i.e. a **real** (non-test) document;
        test-mode documents are not addressable and cannot be credited.

        Args:
            reference_document_id: id of the FT/FR being credited (R13).
            reason: Free-text reason, stored as the document's notes.
            lines: Restrict the credit to specific rows/quantities (partial credit).
                Omit to credit every still-creditable line of the document.
            external_reference: Your internal reference. Enables safe POST retries.
            mode: Working mode for the credit note itself.
        """
        try:
            original = self.get(reference_document_id).raw_response
        except NotFoundError as exc:
            raise NotFoundError(_credit_not_found_msg(reference_document_id)) from exc
        body = _build_credit_note_body(
            original, reason, lines, external_reference, self._effective_mode(mode)
        )
        response = self._request("POST", _PATH, json=body)
        return _parse_document(response.json())

    async def create_credit_note_async(
        self,
        reference_document_id: int,
        reason: str,
        lines: list[CreditLine] | None = None,
        external_reference: str | None = None,
        mode: DocumentMode | None = None,
    ) -> Document:
        try:
            original = (await self.get_async(reference_document_id)).raw_response
        except NotFoundError as exc:
            raise NotFoundError(_credit_not_found_msg(reference_document_id)) from exc
        body = _build_credit_note_body(
            original, reason, lines, external_reference, self._effective_mode(mode)
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
        """Cancel (void) a non-fiscal document.

        Fiscal invoices (FT/FR) and credit notes (NC) communicated to the AT
        **cannot** be cancelled — Vendus rejects it. To reverse an invoice, issue
        a credit note with :meth:`create_credit_note`. The SDK fetches the document
        and raises :class:`ValidationError` for these types **before** attempting
        any change.

        Vendus has no API field for a cancellation reason (the document PATCH
        endpoint accepts only status/mode), so none is sent.
        """
        _ensure_cancellable(self.get(document_id).type)
        response = self._request("PATCH", f"{_PATH}/{document_id}", json={"status": "A"})
        return _parse_document(response.json())

    async def cancel_async(self, document_id: int) -> Document:
        doc = await self.get_async(document_id)
        _ensure_cancellable(doc.type)
        response = await self._request_async(
            "PATCH", f"{_PATH}/{document_id}", json={"status": "A"}
        )
        return _parse_document(response.json())

    # ----- payment methods --------------------------------------------------

    def list_payment_methods(self) -> builtins.list[PaymentMethod]:
        """List the account's configured payment methods (id, title, type).

        Use the returned ``id`` as ``Payment.method_id`` when issuing a
        Fatura-Recibo with :meth:`create_invoice_receipt`.
        """
        response = self._request("GET", _PATH_PAYMENTS)
        return [PaymentMethod(**m) for m in response.json()]

    async def list_payment_methods_async(self) -> builtins.list[PaymentMethod]:
        response = await self._request_async("GET", _PATH_PAYMENTS)
        return [PaymentMethod(**m) for m in response.json()]

    # ----- registers --------------------------------------------------------

    def list_registers(self) -> builtins.list[Register]:
        """List the account's registers (caixas) — id, title, working mode.

        Registers are read-only via the API (created/configured in the Vendus
        backoffice). Use the returned ``id`` as ``register_id`` when issuing
        documents, and check ``mode`` to know whether a register is in test or
        normal mode.
        """
        response = self._request("GET", _PATH_REGISTERS)
        return [Register(**r) for r in response.json()]

    async def list_registers_async(self) -> builtins.list[Register]:
        response = await self._request_async("GET", _PATH_REGISTERS)
        return [Register(**r) for r in response.json()]
