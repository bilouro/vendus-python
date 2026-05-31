"""Issue a Fatura (FT) when the client did not provide a NIF.

The SDK supports passing name only — without fiscal_id. Vendus accepts this
and emits the invoice with the buyer's name.
"""

from __future__ import annotations

from decimal import Decimal

from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient.from_env()

invoice = client.documents.create_invoice(
    register_id=1,
    client=ClientData(name="João Silva"),  # fiscal_id omitted
    items=[
        DocumentItem(
            description="Workshop attendance",
            quantity=Decimal("1"),
            unit_price=Decimal("150.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    external_reference="WS-2026-001",
)

print(f"Issued {invoice.number} for {invoice.gross_amount} EUR")
