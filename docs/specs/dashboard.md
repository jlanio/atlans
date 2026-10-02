# Dashboard (landing) — redesign

Date: 2026-09-07. Status: **partially implemented**. Built and in the code today: header (scope +
period), **Saúde** (Health) strip, **Precisa de atenção | Próximas execuções** (Needs attention | Upcoming runs), and the
**Resumo do período** (Period summary; indicators + chart). **NOT** built in this round
(see §4): "Atividade recente" (Recent activity), "Atalhos / Seus workspaces / Armazenamento" (Shortcuts / Your workspaces / Storage), the
`storage` fetch in the data hook, and the freshness stamp ("atualizado há X" — updated X ago)
in the header. Approved example: the "Dashboard, nova versão" (Dashboard, new version) mockup (desktop 1440,
phone 390, dark and light themes).

The `/dashboard` route is the overview for the **system administrator** — restricted to
admins for now (the middleware blocks non-admins, the same gate as `/admin/*`;
it disappears from the sidebar and the palette for everyone else). The post-login **landing** is now the
Home `/` (3D globe + assistant).
The Dashboard's own role: **orientation + triage + routing**, not analysis. It opens by answering
the NOW and goes down by operational priority: **is everything fine right now? → what needs
me? → what is going to run? → how did it go?** (the "where do I go in?" — shortcuts/routing —
was left for later; §4.)

Boundaries — golden rule: the Dashboard **summarizes and routes**; its sibling screens **detail and
edit**. It never has a filterable table, views or an embedded run panel; it never
lists/edits workflows (that is Projects); it never manages workspaces (that is Workspaces).
Reusing `indicadores`/`grafico-por-dia`/`atencao-lista` from History is reuse of the FAMILY,
without the interactive surface (no filters, no table, no views); the only thing inherited is the
**period selector** (7/30/90 days), in the header.

## 1. Decisions

| Decision | Reason |
|---|---|
| **Scope: ACTIVE workspace by default, with a "Todos os workspaces" (All workspaces) toggle** | Requested by the owner. The toggle switches the `workspace_id` of every call (default = `WorkspaceContext.current`; "all" = no `workspace_id`). |
| Scope state in the URL: `?escopo=todos` (default = active, omitted) | F5/back/link preserve the choice; mirrors the History pattern |
| In the "all" scope, every list item **states its workspace** (colored tag); in a single-workspace scope, the tag disappears (it is redundant) | What makes the global view readable without confusion |
| **Colored Health** strip at the top (green/amber/red) with a one-sentence verdict + the "now" line | Nothing on the screen said what was happening at the moment; the data (`now`) was already arriving and being discarded |
| **Precisa de atenção** (Needs attention: stuck runs, repeated failures, executor at its ceiling) that summarizes and deep-links to History/Executors | The backend computes `top_failing_workflows` and the screen ignored it |
| Scheduled **Próximas execuções** (Upcoming runs; forward-looking) — EXCLUSIVE to the Dashboard | No other screen answers "what is going to run" |
| **Period summary: 7 / 30 / 90 days (default 30), with a selector in the header** — the same group as History | Requested by the owner; the window governs the indicators, the chart and the attention failures, as in History |
| 4 indicators compared with the previous period + a 4-series chart — reuse of `observability/indicadores` and `grafico-por-dia` | Same family; without the History surface |
| Enriched recent activity: pt-BR status, **workspace · origin · when**, leads to the run panel — **not built in this round (§4)** | The current one had a raw date and no context |
| Real shortcuts (led by **"Abrir «workspace ativo»"** (Open "active workspace") + New workflow); a "Seus workspaces" (Your workspaces) list for routing; storage with a breakdown — **not built in this round (§4)** | "Duração média" (Average duration) leaves the shortcuts (becomes an indicator); storage without quota/trend (the endpoint does not have them) |
| Removed: `MetricCard`/`AnimatedNumber`, `RunsChart` (2 series), `framer-motion`, raw dates, `avg_duration_seconds` | The family abandoned them; inconsistencies and noise |
| No database migration; the only endpoint touched: `/workspaces/storage/my` gained an optional `workspace_id` (done in the backend, **never wired** on screen and later removed — §2.1, §4) | Storage consistency with the scope |

## 2. API

### 2.1 `GET /workspaces/storage/my` — optional `workspace_id` (done, later removed)

> The route and the web's `getMyStorageUsage` were removed without ever having been called. They stay here
> as a record of the rule, for when the Storage block (§4) is built.

