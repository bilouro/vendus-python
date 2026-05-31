# Contribuir & Desenvolvimento

Obrigado pelo interesse em `vendus`. Este projeto visa qualidade de produção — as regras
estão em [`CLAUDE.md`](https://github.com/bilouro/vendus-python/blob/main/CLAUDE.md) na
raiz do repositório; lê-o antes de qualquer mudança substancial.

## Setup

```bash
git clone https://github.com/bilouro/vendus-python.git
cd vendus-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Quality gate (tem de passar antes de cada PR)

```bash
ruff check .            # lint
ruff format --check .   # formatação
mypy src/               # type checking estrito
pytest                  # testes unitários + cobertura (≥85% obrigatória)
```

Se mexeste na documentação, constrói-a em modo estrito:

```bash
mkdocs build --strict
```

## Testes — duas camadas

O SDK é validado em duas camadas, e a segunda é o que o mantém honesto contra a API real.

### 1. Testes unitários (cada commit)

- `tests/unit/`, com mock via [`respx`](https://lundberg.github.io/respx/) — nunca tocam
  na rede.
- **Asseram o body exato enviado**, não só o valor de retorno. É assim que se apanham
  bugs de nome/forma de campos.
- Gate de cobertura: ≥85% (`pytest` falha abaixo disso).

```bash
pytest                              # todos os unit + cobertura
pytest tests/unit/test_documents.py
pytest -k create_invoice
```

### 2. Testes de integração ao vivo (a pedido)

- `tests/integration/`, marcados `@pytest.mark.integration` e **excluídos da run normal
  do `pytest`**. Atingem a **API real da Vendus**.
- Fazem auto-skip a menos que `VENDUS_API_KEY` e `VENDUS_REGISTER_ID` estejam definidas,
  por isso nunca falham em CI nem numa máquina sem credenciais.
- Correm em **modo teste** (`mode=tests`) onde possível — documentos não-fiscais que a
  Vendus nunca comunica à AT.

```bash
export VENDUS_API_KEY=...         # API key de uma conta de teste/demo
export VENDUS_REGISTER_ID=...     # ver abaixo
pytest -m integration --no-cov    # --no-cov: uma run parcial dispararia o gate de cobertura
```

**Como obter os ids necessários:**

- `register_id` — `client.documents.list_registers()` (ou o backoffice da Vendus). Cada
  caixa tem um `id` e um `mode`.
- ids dos métodos de pagamento (para uma Fatura-Recibo) —
  `client.documents.list_payment_methods()`.

!!! warning "Usa uma conta de teste/demo dedicada"
    A Vendus não tem host de sandbox separado; "testar" é um **modo de teste** ao nível do
    documento. Contas novas têm a caixa em modo teste por defeito, por isso os testes ao
    vivo emitem documentos não-fiscais. Ver
    [Configuração → Testes](getting-started/configuration.md#testes). Documentos de teste
    **não** são consultáveis nem canceláveis, por isso um teste ao vivo não se limpa a si
    próprio — são inertes. Tudo o que criares em modo **real** é um registo fiscal
    permanente; reverte uma fatura com uma nota de crédito (ver abaixo).

## A disciplina de live-validation

A documentação de referência da Vendus nem sempre está completa — **valida a forma do
body contra a API real antes de afirmar que uma operação funciona.** Vários bugs reais só
foram apanhados assim (o `create_invoice` do SDK nunca funcionou até a validação ao vivo
corrigir os campos das linhas). Estão registados como factos verificados no `CLAUDE.md`
(regra R16). Os que um contribuidor tem de respeitar:

- **Linhas** enviam `tax_id` (um código `TaxCategory`: NOR/INT/RED/ISE/OUT), não
  `tax_rate`; `discount_percentage`, não `discount`; `id` para uma linha de produto, não
  `product_id`. Nomes errados → a API devolve `P001`.
- **Fatura-Recibo (FR)** exige `payments` — `[Payment(method_id=..., amount=...)]`, com
  ids de método específicos da conta (de `list_payment_methods()`).
- **Notas de crédito (NC)** creditam um original **real**: o SDK faz GET dele e referencia
  cada linha via `reference_document` (número + linha) + o id da linha original. Uma NC
  **não** pode ser criada em modo teste (o original de teste não é consultável).
- **FT / FR / NC não podem ser canceladas** — o `cancel()` recusa-as; reverte uma fatura
  com uma nota de crédito.
- **O `mode` herda o modo da caixa** (teste em contas novas). Define
  `VendusClient(default_mode=DocumentMode.NORMAL)` para documentos reais, ou passa `mode=`
  por chamada. Esquecê-lo produz silenciosamente um documento de teste.
- **Códigos de tipo desconhecidos** mapeiam para `DocumentType.UNKNOWN` (o código real
  fica em `raw_response`) — nunca rebentar num tipo que o enum não modela.

## Arquitetura (orientação)

```
VendusClient            # a única classe que os utilizadores instanciam; lazy-load dos serviços
  └── DocumentsService  # create_*, get, list, cancel, list_payment_methods
        └── _request / _request_async    (auth + base URL injetados pelo HttpTransport)
              └── HttpTransport           # httpx sync+async, retry, timeout, User-Agent
```

- `_ficheiro.py` = interno; `ficheiro.py` = público (exportado em `__init__.py`).
- Dinheiro é `Decimal` em todo o lado; converte com `float()` só na fronteira do wire.
- Cada método tem uma variante sync e uma `_async`.

Detalhe completo (regras R1–R16, o vocabulário unificado, o playbook) está no `CLAUDE.md`.

## Adicionar um novo tipo de documento

Usa `services/documents.py::create_invoice` como referência.

1. Adiciona o código ao enum `DocumentType` em `models/document.py`.
2. Adiciona um builder `_build_X_body(...)` em `services/documents.py`.
3. Adiciona `create_X` e `create_X_async` ao `DocumentsService`. Passa
   `self._effective_mode(mode)` para o argumento `mode`, para o `default_mode` do cliente
   se aplicar.
4. **Valida ao vivo o body** contra a API real antes de afirmar que funciona — a
   documentação de referência pode estar incompleta (uma FR precisa de `payments`; uma NC
   precisa de `reference_document` por linha).
5. Adiciona testes unitários que asseram o body exato (`tests/unit/`), com fixtures de
   resposta em `tests/fixtures/`.
6. Adiciona um exemplo executável em `examples/` e uma página `docs/documents/X.md` (+ a
   versão portuguesa `X.pt.md`).
7. Atualiza o `CHANGELOG.md`, e o `CLAUDE.md` (roadmap, e a tabela de vocabulário R1 se
   surgir um campo novo).

## Lacunas conhecidas

Pendências e lacunas de verificação estão em
[`TODO.md`](https://github.com/bilouro/vendus-python/blob/main/TODO.md) — consulta-o antes
de começar trabalho relacionado, e mantém-no honesto (marca um item só quando verificado).

## Âmbito

Qualquer coisa fora do roadmap atual (ver `CLAUDE.md`) deve ser discutida num issue
primeiro.
