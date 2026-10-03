# Projects (workflow listing) — redesign

Date: 2026-09-07. State: implemented and integrated into the codebase (exception: the
"Precisa de atenção" (Needs attention) strip in §3.7 was never built — see the note there).
Approved example: the "Projetos, nova versão" (Projects, new version) mockup (desktop 1440, phone 390,
dark and light themes).

The `/projects` route ("Projetos" (Projects) in the sidebar) is the active workspace's bookshelf. It
now answers, in this order: **which workflow do I want?** (find it and open it in one
click) · **what is it?** (trigger, schedule, portal, sub-workflow) · **how is
it doing?** (last run, failure, running) · **what needs
attention?**

This document is the contract between backend and web. What is here is what both
sides implement; what is not here does not go into this round.

## 1. Decisions

| Decision | Reason |
|---|---|
| One primary action in the header: **Criar workflow** (Create workflow). "Novo grupo" (New group) becomes outline; "Atualizar" (Refresh) becomes ghost | Today there are three buttons of the same weight; creating a group happens once a month |
| ~~**Precisa de atenção** (Needs attention) strip~~ (NOT IMPLEMENTED — see §3.7): only when there is something: failed on the last run · schedule paused · has not run yet | Nothing on the screen says that the 6 a.m. scheduled one failed |
| Search + chips with counts (Ativos, Inativos, Em execução, Com falha, Agendados, Webhook, Sub-fluxos, Com portal, Assistente — Active, Inactive, Running, Failed, Scheduled, Webhook, Sub-workflows, With portal, Assistant) + sorting, all in the URL | The status filter lives in a dropdown; F5 resets everything; search does not find groups |
| Each row says **what it is** (trigger icon, metadata) and **how it is doing** (last run with status, when, summarized error; running for X) | An 8px dot is the only reading of state |
| The Ativado/Inativo (Enabled/Inactive) toggle leaves the card: **Ativar** (Activate) is one click away (icon only on the inactive row); **Desativar…** (Deactivate…) goes to the menu, with a confirmation that says what it pauses | A risky action in the most visible spot, with no confirmation |
| The grid goes away; a single list remains | It only changed the number of columns and cut off the name |
| Groups as sections: correct count ("3 workflows · 2 ativos"), description in the header, "vazio" (empty) instead of "(0 workflows)", "Recolher todos" (Collapse all); **Sem grupo** (No group) becomes a section with a title | "(0 workflows)"; the API counts only active ones; the loose ones appear without a title |
| The last run comes from `GET /observability/metrics/workflows` (30-day window set by the web — the endpoint accepts `days` and defaults to 90 —, 45 s cache), in parallel with the listing; if it fails, the list comes out without the column and a discreet notice offers to try again | It already exists, with scope, error summary and tests; a "lifetime last run" in the listing would be a scan without a window |
| Trigger and schedule go into the **listing** (`WorkflowListItem`): four booleans via the same mechanism as the Sub-fluxo (Sub-workflow) badge, and a schedule summary via one extra batched query | They are the nature of the workflow, not execution; cost ~zero |
| The name of whoever changed/created it goes into the listing (`updated_by_username`, `created_by_username`) | Shared workspace: "alterado há 2 d por maria" (changed 2 d ago by maria) |
| What stays: editor prefetch on hover, collapsed groups per workspace in `localStorage`, dragging by the handle (workflow and group), confirmations that state the consequence, toasts with the name, lean listing (parameter schema fetched on click) | Decisions documented in the code |
| No database migration | Everything comes from expressions and queries over what already exists |

## 2. API

### 2.1 `GET /workflows?workspace_id=` — `WorkflowListItem` (additive)

New fields, all with defaults; no existing consumer breaks
(`ActiveRunsContext`, `command-palette`, `sub-workflow-helper` read only
`id_hash`/`name`/`description`).

