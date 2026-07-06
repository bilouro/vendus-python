# Receitas

Guias de integração com frameworks Python populares.

- [FastAPI](fastapi.md) — endpoint async para emitir faturas
- [Flask](flask.md) — emissão síncrona em rota Flask
- [Django](django.md) — view + serviço para emissão e armazenamento local
- [Persistir documentos](persisting-documents.md) — schema de DB de referência (tipos e tamanhos), o padrão write-ahead e reconciliação

Padrões transversais:
- Carregar a API key de `VENDUS_API_KEY` ou ficheiro `.env`
- [Persistir cada documento emitido](persisting-documents.md) — guarda `id`, `number`, `hash` e `atcud` para reimpressões e futuras NCs
- Passar `external_reference` único por pedido para idempotência