New query param `workspace_id?: str`. Without it: sums all of the user's workspaces
(the usual behavior — "all" scope). With it: only that workspace, **validated
by membership** (`workspace_id not in workspace_ids` → 403). Unlike
`/observability/metrics`, this endpoint does not receive the `user` object, so it applies the
rule to everyone equally, **without the admin bypass** that metrics has (§2.2) — in
practice the two only diverge for a platform admin, and the Dashboard never sends a
`workspace_id` outside the user's access (the active scope always uses `current.id_hash`). Web:
`GisFlowService.getMyStorageUsage(workspaceId?)` (the method existed; **the Dashboard never
called it** — §4).

### 2.2 Reused, unchanged — all of them already accept `workspace_id`

- `GET /observability/metrics?days=30[&workspace_id=&force=]` → `IObservabilityMetrics`.
  The `run_f` of `_resolver_escopo` filters `WorkflowRun`, so in the `now` block only
  `running`/`pending`/`stuck` respect the scope. `now.executors`, `queued_on_executors`
  and `overdue_acks` reflect the **user's accessible fleet** (default pool + the user's
  workspaces + assigned ones), global by design — dispatch draws from that same fleet, so
  it is relevant even when scoped; the per-workspace fleet is left for v2 (§4). A `workspace_id`
  outside the user's access → 403 (the platform admin has a bypass: sees any `workspace_id`,
  including a nonexistent one → zeros).
- `GET /observability/runs-by-day?days=30[&workspace_id=&tz=]` → chart (4 series).
- `GET /observability/runs?limit=6[&workspace_id=]` → today it only feeds the detection of the
  "first-use empty state" (§3.10); the "Atividade recente" list was not built (§4).
  `IRunSummary` already includes `workspace_name` and `trigger_source`.
- `GET /observability/metrics/executores?days=30[&workspace_id=&force=]` → the
  "executor at its ceiling" attention item (optional; failure → no such item).
- `GET /workflows[?workspace_id=]` → "Próximas execuções" (uses `schedule` +
  `has_*_trigger` from the listing, already delivered in the Projects PR).

**Window = 7 / 30 / 90 days (default 30)**, chosen in the header (`?periodo=`, reusing
`Periodo`/`PERIODOS` from History), in `metrics`, `runs-by-day` and `metrics/executores`.
The instant (`now`) is not a window: a separate 30 s poll, always on the current window.

## 3. Web

### 3.1 Structure (top to bottom) — what exists today

```
Dashboard              [↻ Atualizar]  [«Bacia do Rio Doce» ▾]  [7 · 30 · 90 dias]
«Bacia do Rio Doce» · 8 workflows ativos   (scope toggle → "Todos os workspaces"; period → ?periodo=)

┌ SAÚDE — agora ────────────────────────────────────────────────────────────────┐
│ (amber edge)  Precisa de você: 1 execução presa há 18 min e 2 workflows falhando │
│ ● 3 em andamento · 2 na fila │ ⏱ 1 presa há 18 min │ ● Executores 5 de 6 online  Ver em andamento →
└──────────────────────────────────────────────────────────────────────────────────┘
     (calm state → a thin green LINE, not a big card)

┌ Precisa de atenção ─────────────────┐  ┌ Próximas execuções ────────────┐
│ stuck → repeated failures → ceiling │  │ scheduled, by time              │
└─────────────────────────────────────┘  └─────────────────────────────────┘

┌ RESUMO DO PERÍODO · ÚLTIMOS N DIAS ────────────────────────── Ver no Histórico →┐
│ [Execuções] [Taxa de sucesso] [Duração típica] [Falhas]   (4 indicators)         │
│ ▂▃▅▇… daily chart (4 status series)                                               │
└────────────────────────────────────────────────────────────────────────────────┘
```

The Atenção|Próximas (Attention|Upcoming) region uses the `lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]` grid;
Saúde (Health) and Resumo (Summary) take the full width. Phone: one column, same order; the header
stacks (title; below it the toggle, the period and Atualizar (Refresh)); indicators 2×2; chart
`h-40`; targets ≥ 40 px. (The "Atividade recente" (Recent activity) and "Atalhos" (Shortcuts) regions of the original plan
were not built — §4.)

### 3.2 Modules (`web/app/components/dashboard/`)

