"""Issue a credit note (NC) referencing a previously-issued invoice.

R13: a credit note always references an existing document.
"""

from __future__ import annotations

from decimal import Decimal

from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient.from_env()

# In a real app, original_invoice_id comes from your database — the id you
# stored when you issued the original invoice.
original_invoice_id = 12345

credit_note = client.documents.create_credit_note(
    register_id=1,
    reference_document_id=original_invoice_id,
    reason="Customer returned 2 hours of consulting",
    client=ClientData(fiscal_id="123456789", name="Acme Lda"),
    items=[
        DocumentItem(
            description="Consulting hours (credited)",
            quantity=Decimal("2"),
            unit_price=Decimal("75.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    external_reference="refund-2026-0001",
)

print(f"Issued {credit_note.number} (id={credit_note.id})")
print(f"Credited: {credit_note.gross_amount} EUR")
