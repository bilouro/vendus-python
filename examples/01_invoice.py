"""Issue a basic invoice (FT).

R10: minimal — only the parameters a real app passes every time.
"""

from __future__ import annotations

from decimal import Decimal

from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient.from_env()  # reads VENDUS_API_KEY

invoice = client.documents.create_invoice(
    register_id=1,
    client=ClientData(
        fiscal_id="123456789",
        name="Acme Lda",
        email="billing@acme.pt",
    ),
    items=[
        DocumentItem(
            description="Consulting hours",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"),  # gross (includes tax)
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    external_reference="order-2026-0001",  # enables safe POST retries (R3)
)

print(f"Issued {invoice.number} (id={invoice.id})")
print(f"Total: {invoice.gross_amount} EUR")
print(f"ATCUD: {invoice.atcud}")