| File | Responsibility |
|---|---|
| `index.tsx` | Orchestrates: scope, data, composition, routing of the actions. |
| `dashboard-url.ts` / `use-dashboard-url.ts` | Scope and period state in the URL (`?escopo=todos`, `?periodo=`; `Periodo`/`PERIODOS` reused from History). |
| `use-dashboard-dados.ts` | 5 scoped calls in parallel (§3.3), partial failure per section, 30 s health poll, sequencing. |
| `saude.ts` / `saude-hero.tsx` | Tone (pure) + colored strip with a verdict (§3.4). |
| `proximas.ts` / `proximas-lista.tsx` | Derives and lists the upcoming scheduled runs (§3.6). |
| `estados.tsx` | 1st-load skeleton, backbone error, first-use empty state and the amber per-section partial-failure notice (§3.10). |
| `cabecalho.tsx` | Title, subtitle with scope, scope toggle, period selector, Atualizar (§3.9). |
| reuse from History | `observability/indicadores.tsx`, `grafico-por-dia.tsx`, `atencao.ts`+`atencao-lista.tsx`; `ItensAgora` extracted from `agora-faixa.tsx` (named export, non-breaking) so Health can reuse the same line. |

`page.tsx` is a thin wrapper that renders `<DashboardView/>`.

### 3.3 Data (`use-dashboard-dados.ts`)

```ts
interface DadosDoDashboard {
  metrics: IObservabilityMetrics | null   // health + attention + indicators
  dias: IRunsByDay[]                       // chart
  runs: IRunSummary[]                      // only feeds the "first-use empty state" (§3.10)
  executores: IExecutorMetrics[]           // "executor at its ceiling" attention item (optional)
  workflows: IWorkflow[]                   // upcoming runs (with schedule)
  carregando: boolean                      // 1st load of the current scope (skeleton)
  atualizando: boolean
  falhas: { metrics: boolean; dias: boolean; runs: boolean; workflows: boolean }
  erroEspinha: string | null               // only when metrics fails on the 1st load (blocks the screen)
  atualizadoEm: number | null              // stamp of the last response; NOT displayed TODAY (§4)
  recarregar: (opts?: { force?: boolean }) => void
}
// null = "all" (no workspace_id); undefined = active scope still without an id (workspace
// loading) → does NOT fetch, keeps the skeleton; dias = 7/30/90
useDashboardDados(escopoWorkspaceId: string | null | undefined, dias: number)
```

- `escopoWorkspaceId` (resolved in `index`): `escopo === "todos" ? null`; in the active
  scope, `undefined` while the workspace list is loading (does not fetch), then
  `current?.id_hash`. The **five** calls go out together (`Promise.allSettled`) —
  `metrics`, `runs-by-day`, `runs`, `executores` and the `workflows` listing; only
  `metrics` is the backbone (it feeds health + attention + indicators) — if it fails on the 1st load,
  `erroEspinha` blocks; the others degrade per section (1-line amber notice,
  `falhas.*`). Never blank the screen. **There is no `storage` call.**
- `executores` is the only optional one that does **not** become a notice: failure → `[]` (attention only
  loses the "executor at its ceiling" item).
- Reloads when the scope changes AND when `current` changes while the scope is the active one. Does not
  reload when `current` changes while the scope is "all". It also reloads when
  the period changes — but that is a RELOAD (the button spins, the screen stays), not a skeleton: the
  skeleton is reserved for the 1st load of a scope, like the History selector.
- "Atualizar" (Refresh) → `force:true` (bypasses the metrics cache). 30 s poll of `metrics` only
  (visible tab), without turning on `carregando`/`atualizando`, with a sequence stamp (a stale
  response never overwrites a newer one; a forced one is not overwritten by a tick — same pattern as
  `use-projetos-dados`). `atualizadoEm` holds the last accepted response (but it is not
  displayed today — §4).
- NO `ActiveRunsContext` for the "now": it belongs to the active workspace and does not serve the
  "all" scope; the instant comes from `metrics.now`.

### 3.4 Health (pure `saude.ts` + `saude-hero.tsx`)

```ts
type TomDeSaude = "calmo" | "atencao" | "critico"
function tomDeSaude(now: INowBlock | null | undefined, temAtencao: boolean): TomDeSaude
// critical: now.stuck_count > 0  OR  (executors.total > 0 && executors.online === 0)
// attention: executors.online < executors.total  OR  overdue_acks > 0  OR there are attention items*
// calm: none of the above
// (* "there are attention items" is decided in index via montarAtencao; health receives, besides
//    `now`, the per-type count of the list (ResumoDaAtencao: falhas, saturado) so it can
//    say "2 workflows falhando" without reimplementing top_failing. Stuck runs are NOT in
//    the summary: they already have their own reason, and counting them again would duplicate the verdict.)
// The fleet (executors) that weighs on the tone is the one accessible to the user, not cut down by
// workspace (§2.2) — dispatch draws from it, so it counts even in a single-workspace scope.
function veredito(now, tom, resumo, semExecucoes?): string
// calm: "Tudo tranquilo — nada pedindo atenção agora." (or "…— nada rodando ainda."
//       when semExecucoes, §3.10);  otherwise: "Precisa de você: {1–2 motivos}."
```

