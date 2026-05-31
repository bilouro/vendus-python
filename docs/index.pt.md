# vendus Python SDK

[![PyPI version](https://img.shields.io/pypi/v/vendus)](https://pypi.org/project/vendus/)
[![Python versions](https://img.shields.io/pypi/pyversions/vendus)](https://pypi.org/project/vendus/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/bilouro/vendus-python/blob/main/LICENSE)

SDK Python para a [Vendus](https://www.vendus.pt), plataforma portuguesa de faturação e POS certificada pela AT.

!!! warning "SDK da comunidade"
    Este é um projeto open-source independente, não afiliado nem endossado pela Vendus.

## Quickstart

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient(api_key="a-tua-key")

invoice = client.documents.create_invoice(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Horas de consultoria",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ],
)

print(invoice.number)   # "FT 2026/123"
print(invoice.atcud)    # código de comunicação à AT
print(invoice.qrcode)   # payload do QR code da AT
```

## Tipos de documentos suportados

| Documento | Código | Método | Estado |
|---|---|---|---|
| [**Fatura**](documents/invoice.md) | FT | `client.documents.create_invoice` | ✅ |
| [**Fatura Simplificada**](documents/simplified-invoice.md) | FS | `client.documents.create_simplified_invoice` | ✅ |
| [**Fatura-Recibo**](documents/invoice-receipt.md) | FR | `client.documents.create_invoice_receipt` | ✅ |
| [**Recibo**](documents/receipt.md) | RG | `client.documents.create_receipt` | ✅ |
| [**Nota de Crédito**](documents/credit-note.md) | NC | `client.documents.create_credit_note` | ✅ |

## Porquê este SDK?

- **Sync + Async** — mesmo client, sufixo `_async` para variantes assíncronas
- **100% tipado** — `mypy --strict`, autocomplete total no IDE
- **`Decimal` para dinheiro** — nunca `float`. Precisão ao cêntimo, exigida pela AT
- **Retries seguros** — GET retenta automaticamente; POST só com `external_reference` (evita documento fiscal duplicado)
- **NIF validado localmente** — algoritmo mod 11, falha antes de tocar na API
- **Redação de PII em logs** — `fiscal_id`, email, telefone, morada
- **AT é opaco** — Vendus comunica com a AT; o SDK nunca fala diretamente com a AT

## Próximos passos

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Instalação**

    ---

    Instalar e configurar em 2 minutos

    [:octicons-arrow-right-24: Começar](getting-started/index.md)

-   :material-file-document:{ .lg .middle } **Documentos**

    ---

    Qual tipo usar? Guia de decisão

    [:octicons-arrow-right-24: Documentos](documents/index.md)

-   :material-flask:{ .lg .middle } **Receitas**

    ---

    Guias para FastAPI, Flask, Django

    [:octicons-arrow-right-24: Receitas](recipes/index.md)

-   :material-alert-circle:{ .lg .middle } **Erros**

    ---

    Hierarquia de exceções e como tratar

    [:octicons-arrow-right-24: Erros](errors/index.md)

</div>
