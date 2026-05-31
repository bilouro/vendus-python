# Métodos de pagamento

Uma **Fatura-Recibo (FR)** regista o pagamento no momento da emissão, por isso exige um ou
mais `payments`. Os ids dos métodos são **específicos da conta** — lista-os uma vez e
reutiliza os ids de que precisas.

## Listar os métodos da conta

```python
from vendus import VendusClient

client = VendusClient.from_env()
for m in client.documents.list_payment_methods():
    print(m.id, m.title, m.type)   # ex.: 191432483 Dinheiro NU
```

Cada um é um `PaymentMethod`:

| Campo | Descrição |
|---|---|
| `id` | o id a passar em `Payment.method_id` |
| `title` | o teu nome de exibição, configurado na Vendus (ex.: "Dinheiro", "Multibanco") |
| `type` | o código oficial Vendus — ex.: `NU` (numerário), `CC` (crédito), `CD` (débito), `MB` (referência MB), `MBWAY`, `TB` (transferência), `DNP` (conta corrente). `title` e `type` são independentes — uma conta pode chamar "Multibanco" a um método `CD` |
| `status` | `on` / `off` |

## Anexar pagamentos a uma fatura-recibo

```python
from decimal import Decimal
from vendus import Payment

cash = next(m for m in client.documents.list_payment_methods() if m.type == "NU")

receipt = client.documents.create_invoice_receipt(
    register_id=1,
    items=[...],
    payments=[Payment(method_id=cash.id, amount=Decimal("90.00"))],
)
```

Os pagamentos têm de cobrir o total do documento.

### Dividir por vários métodos

```python
payments=[
    Payment(method_id=cash.id, amount=Decimal("50.00")),
    Payment(method_id=mbway.id, amount=Decimal("40.00")),
]
```

### Pagamento diferido

Um `Payment` pode levar `date_due`:

```python
from datetime import date

Payment(method_id=transfer.id, amount=Decimal("90.00"), date_due=date(2026, 12, 31))
```

Campos de `Payment`: `method_id` (`int`, obrigatório), `amount` (`Decimal`, obrigatório,
bruto), `date_due` (`date`, opcional).

!!! note "Validado ao vivo"
    Um método único, vários métodos, pagamentos divididos e `date_due` estão todos
    validados contra a API real da Vendus.
