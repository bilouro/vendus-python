"""Async usage of vendus.

Every method has an _async variant. Use it inside async frameworks (FastAPI,
aiohttp, Django ASGI) to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from vendus import ClientData, DocumentItem, TaxCategory, VendusClient


async def main() -> None:
    client = VendusClient.from_env()

    invoice = await client.documents.create_invoice_async(
        register_id=1,
        client=ClientData(name="Acme Lda", fiscal_id="123456789"),
        items=[
            DocumentItem(
                description="Service",
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
                tax_category=TaxCategory.NORMAL,
            ),
        ],
        external_reference="ASYNC-2026-001",
    )
    print(f"Issued {invoice.number}")

    # List async
    recent = await client.documents.list_async(limit=5)
    for doc in recent:
        print(f"  {doc.number} ({doc.gross_amount} EUR)")


asyncio.run(main())
