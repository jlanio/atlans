# Spec — Node data panels (Entradas / Saídas)

Status: implemented · Date: 2026-11-25
Scope: `flow/executor/` (sample builder), `executor/` (envelope), `app/` (execute payload),
`web/app/components/workflow/node-config-modal/` and `web/app/stores/` (panels)
Mockup: the interactive preview reviewed in the project thread (three columns, Schema / Tabela / JSON).

## 1. Problem

While building a workflow, the person configures a node without seeing the data that
reaches it. The side panels of the node modal show **names only**:

- `input-inspector.tsx` lists the parents' output keys (declared, observed in
  `output_keys`, or wired) and a Schema tab with the catalog's declared fields.
- `output-preview.tsx` shows the last status and the declared schema.
- The only content that ever reaches the editor is the debug summary
  (`flow/executor/utils.py::_build_debug_summary`), a string such as
  `"GeoDataFrame | 144 registros | CRS: … | colunas: [...]"`, and only with debug mode on.

Consequences, all verified in the code:

1. To know the values of a column (to write a filter, pick a category, check a CRS)
   the person has to save the result somewhere and open it outside Atlans.
2. The input panel lists **direct parents only**, although every earlier node is reachable
   in an expression: `named[alias] = outputs` accumulates every executed alias
   (`flow/executor/core.py`, `run()`), so `{{ AnyEarlierAlias.key }}` works today and
   the panel does not show it.
3. The side panels are 240 px wide (`node-config-modal/index.tsx::SIDE_PANEL`), too
   narrow for a table.

## 2. Goal / Non-goal

Goal:
- After a run started from the editor, each node's panels show a **sample of the real
  data** of every output: first rows as a table, a schema with types and an example value,
  and a JSON view for outputs that are not tables.
- The input panel can show **any earlier node**, direct parents first.
- Dragging from any view into a field keeps working: a key inserts `{{ Alias.key }}`,
  a column inserts its name, and in the Python Script the variable name.
- Before any run, the panels show the declared schema and an empty state that says how
  to get data.

Non-goal (this round):
- Full data browsing (pagination over the whole output), a map of the sample,
  "run up to this node". They are listed in §9 as follow-ups.
- Samples in scheduled, webhook, MCP or sub-workflow-nested runs.
- Mobile layout of the panels (they are `hidden lg:flex` today and stay so).

## 3. Decisions

| Decision | Reason |
|---|---|
| The sample is built **on the executor**, at the end of each node | Only the executor has the data; the server never sees a DataFrame |
| It travels in a **separate node event** (`status: "sample"`), not inside `completed` | Its own 64 KB budget; a large sample can never push the traceback or `output_columns` out of the lifecycle event through the reduction (`flow/utils/publisher/reducao.py`) |
| Off unless the request asks for it: new `data_preview` flag, sent only by the editor's Run button | Real data leaves the executor only when a person is looking at it; scheduled and webhook runs are unchanged |
| 20 rows, ≤ 40 columns, cells cut at 120 chars, geometry summarized | Enough to read values; keeps one node under ~16 KB in the common case |
| Not persisted in the database (`node_stats` is untouched) | Same retention as the rest of the run events: the 1 h Redis history (`REDIS_TTL_1H`), confirmed as enough. Avoids storing user data in Postgres |
| An admin can turn samples off for the whole installation (on by default) | Some installations handle data that must not leave the executor, even as a sample |
| Live secrets redacted in every string cell before sending | Same guarantee the logs already have (`flow/utils/segredos_vivos.py`) |
| One shared `DataView` component for both panels | Same behavior on both sides, one place to test |

## 4. Wire contract

### 4.1 Execute request (web → API)

`app/api/routers/workflows_router.py::ExecutePayload` gains:

```python
data_preview: bool = Field(default=False, description="Send a data sample of each node's outputs (editor only)")
```

`WorkflowService.start_analysis` computes the effective value as
`data_preview and node_data_preview_enabled` (§4.3), before the idempotency check, and
returns it on `DispatchResult.data_preview`; the route answers it as `data_preview: bool`,
so the editor knows whether to wait for samples.

The description of `debug_mode` is fixed at the same time: it says the executor "pauses at
each node", which it does not.

`execute_workflow` → `WorkflowService.execute…` → `workflow_execution_service._build_envelope`
pass it through and add `"data_preview": bool` to `agent_payload`, next to `debug_mode`.

