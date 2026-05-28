# Receitas

Guias de integração com frameworks Python populares.

- [FastAPI](fastapi.md) — endpoint async para emitir faturas
- [Flask](flask.md) — emissão síncrona em rota Flask
- [Django](django.md) — view + serviço para emissão e armazenamento local

Padrões transversais:
- Carregar a API key de `VENDUS_API_KEY` ou ficheiro `.env`
- Guardar `invoice.id` na DB local para futuras NCs
- Passar `external_reference` único por pedido para idempotência
