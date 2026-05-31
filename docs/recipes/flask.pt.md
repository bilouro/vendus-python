# Flask

Rota síncrona para emitir uma fatura.

```python
# app.py
from decimal import Decimal
from flask import Flask, request, jsonify

from vendus import APIError, ClientData, DocumentItem, RateLimitError, TaxCategory, TransportError, ValidationError, VendusClient

app = Flask(__name__)
vendus = VendusClient.from_env()


@app.post("/invoices")
def create_invoice():
    data = request.get_json()

    client_data = None
    if data.get("client_name"):
        client_data = ClientData(name=data["client_name"], fiscal_id=data.get("fiscal_id"))

    items = [
        DocumentItem(
            description=i["description"],
            quantity=Decimal(i["quantity"]),
            unit_price=Decimal(i["unit_price"]),
            tax_category=TaxCategory(i["tax_category"]),
        )
        for i in data["items"]
    ]

    try:
        invoice = vendus.documents.create_invoice(
            register_id=data["register_id"],
            client=client_data,
            items=items,
            external_reference=data["external_reference"],
        )
    except ValidationError as e:
        return jsonify(error=str(e)), 400
    except RateLimitError:
        return jsonify(error="rate limited"), 429
    except (APIError, TransportError) as e:
        return jsonify(error=str(e)), 502

    return jsonify(
        id=invoice.id,
        number=invoice.number,
        atcud=invoice.atcud,
        qrcode=invoice.qrcode,
    )
```