Compatibility: an old executor ignores the unknown key; a new executor talking to an old
server reads `payload.get("data_preview", False)` and stays off.

### 4.2 Executor

`executor/job_executor.py` reads `data_preview` (bool, optional, validated in
`job_validator.py` like `debug_mode`) and passes it to `WorkflowExecutor(data_preview=…)`.
Nested executors (`flow/nodes/control/sub_workflow.py`) receive `data_preview=False`.

### 4.3 Admin setting

A `SystemConfig` row, key `node_data_preview_enabled`, value `"true"`/`"false"`; a missing
row means on. Same pattern as `artifact_retention_days` (`artifacts_router.py`, `/admin/settings`).

- `GET /workflows/admin/data-preview` and `PUT /workflows/admin/data-preview`
  (`require_admin`), body `{"enabled": bool}`, in `admin_workflows_router.py`.
- Read once per execute request in `workflow_execution_service` (one indexed lookup); no cache,
  so turning it off takes effect on the next run.
- Admin UI: a "Amostras de dados no editor" section with one switch in
  `web/app/components/admin/settings/` (new `amostras-de-dados.tsx`, listed in `nav.tsx`),
  with the text: "Quando ligado, execuções feitas pelo editor enviam as primeiras linhas de
  cada nó para os painéis Entradas e Saídas. Os dados ficam 1 hora no histórico da execução."
- Turning it off does not erase samples already in the 1 h history; it only stops new ones.

### 4.4 The sample event

Published by `flow/executor/events.py::publish_sample` right after `publish_completed`,
only when `data_preview` is on, the node completed (or was served from a pin) and the
executor is not nested:

```jsonc
{
  "run_id": "…", "node": "<node_id>", "status": "sample",
  "kind": "debug", "level": "info", "timestamp": 1764082584.1,
  "extra": {
    "node_name": "Clip", "node_type": "spatial",
    "output_sample": {
      "version": 1,
      "outputs": {
        "output": {
          "kind": "table",                 // "table" | "json"
          "rows_total": 1284,
          "crs": "EPSG:4674",              // GeoDataFrame only
          "columns": [
            {"name": "cd_mun",   "type": "str"},
            {"name": "area_km2", "type": "float"},
            {"name": "geometry", "type": "geometry:MultiPolygon", "geometry": true}
          ],
          "rows": [
            ["1500602", 159533.33, {"type": "Polygon", "vertices": 1880, "wkt": "POLYGON ((-52.21 -3.20, -52.19 …"}]
          ],
          "truncated": {"rows": true, "columns": false, "cells": false}
        },
        "metadata": {
          "kind": "json",
          "value": {"url": "https://…", "features": 58},
          "truncated": false
        }
      },
      "skipped": ["__artifact__"]          // keys left out on purpose
    }
  }
}
```

The builder makes the event fit on its own (§5.4). As a defense, `output_sample` is added
to `HEAVY_EXTRA_KEYS`, so if an executor still sends an oversized one, the reduction on
either side removes it first, and the panel treats a `sample` event without
`output_sample` as "no sample".

## 5. Sample builder (`flow/executor/sample.py`, new)

`build_output_sample(outputs: dict, *, max_rows=20, max_cols=40, max_cell=120, budget_bytes=48_000) -> dict`

Pure function, no I/O, unit-tested in isolation. Runs in `asyncio.to_thread` like
`metrics_collector.end_node`.

### 5.1 Tables (`pd.DataFrame` / `gpd.GeoDataFrame`)

- `rows_total = len(df)`; rows = `df.head(max_rows)`.
- Columns capped at `max_cols`; the geometry column always kept and moved last.
- Column `type`: `int`, `float`, `bool`, `datetime`, `str`, `geometry:<GeomType>`
  (from the first non-null geometry, or `geometry:mixed`), otherwise `object`.
- Cells: `NaN`/`None` → `null`; numpy scalars → Python; `datetime`/`Timestamp` → ISO 8601;
  bytes → `"<bytes N>"`; anything else → `str()`; strings cut at `max_cell` with `…`.
- Geometry cell: `{"type", "vertices", "wkt"}` with `wkt` cut at 80 chars. Vertex count via
  `shapely.get_num_coordinates`, never by serializing the geometry.
