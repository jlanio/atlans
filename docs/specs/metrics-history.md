# History (run metrics) — redesign

Date: 2026-09-06. Status: being implemented.

The `/observability` route ("Histórico" (History) in the sidebar) now answers four
questions, in this order: **is everything fine right now?** · **how did the period go?** ·
**what needs attention?** · **which run, exactly?**

This document is the contract between backend and web. What is here is what both
sides implement; what is not here does not go into this round.

## 1. Decisions

| Decision | Reason |
|---|---|
| Period (7/30/90 days) in the header, once, and every block obeys it | Today the selector lives in the chart and governs eight cards without saying so |
| Four indicators for the period, each compared with the previous period of the same length | Is 1,284 runs a lot or a little? Only the comparison answers that |
| Success rate = completed ÷ (completed + failed) | The current formula puts in-progress and cancelled runs in the denominator and drops at load peaks |
| Typical duration = median of the completed runs, with p95 beside it | The mean includes failures, scheduler zeros and orphans; one 40 min run among a hundred of 30 s becomes "54 s" |
| "Agora" (Now) strip: in progress, queued, stuck, executors online, overdue acknowledgments | Nothing on the screen says what is happening at this instant |
| "Precisa de atenção" (Needs attention): repeated failures (with the last error), stuck runs, executor at the ceiling | The backend computes `top_failing_workflows` and the screen discards it |
| Runs table in Portuguese, with the error on the row, tier (fallback/pool), source and a click that opens the run in a panel | Rows look clickable and open nothing; status in English; `error_message` and `dispatch_tier` arrive and do not show |
| Views of the same table: Execuções (Runs) · Por workflow (By workflow) · Por executor (By executor) · Confirmações (Acknowledgments) (admin) | The Workflows tab is a list of names; the Executors one repeats cards |
| Filters by workspace, workflow, executor, status, source and search, all in the URL | The page adds up every workspace and ignores the selector; F5 resets everything |
| Removed: Total de workflows, Workflows ativos, Execuções (24h), Execuções (7 dias), Duração média, the "Ativo" (Active) toggle per run row | Registration is not execution; three slices of the same counter; turning a workflow off is a workflow action, not a run action |
| Additive migration: `trigger_source`, `triggered_by`, `error_category` in `workflow_runs`; `schedule_id` written on normal dispatch | "Agendado às 03:00" (Scheduled at 03:00) and "manual · ana" change the diagnosis; today `schedule_id` is only written when the schedule fails |

## 2. Database

`workflow_runs` gets three nullable columns (migration `20260909_0001`, revision
`e1f4a2b7c935`, down `d9e3f1a5b624`; reversible):

| column | type | values |
|---|---|---|
| `trigger_source` | VARCHAR(16) | `manual` · `retry` · `webhook` · `schedule` · `mcp` (agent via the MCP server, `docs/specs/mcp-server.md`) |
| `triggered_by` | VARCHAR(36) | the user's `id_hash` (null for webhook and schedule) |
| `error_category` | VARCHAR(16) | the flow taxonomy (`user`, `validation`, `timeout`, `resource`, `transient`, `internal`) plus the server's: `no_executor` (dispatch without an executor), `executor_lost` (executor disconnected), `isolation` (isolation barrier), `dispatch` (exception during dispatch) |

Writing:

- `WorkflowService.start_analysis(..., triggered_by, trigger_source="manual", schedule_id=None)` passes them to `_dispatch_job`, which writes all three in the `INSERT` of the `pending` run.
- Callers: `POST /workflows/{id}/execute` → `manual`; `POST …/retry` → `retry`; webhook → `webhook`; scheduler → `schedule` + `schedule_id`. The scheduler's failure path (`_registrar_falha_agendada`) writes `schedule`, `schedule_id` and `error_category="no_executor"` (no executor available) or `"internal"` (any other failure of the scheduled dispatch — previously swallowed in the log).
- `error_category`: in the `job_result` (consumer) from `payload["error_category"]`; `executor_lost` on disconnection; `no_executor` on exhausted dispatch; `isolation` at the barrier; `dispatch` on the dispatch exception.

