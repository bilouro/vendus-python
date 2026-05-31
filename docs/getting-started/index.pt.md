# Instalação e Quickstart

## Instalação

```bash
pip install vendus
```

Requer Python 3.9+. Dependências: [httpx](https://www.python-httpx.org/) e [Pydantic v2](https://docs.pydantic.dev/).

## Obter API key

1. Inicia sessão em [www.vendus.pt](https://www.vendus.pt)
2. **Definições → Acessos → API**
3. Cria/copia a API key

A API key identifica o utilizador na Vendus — todos os documentos emitidos via API ficam atribuídos a esse utilizador.

## Configurar credenciais

Recomendado: variável de ambiente ou ficheiro `.env`.

```bash
export VENDUS_API_KEY="a-tua-key"
```

```python
from vendus import VendusClient

client = VendusClient.from_env()         # lê VENDUS_API_KEY
# ou
client = VendusClient(api_key="...")
```

!!! danger "Nunca commits API keys"
    O `.env` deve estar no `.gitignore`. Não passes API keys como parâmetro de URL nem as registes em logs.

## Primeira fatura

```python
from decimal import Decimal
from vendus import ClientData, DocumentItem, TaxCategory, VendusClient

client = VendusClient.from_env()

invoice = client.documents.create_invoice(
    register_id=1,                       # ID do POS configurado na Vendus
    client=ClientData(
        name="Acme Lda",
        fiscal_id="123456789",
    ),
    items=[
        DocumentItem(
            description="Consultoria",
            quantity=Decimal("10"),
            unit_price=Decimal("75.00"), # bruto, com IVA incluído
            tax_category=TaxCategory.NORMAL,
        ),
    ],
    external_reference="ORD-2026-001",   # ativa retry seguro em POST
)

print(f"Fatura {invoice.number}")
print(f"Total: {invoice.gross_amount} EUR")
print(f"ATCUD: {invoice.atcud}")
print(f"QR: {invoice.qrcode}")
```

## Próximos passos

- [Configuração](configuration.md) — todas as opções do `VendusClient`
- [Qual tipo de documento escolher?](../documents/index.md)
- [Fatura (FT)](../documents/invoice.md), [Fatura-Recibo (FR)](../documents/invoice-receipt.md), [Nota de Crédito (NC)](../documents/credit-note.md)
