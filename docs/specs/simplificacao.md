# Spec — Simplificação da plataforma (F0)

> Aprovada pelo dono em 2026-09-24 («aprovado como recomendado»). Relatório de
> origem, com evidências e medições: artefato «Simplificação do Atlans».
> Premissa dada: **nada está em produção de verdade** — não há usuários nem
> legado a preservar. Cada fase é um PR com o portão completo; nenhuma fase
> começa antes de a anterior estar verde.

## O norte (as três decisões que sustentam tudo)

- **N1 — A Home é o produto; `(dashboard)` é console do admin.** O middleware
  já devolve `/` a quem não é admin. Assumido: cada funcionalidade tem UMA casa
  por público; página × modal deixa de ser ambiguidade.
- **N2 — Um vocabulário: «assistente».** `copiloto`/`agente`/`assistente` são o
  mesmo conceito. Nome público único: **assistente**, incluindo as rotas.
- **N3 — Base zero: o banco nasce pronto.** A cadeia de 53 migrações colapsa
  numa revisão inicial única; o `init_schema.sql` (já testado por convergência)
  é o corpo.

## Decisões congeladas (do dono, 2026-09-24)

| Item | Decisão |
|---|---|
| A2 | **Remover** o mecanismo global de assinatura (`verify_signature` + `ENABLE_SIGNATURE_VERIFICATION` + validação por `NODE_ENV`). A borda continua com JWT, PAT, mTLS e HMAC por webhook. |
| A3 | A página `/drive` **fica como console do admin, com a própria UploadZone**. O corte é declarativo (N1), não de código. |
| A5 | Rename para **assistente** inclui **as rotas** (`/assistente/*` na Home; `/assistente/editor/*` na gaveta). |
| A6 | A gaveta do editor **fica**; a dependência inverte — a gaveta importa da Home, nunca o contrário. |
| A15 | Critério de helper no front: **só quando há comportamento** (sondagem, teste de webhook, portas de sub-fluxo). Layout e validação simples viram schema. |

## Protocolo de órfão

Nenhum endpoint, símbolo ou arquivo é apagado sem a busca registrada no PR em
**seis territórios**: `web/` (service + componentes), `app/mcp/tools/`,
`executor/` + `flow/`, agendadas/consumidores internos (`run_result_consumer`,
workers), `tests/`, `docs/`. A busca e o resultado entram na descrição do PR.
Um símbolo com consumidor em QUALQUER território não é órfão — corta-se só a
casca sem consumidor.

**Resultado já executado para A1 (2026-09-24):** as ROTAS de usuário
`POST /drive/upload-url` e `POST /drive/confirm-upload/{id}` não têm nenhum
consumidor (web: 0; MCP: 0; executor: usa as rotas `executor-*` próprias). Mas
os MÉTODOS `DriveService.create_upload_url` e `confirm_upload` têm consumidores
vivos — as tools MCP de escrita no Drive (`app/mcp/tools/drive_escrita.py`) e o
confirm do executor. **Corta-se: as duas rotas + `UploadUrlRequest` + testes de
rota. Ficam: os métodos do service.**

## Achados (o quê e onde — evidências no relatório)

**Grupo I — morto e caminhos duplos**
- A1 Rotas de presign de usuário órfãs (ver protocolo acima). *(F1)*
- A2 Assinatura global que nunca liga; `NODE_ENV` sem uso fora do config. *(F1)*
- A3 `/drive` = console do admin com upload próprio (declarado; sem código).
- A4 Não mexer: páginas `(auth)` são adaptadores (e-mail/next-auth); `workflow-groups` tem consumidor; `executor_ws` é WS.

**Grupo II — vocabulário e fronteiras**
- A5 copiloto/agente → assistente, ponta a ponta. *(F4)*
- A6 Gaveta importa da Home. *(F5)*
- A7 Tipos do web numa casa só (`web/interface/` some). *(F2)*
- A8 `lib/formatos.ts` único (hoje 3 cópias; 37 arquivos importando de observability). *(F2)*

**Grupo III — fundação**
- A9 Squash 53→1 migração; `ATLANS_DROP_*` fora; CD = `upgrade head`. *(F3)*
- A10 Fatiar monólitos: `drive_router` (3 routers num arquivo), `executor_ws_router` (2.420 l), `observability_service` (1.822 l). *(F5)*

**Grupo IV — front**
- A11 `admin/settings/page.tsx` (1.707 l, 16 componentes) fatiado na pasta. *(F2)*
- A12 `GisFlowService` por domínio + lint pendente. *(F1 lint, F5 fatiamento)*