Runs from before the migration have everything null; the web shows "—".

## 3. API (`/observability`)

Common filters (optional). `workspace_id` applies to the five endpoints (`/metrics`, `/runs-by-day`, `/metrics/workflows`, `/metrics/executores` and `/runs`); `workflow_id` only to `/metrics`, `/runs-by-day` and `/runs` (the "by workflow" and "by executor" views take no per-workflow slice); `tz` only to `/runs-by-day`:

- `workspace_id`: for a regular user it must be among their workspaces (otherwise 403 `workspace_access_denied`); an admin filters any of them.
- `workflow_id` (only `/metrics`, `/runs-by-day`, `/runs`): must belong to an accessible workspace (otherwise 404).
- `tz` (only `/runs-by-day`): IANA name (e.g. `America/Sao_Paulo`) used to cut the day; default `UTC`; invalid → 422.

The scope stays as it is today (admin sees everything; a user sees the workspaces where they are owner or member). The 45 s Redis cache includes the filters in the key.

### 3.1 `GET /metrics?days=&workspace_id=&workflow_id=&force=`

Existing fields stay (`period_days`, `total_workflows`, `active_workflows`, `total_runs`, `failed_runs`, `avg_duration_seconds`, `runs_last_24h`, `runs_last_7d`, `runs_prev_7d`, `success_rate_prev_7d`, `by_status`, `top_failing_workflows`), with these changes:

