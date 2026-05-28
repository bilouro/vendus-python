"""Read, list, and cancel documents."""

from __future__ import annotations

from vendus import DocumentType, VendusClient

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

# Cancel a document (reason required by AT)
cancelled = client.documents.cancel(12345, reason="Issued in error")
print(f"Cancelled: {cancelled.number} ({cancelled.status})")
