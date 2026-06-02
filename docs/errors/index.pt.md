---
description: "Trata erros da API Vendus em Python — hierarquia de exceções, códigos como P001, validação local, retries e resolução de problemas."
---

# Erros e Troubleshooting

## Hierarquia de exceções

Todas as exceções do SDK herdam de `VendusError`. Capturas mais específicas no topo, mais gerais em baixo.

```python
from vendus import (
    VendusError,            # base
    ValidationError,        # validação local (antes da API)
    AuthenticationError,    # 401
    AuthorizationError,     # 403
    NotFoundError,          # 404
    RateLimitError,         # 429
    APIError,               # outros erros da API (status_code + response_body)
    TransportError,         # rede: timeout, DNS, conexão recusada
)
```

## Tratamento típico

```python
from vendus import VendusClient, ValidationError, RateLimitError, APIError, TransportError

client = VendusClient.from_env()

try:
    invoice = client.documents.create_invoice(...)
except ValidationError as e:
    # NIF inválido, items vazios, 999999990, etc.
    logger.warning("Validação falhou: %s", e)
except RateLimitError:
    # Vendus está a rate-limitar. Espera e tenta de novo.
    time.sleep(60)
except APIError as e:
    # Outro erro do lado da Vendus
    logger.error("Vendus API %s: %s", e.status_code, e.response_body)
except TransportError as e:
    # Rede caiu. O GET já retentou; o POST sem external_reference NÃO retentou.
    logger.error("Rede falhou: %s", e)
```

## Erros comuns

### `ValidationError: Invalid Portuguese NIF`

O check digit do NIF não corresponde ao algoritmo mod 11.

**Solução:** verifica os dígitos. Se for um NIF válido que o SDK não aceita, abre issue.

### `ValidationError: Do not pass fiscal_id='999999990'`

Estás a tentar emitir a consumidor final passando o NIF genérico. **Errado** — em PT, consumidor final = omitir o argumento `client`.

```python
# ❌ Errado
client.documents.create_invoice(
    register_id=1, items=[...],
    client=ClientData(name="Anyone", fiscal_id="999999990"),
)

# ✅ Certo
client.documents.create_invoice(register_id=1, items=[...])
```

### `ValidationError: Credit note requires reference_document_id`

A NC tem que referenciar o documento original via `reference_document_id`.

### `AuthenticationError`

API key incorreta, expirada ou revogada. Verifica em **Vendus → Definições → Acessos → API**.

### `RateLimitError`

A Vendus está a limitar pedidos. O SDK já retenta automaticamente em GETs. Para POSTs, retenta apenas com `external_reference`.

**Solução:** espera (`time.sleep`) ou implementa fila com backoff exponencial.

### POST falhou — como retentar com segurança?

Se passaste `external_reference`, o SDK já retenta automaticamente. Se não passaste:

1. **Não retentes cegamente** — corres o risco de criar fiscal documento duplicado
2. Verifica via `client.documents.list(date_from=..., date_to=...)` se o original foi de facto criado
3. Se sim, descarta. Se não, retenta com `external_reference` desta vez

A regra geral: **sempre que emites algo, passa `external_reference`.**

## Logging

O SDK loga pedidos/respostas no logger `vendus`. PII (NIF, email, telefone, morada) é redigida automaticamente.

```python
import logging
logging.getLogger("vendus").setLevel(logging.DEBUG)
```
