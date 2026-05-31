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

## Testes

A Vendus **não tem um host de sandbox separado** — não há URL de testes; todos os pedidos vão para `www.vendus.pt`. O que a Vendus tem é um **modo de testes ao nível do documento** ("Modo de Formação/Testes"): documentos emitidos em modo testes **não têm validade fiscal** e **nunca são comunicados à AT**.

O modo de testes controla-se de duas formas:

1. **Por caixa (register).** Cada caixa tem um modo de funcionamento (`normal` ou `tests`), configurado no backoffice da Vendus (*Configuração → Definições → Lojas e Caixas*). **Contas novas vêm em `tests`** — uma conta acabada de criar emite documentos sem validade fiscal até a passares para `normal`.
2. **Por pedido.** Passa `mode` a qualquer método de criação:

```python
from vendus import DocumentMode

invoice = client.documents.create_invoice(
    register_id=1,
    items=[...],
    mode=DocumentMode.TESTS,   # não-fiscal — não comunicado à AT
)
```

Se omitires `mode`, a Vendus usa o modo configurado na caixa. Um documento de teste recebe na mesma um `number` e é impresso com a nota "sem validade fiscal". Confirmas que um documento **não** foi comunicado à AT porque o `tax_authority_id` vem vazio (esse campo só é preenchido quando a Vendus comunica o documento à AT).

!!! note "O que está verificado e o que não está"
    O comportamento acima vem da documentação oficial: o campo `mode` ([documents.doc](https://www.vendus.pt/ws/v1.1/documents.doc)), o modo por caixa ([registers.doc](https://www.vendus.pt/ws/v1.1/registers.doc)) e a página de ajuda [Modo de Formação/Testes](https://www.vendus.cv/ajuda/modo-formacao-testes/). O que ainda **não** confirmámos contra a API ao vivo é se um `mode=tests` por pedido é respeitado numa caixa configurada como `normal`. O caminho fiável e verificado é usar uma caixa que esteja ela própria em modo `tests`.

### Setup recomendado

- **Testes unitários** — mock com `respx`; nunca tocar na API real.
- **Testes de integração** — correr contra uma caixa em modo `tests`, assertar que `tax_authority_id` está vazio e cancelar o que for criado (ver `tests/integration/`).
