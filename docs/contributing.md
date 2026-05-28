# Contribuir

Obrigado pelo interesse. Este projeto segue padrões rigorosos — lê `CLAUDE.md` no repositório antes de propor mudanças.

## Setup

```bash
git clone https://github.com/bilouro/vendus-python.git
cd vendus-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Antes de abrir PR

Todos têm que passar:

```bash
ruff check .
ruff format --check .
mypy src/
pytest
```

Cobertura mínima: 85%.

## O que ler primeiro

- `CLAUDE.md` — arquitetura, regras (R1–R15), tipos de documentos, vocabulário
- `src/vendus/services/documents.py` — implementação de referência
- `tests/unit/test_invoice_scenarios.py` — padrão de testes para novos tipos de documento

## Âmbito

Tudo fora do roadmap atual (ver `CLAUDE.md`) deve ser discutido em issue primeiro.

## Adicionar um novo tipo de documento

1. Adicionar ao enum `DocumentType` em `models/document.py`
2. Criar `_build_X_body` em `services/documents.py`
3. Criar métodos `create_X` e `create_X_async` em `DocumentsService`
4. Adicionar testes em `tests/unit/test_X.py` com fixtures em `tests/fixtures/`
5. Criar exemplo em `examples/`
6. Criar página em `docs/documents/X.md` (PT) e `X.en.md` (EN)
7. Atualizar `CLAUDE.md` (roadmap) e `CHANGELOG.md`
