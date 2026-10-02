# Assistant — building workflows from natural language

The assistant is a panel in the editor where the person describes what they want and the workflow appears on the canvas. Under
the hood, it talks to a language model that has access to the **same 42 tools** that the
MCP server exposes to an external agent — node catalog, authoring guide, validation, execution.

It is the first time the platform consumes its own MCP.

## How it delivers: `desenhar_no_canvas`

The assistant has a tool that **does not exist in the MCP** and never appears to an external
client: `desenhar_no_canvas(definition, nota?)`. The canvas belongs to the editor, and only makes sense to
whoever is looking at it.

**It is the delivery.** Until the model calls it, the screen of whoever asked is empty — however
well the model explained. The prompt tells it to call it early and repeatedly: the workflow grows
while it builds, instead of appearing whole at the end.

This fixes a design flaw. Before, putting the workflow on the screen was a **side effect** of a
call to `validate_workflow` — the panel read the definition from that tool's argument.
It worked when the model validated, and nothing forced it to validate: asked *"read the shapefile and
do a 500 m buffer"*, it could read the Drive, execute and return the GeoJSON. Request fulfilled,
empty canvas. No instruction fixes that, because there was nothing whose name was
"deliver the workflow". Now there is, and `validate_workflow` went back to being a means.

**Executing requires having drawn first.** `run_workflow` is refused while there is no workflow on the
screen — it is the same path that produced the data-as-answer. The refusal is about order, not scope:
once it has drawn, it may run (with the usual approval in text).

**The drawing goes in by itself.** On an empty canvas, always. On a canvas that already has work, the
first drawing of the conversation waits for a click — and from then on it draws without interrupting.
`Ctrl+Z` undoes. Drawing **does not save**: the editor's Salvar (Save) still belongs to whoever is using it.

## What it does, and what it does not do

| | |
|---|---|
| **builds and edits** | reads the guide, queries the catalog, checks each property in `describe_node`, drafts the definition and validates until the report is clean |
| **shows** | at the end, the panel displays a card with the finished workflow and the **Aplicar no canvas** (Apply to canvas) button |
| **executes** | runs the workflow with node-by-node tracking — **after asking for approval in text** |
| **does NOT save** | `create_workflow` and `update_workflow` do not exist for it. Whoever applies to the canvas is you, through the editor's button |
| **does NOT delete** | schedules and Drive files are out of its reach |

### Why the write gate is hard

The alternative was to trust the prompt text for the model to ask for confirmation before saving.
A promise in text is not a guarantee: a model that does not ask saves, and then the apply button becomes
decoration.

The rule is not a hand-written list — it is derived from `GUARDAS`
(`app/mcp/guardas.py`): **every tool that is not read-only is out**, except
`validate_workflow` (which simulates and persists nothing) and `run_workflow` (the deliberate exception). A
new write tool is born blocked.

And it applies in two places, for the same reason the MCP separates `list_tools` from `call_tool`: hidden from the
list the model sees (comfort) **and refused at dispatch** (the guarantee — even if the model
names it because it read it in an example, hallucinated it, or someone asked for it in the text of a shared workflow).

## Surfaces

The loop (`app/services/assistente_service.py`) is a single one; what changes between the **editor** assistant and the
**Home** assistant is a package of six things, gathered in a `Superficie`:

| | what varies |
|---|---|
| `instrucoes` | the system block that corrects where the MCP policy does not apply there |
| `ferramentas_extras` | the LOCAL tools that open the model's list (the canvas drawing; the globe and the quick replies on the Home) — they do not exist in the MCP |
| `executores_locais` | what those tools do, without going to the server |
| `permitida` | which MCP tools go into the list |
| `portao` | the check before dispatching to the server |
| `quadros_extras` | the SSE frames that that surface emits after a tool |

**The editor is the `EDITOR`, and it is the default for everything** — `conversar`, `montar_sistema` and
`ferramentas_para_o_modelo` fall back to it when nobody passes a surface. So everything this
document describes about the editor still holds byte for byte: the canvas drawing, the hard write
gate, the `proposta` frame.

The **Home** (`app/services/assistente_superficie.py`) is the other surface. The differences are about product,
not mechanics:

