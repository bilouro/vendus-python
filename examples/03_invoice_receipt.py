"""Issue a Fatura-Recibo (FR).

An FR bills and acknowledges payment in a single document. Use it when the
client pays immediately — common for services and freelancers.

All three client shapes are valid:
- ClientData(name=..., fiscal_id=...)  — client gave NIF
- ClientData(name=...)                  — client gave name only
- (omit client)                         — final consumer, anonymous
"""

from __future__ import annotations

from decimal import Decimal

from vendus import ClientData, DocumentItem, VendusClient

client = VendusClient.from_env()

fr = client.documents.create_invoice_receipt(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Consulting session (paid on the spot)",
            quantity=Decimal("1"),
            unit_price=Decimal("90.00"),
            tax_rate=Decimal("23"),
        ),
    ],
    external_reference="FR-2026-001",
)

print(f"Issued {fr.number} for {fr.gross_amount} EUR")
print(f"ATCUD: {fr.atcud}")