- `saude-hero.tsx`: when **calm**, a thin green line (4px stripe + check icon + sentence
  + `ItensAgora`), like History's neutral `agora-faixa` — NOT a big green card.
  When **attention/critical**, the `rounded-xl` envelope gets a thick stripe (the
  `workspace-hero` pattern, no diffuse glow) + a two-part verdict. Reuses `ItensAgora` (extracted from
  `agora-faixa.tsx`). "Ver em andamento →" (See running) → `/observability?status=running` (with
  `&workspace=` when scoped). A stuck run is clickable → `/observability/run/{runId}`.
- Reason texts: "1 execução presa há 18 min" (1 run stuck for 18 min), "2 workflows falhando" (2 workflows failing), "1 executor
  no teto" (1 executor at its ceiling), "frota parcialmente offline: 5 de 6" (fleet partially offline: 5 of 6). It joins the 1–2 most severe.

### 3.5 Precisa de atenção (Needs attention) — reuse of `observability/atencao.ts` + `atencao-lista.tsx`

`montarAtencao({ metrics, executores })` already exists. `index` maps `AcaoDeAtencao`:
`abrir-execucao` → `/observability/run/{runId}`; `filtrar-workflow` →
`/observability?workflow={id}&status=failed` (the default view — runs — applies both
filters; the "workflows" view would ignore both and land on an unfiltered list);
`abrir-executor` → `/executores`. The deep links carry `&workspace={id}` when the dashboard
is scoped to a workspace. In the "all" scope, each item gets the workspace tag via the join
`workflow_hash → Workflow.id_hash → workspace_id → WorkspaceContext` (using the index of
`workflows` already fetched for the Próximas); if it does not resolve → the tag disappears, it never invents one.
Empty → green "Nada pendente. Última falha há X." (Nothing pending. Last failure X ago.; History's `textoDeVazio`).

### 3.6 Próximas execuções (Upcoming runs; pure `proximas.ts` + `proximas-lista.tsx`)

- `proximas(workflows, agora)`: filters `schedule?.active && flag_ative && next_run_at`
  in the future; sorts by `next_run_at` asc; cuts at 5. Each item: trigger icon +
  name + workspace ("all" scope) + `resumirAgendamento`/`formatarProxima`
  (from `projects/gatilho.ts`). Click → editor `/workflow/{id}` with prefetch.
- Empty → "Nenhuma execução agendada." (No scheduled runs.) Paused/never-run ones are NOT included.
- Contrast with the Home: the "Meu → Agendamentos" (My → Schedules) panel (`GET /me/schedules`) lists the
  person's schedules across ALL workspaces, active AND paused — the paused ones
  appear with the `motivoPausa` from `resumirAgendamento` (e.g. "workflow inativo" — inactive workflow) — and
  offers pause/activate and run now (with a click, by operator role). Here, on the
  Dashboard, "Próximas" is just a preview of the active ones.

### 3.7 Header + scope toggle (`cabecalho.tsx`)

- `h1` "Dashboard"; subtitle = scope + count: active scope → "«{nome}» · {N}
  workflows ativos"; "all" → "Todos os workspaces · {W} workspaces · {N} workflows
  ativos" (`N = metrics.active_workflows`). Skeleton while loading.
- **Scope toggle** (segmented, only with > 1 workspace): "«{workspace ativo}»" ↔
  "Todos os workspaces". Changes `?escopo=`. `aria-label="Escopo do painel"`.
- **Period selector** (segmented, 7/30/90 days, default 30): reuses `PERIODOS` from
  History and the same design. Changes `?periodo=`. `aria-label="Período"`, each button
  `aria-label="Últimos N dias"`. It governs the window of the indicators, the chart and the
  failures in "Precisa de atenção" (the "Saúde · agora" (Health · now) and the "Próximas" do not change).
- Atualizar (`ghost`, `TbRefresh` under `motion-safe:`). The freshness stamp
  "atualizado há X" is **NOT** displayed here: `atualizadoEm` exists in the hook but the header
  does not render it; `textoDeFrescor` is only used in History (§4).

### 3.8 States

- Loading (1st time for the scope): skeletons with the real height per block. Reloads do not
  show a skeleton.
- Backbone error (`metrics` failed on the 1st load): a "Não foi possível carregar o
  painel" (Could not load the dashboard) block + "Tentar de novo" (Try again). On a reload with data on screen, it keeps it + a notice.
- Partial failure: each section (chart/attention/upcoming) with a 1-line amber notice; the
  rest carries on.
- First-use empty state (0 workflows AND 0 recent runs AND 0 in the period): a
  centered "Nada rodou ainda" (Nothing has run yet) block + "Criar workflow" (Create workflow); the other blocks do not appear.
- No runs but with workflows: health "Tudo tranquilo — nada rodando ainda" (All quiet — nothing running yet);
  indicators "—"; chart "Sem execuções no período." (No runs in the period.); green attention; upcoming shows
  the scheduled ones.
- Changing the scope/`current` restarts the 1st load of that scope (skeleton).

### 3.9 Accessibility

Health and each section as `<section aria-labelledby>`; toggle with `aria-label`; attention/upcoming
items are buttons/links with a name; icons `aria-hidden`; targets ≥ 40 px
on the phone; motion under `motion-safe:`; focus `ring-[3px]`.

### 3.10 Copy (pt-BR) — only the strings that exist today

"Dashboard" · "«{nome}» · {N} workflows ativos" · "Todos os workspaces · {W} workspaces
· {N} workflows ativos" · "Escopo do painel" · "Todos os workspaces" · "Atualizar" ·
"Saúde · agora" · "Precisa de você: …" · "Tudo tranquilo — nada pedindo atenção agora." ·
"Tudo tranquilo — nada rodando ainda." · "N workflows falhando" · "N executores no
teto" · "em andamento" · "na fila" · "presa há X" · "Executores N de M online" · "Ver em
andamento" · "Precisa de atenção" · "Próximas execuções" · "Nenhuma execução agendada." ·
"Período" · "Últimos N dias" · "Resumo do período · últimos N dias" · "Ver no Histórico" ·
"Nada rodou ainda" · "Criar workflow".

## 4. Not implemented in this round / future

Described in the original plan but **not built** — not present in the code today:

- **Recent activity** (it was a block of its own): list of the 6 most recent runs
  (`getObservabilityRuns({limit:6})`) with a pt-BR `StatusBadge`, `workspace · origem ·
  quando` and duration, leading to `/observability/run/{id}`. There is no `atividade-lista.tsx`;
  the `runs` fetched today only feeds the detection of the "first-use empty state" (§3.8). Copy
  that would go with this block: "Atividade recente", "Nenhuma execução recente.".
- **Shortcuts + Your workspaces + Storage** (it was a block of its own): "Abrir
  «{workspace}»", "Novo workflow", shortcuts to Projects/History/Executors/Workspaces;
  the "Seus workspaces" list (routing with `setCurrent`); and the storage summary
  (`formatBytes` + Drive/Artifacts). There is no `atalhos.tsx`. Copy that would go with it:
  "Atalhos", "Abrir «{nome}»", "Novo workflow", "Seus workspaces", "Armazenamento".
- **Storage in the data hook**: the `storage: IStorageUsage | null` field and
  `falhas.storage`, and the `getMyStorageUsage(escopoWorkspaceId)` call. The endpoint and the
  service method did exist at one point (§2.1), but were never wired and were removed: building
  this block includes recreating them.
- **Freshness stamp in the header**: "atualizado há X". `atualizadoEm` is tracked in the
  hook but not displayed; `textoDeFrescor` is only rendered in History.

Out of scope (v2): a map of per-workspace health cards; per-workspace metrics
(would require an aggregate endpoint `GET /observability/metrics/by-workspace?days=N`); splitting
"running" by workspace; storage quota/trend.

## 5. Tests

- API: `tests/unit/test_storage_meu_por_workspace.py` (with/without `workspace_id`, 403 outside
  the scope, zeros with no workspaces) was removed together with the route (§2.1).
- Web (`web/__tests__/components/dashboard/`): `saude` (calm/attention/critical tone,
  verdict, reasons); `proximas` (filters future/active, sorts, cuts at 5, ignores
  paused); `dashboard-url` (read/write `escopo`, default omitted); `use-dashboard-dados`
  (scope switches workspace_id, partial failure per section, backbone blocks only on the 1st load,
  a forced fetch is not overwritten by a tick); `cabecalho` (subtitle per scope, toggle only with >1);
  `proximas-lista`/`saude-hero` (render, copy, aria); `index` (composition, toggle switches
  scope and goes to the URL, health reflects tone, attention routes, first-use empty state).
- E2E (Playwright, real API): default scope (active workspace) and "all" toggle; colored
  health; attention with deep link; upcoming; 30 d indicators; clean console; dark and
  light; 1440 and 390.