```python
# Triggers — same mechanism as has_publish_map/is_subworkflow (`_has_node`,
# LIKE over definition->>'nodes', which the query already parses). Known and
# accepted substring collisions (documented in the CRUD).
has_webhook_trigger:  bool = False   # _has_node("WebhookTrigger",  "has_webhook_trigger")
has_schedule_trigger: bool = False   # _has_node("ScheduleTrigger", "has_schedule_trigger")
has_file_trigger:     bool = False   # _has_node("FileTrigger",     "has_file_trigger")
has_geofence_trigger: bool = False   # _has_node("GeofenceTrigger", "has_geofence_trigger")
# "Manual only" = none of the four and not a sub-workflow — derived on the web.

# Schedule — one extra query, batched, merged in Python:
#   SELECT workflow_hash, active, next_run_at, last_run_at, strategy,
#          cron_expression, interval, unit, rrule_expression, timezone
#     FROM schedules WHERE workflow_hash IN (<hashes da página>)
# If there is more than one row per workflow: the active one with the lowest next_run_at;
# with no active one, any of them. `next_run_at`/`last_run_at` are stored as naive UTC
# (see `_to_utc_naive` in the scheduler): normalize with tzinfo=UTC BEFORE
# returning, otherwise Pydantic serializes without an offset and the web reads it as local time.
schedule: Optional[WorkflowScheduleSummary] = None

class WorkflowScheduleSummary(BaseModel):
    active: bool
    next_run_at: Optional[datetime]      # None = paused, or just created (the scheduler fills it in within ≤30 s)
    last_run_at: Optional[datetime]
    strategy: str                        # "cron" | "interval" | "rrule"
    cron_expression: Optional[str] = None
    interval: Optional[int] = None
    unit: Optional[str] = None
    rrule_expression: Optional[str] = None
    timezone: Optional[str] = None

# Authorship — one `users WHERE id_hash IN (...)` query (same pattern as
# `_nomes_de_usuarios` in observability/frota.py). An id with no row in `users`
# (there is no FK) → None; a user deleted by the admin (soft delete) keeps the name.
created_by_username: Optional[str] = None
updated_by_username: Optional[str] = None
```