**Grupo V — motor de fluxos (nós e arestas)**
- A13 Porta declarada 2× por nó (`outputs` × `static_output`) → uma forma, com tipo. *(F6)*
- A14 `'type'` com 3 papéis e 19 valores; docstring da base mente; `register_node` passa a validar o description na importação. *(F6)*
- A15 Schema pobre → 14 helpers; enriquecer (`required`/`placeholder`/`help`/`visible_when`) e aplicar o critério de helper. *(F6, por último)*
- A16 `isValidConnection` no gesto, derivado do catálogo de `GET /nodes`; o validate segue juiz final. *(F6)*

**O que está bom e não se toca:** IResponse/dedup de GETs; stores documentadas;
catálogo de fontes com teste de convergência; guardas de segurança específicas;
no motor: registry de fonte única, `execute_sync` em thread, lint pré-executor,
validate com corpo único para rota e MCP.

## Plano

| Fase | Conteúdo | Portão |
|---|---|---|
| F0 | Esta spec | — |
| F1 | A1 (rotas), A2, `NODE_ENV`, lint do service | completo |
| F2 | A8, A7, A11 | completo |
| F3 | A9 | completo + stack limpa do zero |
| F4 | A5 | completo + revisão adversarial |
| F5 | A10, A12, A6 | completo + revisão adversarial |
| F6 | A13 → A14 → A16 → A15 | completo + revisão adversarial + canvas manual |
| F7 | `architecture.md`, follow-ups, antes×depois | relatório final |

**Portão completo** = backend `pytest` integral · web `lint + typecheck +
testes + build` · `detect-secrets` sem novidade. Fases estruturais fecham com
revisão adversarial própria.

## Resultado (F7 — fechamento, 2026-09-24)

Medido entre o commit anterior à F0 e o fim da F6. Fora de docs:
**391 arquivos, +8.665 −12.393 = −3.728 linhas líquidas** — com as suítes
MAIORES no fim (backend 4.516 testes, web 1.972) do que no início.

| Alvo | Antes | Depois |
|---|---|---|
| `executor_ws_router.py` | 2.420 l num arquivo | fachada de 452 l + pacote `executor_ws/` (4 módulos, grafo acíclico) |
| `observability_service.py` | 1.822 l | fachada de 950 l + pacote `observability/` (5 módulos, um dono por constante) |
| `GisFlowService.ts` | 1.076 l de classe estática | fachada de 42 l + 11 domínios em `service/dominios/` |
| `admin/settings/page.tsx` | 1.707 l | 341 l + 9 componentes na pasta |
| `drive_router.py` | 669 l, 3 públicos num arquivo | 173 l (usuário) + executor + admin, permissão na borda |
| Migrações Alembic | 54 revisões | 1 (base zero com guarda anti-purga); CD = `upgrade head` |
| Vocabulário | 28 arquivos `copiloto`/`agente` | 0 — um nome (`assistente`), rotas incluídas |
| Tipos do web | `interface/` (5 arquivos) + `types.ts` | uma casa (`service/types.ts`) |
| Formatos de número/data | 3 cópias | `lib/formatos.ts` |
| Saída dos nós | declarada 2× ×64 nós, sem tipo | `outputs` única, tipada, ordem preservada |
| `description()` | nunca validado; docstring da base mentia | 3 vocabulários fechados, validados na importação |
| Conexão no canvas | qualquer porta em qualquer porta | recusa no gesto, derivada do catálogo; validate segue juiz |
| Form dos nós | 14 helpers; layout no front | `required` (26) + `placeholder` no schema; critério escrito; FileTriggerHelper (112 l de layout) morto |
| `app/core/security.py` + presign de usuário | 66 l + rotas | mortos (upload só pelo filtro do Drive) |

**Follow-ups varridos**: `ExecuteParamsDialog` já mora no domínio de execução
(`workflow/`) — encerrado sem ação. Ações de deploy do dono, fora do repo:
`alembic stamp --purge 9ed006ca1660` no banco existente e, se definidas,
renomear as envs `COPILOTO_*` → `ASSISTENTE_*` no servidor. Backlog de produto
(botão de clipe, placeholder com etapa, anexos como chips, evento `payment` no
painel do provedor) não é simplificação e segue como backlog.

**Pendência da F6**: canvas manual interativo na primeira janela com a stack
autenticada (roteiro no fechamento da F6); coberto até lá por 4.516+1.972 testes e pelo
previewer.
