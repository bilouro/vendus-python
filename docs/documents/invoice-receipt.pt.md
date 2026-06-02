---
description: "Emite uma fatura-recibo Vendus (FR) em Python — junta fatura e recibo num só documento, com métodos de pagamento obrigatórios."
---

# Fatura-Recibo (FR)

## O que é

A Fatura-Recibo (FR) é **fatura e recibo num só documento**: factura a venda **e** dá quitação do pagamento ao mesmo tempo. É o documento certo quando o cliente **paga na hora**.

- Muito comum em **serviços** (consultas, freelancers, profissionais liberais)
- Evita emitir uma [Fatura (FT)](invoice.md) e depois um [Recibo (RG)](receipt.md) separado
- Identificação do cliente: pode ter NIF, só nome, ou ser anónima

## Exemplo

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, Payment, TaxCategory, VendusClient

client = VendusClient.from_env()

# Uma FR regista o pagamento na emissão, por isso tens de dizer COMO foi pago.
# Os ids dos métodos são específicos da conta — consulta-os uma vez.
cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

fr = client.documents.create_invoice_receipt(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Sessão de consultoria (paga na hora)",
            quantity=Decimal("1"),
            unit_price=Decimal("90.00"),
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    payments=[Payment(method_id=cash.id, amount=Decimal("90.00"))],
    external_reference="FR-2026-001",
)

print(fr.number)  # "FR 2026/12"
print(fr.atcud)
```

## Cenários

```python
# 1. Com NIF
client.documents.create_invoice_receipt(
    register_id=1, items=[...], payments=[...],
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
)

# 2. Só com nome (cliente não deu NIF)
client.documents.create_invoice_receipt(
    register_id=1, items=[...], payments=[...],
    client=ClientData(name="João Silva"),
)

# 3. Consumidor final (anónimo)
client.documents.create_invoice_receipt(register_id=1, items=[...], payments=[...])
```

## Variante async

```python
fr = await client.documents.create_invoice_receipt_async(
    register_id=1,
    items=[...],
    payments=[...],
)
```

## FT vs FR

| | Fatura (FT) | Fatura-Recibo (FR) |
|---|---|---|
| Factura a venda | ✅ | ✅ |
| Dá quitação do pagamento | ❌ (precisa de um [Recibo (RG)](receipt.md) à parte) | ✅ |
| Quando usar | Cliente paga depois (a crédito, a 30 dias) | Cliente paga **na hora** |

## Notas

1. **Pagamento imediato:** a FR pressupõe pagamento no momento da emissão, por isso `payments` é **obrigatório** — obtém os ids dos métodos com `list_payment_methods()`. Se faturas a crédito, usa [`create_invoice`](invoice.md) (FT).
2. **Cancelamento:** uma FR **não pode ser cancelada** — reverte-a com uma [nota de crédito](credit-note.md) (`create_credit_note(reference_document_id=fr.id, reason=...)`).
3. **Nota de crédito:** creditar uma FR usa o mesmo `create_credit_note` — ele vai buscar a FR e credita as suas linhas.
