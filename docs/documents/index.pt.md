---
description: "Que tipo de documento Vendus emitir em Python — fatura (FT), fatura simplificada (FS), fatura-recibo (FR), recibo (RG) ou nota de crédito (NC)."
---

# Qual tipo de documento escolher?

A AT define vários tipos de documentos fiscais. O SDK emite estes:

| Tipo | Código AT | Quando usar |
|---|---|---|
| **Fatura (FT)** | FT | Venda em que o cliente paga depois (a crédito, a 30 dias) |
| **Fatura Simplificada (FS)** | FS | Venda rápida a retalho / consumidor final, paga na hora (limites de valor AT) |
| **Fatura-Recibo (FR)** | FR | Venda em que o cliente paga **na hora** (factura + recibo num só) |
| **Recibo (RG)** | RG | Dar quitação do pagamento de uma fatura já emitida (ex.: uma FT) |
| **Nota de Crédito (NC)** | NC | Anular ou creditar parcialmente um documento já emitido |

## Árvore de decisão

```mermaid
flowchart TD
    A[Vou emitir um documento] --> B{Reverter uma fatura existente?}
    B -->|Sim| NC[Nota de Crédito NC]
    B -->|Não| P{Pagar uma fatura anterior?}
    P -->|Sim| RG[Recibo RG]
    P -->|Não| C{Cliente paga na hora?}
    C -->|Sim| D{Venda rápida a retalho?}
    D -->|Sim| FS[Fatura Simplificada FS]
    D -->|Não| FR[Fatura-Recibo FR]
    C -->|Não| FT[Fatura FT]
```

## Os 3 formatos de cliente

Todos os três métodos de criação aceitam as mesmas três formas de identificação:

```python
from vendus import ClientData

# 1. Com NIF (B2B típico ou B2C que pediu NIF)
ClientData(name="Acme Lda", fiscal_id="123456789")

# 2. Só com nome (B2C sem NIF)
ClientData(name="João Silva")

# 3. Consumidor final — OMITIR o argumento client por completo
# (não passes nada, nem ClientData(), nem fiscal_id="999999990")
```

!!! danger "Nunca uses 999999990"
    O SDK rejeita explicitamente `fiscal_id="999999990"`. Para consumidor final, omite o argumento `client`.

## Validações automáticas

O SDK valida localmente **antes** de tocar na API:

- **NIF português:** algoritmo mod 11 (rejeita check digits errados)
- **NIF 999999990:** explicitamente rejeitado
- **Items:** pelo menos um, `quantity > 0`, uma `tax_category` (NORMAL/INTERMEDIATE/REDUCED/EXEMPT/OTHER)
- **Nota de Crédito:** exige `reference_document_id` e `reason`
- **Documentos pagos (FR/FS) e recibos (RG):** exigem `payments`

## Próximos passos

- [Fatura (FT)](invoice.md)
- [Fatura Simplificada (FS)](simplified-invoice.md)
- [Fatura-Recibo (FR)](invoice-receipt.md)
- [Recibo (RG)](receipt.md)
- [Nota de Crédito (NC)](credit-note.md)
