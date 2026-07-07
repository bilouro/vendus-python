---
description: "Postura de segurança do SDK Python da Vendus: proteger a API key, a fronteira modo teste/real, redação de PII (R6) e manter os registos fiscais à prova de adulteração."
---

# Segurança

O que importa mesmo, em termos de segurança, quando emites documentos fiscais pela
Vendus com este SDK. É deliberadamente curto — a superfície de ataque do SDK é pequena:
**uma API key, sem webhooks, sem dados de cartão.** Onde um tópico tem mais detalhe,
liga para lá.

## A superfície é pequena — sabe porquê

- **A auth é uma única API key** por HTTPS Basic Auth (a key é o username, a password é
  vazia — regra R4). Não há OAuth, nem callback assinado, nem um segundo segredo.
- **Ainda sem webhooks** (roadmap v0.5). Nada chega sem ser pedido, por isso não há
  evento de entrada para forjar ou repetir, nem uma decisão de "confio nisto?" para
  errar.
- **Sem dados de cartão / pagamento.** A Vendus é faturação — o SDK nunca toca num PAN.

Ou seja, "manter seguro" resume-se a quatro coisas: proteger a key, respeitar a fronteira
teste/real, tratar a PII do cliente, e manter os registos fiscais intactos.

## A API key é a totalidade da auth

| Credencial | Desbloqueia | Se vazar |
|---|---|---|
| **`api_key`** | Emitir, ler, listar e cancelar documentos **como tu** | Um atacante pode emitir documentos **reais** — comunicados à AT em teu nome — que depois tens de reverter com notas de crédito. Uma trapalhada fiscal e financeira, não apenas spam. |

Regras práticas:

- A key vive numa **variável de ambiente ou num gestor de segredos** — nunca no código,
  no repositório, na base de dados, num URL, ou numa linha de log. O SDK lê-a uma vez na
  construção do cliente; mais nada precisa dela. Mantém o `.env` no `.gitignore`.
- O SDK **nunca faz log da key**. Não anules isso imprimindo tu o cliente ou o header
  `Authorization`.
- Se vazar, **roda-a** no backoffice da Vendus. Keys de teste e de produção são mundos
  diferentes — nunca deixes uma key de produção num `.env.example`, num log de CI, ou no
  histórico da shell de um portátil.

## O modo teste vs real é uma fronteira de segurança

O `mode` **herda o modo configurado da caixa** (R16). Omite-o e podes emitir
*silenciosamente* um **documento fiscal real, comunicado à AT** — ou um de teste
não-fiscal quando precisavas de uma fatura real. Um documento real não pode ser
"des-emitido" (FT/FR/NC não podem ser canceladas; reverte-lo com uma nota de crédito),
por isso errar isto tem consequências fiscais, não só um mau teste.

Define-o explicitamente — uma vez no cliente ou por chamada:

```python
from vendus import DocumentMode, VendusClient

client = VendusClient(api_key="...", default_mode=DocumentMode.NORMAL)  # ou por chamada: mode=...
```

Vê [Configuração](getting-started/configuration.md) para os detalhes.

## PII: o SDK redige os logs — não o anules

- O logger `vendus` redige automaticamente `fiscal_id`, `email`, `billing_email`,
  `phone`, `mobile`, `address` e `postalcode` dos registos de log (R6). **Nunca encaminhes
  payloads da Vendus pelo teu próprio logger** "por conveniência", e nunca ponhas PII do
  cliente em mensagens de exceção.
- O SDK **não** expõe um redactor na sua API pública. Se persistires payloads crus (uma resposta
  `GET` transporta um bloco de cliente), **redige-os tu à entrada** e combina isso com
  retenção limitada (uma coluna `purge_after`). Vê a receita
  [Persistir documentos](recipes/persisting-documents.md#seguranca-pii-e-retencao).
- **Minimiza o que guardas**: liga um documento a uma pessoa por `customer_id` na tua
  própria tabela de utilizadores — não copies o NIF / email / telefone do cliente para
  cada linha de documento.

## Os registos fiscais são críticos para a integridade

- Um documento real é comunicado à AT e **imutável**: nunca edites `hash`, `atcud`,
  `number` ou `qrcode`, e nunca apagues uma linha fiscal. As correções são **novas notas
  de crédito**, não edições.
- Torna o histórico **à prova de adulteração**: o role de BD da tua aplicação tem
  `INSERT` mas não `UPDATE`/`DELETE` no log de eventos (impõe-o com grants, não com
  disciplina).
- **Retenção**: guarda os registos de faturação (e o SAF-T que deles deriva) pelo período
  legalmente exigido — comummente citado como **10 anos** em Portugal; confirma o
  requisito atual com o teu contabilista.

## Ainda fora de âmbito (a ser honesto)

- **Webhooks / verificação de assinatura** — roadmap v0.5. Até lá não há superfície de
  confiança em eventos de entrada; quando os webhooks chegarem, esta página ganha uma
  secção de assinaturas.
- **Reportar uma vulnerabilidade** — vê o
  [SECURITY.md](https://github.com/bilouro/vendus-python/blob/main/SECURITY.md) para
  divulgação privada. Não abras uma issue pública para um bug de segurança.

## Checklist

- [ ] API key em env / gestor de segredos; nunca no código, repo, logs ou URLs
- [ ] `default_mode` (ou `mode` por chamada) definido explicitamente — sem surpresas
      silenciosas real/teste
- [ ] PII do cliente nunca encaminhada pelo teu logger, nunca em mensagens de exceção
- [ ] Payloads crus persistidos redigidos à entrada + retenção limitada (`purge_after`)
- [ ] Documentos ligados à tua tabela de clientes por id, não por PII copiada
- [ ] Linhas fiscais nunca editadas ou apagadas; log de eventos append-only por grant

---

Relacionado: [Configuração](getting-started/configuration.md) ·
[Persistir documentos](recipes/persisting-documents.md) ·
[Erros e Troubleshooting](errors/index.md)
