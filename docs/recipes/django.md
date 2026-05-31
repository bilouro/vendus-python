# Django

Service + view to issue invoices and store the ID locally for future NCs.

## Service

```python
# billing/services.py
from decimal import Decimal
from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

_vendus = VendusClient.from_env()


def issue_invoice_for_order(order):
    """Issue an invoice for an Order from your domain.

    Stores Vendus's id on order.vendus_document_id for future use
    (cancellation, credit note, etc.).
    """
    client_data = None
    if order.customer.name:
        client_data = ClientData(
            name=order.customer.name,
            fiscal_id=order.customer.nif or None,
            email=order.customer.email,
        )

    items = [
        DocumentItem(
            description=line.description,
            quantity=Decimal(str(line.quantity)),
            unit_price=Decimal(str(line.gross_unit_price)),
            tax_category=TaxCategory(line.tax_category),
        )
        for line in order.lines.all()
    ]

    invoice = _vendus.documents.create_invoice(
        register_id=order.register_id,
        client=client_data,
        items=items,
        external_reference=f"order-{order.id}",
    )

    order.vendus_document_id = invoice.id
    order.vendus_document_number = invoice.number
    order.vendus_atcud = invoice.atcud
    order.save(update_fields=["vendus_document_id", "vendus_document_number", "vendus_atcud"])

    return invoice
```

## View

```python
# billing/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from vendus import ValidationError, APIError

from .models import Order
from .services import issue_invoice_for_order


@require_POST
def issue_invoice(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    try:
        invoice = issue_invoice_for_order(order)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except APIError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse({
        "id": invoice.id,
        "number": invoice.number,
        "atcud": invoice.atcud,
    })
```

## Notes

- `VendusClient` is thread-safe for reuse — instantiated once on module import
- Retry policy is handled internally; `external_reference=f"order-{order.id}"` makes retries safe
- If you prefer async with Django ASGI, swap to `create_invoice_async` and `async def` on the view