- `success_rate` = `success / (success + failed)` in the window; `0.0` when the denominator is zero. `success_rate_prev_7d` follows the same formula.
- `by_status` gains `cancelled` and `pending`; `other` becomes only what is none of the five.
- `top_failing_workflows[]` now carries `workflow_name`, `total_runs`, `failure_rate` (failures ÷ the workflow's total in the window), `last_error` (text, up to 200 characters), `last_error_category`, `last_failed_at`. Top 5 by `failure_count`.

New fields:

```jsonc
{
  "success_runs": 1235, "cancelled_runs": 3, "running_runs": 3, "pending_runs": 1,
  "prev_period": {            // previous window of the same length (days..2*days ago)
    "total_runs": 1147, "success_runs": 1118, "failed_runs": 29, "success_rate": 0.975,
    "p50_seconds": 38.0
  },
  "duration": { "p50_seconds": 42.0, "p95_seconds": 190.0 },   // only success status with duration > 0; null without data
  "now": {                    // NO window: the instant of the query
    "running": 3, "pending": 1,
    "stuck_count": 1,
    "stuck": [{ "run_id": "…", "workflow_hash": "…", "workflow_name": "Cadastro rural · lote 7",
                "agent_host": "executor:…", "executor_name": "geo-02", "started_at": "…",
                "elapsed_seconds": 8040, "typical_seconds": 360 }],   // up to 5, oldest first
    "executors": { "online": 4, "total": 5 },                         // active executors in scope
    "queued_on_executors": 12,                                        // sum of capacity.queued of the online ones; null if none publishes
    "overdue_acks": 2                                                 // admin; null for everyone else
  }
}
```

"Stuck" = `status IN ('running','pending')` for longer than `max(3 × p50 do workflow nos últimos 90 dias, 900 s)` (3 × the workflow's p50 over the last 90 days, at least 900 s); without a p50, `3600 s`.

Executors in scope: admin → all with `status='active'`; user → the accessible ones (`get_user_accessible_agents`). `online` via presence in Redis.

### 3.2 `GET /runs-by-day?days=&workspace_id=&workflow_id=&tz=`

`{ "days": [ { "day": "2026-09-06", "total", "success", "failed", "running", "cancelled", "other" } ] }`

- Every day of the window, in order, with zeros where there was no run.
- Day computed in `tz` (`start_time AT TIME ZONE tz` in PostgreSQL; in SQLite, computed in Python).
- `running` = only `running` + `pending`; `cancelled` separate; `other` = the rest.

### 3.3 `GET /metrics/workflows?days=&workspace_id=&force=` (new)

```jsonc
{ "period_days": 30, "workflows": [ {
  "workflow_hash": "…", "workflow_name": "Integração SICAR", "workspace_id": "…", "workspace_name": "Cadastro",
  "active": true, "total_runs": 61, "success_runs": 33, "failed_runs": 28, "running_runs": 0,
  "success_rate": 0.54, "p50_seconds": 170.0, "last_run_at": "…", "last_status": "failed",
  "last_error": "Timeout ao consultar o WFS do SICAR (30 s)", "last_error_category": "timeout",
  "origem": "usuario"
} ] }
```

All accessible workflows (including those without runs in the window, with zeros); order: `total_runs` desc, name asc. 45 s cache.

`origem` is the WORKFLOW's origin (`workflows.origem`: `usuario` | `assistente` — who created it), not the trigger's. The "Por workflow" view uses this field for the assistant badge and for the filter chip, without a second call: the inventory comes in full and the slicing is local.

### 3.4 `GET /metrics/executores?days=&workspace_id=&force=`

Each item keeps `agent_host`, `display_name`, `total_runs`, `success_runs`, `failed_runs`, `success_rate`, `avg_duration_seconds`, `last_run_at` and gains:

`executor_id`, `executor_type` (`default`|`dedicated`), `is_default`, `status`, `online` (bool), `capacity` (`{running, queued, max_concurrent, max_queue}` or `null` when the executor does not publish), `p50_seconds`.

The row of runs without a host is no longer called "desconhecido" (unknown): `agent_host: null`, `display_name: "Sem executor"`, `unassigned: true` (they are dispatch failures). Online executors without runs in the window are included too (with zeros), so the view shows the whole fleet.

### 3.5 `GET /runs`

New filters: `workspace_id`, `trigger_source`, `tier` (`primary`|`fallback`|`pool`), `q` (`ILIKE` search in `error_message`, the workflow name and the run id). `date_from` already exists and the web now sends the start of the window.

`workflow_origem` (`usuario`|`assistente`) slices by the WORKFLOW's origin — the bar's "Assistente" (Assistant) chip. It is a different axis from `trigger_source` (the trigger) and combines with it: an assistant workflow run by hand matches `workflow_origem=assistente` and `trigger_source=manual`. Like `q`, it requires the join with `workflows`, so runs of permanently deleted workflows fall outside the slice (the slice is over live workflows); without the parameter, the listing still runs with no join at all.

Each run gains, for any user in scope: `workflow_name`, `workspace_id`, `workspace_name`, `executor_id`, `executor_name` (friendly name; `null` without a host), `trigger_source`, `triggered_by`, `triggered_by_username`, `error_category`, `schedule_id`, `workflow_origem` (`null` when the workflow was permanently deleted). `workflow_active` and `owner_username` remain admin-only.

### 3.6 `GET /runs/{run_id}`

The same new fields as 3.5, plus `typical_seconds` (the workflow's p50 over the last 90 days, `null` without data).

## 4. Web

Everything new in `web/app/components/observability/`; the `page.tsx` page only composes.

### 4.1 State in the URL (`historico-url.ts`, pure)

`?periodo=7|30|90&visao=execucoes|workflows|executores|confirmacoes&status=&workspace=&workflow=&executor=&origem=&assistente=1&q=&execucao=`

- `lerEstado(searchParams)` validates and returns `EstadoDoHistorico` with defaults (`periodo=30`, `visao=execucoes`); invalid values fall back to the default.
- `assistente=1` is the "Assistente" chip (boolean; only "1" turns it on). It has its own name because `origem` is already the TRIGGER (`trigger_source`) and this one slices by who CREATED the workflow — the two coexist in the URL and combine.
- `escreverEstado(estado)` returns the query string without the defaults (clean URL).
- The `useHistoricoUrl()` hook reads with `useSearchParams` and writes with `router.replace` (no scroll).

### 4.2 Copy (`formatos.ts` and `shared/status-rotulos.ts`, pure)

- `rotuloDoStatus`: `success`→"Concluída" (Completed), `failed`/`error`→"Falhou" (Failed), `running`→"Em andamento" (In progress), `pending`→"Na fila" (Queued), `cancelled`→"Cancelada" (Cancelled), `cached`→"Cache", other→the text itself. `StatusBadge` now uses this (it applies to every screen).
- `formatarDuracao(segundos)`: `< 60` → "31 s"; `< 3600` → "4 min 02 s"; otherwise "2 h 14 min"; `null` → "—".
- `formatarInicio(iso, agora)`: `< 60 min` → "há 12 min" (12 min ago); today → "hoje, 03:00" (today, 03:00); yesterday → "ontem, 17:22" (yesterday, 17:22); same year → "4 set, 03:00"; otherwise "4 set 2025, 03:00".
- `rotuloDaOrigem`: `manual`→"manual", `retry`→"reexecução" (re-run), `webhook`→"webhook", `schedule`→"agendado" (scheduled), null→null.
- `rotuloDaCategoria`: `timeout`→"tempo esgotado" (timed out), `no_executor`→"sem executor" (no executor), `executor_lost`→"executor caiu" (executor dropped), `isolation`→"isolamento" (isolation), `user`→"erro do fluxo" (workflow error), `validation`→"validação" (validation), `resource`→"recursos" (resources), `transient`→"transitório" (transient), `internal`→"interno" (internal), `dispatch`→"despacho" (dispatch).
- `rotuloDoNivel`: `primary`→null (the normal case is not marked), `fallback`→"reserva" (fallback), `pool`→"pool".
- `variacao(atual, anterior)` → `{ pct, delta, direcao: 'sobe'|'desce'|'igual' } | null`.

### 4.3 Blocks

- **Header**: "Histórico" + subtitle "Execuções dos seus workflows · comparado com os N dias anteriores" (Runs of your workflows · compared with the previous N days); on the right, a 7/30/90 segmented control and "Atualizar" (Refresh) (`<Button variant="ghost" size="sm" disabled={carregando}>`). NOTE: the freshness stamp "atualizado há X s" (updated X s ago) is **not rendered** today — `textoDeFrescor` exists in `cabecalho.tsx` but is never called, and `atualizadoEm` is tracked in the hook (`use-historico-dados.ts`) without being displayed.
- **Now strip** (`agora-faixa.tsx`): "Agora · N em andamento · N na fila · N presa(s) há X · Executores a de b online · N confirmações atrasadas (admin)" (Now · N in progress · N queued · N stuck for X · Executors a of b online · N overdue acknowledgments) + the link "Ver em andamento →" (See in progress →) (applies `status=running`). Whatever is zero disappears, except "em andamento". It refreshes every 30 s while the tab is visible (the 10 s ACK poll remains admin-only).
- **Indicators** (`indicadores.tsx`): Execuções (Runs) (trend vs previous, sparkline of the total per day), Taxa de sucesso (Success rate) (trend in points, sparkline of the rate per day), Duração típica (Typical duration) ("42 s" + "5% mais lentas acima de 3 min 10 s" (slowest 5% above 3 min 10 s); previous median in the description), Falhas (Failures) (absolute delta, "28 delas em «X»" (28 of them in "X") from `top_failing_workflows[0]`). Fewer failures is green. Each card has an `aria-label` with the full text.
- **Per-day chart** (`grafico-por-dia.tsx`): Recharts under `dynamic()`, stacked bars Concluídas / Falhas / Em andamento / Canceladas (Completed / Failed / In progress / Cancelled) in the status colors; X axis "8 ago"; tooltip in Portuguese; no re-animation when the period changes (`isAnimationActive={false}` after the first paint).
- **Needs attention** (`atencao.ts` pure + `atencao-lista.tsx`): up to 5 items, in this order: stuck runs (`now.stuck`), repeated failures (`top_failing_workflows` with `failure_count ≥ 3` or `failure_rate ≥ 0.2`), executors at the ceiling (`capacity.running ≥ max_concurrent` and `queued > 0`). Each item leads to an action: open the run, filter the table by the workflow with `status=failed`, open the executor. Items that have a workflow carry the assistant badge when the origin can be resolved (the metrics do not carry it: whoever composes the screen passes `origemDoWorkflow`, from the per-workflow inventory — on the Dashboard, from the workflow listing). Empty: "Nada pendente. Última falha há X." (Nothing pending. Last failure X ago.) (or "Nenhuma falha no período." (No failures in the period.)).
- **Filters** (`filtros.tsx`): status chips (Todas / Falhas / Em andamento / Concluídas / Canceladas — All / Failures / In progress / Completed / Cancelled) with counts from `by_status`; after a separator, the "Assistente" chip — an independent toggle (it combines with the status), WITHOUT a number, because the available count is of workflows and the other chips count runs; Workspace selects (if the user has more than one, or is admin), Workflow (with the sparkle on the assistant's), Executor, Origem (Source); search with a 300 ms debounce. The chip becomes `workflow_origem=assistente` in `/runs` and, in the "Por workflow" view, a local slice of the inventory.
- **Views**: `tabela-execucoes.tsx` (Status · Workflow (workspace · source · who) · Start · Duration · Executor (+tier) · Error · ›; stacked card on the phone with `CELULA_COM_ROTULO`), `visao-workflows.tsx` (Workflow · Runs · Success · Typical duration · Last · Failures/last error · Active (admin, with confirmation when turning off)), `visao-executores.tsx` (Executor · online · Running/queue · Runs · Success · Typical duration · Last), `visao-confirmacoes.tsx` (today's ACK card, with copy in Portuguese).
- **Run panel** (`painel-execucao.tsx`): `Sheet` on the right (default width 520, resizable like the executor one); header (workflow, status, tier, source, who triggered it); facts (start, duration + typical, executor, workspace); full error with category; nodes with duration and which one failed; actions: "Executar de novo" (Run again) (`POST /workflows/{id}/runs/{run}/retry`, with confirmation), "Abrir workflow" (Open workflow) (`/workflow/{id}`), "Ver log" (View log) (`/runs/{id}/events`, reusing the existing log panel when there is one), "Abrir em página" (Open as a page) (`/observability/run/{id}`), "Copiar ID" (Copy ID). It opens via `?execucao=` in the URL.
- **Data** (`use-historico-dados.ts`): four parallel calls per (period, filters) with a 60 s cache per key and a sequence stamp (the stale response never overwrites the new one); a partial failure becomes a warning in the affected section, not silence.

Rates colored by band use `successRateColor(taxa, "amber")`: the default yellow has no contrast in the light theme.

### 4.4 Side effects handled

- `StatusBadge` in Portuguese (every screen).
- Overview (`/dashboard`): uses the corrected `success_rate` automatically; the "Workflows" card no longer shows a runs sparkline.
- Workflow detail (`/observability/{id}`): rows lead to the run; link to the editor.
- The "Ver todas no Observability"/"Abrir na observabilidade" links now say "Histórico".
- `page.tsx.bak` removed.

## 5. Out of this round

Executor capacity history, `workflow_runs` rollup, real time in the queue (`acked_at`), per-user metrics with their own RBAC, schedule health ("didn't run at 03:00" requires comparing `next_run_at` with the last scheduled run; it comes in when `schedule_id` has history).