Where: the four expressions go into `_METADATA_COLUMNS` (`app/crud/workflow_crud.py`);
the schedule and name merge lives in `WorkflowService.list_workflows_metadata`
and `list_workflows_metadata_by_ids` (`app/services/workflow_service.py`), which
now return dicts (the CRUD's `RowMapping` objects are immutable). The listing
goes from 1 to 3 queries, all indexed and batched — none per row.
`deleted_at` (always null) leaves the schema.

### 2.2 `GET /workflow-groups` — `WorkflowGroupRead`

`workflow_count` now counts **all** non-deleted workflows in the group
(`deleted_at IS NULL`); a new `active_count` field counts those with `flag_ative`.
A single aggregation (`count(*)` + `count(*) FILTER (WHERE flag_ative)`, or
`sum(case …)` so it also works in SQLite). Fix it in the router's four places
(`create_group`, `list_groups`, `get_group`, `update_group`).

### 2.3 Reused, unchanged

- `GET /observability/metrics/workflows?workspace_id=X&days=30[&force=1]` →
  `IWorkflowMetricsRow` per workflow: `last_run_at`, `last_status`, `last_error`,
  `last_error_category`, `total_runs`, `success_runs`, `failed_runs`,
  `running_runs`, `success_rate`, `p50_seconds`. Always with `workspace_id`. The
  30 days (`days=30`) are the web's choice (`WINDOW_IN_DAYS` in `como-anda.ts`); the
  endpoint itself accepts any `days` and defaults to 90.
- `GET /observability/runs?status=running&limit=200` (already consumed by
  `ActiveRunsContext`): the context now also stores `started_at`,
  `trigger_source` and `executor_name` for each live run.
- `POST /workflows/{id}/execute`, `PUT /workflows/{id}/status`, groups, move,
  duplicate, delete, portal: as today.

## 3. Web

### 3.1 Page structure (top to bottom)

```
Projetos                                                  [Atualizar]  [Novo grupo] [+ Criar workflow]
10 workflows em 3 grupos · 8 ativos · 4 agendados · 2 com portal

[🔍 Buscar workflow ou grupo…]  [Ordenar: Nome ▾]  [Recolher todos]
(Todos 10) (Ativos 8) (Inativos 2) | (Em execução 1) (Com falha 2) (Agendados 4) (Webhook 1) (Sub-fluxos 1) (Com portal 2)

┌ ⋮⋮ ▾ Hidrologia  3 workflows · 3 ativos  Rotinas diárias da bacia                                  ⋯ ┐
│  ⋮⋮ [⏱]  Consolidação de outorgas                         ● Concluída há 3 h              [▶] [⋯]   │
│          Une as outorgas da ANA e do IGAM…                61 execuções em 30 d · 3 falhas · mediana 3 min │
│          Agendado todo dia às 06:00 · próxima amanhã, 06:00 · alterado há 2 d por maria                    │
│  …                                                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ ⋮⋮ ▸ Entregas de campo  2 workflows · 1 ativo  (collapsed)                                            ⋯ ┐
┌ ⋮⋮ ▾ Rascunhos  vazio                                                                                ⋯ ┐
│     Nenhum workflow aqui. Arraste um para cá ou use "Mover para grupo" no menu do workflow.              │
SEM GROUP  4 workflows · 3 ativos
   [Ta] Recorte por município  (Sub-fluxo)                    ● Concluída há 15 min          [▶ dimmed]  [⋯]
   …
```

Phone (390px): stacked header (the primary button takes the whole line, a "⋯" menu
with Novo grupo (New group) and Atualizar (Refresh)); search at full
width; chips scroll horizontally; groups and rows in a single column; the row
shows the icon, name + badges, metadata (trigger/schedule), how it is doing, and the
two buttons (40px) on the right; the description disappears; the drag handle disappears
(move via the menu).

### 3.2 Modules (`web/app/components/projects/`)

| File | Responsibility |
|---|---|
| `index.tsx` | Orchestrates: data, URL, DnD, dialogs, composition of the sections. No pure logic. |
| `projetos-url.ts` / `use-projetos-url.ts` | State in the URL (§3.6). Same pattern as `observability/historico-url.ts` + `use-historico-url.ts`. |
| `use-projetos-dados.ts` | Three calls in parallel (§3.3), partial failure, `atualizadoEm`, periodic refresh of the metrics. |
| `gatilho.ts` | Derives the trigger and the schedule summary (§3.4). Pure. |
| `como-anda.ts` / `como-anda-celula.tsx` | Derives and renders the "how it is doing" column (§3.5). The component has its own name because Next's webpack resolves `.tsx` before `.ts` and tsc does the opposite. |
| `filtros.ts` / `filtros-barra.tsx` | Predicates and counts for the chips; search; sorting; bar (§3.6). |
| `cabecalho.tsx` | Title, subtitle with counts, Atualizar, Novo grupo, Criar workflow. (There is no "atualizado há X" (updated X ago) freshness in the Projects header — only in Histórico (History).) |
| `grupo-secao.tsx` | Group header, body, empty, drag targets (§3.8). |
| `linha-workflow.tsx` | The row (§3.9). Replaces `workflow-card.tsx` (which is removed). |
| `confirmar-desativar.tsx` | Deactivation confirmation dialog (§3.9). |
| `estados.tsx` | Skeleton, first-use empty state, no results, metrics-unavailable notice (§3.10). |
| kept | `dialog-content/*`, `grupos-colapsados.ts`, `ordem-dos-grupos.ts`, `selo-subfluxo.tsx` |

Formatters reused from `web/lib/formatos.ts`: `formatarInicio`
("há 3 h" / "hoje, 18:00" / "ontem" / "4 set, 03:00" — "3 h ago" / "today, 18:00" / "yesterday" / "Sep 4, 03:00"), `formatarDuracao`,
`originLabel`, `formatInteger`, `plural`. Status
label via `shared/status-rotulos.ts` (`rotuloDoStatus`).

### 3.3 Data (`use-projetos-dados.ts`)

```ts
interface ProjectsData {
  workflows: IWorkflow[]            // GET /workflows?workspace_id
  grupos: IWorkflowGroup[]          // GET /workflow-groups?workspace_id
  metricas: Map<string, IWorkflowMetricsRow> | null   // by workflow_hash; null = unavailable
  carregando: boolean               // first load (skeleton)
  atualizando: boolean              // subsequent reloads (button spins, list stays)
  erro: string | null               // listing or groups failed (error state with "Tentar de novo")
  metricasIndisponiveis: boolean    // only the metrics failed (discreet notice)
  atualizadoEm: number | null       // stamp of the last accepted response
  recarregar: (opcoes?: { force?: boolean }) => void
  // local (optimistic) mutations, used by the index: setWorkflows/setGroups or equivalents
}
```

- The three calls go out together (`Promise.allSettled`); listing and groups are
  mandatory, metrics are not. `days=30`, always with `workspace_id`.
- Reloads when switching workspace (waiting for `workspaceLoading`). "Atualizar" (Refresh)
  calls with `force: true` (bypasses the metrics cache).
- Metrics refresh on their own every 60 s while the tab is visible (only the metrics
  call; the listing does not change on its own). A sequence stamp discards a
  late response, as in `use-historico-dados.ts`.
- `ActiveRunsContext` (`runningRuns`) takes precedence over `metricas` for
  "running" — it is fresher (10 s).

### 3.4 Trigger (`gatilho.ts`)

```ts
type TriggerKind = "agendado" | "webhook" | "arquivo" | "geofence" | "manual" | "subfluxo"
interface Gatilho {
  tipo: TriggerKind              // the main one, in this precedence: subfluxo > agendado > webhook > arquivo > geofence > manual
  rotulo: string                   // "Agendado" | "Webhook" | "Por arquivo" | "Por geofence" | "Só manual" | "Chamado por outros workflows"
  extras: TriggerKind[]          // other triggers present (e.g. agendado + webhook) — the label becomes "Agendado + webhook"
}
function derivarGatilho(wf: Pick<IWorkflow, "is_subworkflow" | "has_schedule_trigger" | "has_webhook_trigger" | "has_file_trigger" | "has_geofence_trigger">): Gatilho

interface ScheduleSummary {
  estado: "ativo" | "pausado" | "calculando"   // pausado = schedule.active false; calculando = active without next_run_at
  descricao: string                            // "todo dia às 06:00" · "a cada 6 h" · "a cada 15 min" · "dia 1 às 08:00" · "seg–sex às 07:30" · "aos domingos às 02:00" · raw cron when not recognized · "recorrência (RRULE)"
  descricaoCrua: boolean                       // descricao is the untranslated cron expression — the component shows it in `code`
  proxima: string | null                       // formatarInicio(next_run_at) → "hoje, 18:00" / "amanhã, 06:00" / "1 out, 08:00"; null when pausado/calculando
  motivoPausa: "workflow inativo" | null       // when paused and the workflow is inactive
}
function resumirAgendamento(schedule: IWorkflowSchedule | null | undefined, flagActive: boolean, agora?: Date): ScheduleSummary | null
```

Recognized cron (5 fields): `M H * * *` → "todo dia às HH:MM" (every day at HH:MM); `M H * * 1-5` →
"seg–sex às HH:MM" (Mon–Fri at HH:MM); `M H * * D` (one day) → "às segundas às HH:MM" (on Mondays at HH:MM) etc.;
`M H D * *` → "dia D às HH:MM" (day D at HH:MM); `0 */N * * *` → "a cada N h" (every N h) (`0 * * * *` → "a
cada 1 h"); `*/N * * * *` → "a cada N min" (every N min) (`* * * * *` → "a cada 1 min").
Anything else: the raw cron in `code`. Interval:
`interval`+`unit` → "a cada 15 min" / "a cada 6 h" / "a cada 2 dias".
The time is the cron's, in the schedule's time zone (`timezone`), without converting — it is what
the user wrote. `proxima` uses the browser's local clock (it is an instant).
Trigger badge/tile on the row: scheduled = clock, webhook = lightning bolt, file =
file, geofence = pin, manual = play, sub-workflow = `TbSubtask` icon in
indigo (same color as `SeloSubFluxo`).

### 3.5 How it is doing (`como-anda.ts`)

```ts
type HowItsGoing =
  | { tipo: "executando"; desde: string; instante: number; origem: string | null; executor: string | null; tipica: number | null }
  | { tipo: "concluida" | "falhou" | "cancelada"; quando: string; instante: number; erro: string | null; total: number; falhas: number; mediana: number | null }
  // `instante` (ms) is the stamp used to sort by "last run" (§3.6).
  | { tipo: "sem-execucoes" }        // no metrics row in the window, or last_run_at null, and the workflow is more than 30 days old
  | { tipo: "nunca" }                // total_runs 0 and created less than 30 days ago → "Ainda não executou · execute uma vez para validar"
  | { tipo: "indisponivel" }         // metrics failed
function derivarComoAnda(wf: IWorkflow, metrica: IWorkflowMetricsRow | undefined, emExecucao: RunningRun | undefined, metricasIndisponiveis: boolean, agora?: Date): HowItsGoing
```

Rendering (`como-anda-celula.tsx`), two lines:
- executando (running): `● Em execução há 4 min` (blue, dot with `motion-safe:animate-ping`) · `agendada · em geo-01 · costuma levar 7 min`
- concluida (completed): `● Concluída há 3 h` (green) · `61 execuções em 30 d · 3 falhas · mediana 3 min` (omits "· 0 falhas" → "nenhuma falha" (no failures); omits a null median)
- falhou (failed): `● Falhou há 40 min` (red) · summarized error in red, truncated, `title` with the full text
- cancelada (canceled): `● Cancelada há X` (gray) · same second line as completed
- sem-execucoes (no runs): `○ Sem execuções em 30 dias` (gray)
- nunca (never): `○ Ainda não executou` · `execute uma vez para validar`
- indisponivel (unavailable): `— Sem dados de execução` (gray), no second line

A sub-workflow run by another workflow: the origin comes in `trigger_source` only for the live
run; for the last run there is no cheap "via X" — the second line is the
normal count. (The mockup showed "via «Mapa de risco»"; it stays out.)

### 3.6 Search, filters, sorting, URL (`projetos-url.ts`, `filtros.ts`)

```ts
type Filtro = "todos" | "ativos" | "inativos" | "executando" | "falha" | "agendados" | "webhook" | "subfluxos" | "portal" | "pausado" | "nunca"
type Ordem = "nome" | "execucao" | "alterado"
interface ProjectsState { q: string; filtro: Filtro; ordem: Ordem }
const DEFAULT_STATE = { q: "", filtro: "todos", ordem: "nome" }
// URL: ?q=&filtro=&ordem=  (omitted when equal to the default) — replace, not push, as in Histórico
```

- Chips (with counts over the whole list, not the filtered one): Todos · Ativos ·
  Inativos | Em execução · Com falha · Agendados · Webhook · Sub-fluxos · Com
  portal | Assistente (All · Active · Inactive | Running · Failed · Scheduled · Webhook ·
  Sub-workflows · With portal | Assistant). The last one sits after the second separator and carries the
  badge's sparkle: it is the only one that filters by WHO CREATED the workflow, not by a
  property of it. `pausado` and `nunca` exist only in the URL (they would arrive through the attention strip
  of §3.7, not implemented; today they are reachable only via the query string); when
  active, the "Todos" chip is unselected and "Limpar filtros" (Clear filters) appears.
- Predicates: ativos = `flag_ative`; executando = in `runningHashes`; falha =
  `comoAnda.tipo === "falhou"`; agendados = `has_schedule_trigger`; webhook =
  `has_webhook_trigger`; subfluxos = `is_subworkflow`; portal =
  `has_publish_map && portal_access !== "disabled"`; assistente =
  `origem === "assistente"`; pausado =
  `schedule && !schedule.active`; nunca = `comoAnda.tipo === "nunca"`.
- Search (`q`, accent- and case-insensitive — normalize with `normalize("NFD")`):
  name, description and **group name** (a group whose name matches shows all of
  its workflows). `useDeferredValue` as today.
- Sorting: name (`localeCompare` pt-BR) · execution (most recent last run
  first; no run last) · changed (`updated_at` desc).
  The order applies within each group and in the Sem grupo (No group) section; the order of the groups is
  the `position` (drag), as today.
- With a search or filter active, groups with no matching row do not
  appear; with neither search nor filter, all appear (including empty ones).
- Count in the header subtitle: always from the whole list.

### 3.7 Needs attention — NOT IMPLEMENTED (future)

> **State:** this strip was NOT built on the Projects screen. The
> modules `atencao.ts` / `atencao-faixa.tsx` do not exist under `web/app/components/projects/`,
> and the `index` renders no strip at all between the header and the filter bar.
> The `pausado` and `nunca` filters exist in the URL (`projetos-url.ts`) and the bar
> shows a provisional chip for them (`filtros-barra.tsx`), but **nothing in the UI
> triggers them** — they are only reachable by typing the query string by hand. Today the concept
> lives only on the Histórico (History) screen (`observability/atencao.ts` + `atencao-lista.tsx`,
> `montarAtencao`). The design below is the target, should the strip ever be ported.

```ts
interface AttentionItem { chave: "falha" | "pausado" | "nunca"; n: number; texto: string; filtro: Filtro }
function montarAtencao(workflows, comoAndaPorHash, resumoPorHash): AttentionItem[]  // only items with n > 0; order: falha, pausado, nunca
```

Copy: "2 falharam na última execução" (2 failed on the last run) · "1 agendamento pausado" (1 schedule paused) · "1 ainda
não executou" (1 has not run yet). The strip would be a `<section aria-labelledby>`; each item a button
that applies the filter (`aria-pressed` when it is the active filter); on the right, a link
"Ver no Histórico" (See in History) → `/observability?visao=workflows&workspace=<id>`. With no
items, the strip is not rendered. Paused because the workflow is inactive counts as
paused (it is what the person sees: it will not run).

### 3.8 Groups (`grupo-secao.tsx`)

- Header: handle (only `canEdit` and more than one group; `title="Arraste para
  reordenar os grupos"`), collapse button (`aria-expanded`, chevron), name,
  count "3 workflows · 2 ativos" (or "vazio"; singular "1 workflow · 1
  ativo"), description (truncated, disappears on the phone), ⋯ menu (`canEdit`): Renomear
  grupo (Rename group) · Excluir grupo (Delete group) (same confirmation as today, with the count).
- Header count: from the group's whole list (not the filtered one); with a
  filter active, it appends "· N com este filtro" (· N with this filter) when N < total.
- Body: rows with a 6px `gap`; empty: "Nenhum workflow aqui. Arraste um para
  cá ou use «Mover para grupo» no menu do workflow." (No workflow here. Drag one here or use
  "Move to group" in the workflow's menu.) (`canEdit`) / "Nenhum
  workflow neste grupo." (No workflow in this group.) (others).
- Drag: same targets and states as today (receiving a workflow: primary border and
  "Solte para mover «X» para <grupo>" (Drop to move "X" to <group>); reordering a group: dashed and "Soltar
  aqui move o grupo para esta posição" (Dropping here moves the group to this position); the dragged one at 40%). The "Solte aqui
  para remover do grupo" (Drop here to remove from the group) zone appears when dragging a grouped workflow, as today.
- "Recolher todos" / "Expandir todos" (Collapse all / Expand all) in the filter bar (appears only with
  groups); persists per workspace through the `grupos-colapsados.ts` mechanism.
- **Sem grupo** (No group) section: uppercase title (eyebrow) + "4 workflows · 3
  ativos"; it only exists when there is at least one group. With no groups, the list comes out without a
  title, and the "Agrupar workflows" (Group workflows) invitation (dashed) keeps appearing with
  more than two workflows, as today; so does the handle hint on the first group.

### 3.9 Workflow row (`linha-workflow.tsx`)

Desktop grid: `[alça 14px] [tile 34px] [principal 1fr] [como anda 260px] [ações]`;
minimum height 56px; `border bg-card rounded-lg shadow-xs`; hover `bg-accent/40`.

- **Handle**: only with groups (`hasDnd`), `cursor-grab`, disappears on the phone.
- **Tile** (34px, `rounded-lg bg-muted text-muted-foreground`; indigo for a
  sub-workflow): trigger icon; a 10px dot in the bottom-right corner with a
  border in the card's color: green active · gray inactive · blue with `animate-ping`
  when running. `title` with the trigger label.
- **Main**: line 1 = name (`<button>` `text-sm font-medium truncate`,
  opens the editor, `aria-label="Abrir <nome> no editor"`) + badges (`Sub-fluxo`
  indigo; `Portal público` / `Portal privado` teal with a globe/padlock icon
  when `has_publish_map && portal_access !== "disabled"`; `Inativo` gray;
  `Novo` primary when created less than 24 h ago); line 2 = description
  (`text-xs text-muted-foreground truncate`, only when it exists; disappears on the
  phone); line 3 = metadata (`text-xs text-muted-foreground`, separated
  by "·"): trigger label in `font-medium text-foreground`, schedule description
  and "próxima <quando>" (next <when>) (or "Agendamento pausado (workflow inativo)" (Schedule paused (workflow inactive))
  in amber, or "próxima: calculando…" (next: calculating…)), "alterado há X por <username>" (changed X ago by <username>) (or
  "criado há X por Y" (created X ago by Y) when `created_at === updated_at`; no name → just "alterado há X").
- **How it is doing**: §3.5. On the phone it goes below the main block.
- **Actions** (`onClick` with `stopPropagation`): **Executar** (Run) button (`aria-label="Executar <nome> agora"`,
  play icon, border; `canExecute`; disabled while preparing/triggering; on a
  sub-workflow it sits at 45% with the `title` "Sub-fluxo: executar sozinho normalmente não
  faz o esperado" (Sub-workflow: running it on its own usually does not do what you expect), but stays clickable); on a **running** row the button
  becomes "Ver execução" (See run) (history icon → `/observability?execucao=<run_id>`);
  on an **inactive** row (`canEdit`) the Executar slot is **Ativar** (Activate) (toggle
  icon, `aria-label="Ativar <nome>"`, no confirmation, toast "«X» ativado" (X activated));
  ⋯ menu (`aria-label="Mais ações de <nome>"`).
- **Clicking the row** opens the editor (like today's card); the name button is the
  keyboard target; the row has no `role`.
- **Prefetch** of the editor on `onPointerEnter` (as today).
- **Menu** (fixed order; items gated as today): Abrir no editor (Open in editor) · Ver
  execuções (See runs) (→ `/observability?workflow=<id>`) · Duplicar (Duplicate) (`canEdit`) ·
  Configurar (Configure) (`canEdit`) · Configurar portal (Configure portal) (`canEdit && has_publish_map`) ·
  — · Mover para grupo ▸ (Move to group) (`canEdit`, groups ≠ the current one) · Remover do grupo (Remove from group)
  (`canEdit && group_id`) · Mover para workspace (Move to workspace) (`canManage && podeMover &&
  workspace_id`) · — · Desativar… / Ativar (Deactivate… / Activate) (`canEdit`) · Excluir… (Delete…) (`canEdit`,
  red).
- **Desativar…** (Deactivate…) opens `confirmar-desativar.tsx`: title "Desativar «X»?";
  text "O agendamento e o webhook deixam de disparar até você ativar de novo.
  Execuções em andamento continuam." (The schedule and the webhook stop triggering until you activate it again. Runs in progress continue.) (when it has neither a schedule nor a webhook:
  "Ele some dos gatilhos e não pode ser executado até você ativar de novo." (It disappears from the triggers and cannot be run until you activate it again.));
  buttons Cancelar / Desativar (Cancel / Deactivate). Success: toast "«X» desativado" (X deactivated). Optimistic
  update with rollback, like today's `handleChangeActive`.
- `React.memo` with stable callbacks, like today's card (the reason is
  documented there; preserve it).

### 3.10 States (`estados.tsx`)

- **Loading** (first load): skeleton with the real header and three
  56px row blocks inside a group outline + two loose rows.
  Subsequent reloads do not show the skeleton (the list stays, the button spins).
- **First-use empty state** (`workflows.length === 0 && grupos.length === 0`):
  icon, "Comece pelo primeiro workflow" (Start with your first workflow), paragraph "Um workflow encadeia nós de
  leitura, processamento e saída. Ele roda quando você manda, num horário, ou
  quando um webhook ou um arquivo chega." (A workflow chains reading, processing and output nodes. It runs when you tell it to, at a set time, or when a webhook or a file arrives.), three steps (Desenhe · Execute uma
  vez · Agende ou exponha — Draw · Run once · Schedule or expose), button "Criar o primeiro workflow" (Create the first workflow) (`canEdit`; without
  permission: "Peça a um editor do workspace para criar o primeiro workflow." (Ask a workspace editor to create the first workflow.)).
- **No results** (search/filter with no rows): "Nenhum workflow com «q»" /
  "Nenhum workflow com este filtro" / "Nenhum workflow com «q» e este filtro" (No workflow with "q" / with this filter / with "q" and this filter);
  when there are results without the filter: "Há N com «q» sem o filtro." (There are N with "q" without the filter.); button
  "Limpar filtros" (Clear filters).
- **Load error** (listing/groups): a block with "Não foi possível carregar os
  projetos" (Could not load the projects), the message, a "Tentar de novo" (Try again) button. A toast too, as today.
- **Metrics unavailable**: a one-line notice above the list, discreet
  amber: "Sem dados de execução agora — a lista continua completa. [Tentar
  de novo]" (No run data right now — the list is still complete. [Try again]); the rows show "— Sem dados de execução".
- **No permission**: a viewer sees everything without the handle, without Executar/Ativar, without the group
  menu and with the workflow menu reduced to "Abrir no editor" and "Ver execuções".

### 3.11 Accessibility and motion

- Chips: `<button aria-pressed>` inside `role="group" aria-label="Filtros"`.
- Attention strip (§3.7, not implemented): it would be a `<section aria-labelledby>` with button items.
- Group: collapse button with `aria-expanded` and `aria-controls` pointing to
  the body (stable `id` per `id_hash`).
- Row: no `role`; button on the name; action buttons with an `aria-label` that includes
  the name; icons `aria-hidden`.
- 40px targets on the phone (`max-md:h-10 max-md:w-10`, `max-md:h-10` on
  chips and fields).
- Animations under `motion-safe:`; the "running" ping likewise.
- Visible focus: `focus-visible:ring-[3px] focus-visible:ring-ring/50`.

### 3.12 Copy (pt-BR)

Header: "Projetos" · "{N} workflows em {G} grupos · {A} ativos · {S} agendados · {P} com portal" (omit parts that are zero; with no groups: "{N} workflows · …"; singular: "1 workflow") · "Atualizar" · "Novo grupo" · "Criar workflow". (No "atualizado há X" freshness — see §3.1.)
Strip (NOT IMPLEMENTED — see §3.7): "Precisa de atenção" · "{n} falharam na última execução" / "1 falhou na última execução" · "{n} agendamentos pausados" / "1 agendamento pausado" · "{n} ainda não executaram" / "1 ainda não executou" · "Ver no Histórico".
Bar: placeholder "Buscar workflow ou grupo…" · "Ordenar:" Nome / Última execução / Alterado · "Recolher todos" / "Expandir todos" · "Limpar filtros".
Chips: Todos · Ativos · Inativos · Em execução · Com falha · Agendados · Webhook · Sub-fluxos · Com portal.
Trigger: "Agendado" · "Webhook" · "Por arquivo" · "Por geofence" · "Só manual" · "Chamado por outros workflows" · "próxima {quando}" · "próxima: calculando…" · "Agendamento pausado" · "(workflow inativo)".
How it is doing: "Concluída" · "Falhou" · "Cancelada" · "Em execução" · "Sem execuções em 30 dias" · "Ainda não executou" · "execute uma vez para validar" · "Sem dados de execução" · "{n} execuções em 30 d" · "nenhuma falha" / "{n} falhas" · "mediana {duração}" · "costuma levar {duração}" · "em {executor}".
Actions: "Executar agora" · "Ver execução" · "Ativar" · "Mais ações" · menu as in §3.9 · toasts: `Workflow "X" iniciado!` (as today) · "«X» ativado" · "«X» desativado" · "Cópia criada: «Y»" (as today) · "Grupo excluído." (as today).
Groups: "{n} workflows · {a} ativos" · "vazio" · "Nenhum workflow aqui. Arraste um para cá ou use «Mover para grupo» no menu do workflow." · "Sem grupo" · "Solte para mover «X» para {grupo}" · "Soltar aqui move o grupo para esta posição" · "Solte aqui para remover do grupo".
States: §3.10.

## 4. Out of scope

Number of nodes; version; "called by N sub-workflows" (N² cost); configurable
period in Projects; a per-workspace schedules endpoint; a side summary
panel before the editor; changing the cadence of `ActiveRunsContext`;
new columns in `workflows`; pagination of the listing.

## 5. Tests

- API (`tests/integration/`, SQLite, modeled on `test_listagem_marca_subfluxo.py`):
  the four trigger booleans; merged `schedule` (active, paused, no
  `next_run_at`, more than one schedule, UTC `tzinfo` in the return value); user
  names (existing, deleted); `deleted_at` out of the payload; groups:
  `workflow_count` counts inactive ones and ignores deleted ones, `active_count`, in the
  four places.
- Web (`web/__tests__/components/projects/`): `gatilho` (precedence, recognized and raw
  cron, interval, paused, calculating); `como-anda` (each
  type, precedence of the live run, `nunca` × `sem-execucoes`); `filtros`
  (predicates, counts, accent-insensitive search and search by group, sortings);
  `projetos-url` (read/write, default omitted); `use-projetos-dados`
  (parallel, partial failure, sequence); `linha-workflow` (button on the name, Ativar
  on the inactive row, Ver execução on the running row, menu by permission, dimmed
  sub-workflow); `grupo-secao` (count, empty, aria-expanded); `estados`;
  `index` (composition: sections, Sem grupo, a chip filters, search by group,
  deactivating asks for confirmation and rolls back on error).
- E2E (Playwright, real seeded API): the fold at 1440 and 390 in both themes; chips
  filter and go into the URL; search by group; opening the editor via the name; Executar;
  Desativar with confirmation; Ativar; collapsing and persisting; dragging into a group;
  no console errors.
