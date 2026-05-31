"""Issue a credit note (NC) that credits a previously-issued invoice.

R13: a credit note always references an existing document. The SDK fetches the
original (a real FT/FR) and credits the full document — every line — so you pass
only the document id and a reason. The client and amounts come from the original.
"""

from __future__ import annotations

from vendus import VendusClient

client = VendusClient.from_env()

# In a real app, original_invoice_id comes from your database — the id you
# stored when you issued the original invoice.
original_invoice_id = 12345

credit_note = client.documents.create_credit_note(
    reference_document_id=original_invoice_id,
    reason="Customer returned the service",
    external_reference="refund-2026-0001",
)

print(f"Issued {credit_note.number} (id={credit_note.id})")
print(f"Credited: {credit_note.gross_amount} EUR")
