"""Error handling — full exception hierarchy."""

from __future__ import annotations

from decimal import Decimal

from vendus import (
    APIError,
    AuthenticationError,
    ClientData,
    DocumentItem,
    RateLimitError,
    TransportError,
    ValidationError,
    VendusClient,
)

client = VendusClient.from_env()

try:
    invoice = client.documents.create_invoice(
        register_id=1,
        client=ClientData(name="Acme Lda", fiscal_id="123456789"),
        items=[
            DocumentItem(
                description="x",
                quantity=Decimal("1"),
                unit_price=Decimal("10"),
                tax_rate=Decimal("23"),
            ),
        ],
        external_reference="ERR-001",
    )

except ValidationError as e:
    # Local validation failed BEFORE any API call.
    # Examples: invalid NIF, fiscal_id="999999990", empty items.
    print(f"Validation failed: {e}")

except AuthenticationError:
    # API key rejected (401). Fix the key.
    print("Invalid API key")

except RateLimitError:
    # 429 — Vendus is throttling. Wait and retry.
    print("Rate limited — back off")

except APIError as e:
    # Other API errors. Inspect status_code and response_body.
    print(f"Vendus API error {e.status_code}: {e.response_body}")

except TransportError as e:
    # Network failure. GET retried automatically, POST only if external_reference set.
    print(f"Network failed: {e}")
