# Fatura-Recibo (FR)

## O que é

A Fatura-Recibo (FR) é **fatura e recibo num só documento**: factura a venda **e** dá quitação do pagamento ao mesmo tempo. É o documento certo quando o cliente **paga na hora**.

- Muito comum em **serviços** (consultas, freelancers, profissionais liberais)
- Evita emitir uma FT e depois um RC separado
- Identificação do cliente: pode ter NIF, só nome, ou ser anónima

## Exemplo

```python
from decimal import Decimal
from vendus import VendusClient, ClientData, DocumentItem

client = VendusClient.from_env()

fr = client.documents.create_invoice_receipt(
    register_id=1,
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
    items=[
        DocumentItem(
            description="Sessão de consultoria (paga na hora)",
            quantity=Decimal("1"),
            unit_price=Decimal("90.00"),
            tax_rate=Decimal("23"),
        ),
    ],
    external_reference="FR-2026-001",
)

print(fr.number)  # "FR 2026/12"
print(fr.atcud)
```

## Cenários

```python
# 1. Com NIF
client.documents.create_invoice_receipt(
    register_id=1, items=[...],
    client=ClientData(name="Acme Lda", fiscal_id="123456789"),
)

# 2. Só com nome (cliente não deu NIF)
client.documents.create_invoice_receipt(
    register_id=1, items=[...],
    client=ClientData(name="João Silva"),
)

# 3. Consumidor final (anónimo)
client.documents.create_invoice_receipt(register_id=1, items=[...])
```

## Variante async

```python
fr = await client.documents.create_invoice_receipt_async(
    register_id=1,
    items=[...],
)
```

## FT vs FR

| | Fatura (FT) | Fatura-Recibo (FR) |
|---|---|---|
| Factura a venda | ✅ | ✅ |
| Dá quitação do pagamento | ❌ (precisa de RC à parte) | ✅ |
| Quando usar | Cliente paga depois (a crédito, a 30 dias) | Cliente paga **na hora** |

## Notas

1. **Pagamento imediato:** a FR pressupõe que o pagamento ocorre no momento da emissão. Se faturas a crédito, usa `create_invoice` (FT) e emite o recibo (RC) quando o cliente pagar — RC chega numa versão futura.
2. **Cancelamento:** mesma API (`client.documents.cancel(id, reason)`).
3. **Nota de crédito:** uma FR pode ser creditada via `create_credit_note` referenciando o `id` da FR.
