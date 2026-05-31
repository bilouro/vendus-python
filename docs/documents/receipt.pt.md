# Recibo (RG)

## O que é

Um **Recibo (RG)** dá quitação do pagamento de uma ou mais faturas já emitidas (ex.: uma
[FT](invoice.md)). Referencia as faturas pelo seu **número de documento** e regista os `payments` — não
tem linhas próprias. Usa-o quando emitiste uma fatura por pagar (FT) e o cliente paga
depois.

## Exemplo

```python
from decimal import Decimal
from vendus import Payment, VendusClient

client = VendusClient.from_env()
cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

receipt = client.documents.create_receipt(
    register_id=1,
    invoice_numbers=["FT 2026/123"],   # a(s) fatura(s) a pagar
    payments=[Payment(method_id=cash.id, amount=Decimal("100.00"))],
)
print(receipt.number)  # "RG 2026/1"
```

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `register_id` | `int` | Sim | id da caixa POS |
| `invoice_numbers` | `list[str]` | Sim | números das faturas a pagar |
| `payments` | `list[Payment]` | Sim | como foi feito o pagamento |
| `external_reference` | `str` | Não | permite retries seguros do POST |
| `mode` | `DocumentMode \| None` | Não | `TESTS` para um documento de teste (não-fiscal) |

## Notas

- **FT vs FR vs RG:** uma **FT** factura a venda (pode estar por pagar); um **RG** é o
  recibo emitido quando é paga; uma **FR** combina os dois de uma vez.
- Ao contrário das faturas, um **recibo pode ser cancelado** —
  `client.documents.cancel(receipt.id)` (verificado ao vivo).
