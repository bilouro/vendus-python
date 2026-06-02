---
description: "Emite uma fatura simplificada Vendus (FS) em Python — paga no ato, com os payments obrigatórios e categorias de imposto."
---

# Fatura Simplificada (FS)

## O que é

Uma **Fatura Simplificada (FS)** é uma fatura simplificada para vendas a retalho /
consumidor final, sujeita a limites de valor da AT (ex.: até 1000 € para consumidor final,
100 € quando é dado NIF). Tal como a Fatura-Recibo, é **paga na emissão**, por isso
`payments` é obrigatório; o cliente é normalmente omitido (consumidor final).

## Exemplo

```python
from decimal import Decimal
from vendus import DocumentItem, Payment, TaxCategory, VendusClient

client = VendusClient.from_env()
cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

fs = client.documents.create_simplified_invoice(
    register_id=1,
    items=[
        DocumentItem(
            description="Café",
            quantity=Decimal("1"),
            unit_price=Decimal("2.50"),
            tax_category=TaxCategory.INTERMEDIATE,
        ),
    ],
    payments=[Payment(method_id=cash.id, amount=Decimal("2.50"))],
)
print(fs.number)  # "FS 2026/1"
```

## Parâmetros

Mesma forma que `create_invoice_receipt`: `register_id`, `items`, `payments`
(**obrigatório**), e opcionais `client`, `external_reference`, `mode`. Ver
[Métodos de pagamento](payment-methods.md).

## Notas

- Usa-a para vendas rápidas a retalho. Para uma fatura completa com NIF acima do limite da
  FS, usa [`create_invoice`](invoice.md) (FT).
- Uma FS é uma fatura, por isso reverte-se com uma [nota de crédito](credit-note.md), não
  por cancelamento.
