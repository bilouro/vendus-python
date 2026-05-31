"""Issue a Fatura-Recibo (FR).

An FR bills and acknowledges payment in a single document. Use it when the
client pays immediately — common for services and freelancers.

Because an FR records payment, you must say HOW it was paid (`payments`).
Payment-method ids are account-specific — list them with list_payment_methods().
"""

from __future__ import annotations

from decimal import Decimal

from vendus import ClientData, DocumentItem, Payment, TaxCategory, VendusClient

client = VendusClient.from_env()

# Look up the account's payment methods once (e.g. cache the id you need).
methods = client.documents.list_payment_methods()
cash = next(m for m in methods if m.type == "NU")  # "Dinheiro"

fr = client.documents.create_invoice_receipt(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Consulting session (paid on the spot)",
            quantity=Decimal("1"),
            unit_price=Decimal("90.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    payments=[Payment(method_id=cash.id, amount=Decimal("90.00"))],
    external_reference="FR-2026-001",
)

print(f"Issued {fr.number} for {fr.gross_amount} EUR")
print(f"ATCUD: {fr.atcud}")
