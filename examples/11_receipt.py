"""Issue a Recibo (RG) acknowledging payment of a previously-issued invoice.

An RG references the invoice(s) by document number and records the payment — it
carries no line items of its own. Use it when you issued an unpaid invoice (FT)
and the client pays afterwards.
"""

from __future__ import annotations

from decimal import Decimal

from vendus import Payment, VendusClient

client = VendusClient.from_env()

cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

# In a real app, the invoice number comes from when you issued it.
receipt = client.documents.create_receipt(
    register_id=1,
    invoice_numbers=["FT 2026/123"],
    payments=[Payment(method_id=cash.id, amount=Decimal("100.00"))],
    external_reference="RC-2026-001",
)

print(f"Issued {receipt.number}")
