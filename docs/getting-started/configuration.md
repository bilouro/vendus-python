# Configuração

## Opções do `VendusClient`

```python
from vendus import VendusClient

client = VendusClient(
    api_key="a-tua-key",
    base_url="https://www.vendus.pt/ws",  # produção (default)
    timeout=30.0,                          # segundos
    max_retries=3,                         # GETs retentam, POST só com external_reference
)
```

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `api_key` | `str` | — | API key da Vendus (obrigatório) |
| `base_url` | `str` | `https://www.vendus.pt/ws` | Base da API. Para Espanha: `https://www.vendus.es/ws` |
| `timeout` | `float` | `30.0` | Timeout HTTP em segundos |
| `max_retries` | `int` | `3` | Número máximo de retentativas em pedidos elegíveis |

## A partir do ambiente

```python
client = VendusClient.from_env()             # lê VENDUS_API_KEY
client = VendusClient.from_env(env_var="X")  # variável custom
```

## Política de retries

| Método | Retenta? | Quando |
|---|---|---|
| GET | ✅ Sempre | 408, 429, 5xx, timeout |
| POST / PUT / PATCH | Condicional | Apenas se o body contém `external_reference` |
| DELETE | ❌ Nunca | Cancelamento tem que ser explicitamente idempotente do lado da app |

A regra existe porque a Vendus **não oferece idempotency keys**. Sem `external_reference`, um POST repetido poderia criar dois documentos fiscais (e dois números de série gastos). O parâmetro `external_reference` é o âncora de deduplicação que a Vendus aceita.

**Recomendação:** passa sempre `external_reference` ao emitir documentos.

```python
invoice = client.documents.create_invoice(
    register_id=1,
    items=[...],
    external_reference="ORD-2026-001",  # idempotência
)
```

## Logging

O SDK usa o logger `vendus`. Tem um filtro automático que redige PII: `fiscal_id`, `email`, `phone`, `mobile`, `address`, `postalcode`, `billing_email`.

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("vendus").setLevel(logging.DEBUG)
```

!!! warning "Nunca faças bypass ao logger"
    Não imprimas payloads diretamente com `print(json)` ou outro logger. Usa sempre `logging.getLogger("vendus")` para que a redação se aplique.

## Sandbox

A Vendus **não tem ambiente de sandbox público** documentado. Toda chamada autenticada atinge produção e pode criar documentos fiscais reais com implicações fiscais com a AT.

Estratégias recomendadas:

1. **Conta dedicada para testes** — Vendus aceita criar contas de demonstração comerciais
2. **Série dedicada** — configura uma série de documentos exclusiva para testes ("FT-TESTE") na conta de produção
3. **Cancelar imediatamente** — todos os documentos de teste devem ser cancelados via `client.documents.cancel(id, reason="teste")`
4. **Mocks em testes unitários** — usa `respx` para fingir respostas, evitando completamente chamadas à API real
