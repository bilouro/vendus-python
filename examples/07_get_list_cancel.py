"""Read, list, and reverse documents."""

from __future__ import annotations

from vendus import DocumentType, ValidationError, VendusClient

client = VendusClient.from_env()

# Fetch one document by id
doc = client.documents.get(12345)
print(f"{doc.number} — {doc.gross_amount} EUR — {doc.status}")

# List recent invoices (FT only)
invoices = client.documents.list(
    type=DocumentType.INVOICE,
    date_from="2026-01-01",
    date_to="2026-12-31",
    limit=20,
)
for inv in invoices:
    print(f"  {inv.number}  {inv.gross_amount} EUR")

# Fiscal documents (FT/FR/NC) cannot be cancelled — the SDK refuses them.
# To reverse an invoice, issue a credit note that credits it.
try:
    client.documents.cancel(12345)
except ValidationError as e:
    print(f"Cannot cancel: {e}")
    nc = client.documents.create_credit_note(
        reference_document_id=12345,
        reason="Issued in error",
    )
    print(f"Reversed with {nc.number}")
