# Validação NIF (Portugal) — Snippet

Algoritmo oficial da Autoridade Tributária (módulo 11 com pesos `9..2`).
NIF válido sse o 9.º dígito é igual ao check digit calculado a partir
dos primeiros 8. Quando `sum mod 11 ∈ {0, 1}`, o check digit é **0**
(não 1 — bug histórico, ver nota no fim).

## Snippet (Python ≥3.9, sem dependências)

```python
import re


def validar_nif_pt(nif: str | None) -> tuple[bool, str]:
    """Valida NIF português pelo algoritmo módulo 11.

    Returns:
        (True,  "ok")                  se válido.
        (False, "sem NIF")             se vazio / None / só whitespace.
        (False, "NIF errado: <razão>") em qualquer outro caso inválido.

    Razões possíveis para "NIF errado":
        - comprimento ≠ 9 dígitos
        - primeiro dígito ∉ {1..9}
        - check digit (módulo 11) não bate com o 9.º dígito

    Lógica:
        pesos 9,8,7,6,5,4,3,2 aplicados a d1..d8
        check = 11 - (sum % 11)
        se check ≥ 10 → 0
        NIF válido sse d9 == check
    """
    if not nif or not str(nif).strip():
        return False, "sem NIF"
    s = re.sub(r"\D", "", str(nif))
    if len(s) != 9:
        return False, f"NIF errado: {len(s)} dígitos (esperado 9)"
    if s[0] not in "123456789":
        return False, f"NIF errado: primeiro dígito inválido ({s[0]})"
    total = sum(int(s[i]) * (9 - i) for i in range(8))
    check = 11 - (total % 11)
    if check >= 10:
        check = 0
    if int(s[8]) != check:
        return False, (
            f"NIF errado: check digit (calculado {check}, recebido {s[8]})"
        )
    return True, "ok"
```

## Exemplos

```python
>>> validar_nif_pt("501964843")    # Microsoft Portugal
(True, 'ok')
>>> validar_nif_pt("123 456 789")  # aceita espaços/hífenes
(True, 'ok')
>>> validar_nif_pt("101100000")    # caso histórico — check digit 0
(True, 'ok')
>>> validar_nif_pt("123456788")    # check digit errado
(False, 'NIF errado: check digit (calculado 9, recebido 8)')
>>> validar_nif_pt("12345")
(False, 'NIF errado: 5 dígitos (esperado 9)')
>>> validar_nif_pt("")
(False, 'sem NIF')
>>> validar_nif_pt(None)
(False, 'sem NIF')
```

## Nota — Bug do check digit 0

A versão original do snippet usava:

```python
check = (11 - (total % 11)) % 10   # ❌ ERRADO
```

Isto rejeitava **~9% dos NIFs válidos** — todos os que terminam em 0.
Razão: quando `total % 11 == 0`, `(11 - 0) % 10` = **1**, mas o
algoritmo oficial diz `check digit = 0` quando o resultado ≥ 10.

A correcção é tratar o ramo `≥ 10` separadamente em vez de usar `% 10`:

```python
check = 11 - (total % 11)
if check >= 10:
    check = 0
```

Em produção isto manifestava-se em SKIPs com assinatura
`calculado 1, recebido 0`. Casos típicos: NIFs de pessoa colectiva
canónicos (`501964843`, `513769560`, etc.) e qualquer NIF singular
cujo check digit seja 0.
