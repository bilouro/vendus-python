"""Issue a Fatura Simplificada (FS) — a quick retail / final-consumer sale.

Like a Fatura-Recibo, an FS is paid on issue, so you pass `payments`. The client
is usually omitted (final consumer).
"""

from __future__ import annotations

from decimal import Decimal

from vendus import DocumentItem, Payment, TaxCategory, VendusClient

client = VendusClient.from_env()

# An FS records payment — look up a method id (account-specific).
cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

fs = client.documents.create_simplified_invoice(
    register_id=1,
    items=[
        DocumentItem(
            description="Coffee",
            quantity=Decimal("1"),
            unit_price=Decimal("2.50"),
            tax_category=TaxCategory.INTERMEDIATE,
        ),
    ],
    payments=[Payment(method_id=cash.id, amount=Decimal("2.50"))],
    external_reference="POS-2026-1001",
)

print(f"Issued {fs.number} for {fs.gross_amount} EUR")
