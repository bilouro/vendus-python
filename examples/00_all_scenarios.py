"""All issuing scenarios side by side.

Six invoice scenarios (FT/FS x with-NIF/name-only/final-consumer) plus
credit note. Run sections independently — comment out the rest.
"""

from __future__ import annotations

from decimal import Decimal

from vendus import ClientData, DocumentItem, VendusClient

client = VendusClient.from_env()

REGISTER_ID = 1

# Common item used across all examples
items = [
    DocumentItem(
        description="Service",
        quantity=Decimal("1"),
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("23"),
    ),
]


# ---------------------------------------------------------------------------
# FATURA (FT)
# ---------------------------------------------------------------------------

# 1. FT — client with NIF (typical B2B)
ft_with_nif = client.documents.create_invoice(
    register_id=REGISTER_ID,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=items,
    external_reference="FT-NIF-001",
)
print(f"FT with NIF:        {ft_with_nif.number}")


# 2. FT — name only, no NIF (B2C, customer didn't give NIF)
ft_name_only = client.documents.create_invoice(
    register_id=REGISTER_ID,
    client=ClientData(name="João Silva"),  # fiscal_id omitted
    items=items,
    external_reference="FT-NAME-001",
)
print(f"FT name only:       {ft_name_only.number}")


# 3. FT — final consumer (anonymous, no client at all)
ft_final = client.documents.create_invoice(
    register_id=REGISTER_ID,
    # no client= argument!
    items=items,
    external_reference="FT-FINAL-001",
)
print(f"FT final consumer:  {ft_final.number}")


# ---------------------------------------------------------------------------
# FATURA-RECIBO (FR) — invoice + receipt in one, when paid on the spot
# ---------------------------------------------------------------------------

# 4. FR — with NIF
fr_with_nif = client.documents.create_invoice_receipt(
    register_id=REGISTER_ID,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=items,
    external_reference="FR-NIF-001",
)
print(f"FR with NIF:        {fr_with_nif.number}")


# 5. FR — name only
fr_name_only = client.documents.create_invoice_receipt(
    register_id=REGISTER_ID,
    client=ClientData(name="João Silva"),
    items=items,
    external_reference="FR-NAME-001",
)
print(f"FR name only:       {fr_name_only.number}")


# 6. FR — final consumer (anonymous)
fr_final = client.documents.create_invoice_receipt(
    register_id=REGISTER_ID,
    items=items,
    external_reference="FR-FINAL-001",
)
print(f"FR final consumer:  {fr_final.number}")


# ---------------------------------------------------------------------------
# NOTA DE CRÉDITO (NC) — credits a previously issued document
# ---------------------------------------------------------------------------

# 7. NC referencing the FT with NIF above. Client must match the original.
nc = client.documents.create_credit_note(
    register_id=REGISTER_ID,
    reference_document_id=ft_with_nif.id,
    reason="Customer returned the service",
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=items,
    external_reference="NC-001",
)
print(f"NC:                 {nc.number}")


# ---------------------------------------------------------------------------
# WHAT NOT TO DO
# ---------------------------------------------------------------------------

# ❌ Don't pass 999999990 for final consumer — the SDK rejects it.
# from vendus import ValidationError
# try:
#     client.documents.create_invoice(
#         register_id=REGISTER_ID,
#         client=ClientData(name="X", fiscal_id="999999990"),
#         items=items,
#     )
# except ValidationError as e:
#     print(f"Rejected: {e}")
#
# ✅ Right way: omit the client argument entirely for final consumer.