- `crs`: `df.crs.to_string()` when present.

### 5.2 Everything else

- `dict` / `list` / scalar → `kind: "json"`: depth ≤ 4, lists ≤ 20 items, strings ≤ `max_cell`,
  DataFrames found inside replaced by `"<DataFrame RxC>"`.
- `str` / `bytes` (e.g. HttpRequest's raw body) → `kind: "json"`, value cut **before** any
  decode, like `_build_debug_summary` already does.
- Keys `__artifact__`, `__response__` and spilled references go to `skipped`.

### 5.3 Redaction

- Every string cell and JSON leaf goes through the live-secret redaction. `segredos_vivos`
  exposes a new `redact_text(texto: str) -> str` that applies the forms currently
  `in_use` (the same `_redact` it uses for log records).
- Columns or keys whose name matches `password|passwd|secret|token|api[_-]?key|authorization`
  (case-insensitive) have their values replaced by `"***"`.

### 5.4 Budget

The serialized `output_sample` must stay ≤ `budget_bytes` (48 KB, leaving room under the
64 KB event ceiling). If it does not fit: halve the rows of every table, repeat down to
1 row; then drop columns from the right (never the geometry); then replace the largest
outputs by `{"kind": "omitted", "reason": "too_large"}`. Every cut is recorded in
`truncated`. Measured by `json.dumps`, never estimated (same rule as `reducao.py`).

### 5.5 Where it is called in `core.py`

In `_run_node_with_tracking`:

- **Pinned branch**: after `_publish_completed(..., cache_hit=True)`, with `pinned`.
- **Normal branch**: after the `finally`, only when `status == "completed"`, with the
  real `outputs` (not the spilled dict — same reason as the debug event's comment).
- A failure publishes nothing new: the panel shows the failed node's inputs from its
  parents' samples, which already arrived.

## 6. Frontend

### 6.1 Types and store

- `RawEvent.extra.output_sample?: OutputSample` in `workflowExecutionStore.ts`, with
  `OutputSample` / `OutputSampleEntry` types in `web/types/`.
- New store slice `samples: Record<nodeId, { sample: OutputSample; runId: string; stale: boolean }>`.
- `useExecuteWorkflow.ts` sends `data_preview: true` (via `GisFlowService.executeWorkflow`),
  stores the effective `data_preview` from the response, and routes `status === "sample"` events into the slice instead of the canvas status.
- When a run starts, existing samples are marked `stale: true` (shown greyed with
  "da execução anterior"); each one is replaced when its node's new sample arrives.
- `loadHistoricalEvents` handles `sample` events too, so reopening the editor within the
  1 h history window brings the samples back.
- `eventKind`/raw tab: `sample` events are hidden from the Problems and Nodes tabs and
  shown in the Raw tab as a one-line `amostra: output (20 de 1.284 linhas)`.

### 6.2 Components (`node-config-modal/data-view.tsx`, new)

| Component | Role |
|---|---|
| `SeletorDeVisao` + `useVisaoLembrada` | Schema / Tabela / JSON switch, remembered per panel in `localStorage` (Tabela when a sample exists, Schema otherwise) |
| `FilhosDaChave` | Schema view: under each output key, its columns or JSON keys with type and first value; falls back to the column names of `output_columns` without a sample |
| `VisaoTabela` | Sticky header with name + type, numeric columns right-aligned with `tabular-nums`, geometry cell as `Polygon · 412 vért.` (WKT on hover), footer `Mostrando 20 de 1.284 linhas (amostra) · EPSG:4674` |
| `VisaoJson` | Highlighted JSON; tables shown as their first 3 rows as objects; keys of a JSON output draggable |
| `VisaoDaSaida` | Table or JSON of one output, with the "Esta saída não é uma tabela" fallback |
| `AbasDeChave` | One button per output key when the node has more than one (`output`, `metadata`, `removed`…) |
| `SemAmostra` | "Ainda sem dados de execução" / "não trouxe dados (histórico expirado)" / "Amostras de dados desligadas" |
| `SeloAnterior` | "da execução anterior" on a stale sample |

The source picker lives in `input-inspector.tsx`: "Ligados a este nó" (direct parents) then
"Outros nós anteriores" (every other ancestor, nearest first, each once).

Drag payloads keep the current rules of `input-inspector.tsx`:
key → `{{ Alias.key }}`; column → column name; JSON leaf → `{{ Alias.key.path }}`;
in the Python Script, the arrival variable name (`to_key || from_key`), and a JSON leaf
becomes `variavel["key"]`. An earlier node that is not wired is draggable as an expression,
but not in the Python Script, where only edges create variables.
The copy button stays on every draggable row.

### 6.3 Panels

- `input-inspector.tsx` becomes `SourcePicker` + `KeyTabs` + `DataView`. It keeps what it
  has today and still matters: "Aguardando conexão" ports, the schema-drift warning, the
  per-edge arrival name (`key → variavel`), the status chip of the source node.
- `output-preview.tsx` becomes `KeyTabs` + `DataView` for the node itself, plus a
  "dados fixados" chip when the node is pinned. Pinning itself stays where it is, in the
  central modal (`nodes-configuration/pin-section.tsx`), so there is one place to do it.
  The row-count chip of the mockup (`1.284 linhas · era 144 na entrada`) is left for later:
  `input_features` only exists in the persisted `node_stats`, not in the live node status.
- View choice (Schema / Tabela / JSON) is remembered per panel in `localStorage`
  (try/catch, default Tabela when a sample exists, Schema otherwise).

### 6.4 Layout

`SIDE_PANEL` stops being `w-[240px]`: default 360 px, resizable by a drag handle on the
inner edge, min 280 px, max `35vw`, width remembered in `localStorage`. The center form
keeps its current width; on screens below `lg` nothing changes.

## 7. Security and privacy

- Who sees a sample: whoever can already read the run's events (the run log WebSocket),
  the same audience that sees `output_columns` and tracebacks today. No new endpoint.
- Data leaves the executor only for editor runs (`data_preview`), only as a bounded sample,
  with live secrets redacted, and lives 1 h in Redis.
- The server does not trust the executor's size: `_serialize_node_event` keeps applying
  the byte ceiling to `sample` events like any other.
- An admin can turn samples off for the whole installation (§4.3).

## 8. Tests

Python (`tests/unit/`):
- `test_amostra_de_saida.py`: GeoDataFrame (types, CRS, geometry summary, vertex count),
  plain DataFrame, NaN/datetime/numpy values, dict/list/str/bytes, `__artifact__` skipped,
  budget cuts in order (rows → columns → omitted) and `truncated` flags, redaction of live
  secrets and of sensitive column names.
- `test_core_amostra.py`: sample event emitted only with `data_preview`, for completed and
  pinned nodes, never for failed or nested ones; spilled outputs still sampled from the real
  payload.
- Server: `ExecutePayload.data_preview` reaches the envelope; with the setting off the
  envelope carries `false` and the response says so; the admin routes require admin and
  validate the body; a `sample` event above the ceiling is reduced by `_serialize_node_event`.

Web (`web/__tests__/`, vitest):
- Store: `sample` events go to the slice, are marked stale on a new run, are restored by
  `loadHistoricalEvents`, never touch node status.
- `DataView`: each view, empty state, non-table output in Tabela, drag payloads (key, column,
  JSON leaf, Python variable).
- `SourcePicker`: direct parents first with their ports, then other ancestors; diamond graphs
  list each node once.

## 9. Delivery

1. **PR 1 — backend**: `sample.py`, `redact_text`, `data_preview` through API → envelope →
   executor → `core.py`, the admin setting and its routes, `HEAVY_EXTRA_KEYS`,
   `debug_mode` description, Python tests.
   Mergeable alone: with no client sending `data_preview`, nothing changes.
2. **PR 2 — web**: store, `data-view/`, both panels, resizable layout, the admin switch, vitest.

Follow-ups, out of this round:
- Mini map of the sample geometries in the Tabela view.
- Full data from the pin artifact when the node is pinned (paginated read from MinIO).
- "Executar até este nó": run only the ancestors of a node, reusing pins as cache.
- Debug mode: publish the failing node's inputs summary on failure, or retire the toggle
  now that samples cover its use.

## 10. Decided

- Admin switch to turn samples off: yes, on by default (§4.3).
- Retention: the 1 h of the run event history is enough; nothing is persisted.
- MCP `run_workflow` does not request samples in this round; it can be added later by
  sending `data_preview` from the tool, under the same admin switch.