- **The delivery is a layer on the globe**, not a drawing on the canvas — `exibir_no_globo` in place of
  `desenhar_no_canvas`, and the answer reaches the globe by itself when a run by the assistant finishes.
  The second local tool, `sugerir_respostas`, offers the person up to three short follow-ups
  (the chips under the answer) through the `respostas_rapidas` frame.
- **Full reach** (the six PAT scopes, against the editor's four), because the assistant creates
  and runs its OWN workflows — marked `origem="assistente"` by the identity, hidden from the
  listings — without asking for permission.
- **Click confirmation** for whatever touches what already existed (editing/running one of the person's workflows,
  schedules, deleting a Drive file, publishing, restoring, turning on/off). The gate stores the action
  in Redis for 15 min and emits a `confirmacao` frame; the click executes the STORED arguments, on the
  server — never a promise in text, never the arguments the client sends with the click.

The API that serves the Home (persisted conversations, the confirmation endpoint, the globe) is described separately;
this section covers only the boundary of the loop. The other boundary — who talks to the model — is the
OpenRouter client, below; a future runtime (Hermes) would swap one of the two, never the middle.

## Turning it on

The assistant is **optional**. Without a key it simply does not exist, and the rest of the editor remains
whole — the right behavior for whoever runs Atlans as a self-hosted installation and does not want the
external dependency.

```bash
# API .env
LLM_API_KEY=sk-or-v1-...         # or OPENROUTER_API_KEY, the old name
#LLM_BASE_URL=                   # empty = https://openrouter.ai/api/v1; or a gateway, or a local server
#ASSISTENTE_ATIVO=true           # false/0/off/no turns it off even when there is a key
#ASSISTENTE_MODELO=              # the name in the provider's catalog; a restart is enough
#ASSISTENTE_ATRIBUICAO=false     # true: the name and FRONTEND_URL go as attribution on OpenRouter
```

Outside OpenRouter, any server with the OpenAI API (`/chat/completions` streaming, with
tools) works: a gateway such as LiteLLM, or a local server such as Ollama, vLLM and
llama.cpp. Example with Ollama:

```bash
LLM_BASE_URL=http://ollama:11434/v1
LLM_API_KEY=local                # Ollama does not ask for a key; any non-empty value turns the assistant on
ASSISTENTE_MODELO=qwen3:14b      # a model that knows how to call tools
```

Outside OpenRouter, the request goes only in the OpenAI API format: without OpenRouter's own fields
(`reasoning`, `usage.include`, the prompt cache), which OpenAI itself refuses, and with
`stream_options.include_usage`, which is how these servers send the token count in the stream.
The daily quota depends on that count: a server that does not send it leaves the quota uncounted, and the API
log warns on the first such response. Without a price in the provider's catalog, the admin's cost screen
shows the cost as unknown.

The key belongs to the **platform**, not to the user: whoever pays for the tokens is the installation. The per-person ceiling
is below. If your deploy rewrites the server's `.env` from a copy stored outside it
(a CI secret, for example), the key has to be **in that copy**, and not just edited on the server.

## The provider: OpenRouter

The model comes through [OpenRouter](https://openrouter.ai): a router with a single key and a single API for
models from Anthropic, OpenAI, Google and open models. Switching models means changing `ASSISTENTE_MODELO`
to the catalog name (`fornecedor/modelo`, e.g. `anthropic/claude-opus-5`, `openai/gpt-5`,
`google/gemini-2.5-pro`; the live list is at [openrouter.ai/models](https://openrouter.ai/models)) and
restarting the API. The default is `anthropic/claude-opus-5`.

**A single module talks to it**, `app/services/openrouter.py`, on top of `httpx` — no vendor SDK
goes into the image, and a single connection pool per process serves all conversations. It uses
OpenRouter's native API (`POST /chat/completions`, streaming) and translates in both directions:

| | |
|---|---|
| **transcript** | belongs to the **project**, not to the provider: `text`, `thinking`, `tool_use` and `tool_result`, in plain dictionaries. It is what Redis (editor) and Postgres (Home) store, what the replay reads and what the click confirmation matches by `tool_use_id`. On the way out it becomes `system`/`user`/`assistant` (`tool_calls`)/`tool`; on the way back, the stream is reassembled into these blocks |
| **reasoning** | requested with `reasoning.effort = high` (OpenRouter translates it to what each family accepts). The summarized text goes out in the `pensando` frame; the `reasoning_details` come back **verbatim** in the next round, which is what the model needs to continue reasoning between tool calls |
| **prompt cache** | two breakpoints: the stable prefix (tools + system) and the last human message. OpenRouter passes them on to providers that have explicit caching and ignores them for the ones that cache on their own |
| **quota** | the count comes in the last frame of the stream (`usage.include`). `entrada` already includes what came from the cache; the quota adds input + output. The cost in credits (dollars) goes in `fim` and in the API log, as information |
| **failures** | network errors, 429 and 5xx **before the body** are retried (3 attempts); a 400 with stored reasoning is redone once without it. A stream that dies midway, or that ends without `finish_reason` (a gateway 200 with HTML), is `modelo_indisponivel`, never a half answer. A response with no block at all does not enter the transcript, and an assistant message with no text and no call does not go to the provider |
| **stops** | `stop` ends; `tool_calls` runs the tools; `length` (cut by `max_tokens`) **runs no tool at all** — the argument may have arrived halfway; `content_filter` becomes `recusado` |

An old `thinking` block — from when the transcript came from another API and carried a `signature`
— stays in the database for the replay and is **omitted** on the way out: what was already thought in past turns is not
needed, and resending it in a format the provider does not recognize would bring down the conversation.

## The panel

A drawer anchored to the right of the canvas, in the editor (`/workflow/[id]`) and on the create
screen (`/workflow/create`). **It is not an overlay**: the canvas shrinks and both stay visible — you can watch
the workflow appear while reading the explanation, which is what keeps someone from applying it without understanding.

| | |
|---|---|
| open/close | `Ctrl+I`, or the star button in the corner of the canvas |
| default | **open** on the create screen (the canvas starts empty), **closed** in the editor of an existing workflow |
| width | 300–560 px, draggable by the edge; the preference stays in the browser |
| phone | becomes a full-height sheet |
| start over | `⋯` menu → *Recomeçar a conversa* (Restart the conversation; deletes the history of that workflow, never the workflow) |

Without `LLM_API_KEY` (or `OPENROUTER_API_KEY`) in the installation, none of this appears — neither the drawer nor the button.

## Quota

### When it runs out, the way out

The full-quota notice (`aviso-de-cota.tsx`) can carry an extension's offer
(`ofertaDaCota`, see `docs/architecture.md`, Web extensions). Without an extension, the notice stands
alone.

The component is a single one on purpose. The text lived duplicated in **three** surfaces — the Home's
bar, the Home's floating panel and the assistant drawer in the editor; while it was only a notice, the
duplication cost little, but a button that exists on one surface and not on the other is a sale
that disappears depending on the screen where the person hit the ceiling. The shell remains each surface's own (a capsule
in the bar, a block in the other two); the content belongs to the component.

The colors are **theme-aware** because of the third one: the Home forces `dark` on its shells,
but the editor's drawer follows the viewer's theme, and fixing the dark palette would paint amber-400
on a light background.

`GET /assistente/editor/estado` and `/assistente/estado` carry `plano` and `assinaturas_ativas`, which the
extension registry fills in (without an extension: `null` and `false`). The notice also states the **real**
reopening time — the server sends `reabre_em_segundos`, the donut right below already used it, and
"algumas horas" (a few hours) was the screen knowing more than it told.

The quota is by **accumulated tokens** in a 24 h window, not by message. The reason is straightforward: a
message that triggers ten tool calls costs ten times one that triggers none. Counting
messages would measure the wrong thing and give the same quota to "thanks!" and to the twenty-node workflow.

| | |
|---|---|
| ceiling | **the installation's**: `ASSISTENTE_TETO_DE_TOKENS_POR_DIA` (default 1,500,000), the same for everyone. What answers is `teto_do_assistente.plano_e_teto()`, which asks the extension registry (`app/extensoes`): in an installation with a plans extension, the ceiling is that of each person's plan, which the admin edits |
| window | 24 h from the first conversation |
| where | Redis, key `assistente:tokens:{user_id}` |
| query | `GET /assistente/editor/estado` returns spent, ceiling, when it reopens and the `plano` that gives that ceiling; during the turn the stream sends the running total on each model response (`cota` frame), with the SAME ceiling — the loop resolves the plan once and carries it through to billing, otherwise the donut would oscillate in the middle of the answer |
| on screen | a donut with the percentage sits UNDER the message field (bar and panel on the Home, editor drawer) — `uso-da-cota.tsx`; terracotta up to 79%, amber from there on, a reopening countdown when it runs out; the tooltip brings the detail (spent, ceiling, percentage, time). It rises during the turn through the `cota` frame and is reread from `/estado` when the stream closes |

> **The current ceiling is generous on purpose and has not been measured yet.** It came from an estimate: the
> tool definitions added up to ~22 KB (~6.9 k tokens, the stable prefix the cache keeps) when there were 38 — today there are 42 —, and
> what dominates the cost are the **results** — the catalog index is ~10 KB, a whole definition
> about as much. The definitive number has to come from a real session building a real workflow.
>
> **Since 2026-09-21 the measurement exists**: `uso_do_assistente` records the real consumption of each round.

### Two brakes, and one does not depend on Redis

The daily quota degrades **open** when Redis goes away, like all the rest of the quota module. But
spending is money, not load — that is why there is also a ceiling on **loop rounds**
(`TETO_DE_VOLTAS`, an in-memory counter) that closes the conversation no matter what. A model stuck in a
tool cycle is the fastest way to spend a lot without anyone noticing.

## Which model: env as the floor, database on top

`ASSISTENTE_MODELO` is still the default — a new installation comes up working without
anyone configuring anything. When there is a choice saved by the admin (`SystemConfig`, key
`assistente.modelo`), it wins. Switching models is an operations decision, and requiring a deploy
for it was what kept the operator from switching.

**There is no new table**: `SystemConfig` is already the global configuration keyring, with the
same requirements — one row, read a lot, written rarely.

The model is resolved **once per conversation**, together with the quota ceiling. Resolving it on every
round would let the admin switch the model in the middle of a reasoning in progress, changing the
behavior midway; whoever has already started finishes on the model they started with.

`assistente_config_service.modelo_em_uso` never returns empty: Redis down, database down or a
corrupted row fall back to the environment default. Being left without a model would mean the whole
assistant out of service because of a configuration, and the default is always better than nothing.
Cached in Redis with a 5 min TTL, invalidated on save — without the invalidation, the switch
takes up to five minutes to take effect and the admin concludes that the button is broken.

### `/admin/assistente/modelo` — the switch with the cost up front

Admin only. The `GET` returns the model in use and the provider's catalog
(`openrouter.listar_modelos`, with the prices **already converted to dollars per million
tokens**). An extension can add fields to the response, and `?simular=<id>` reaches it, to
recompute what depends on the model without saving anything.

#### The `PUT` PROBES before saving

**"It is in the catalog" does not mean "it works".** The provider lists a few hundred
models, and among them there are variants that the chat endpoint refuses entirely (the
`:batch` ones — "cannot be used with the chat/completions endpoint"), models without tool
support (and the assistant sends all 42 on every call) and models whose output ceiling is
lower than our `MAX_TOKENS`.

That is how the assistant went down in production: a valid id, picked from the catalog, saved without
checking — and every user started seeing "não consegui falar com o modelo" (I couldn't reach the
model) while whoever made the switch saw nothing.

Before saving, `openrouter.sondar_modelo` makes a real call with the **shape** of the real
request (the same tools, the same `max_tokens`, the same effort) and minimal
content. Filtering by catalog fields would mean guessing which fields exist and keeping the
guesswork up to date; one call answers correctly for every case at once — including
the ones nobody foresaw, such as the batch variant, which was on no list of suspects
at all.

Three rules of the probe:

- **The provider's refusal becomes a 400 with its own words.** Whoever is switching reads "cannot be used
  with the chat/completions endpoint" on the click.
- **Only an HTTP `status` blocks.** A stream that opens with 200 and ends without a useful frame is a
  transmission detail, not configuration — failing because of it would bar a model that
  works.
- **Going back to the default (`modelo: null`) is NEVER probed.** It is the emergency exit: if the
  provider is down with a bad model saved, probing it would lock the door at the very moment
  it is needed.

**A model with no known price becomes `null`, never `0`.** Zero reads as "free", and it is that
reading that would lead to the wrong choice.

A provider that is down does not bring down the screen: the catalog comes empty with the reason in
`catalogo_indisponivel`, and the admin can still see what is in use and go back to the
default. Responding 500 there would lock the only way out.

The screen is the **Assistente** (Assistant) section in `/dashboard/admin/settings`.

## What it cost: `uso_do_assistente`

One row per **round** of the loop, recorded at the same point where the quota is charged
(`cotas.cobrar_tokens_do_assistente`). Recording there, and not at the end of the conversation, has two
consequences: the quota and the consumption ledger count the same thing and cannot
diverge, and a conversation abandoned midway (tab closed, dead stream) has already
recorded what it spent up to that point — adding up only at the end would lose those, and would lose them **on the
low side**, the wrong side to err on for data that becomes a pricing decision.

| Column | What for |
|---|---|
| `modelo` | recorded, **not inferred**. On the day of the first model switch, comparing before and after depends on this |
| `entrada` / `saida` | repricing with another model — input and output prices differ by several times |
| `cache_leitura` | a subset of `entrada`, informational: it costs ~10 % of the input price but counts in full against the quota |
| `custo_usd` | what the provider said it cost. `NUMERIC`, not `FLOAT`: these are sums of money over thousands of rows |

`uso_service.registrar_volta` **never raises** and opens its own session (the loop runs
inside an SSE generator and has no request session). It is the same reasoning as the quota
charge: the conversation already happened and was already paid for, and losing the note is better than throwing
away the work. A round with no tokens at all does not become a row — a row of zeros would pull the
median down, and it is the median that decides pricing.

**No content lives here**: counts, the model and the cost. The table answers how much
the bill was, not what was said.

## The conversation

The history lives on the **server**, not in the browser. Keyed by `(usuário, fluxo)` (user, workflow): reopening the editor
resumes the conversation of that workflow; the create screen has its own. 24 h TTL.

This is not just convenience. A `tool_result` is the **server's** word about what happened; a
client that stored the transcript could rewrite it and tell the model whatever it wanted — *"the
validation passed"*, *"the user is an administrator"*. That is why `POST /assistente/editor/conversa` accepts
**only** the new message, and refuses with 422 any extra field.

One conversation at a time, per workflow: two tabs on the same workflow would write to the same transcript and
scramble it. The second one gets `conversa_em_andamento`.

## Routes

| | |
|---|---|
| `POST /assistente/editor/conversa` | `{mensagem, workflow_id?}` → `text/event-stream` |
| `GET /assistente/editor/estado` | `{ativo, motivo?, cota?, plano, assinaturas_ativas}` — the panel queries it before appearing; without an extension, `plano` is `null` and `assinaturas_ativas` is `false` |
| `DELETE /assistente/editor/conversa?workflow_id=` | forgets the history of that workflow (204) |

All of them require a JWT session. They do **not** accept a personal access token: the PAT is for external clients, which talk
through `/mcp`.

### The SSE frames

Each frame is a named `event:` with a JSON `data:`. The panel subscribes by type.

| `event` | `data` |
|---|---|
| `pensando` | `{texto}` — the model's summarized reasoning |
| `texto` | `{texto}` — what it is writing |
| `ferramenta` | `{id, nome, argumentos}` — **summarized arguments**: keys and sizes, never the content |
| `progresso` | `{concluidos, total, mensagem, id?}` — the node-by-node progress of a run; `id` is the `tool_use_id` of the owning call (the tools of a round run in parallel — without it, the frame paints the wrong card; absent only in conversations recorded before the field existed) |
| `cota` | `{gasto, teto}` — the window's running total after each model response; only with Redis; it is not a conversation block and does not enter the replay |
| `ferramenta_fim` | `{id, nome, erro}` |
| `proposta` | `{definicao, nos, arestas, ok, erros, avisos}` — the validated definition, **whole** |
| `erro` | `{code, message, hint?}` |
| `fim` | `{transcrito, uso, voltas, ok}` — **always the last**, even when something went wrong |

The `fim` is always the last frame on purpose: it is the one that carries the transcript, and losing the conversation
because the model tripped on the eighth round would make the person start over from scratch. When there was a failure, an
`erro` comes before and the `fim` carries `ok: false`.

Closing the tab in the middle of the response does **not** lose the conversation: the generator records the transcript in a
`finally` shielded by `asyncio.shield`, so that the disconnection's cancellation does not abort the write
halfway. And a long turn does not die silently at the proxy: the editor's SSE goes through the same heartbeat
(`: ping` every 15 s of silence, `app/api/routers/_streaming.py`) as the Home assistant. The quota
is already protected without this — it is charged after each call to the model, inside the loop.

### The `proposta` frame, and why it is the exception

Every `ferramenta` frame carries **summarized** arguments — keys and sizes, never content. The
`proposta` is the only exception, and it is narrow on purpose: it carries the WHOLE definition, only from
`validate_workflow`, and only when the tool did not fail.

The reason is straightforward. The assistant does not save; what takes the workflow to the canvas is the **Aplicar** (Apply) button. With the
summary, `definition` would reach the panel as `{"__campos__": 2}` — and the button would have nothing to apply.

The definition comes from the **argument**, not from the result: it is what the model asked to validate, it is what the
server validated, and it is exactly what will be applied. Reading from the result would open room for the two to
diverge.

`ok`, `erros` and `avisos` come from the validation report. `ok: null` means the report could not
be read — it does **not** mean it passed, and the panel disables Aplicar in that case.

### Aplicar (Apply)

The button is local: it builds the canvas from the definition and calls no route at all. Saving is still
the editor's **Salvar** (Save), as in any other edit.

Applying **replaces** the canvas, but **preserves the position** of every node whose `id` survived. This is not a
detail: the assistant's definition has no positions, and without the preservation a twelve-node workflow arranged by
hand would turn into a horizontal row. The new nodes come in through the same auto-layout as the arrange button, and
move down if they land on top of a card that was already there.

Before the click, the card shows what is going to happen — `n novos · n alterados · n removidos` — because
applying on a full canvas is destructive. `Ctrl+Z` undoes.

### Consuming it in the browser

**It is not `EventSource`**: that is GET, sends no header, and the conversation needs a body and
`Authorization`. Use `fetch` and read `response.body`:

```ts
const r = await fetch("/assistente/editor/conversa", {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify({ mensagem, workflow_id }),
})
const leitor = r.body!.getReader()
// …decode the `event:`/`data:` frames and dispatch by type
```

A frame can arrive **split in half** between two `read()` calls — the network does not respect message
boundaries. The decoder needs to keep the remainder; the web one is in
`web/app/components/home/assistente/quadros.ts`, with that case covered by a test.

Inside the web application itself the `Authorization` is **not** sent: the call goes through the
`/terra` proxy, which authenticates to the API with the server's token and ignores the client's header. The example above is
for whoever talks directly to the API.

## Security

- **The assistant gains nothing you did not have.** The scope is that of your session, with two scopes
  FEWER than a full personal access token (`triggers:manage` and `drive:write` are left out), and the gate
  above removes every write tool except `run_workflow`. The authorization is the same as the MCP's,
  through the same `call_tool` — there is no second rule to diverge.
- **Workflow text is data, not instruction.** Workflow names, Drive file names and error
  messages are written by people in the workspace, and in a shared workspace that includes third parties. The
  MCP already wraps them in `untrusted_data`, and the assistant's system prompt says out loud that those
  are not to be obeyed.
- **Execution is real.** `run_workflow` triggers nodes that write to databases and publish maps. The assistant
  asks for approval in text and only executes on the following turn.
- **The call's argument does not go whole into the SSE.** The `ferramenta` frame carries keys and
  sizes; the workflow definition and the text of whoever is using it stay out, because the stream is someone's
  log at some point.

## Known limits

- **A long session ends.** At the round ceiling the conversation ends with a notice, instead of continuing
  to spend. Context compaction is recorded as the next step.
- **Without Redis the conversation has no memory**: each message starts from scratch, and the quota degrades open.
  It is the same policy as the rest of the platform — the API does not even start without Redis, so this is an incident of
  seconds, not an operating mode.
- **Raster remains outside** the workflow engine, and the guide tells the model so.
- **The conversation lock (Redis, 300 s) is renewed** while the turn runs, so that it does not expire in the middle of
  a long conversation and let a second tab into the same transcript; and the daily quota key
  gets its expiry in the same transaction as the `INCRBY` (`contar_na_janela`, in `app/core/redis.py`), so that the
  ceiling never becomes immortal and locks the assistant forever — the same counter as the MCP quotas and the
  WebSocket rate limit.
