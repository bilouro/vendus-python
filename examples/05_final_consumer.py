"""Issue an invoice to a final consumer (consumidor final).

In Portugal, "final consumer" means NO client identification at all. Do NOT
pass fiscal_id="999999990" — the SDK rejects it. Just omit the client argument.
"""

from __future__ import annotations

from decimal import Decimal

from vendus import DocumentItem, TaxCategory, VendusClient

client = VendusClient.from_env()

# FT to final consumer
invoice = client.documents.create_invoice(
    register_id=1,
    # no client= argument
    items=[
        DocumentItem(
            description="Coffee",
            quantity=Decimal("1"),
            unit_price=Decimal("2.50"),
            tax_category=TaxCategory.INTERMEDIATE,
        ),
    ],
    external_reference="POS-2026-9001",
)

print(f"FT to final consumer: {invoice.number}")

# Or an invoice-receipt (when the client pays on the spot)
fr = client.documents.create_invoice_receipt(
    register_id=1,
    items=[
        DocumentItem(
            description="Coffee",
            quantity=Decimal("1"),
            unit_price=Decimal("2.50"),
            tax_category=TaxCategory.INTERMEDIATE,
        ),
    ],
    external_reference="POS-2026-9002",
)

print(f"FR to final consumer: {fr.number}")
