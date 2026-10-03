# Spec — Workflow edge (Edge) data contract

Status: implemented (merged into `main`) · Date: 2026-09-05
Scope: `flow/` (engine), `app/` (validation/persistence), `web/app/components/workflow/` (canvas)

## 1. Problem

Today an edge is an untyped `dict` that carries **three concerns in the same object**,
read by different subsystems:

1. Topology — `source`, `target` (solid; `flow/core/graph.py`).
2. Data mapping — `from_key`, `to_key` (optional).
3. Branch routing — `condition` (bool) / `source_handle` (`true`/`false`), control nodes.

The meaning of the data mapping is resolved by an **implicit 4-mode cascade**
in `flow/executor/core.py` (input assembly, ~576-601):

| Fields on the edge      | Behavior                                                  |
|-------------------------|----------------------------------------------------------|
| `from_key` found        | uses that field (explicit) ✅                              |
| `from_key` not found    | warn + `next(iter(...))` (1st value) ⚠️ order-dependent    |
| only `to_key`           | `next(iter(...))` (1st value) ⚠️                           |
| none                    | `inputs.update(parent_outputs)` (spreads everything) ⚠️   |

Three of the four modes pick "first value" or "spread everything" — dependent on the
**dict insertion order**. Verified consequences:

- **Boolean leak at a fork** (fixed): the branch edge
  is born without `from_key`, falls into "spread everything", and whoever reads `next(iter(inputs.values()))`
  (ComputeBBox, Geocode, HttpRequest, ResponseNode) got the `branch` decision instead of the
  data. Today the workaround is for control nodes to **defensively order** the
  `static_output` (the data before the `branch`) — fragile, and documented in
  `flow/nodes/control/conditional.py`.
- **Two diverging parsers**: the real run (`core.py:~576`) and the schema simulation/preview
  (`core.py:~795`) interpret the SAME edge with different rules. In the
  "no keys" case: the run **spreads everything**; the simulation names by **`parent_id`**
  (`to_key = to_key or from_key or parent_id`). The input-inspector can announce something
  the run does not produce.
- **Third resolution layer**: `node_manager.auto_map_edges()` (`core.py:157`)
  mutates the edges on every execution, backfilling `from_key`/`to_key` from the nodes' legacy
  params (`outputKey*`/`inputKey*`).
- **No typed model**: the edge is a raw `dict` in the engine, API and UI
  (`edge['source']`, `edge.get('from_key')`, `data?.from_key as string`).

What is **not** a problem (do not touch): the render component `custom-edges/index.tsx`
(large, but cohesive) and the documented sub-workflow contract in
`flow/utils/workflow_contract.py` (1 edge without a key = spreads the dict, on purpose).

## 2. Goal / Non-goal

Goal:
- **One** typed edge definition, conceptually shared between engine and web.
- **One** per-edge input resolver, used by the real run AND by the simulation.
- **Explicit and deterministic** resolution rules; the blind "first value" is
  **removed** — a `from_key` with no match at run time OMITS the port (never someone else's data, never a
  crash); an undeclared `from_key` is flagged as an error in static validation (`/validate`, §7).
- Branch routing (`condition`) and data mapping stop colliding — a branch
  edge now carries explicit data, and routing now gates on `Edge.is_branch`.
- Graph and skip robustness: an orphan edge does not bring down the run (F1); a merge/diamond does not
  skip a node with a live parent (F2).

Non-goal:
- Redesigning the edge rendering.
- A NEW port field on the edge. Multi-port stays expressed through
  `from_key`/`to_key` — there is no data `target_handle`/`source_handle` in the model.

> **Update (multi-port sub-workflow).** What used to be a non-goal — "multi-port
> input" — became supported for the three sub-workflow nodes WITHOUT touching the edge
> model: the ports are DECLARED on the node and each edge lands on its own key.
> - `SubWorkflowOutput` (`dynamic_inputs`) and `SubWorkflow` (ports from the child's contract):
>   named inputs → each edge writes a distinct `to_key`.
> - `SubWorkflowInput` (`outputs_from_ports`): named outputs → each outgoing edge carries
>   a distinct `from_key`, choosing what to pass along.
> - `≤1` declared port keeps the anonymous handle and the **spread** (edge without a key),
>   preserving existing sub-workflows.
> - The React Flow `handle` of a SubWorkflow (invoke) node comes from an ASYNCHRONOUS contract;
>   the edges are re-anchored (`reancorarArestasDoNo`) when the contract arrives, otherwise they
>   collapse onto the first port on reload (the edge's `data` preserves `to_key`/`from_key`).

**Owner's decision (2026-09-05): strict by default, NO migration.** Saved workflows
do not need compatibility — there are few of them and they are fixed by hand. Consequences, all
validated against the real code (blast-radius workflow, 12 agents, C1/C3 confirmed
safe, C2 refuted):
- **No `schema_version` and no version gate** — the field does not exist anywhere
  (engine/app/web/DB) and the engine is already "a single version". Not introducing it costs nothing.
- **No data migration layer** — the old PR 3 (migration + gated strict) goes away.
  `auto_map_edges` is **retired** from the runtime (it is a no-op except for legacy
  `outputKey*/inputKey*` params, which no current node/front end emits).
- **Fixing by hand** = redrawing the edge on the canvas (the front end writes `from_key`) or editing
  the JSON. Reopening+saving alone does NOT backfill.

## 3. Canonical Edge model

Engine (`flow/executor/edge_resolver.py`) — frozen dataclass `Edge`, with a `from_dict`
tolerant of the current format. A separate `flow/core/edge.py` was NOT created (as
sketched in an earlier version of this spec): the model lives alongside the resolver. There is only
`from_dict`; there is no `to_dict` — the executor keeps storing and reading the edge's original
dict, and the model only carries what the semantics use. The `source_handle` written by the UI
stays in the dict and does not enter the model.

```python
@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    # data mapping (both None => "spread" mode, see §4)
    from_key: str | None = None
    to_key: str | None = None
    # branch routing (control nodes); None = plain data edge
    condition: bool | None = None

    @property
    def is_branch(self) -> bool:
        return self.condition is not None
```

Web (`web/app/components/workflow/canvas-types.tsx`) — mirrored type. **PLANNED —
does NOT exist in the code yet:** `AtlansEdgeData` is not defined anywhere in
`web/`; the edge's `data` is read today without a dedicated type (`data?.from_key as string`).
Typing it remains the pending front-end item (§6).

```ts
// PLANNED (not implemented yet)
export interface AtlansEdgeData {
  from_key?: string
  to_key?: string
  condition?: boolean
  // source_handle lives in React Flow's native field (sourceHandle)
}
```

`kind` is derived (`is_branch`), not persisted — it avoids a fourth field to keep in
sync.

## 4. Single resolver

`flow/executor/edge_resolver.py` (new), with no dependency on `core`/asyncio — pure and
testable:

```python
# Returns the inputs that THIS edge injects into the target node.
#   - mapped mode:  {to_key or from_key: value}
#   - spread mode:  the parent's whole dict (shallow copy)
def resolve_edge_inputs(edge, parent_outputs, *, logger=None) -> dict:
    # Does NOT raise: a from_key with no match OMITS the port (injects neither someone
    # else's value nor None). The undeclared-from_key error belongs to static validation
    # (/validate, §7), not to the run — which must tolerate optional/dynamic output.
    if edge.from_key:
        if edge.from_key in parent_outputs:
            return {edge.to_key or edge.from_key: parent_outputs[edge.from_key]}
        log_from_key_ausente(edge)          # actionable log line; contributes nothing
        return {}

    if edge.to_key:                          # rename of the 1st output; empty parent → nothing
        return {edge.to_key: _first(parent_outputs)} if parent_outputs else {}

    # spread: sanctioned ONLY when the parent declares 1 output, or the edge is a sub-workflow
    return dict(parent_outputs)
```

Rules (the strict "default" — validated against the real code):
- **Mapped mode** (`from_key` present): the only path for new graphs. `to_key`
  defaults to `from_key`.
- **Lenient run; strict error in `/validate`** (implementation decision). The
  `resolve_edge_inputs` only sees `parent_outputs` (what the parent emitted in the run) and **does NOT
  raise**: a `from_key` with no match **omits** the port — it injects neither someone else's value
  nor `None`, and does not blow up. This ends the blind "first value" (root of F5/F14) without trading a
  silent cross-feed for a crash in production: an optional/dynamic output missing in a
  batch must not bring down a legitimate workflow. The check for an **undeclared** `from_key`
  (typo/stale = error) lives in STATIC validation (`/validate`, §7), which has the parent's declared
  keys at hand and flags it before running, with no runtime false positive.
  - `from_key` present but not emitted in this run (the Switch's empty bucket — F5; optional
    output) → contributes **nothing**. Fix at the SOURCE: the Switch now emits ALL the
    declared buckets (empty ones included), so a `from_key` for an empty bucket resolves to
    an empty container instead of vanishing and crossing into another bucket.
  - **skipped** parent → the edge **disappears** from the merge (does not inject `None`, F14). Since a skipped
    parent and a parent that returned `{}` are indistinguishable in the resolver, the run detects the
    skip via `node_stats[...]['status'] == 'skipped'` and skips the edge before resolving.
- **`to_key`-only mode** (no `from_key`): rename of the parent's 1st output — stays (a real
  contract, e.g. `SubWorkflowInput`→multi-port node, `static_output=[]`). Empty parent → does not
  contribute. The ambiguity (multi-output source without `from_key`) is flagged in `/validate`
  as a **warning**; it does not block the run.
- **Spread mode** (no key): **stays legal** — it is the fan-out of `SubWorkflowInput`
  and the basis of the schema-less nodes that read `next(iter(inputs.values()))`. It does NOT become an error. The
  validation (§7) emits a warning when the parent has >1 output (unmapped-edge heuristic).
- **Branch edge** (`is_branch`): routing now gates on `Edge.is_branch`
  (`condition` bool), **not** on the raw `"branch"` output (kills F7/F8). The data is mapped
  like any other edge — the UI already writes `from_key` (the data, e.g. `result`) on the branch
  edge; a namespaced `__branch__` is unnecessary (the UI only persists `condition` bool or
  nothing).

Replacements:
- `core.py:576-601` now assembles `inputs` by calling `resolve_edge_inputs` per edge
  (spread = `inputs.update`, mapped = `inputs[k] = v`).
- `core.py:795-807` (simulation) uses the SAME resolver over the simulated schema — killing the
  run × preview divergence. End of `to_key or from_key or parent_id`.

**Run × preview parity.** The two functions — `resolve_edge_inputs` (values, in the run) and
`resolve_edge_schema_inputs` (types, in the preview) — name EXACTLY the same ports
for the same graph. Under strict (implemented):
- **`from_key` with no match** (not emitted in the run / not present in the preview's fields) →
  both **omit** the port (`{}`). End of the "first value" and of the `<unknown>` sentinel:
  run and preview omit alike, so parity holds even with an empty parent
  (`{}` == `{}`).
- The **error** for a stale `from_key` does NOT live in the resolver (which only omits) but in
  `/validate` (§7), which compares against the source's declared schema. Changing one side without the
  other would reopen the run × preview divergence — which is why `resolve_edge_inputs` and
  `resolve_edge_schema_inputs` always go together.

## 5. No migration — strict by default (owner's decision)

There is no data migration and no `schema_version`. The engine is already "a single version"; strict becomes
the only behavior. `auto_map_edges` (`node_manager.py`, called at `core.py:158`)
is **removed from the runtime** — validated as a no-op except for legacy params
`outputKey*/inputKey*`, which neither any node nor the current front end emits.

Adversarial point to keep in mind (validated): removing `auto_map_edges` does **not** make legacy
graphs "blow up" — a legacy edge without `from_key` falls into a **silent spread** (the parent's whole
dict into the child), which can deliver wrong data without an error. Since there are few workflows and the owner
fixes them by hand, this is accepted; optionally, `core.py` logs a `warning` when an edge
falls into spread while the parent has >1 output (turning the silent regression into an actionable line).

Coordinated cleanup when retiring the backfill: remove `_PREFIXOS_LEGADOS`
(`parameter_validation.py`), adjust `test_parametro_descartado.py`, and update
`docs/creating-nodes.md` (§97-170), which still teaches the `inputKey/outputKey` pattern — no
node in the repo follows it, but a new node written from the stale doc would misroute without the
backfill.

## 6. Web

Validated state: the front end is **already** born almost-strict — `handleConnectNodes` (`index.tsx:
504-527`) and the drawer's "+" button (`nodes-drawer.tsx:107`) write `from_key = 1º candidato` (the 1st candidate)
whenever the source declares outputs, **including** on branch edges (the `from_key` of the
pass-through data). The comments in `conditional.py`/`jinja_branch.py`/`change_detector.py`
("branch is born without from_key") are stale (NOT yet fixed in the code — see PR-C).
State of the gaps:
- **F9 — RESOLVED.** `chooseKey` (`custom-edges/index.tsx:101`) now syncs the
  `sourceHandle` when switching `from_key` via `sourceHandleDaChave` (`:117,127`), keeping the
  invariant `sourceHandle == from_key` for a multi-output node.
- **Picker disabled on the branch (PENDING)** (`custom-edges/index.tsx:99`): `canSwitch`
  still excludes `true/false` handles (`!BRANCH_HANDLE.has(handleKey)`), so a wrong `from_key`
  at a fork still has no UI to correct it. Enable `canSwitch` even with a
  `true/false` handle (the color/route keeps coming from the handle; only the DATA becomes selectable).
- **F10 — RESOLVED.** `useCanvasHistory` captures a baseline right after hydration
  (the history reset function), so the 1st edge edit became undoable.
- Validation on the canvas (PENDING): visually mark an **ambiguous** edge (multi-output source
  without `from_key`) before the run — reuses `losingEdgeIds`/edge styling.
- Typed `AtlansEdgeData` (PENDING — does not exist yet); remove the loose `as string` casts.

## 7. Validation & contract

- `app/services/validate_service.py::validar_definicao` (the static validation; today its
  consumer is the MCP `validate_workflow` tool — the REST shell `POST /workflows/validate` was removed
  for having no caller) returns, besides the per-node schema,
  edge diagnostics under the reserved key `__edge_diagnostics__`
  (`WorkflowExecutor.validate_edges()`): a `from_key` that **is not** a declared output of the
  source → **error** (stale wiring); a data edge without `from_key`/`to_key` from a
  multi-output source → ambiguity **warning**. A source with no known schema produces no
  diagnostic. It uses the simulated schema (`resolve_edge_schema_inputs`) as the source of the ports.
- **Accepted body** (PR 3 of the MCP's Phase 0): `nodes[]` = `{id, name, type, parameters?,
  properties?, alias?}` — `properties` is a synonym for `parameters` (on conflict, `parameters`
  wins), `alias` is optional and reaches the executor, `position` is ignored; optional `workspace_id`
  at the top level; `edges[]` unchanged (`source`, `target`, `from_key?`, `to_key?`,
  `condition?`).
- **Database session only when needed**: it opens only if there is a `credential_id` (valid UUID) or a
  `workspace_id`; the common case (a loose definition) does not pay for a connection. With `workspace_id`: **403**
  if the user is not a member (`get_workspace_member_role`, checked BEFORE the credentials — it does not
  reveal the existence of a credential to someone outside the workspace); credentials shared
  with the workspace only enter the scope for the **`operator` or higher** role — the same required
  to execute, because the `DatabaseSpatialQuery` simulation connects to the credential's database;
  below that, only the user's own scope applies and `hints` warns about it. Never other
  members' private ones — `assert_credentials_accessible(…, shared_workspace_id)` in the guard and
  `credential_scope({user}, shared_workspace_id=…)` in the simulation. Disabled nodes
  (`disabled_names`) are checked whenever there is a session; sub-workflow references
  (`validate_subworkflow_references_against_db`) **only with `workspace_id`** — without proven
  membership, the lookup by hash would be an oracle for the existence, state and ports of workflows
  in other workspaces; and, with `workspace_id`, the lookup filters by workspace, so a target
  in another workspace reads as `nao existe` (does not exist; active or not — the same holds for workflow create/update,
  which use the same function). A credential outside the scope → **403** before
  simulating (without `workspace_id`, the message suggests providing it); a `credential_id` that is not a
  UUID → **422** `invalid_definition` (`invalid_credential_id`), without going to the database. Without `workspace_id`,
  `subworkflow_errors` comes back `null` (and so does `disabled_nodes`, when no session opened) and
  `hints` asks for `workspace_id` — including in the `report` of the 422.
- **Lint BEFORE building the executor** (`flow/utils/definition_lint.py`, pure — no database
  and no executor). Fatal codes → **422**
  `{"error": "invalid_definition", "message": "Definição inválida: …", "report": {…}}`
  (`InvalidDefinitionError`, `app/core/exceptions.py`; `report` has the same shape as the
  `__report__` below, with `ok: false`):
  `unknown_node` (the message starts with `Node '<name>' não encontrado para instância
  (id=<id>).`; it is only fatal for a node that would enter the execution order — an isolated one or one outside
  the trigger's cone stays as an error in the report, because the constructor does not even instantiate it),
  `duplicate_node_id`, `cycle`, `construction_error` and `invalid_credential_id` (fatal by
  contract, not by construction: the id never reaches the database, and whoever only looks at the HTTP status —
  the skill's `validar.py` — failed with the earlier 403 and keeps failing). A nonexistent node
  and a cycle used to blow up with a 500; a duplicate id passed silently (the last one
  won) and is now refused on purpose. **Non-fatal** codes (201 response, inside
  `__report__`) — errors: `invalid_alias`, `reserved_alias` (`RESERVED_ALIASES`,
  `flow/core/aliases.py` — moved out of `flow/executor/core.py`), `duplicate_alias` (when there is an explicit
  `alias`), `secret_in_definition` (`{{ }}`/`$Alias` expressions and schemes such as
  `Bearer` do not count), `invalid_json_property` (an `object` property with unreadable JSON — the
  run fails in the node's `validate()`), `empty_fallback_output` (Switch with `fallback_output: ""`
  — the run emits the `''` port, which no edge names: dead wiring that the edge diagnostic
  does not see), `disabled_node`, `subworkflow_reference`, `edge_from_key_unknown`,
  `simulate_error`; warnings: `orphan_edge`, `unreachable_node`, `undeclared_property`,
  `missing_required_parameter`, `duplicate_alias` (derived from the `name` and referenced),
  `edge_spread_ambiguous`. The lint is linear in the size of the definition (a Jinja block
  tokenizer using `str.find`, a per-string cap and a single index of referenced names for the
  duplicate-alias check). The edge diagnostics
  remain in `__edge_diagnostics__` (today's format, only when there are any) and also appear in
  `__report__` as `edge_from_key_unknown` (error) / `edge_spread_ambiguous` (warning).
- **`__report__` (always present in the 201)**: `{"ok": bool, "errors": [...], "warnings": [...],
  "disabled_nodes": list|null, "subworkflow_errors": list|null, "suggested_params_schema":
  {nome: {"type": "string", "required": true}}, "hints": [str]}`. Each item of
  `errors`/`warnings` has exactly `{code, severity, node_id, edge, message}` — `node_id` and
  `edge` may be `null`; `edge` = `{"source", "target"}` or `{"source", "target",
  "from_key"}`. `ok` is `false` when there is any error (warnings do not bring it down);
  `simulate_error` mirrors the node that came out of the simulation with `status: "error"`.
  `suggested_params_schema` is **heuristic**: `inputs.<nome>` references only in nodes with
  `type == "trigger"` (in the others, `inputs` is the edges' input) and the `ports` of
  `SubWorkflowInput` — when it comes back non-empty, `hints` says to review it before writing it to
  `params_schema`.
- **Per-node schema and `schema_source`**: each node comes out as `{"status": "ok", "schema":
  [{"fields": [{"name", "type"}]}], "schema_source": "static" | "simulated" | "declared" |
  "unknown"}` or `{"status": "error", "error": "…"}` (`unknown` = a `dynamic_output` node without
  `simulate()` and with nothing declarable — empty schema, but the node does not disappear; `output_vars` that the
  run would reject becomes `status: "error"` with the runtime's message). A `dynamic_output` node
  **without** `simulate()` no longer disappears
  from the response: the outputs come from the definition, in this order — `output_vars` (PythonScript) →
  `rules[].output` + `fallback_output` (Switch) → `ports` (`outputs_from_ports`,
  `SubWorkflowInput`) → `static_output` (normalized; the flat form `[{name, type}]` becomes
  `[{"fields": […]}]`) — with `schema_source: "declared"`. `validate_edges` now sees
  these nodes, so the "source with no known schema" above became restricted to those that declare no
  output in any form.
- **Reserved keys**: consumers must skip every key that starts with `__`
  (`__edge_diagnostics__`, `__report__` and whatever comes next) when iterating the schemas by `node_id`.
- **Where strict enforcement lives: in STATIC validation (`/validate`), not in the run.** The
  run is resilient on purpose — a `from_key` with no match **omits** the port (it does not
  raise), so that an optional/dynamic output or a skipped parent does not bring down a legitimate
  workflow in production (see §4). The static check has the declared schema at hand and can
  flag the stale `from_key` BEFORE running, with no risk of a false positive.
- **Enforcement at WRITE time** (create/update) is **not** done — it would block saving
  broken drafts; `/validate` reports and the run tolerates.

## 8. Phases / PRs (reordered after the blast-radius validation)

> **Current state (verified against the code):** PR 1, PR-A, PR-B, PR-C and PR-D are
> IMPLEMENTED and merged. The PR-E backend (`/workflows/validate` + `validate_edges`)
> is too. Only PR-E front-end items remain (see the markings below and §6). The order
> below describes the historical sequencing; it is no longer an open backlog. The robust
> validation of `/validate` (lint + structured 422 + declared outputs, §7) came in later, in
> PR 3 of the MCP's Phase 0 (`docs/specs/mcp-server.md` §6.3).

Without the migration layer, the order went from the most isolated to the most coupled. The real coupling
is SEMANTIC — strict × empty skipped parent —, so strict came in LAST, after
skip (PR-B) and routing (PR-C) were already correct.

- **PR 1 — Single resolver (DONE).** `Edge` + `edge_resolver`
  (`flow/executor/edge_resolver.py`), the two sites in `core.py`, run × preview parity
  (includes the empty parent, F3/F12). Risk: low.
- **PR-A — Graph robustness (F1) — DONE.** An orphan edge (`source`/`target` ∉ `node_defs`)
  is discarded and logged in `graph.py` (`_index_edges:44-58`; the same guard in
  `compute_order:70-79`). It no longer brings down the run. Risk: low.
- **PR-B — Skip fix (F2) — DONE.** `skipped` is only marked when there is NO live parent
  with output: the run tracks `has_live_input` (`core.py:558`, set at `:662`, honored in
  `_propagate_skip:711`), independent of the batch order. Risk: medium.
- **PR-C — Routing by `Edge.is_branch` (F7/F8) — DONE** (code); hygiene pending.
  `core.py:637-646` routes only when branch edges exist
  (`Edge.from_dict(e).is_branch`, `condition` bool) AND `outputs["branch"]` is a bool (kills F7); it keeps
  ALL data edges active and deactivates only branch edges with `condition != branch`
  (kills F8). **Pending (hygiene):** the stale comments in
  `conditional.py`/`jinja_branch.py`/`change_detector.py` ("branch is born without from_key" — today
  it is born WITH it) have NOT been fixed yet (verified: the comment is still in
  `conditional.py:252-258`). Risk: medium.
- **PR-D — Strict + retires `auto_map_edges` (F5/F14 + §4/§5) — DONE.** The run no longer
  guesses: a `from_key` with no match **omits** the port (`edge_resolver.py:78-92`, end of the blind
  `_first_value`); a skipped parent drops the edge (`core.py:593`, via the `node_stats` status);
  Switch emits all buckets, empty ones included (`switch.py:145-172`). `auto_map_edges`
  removed — `node_manager.py` only has `instantiate_nodes`; see the comment in
  `core.py:158-162`. `resolve_edge_schema_inputs` aligned on the same axis (`core.py:852`).
  Risk: medium-high.
- **PR-E — Validation + web (F9/F10/F11 + types).** **Backend DONE:**
  `/workflows/validate` returns `__edge_diagnostics__` via `validate_edges()`
  (`validate_service.py::validar_definicao`, `core.py:861-918`); F11 (`schema == []`) guarded at
  `core.py:850-851`. **Front end — partial:** F9 (sync `sourceHandle` when switching
  `from_key`) DONE in `custom-edges/index.tsx:117,127`; F10 (history baseline on load)
  DONE in `useCanvasHistory.ts`. **Still pending:** enable the picker on branch edges
  (`canSwitch` still excludes `true/false` handles, `custom-edges/index.tsx:99`) and type
  `AtlansEdgeData` (§6). Risk: low.
- **Validation in `/validate`: lint + structured 422 + declared outputs — DONE (PR 3 of the
  MCP's Phase 0, `docs/specs/mcp-server.md` §6.3).** Pre-checks before building the
  executor (`unknown_node`/`duplicate_node_id`/`cycle`/`construction_error` → 422
  `invalid_definition`), `__report__` always present with error/warning codes,
  `schema_source: "declared"` for a `dynamic_output` node without `simulate()`, optional `workspace_id`
  with the dispatch's credential scope, and a database session only when there is something to
  check (§7). It does not replace validation on the canvas (§6, still PENDING): the visual marking of the
  ambiguous edge remains a front-end item.

Each PR was mergeable on its own and reversible.

## 9. Test plan

- `edge_resolver` unit tests: the modes (from_key found / only to_key / spread) + branch; under
  strict, a `from_key` with no match → omits the port (nothing), skipped parent → edge absent. The
  undeclared `from_key` as an error is tested in `/validate` (`validate_edges`).
- Switch regression: an empty bucket in a legitimate run does NOT blow up (Switch emits all the
  buckets) and does NOT deliver data from another bucket (F5).
- Fork regression: reproduce the `dca88dc` case (data × boolean) and lock it in; a plain node
  that emits a raw `branch` does NOT hijack routing (F7); a data edge leaving a branch node
  is not deactivated (F8).
- Diamond/merge regression: a node with a live parent + a skipped parent is NOT skipped (F2, determinism
  independent of the batch order).
- Orphan edge: the run does not blow up with `KeyError`; the edge is ignored and logged (F1).
- Run × simulation parity: for the same graph, the run's keys == the preview's keys —
  **including an empty parent and a `from_key` with no match** (both OMIT the port, `{}` == `{}`).
- Web E2E: connecting a multi-output source → `from_key` written; switching `from_key` via the picker
  keeps `sourceHandle == from_key` (F9); the 1st edge edit is undoable (F10).

## 10. Risks & rollback

- **No migration**: a legacy edge without `from_key` becomes a silent spread when
  `auto_map_edges` is removed — it can deliver wrong data without an error. Mitigation: a spread `warning` with a
  multi-output parent (§5); the few affected workflows are fixed by hand.
- **strict × skipped parent**: `core.py:575-585` assembles inputs over ALL incoming
  edges, including those from skipped parents (`output = {}`). Strict has to treat the
  empty/skipped parent as "does not contribute", never "missing key" — otherwise every diamond with
  `from_key` on the losing branch's merge edge fails. That is why PR-D comes after PR-B.
- **Run × preview divergence**: changing the run to strict without aligning `resolve_edge_schema_inputs`
  reopens the bug that PR 1 closed — the two go in the same PR (PR-D).
- **`static_output` order**: the defense in the control nodes only goes away after routing
  starts gating on `Edge.is_branch` (PR-C).

## 11. Success

- One resolver; zero run × preview divergence.
- 0 uses of a blind `next(iter(...))` on the edge axis; the run omits instead of guessing, and the
  undeclared `from_key` becomes an error in `/validate` (not a crash in the run).
- Routing gated by `Edge.is_branch`; control nodes without a comment saying "order the
  static_output or the boolean leaks".
- An orphan edge does not bring down the run; a merge does not skip a node with a live parent.
- Edge with a typed model in engine and web.

## 12. Lifecycle validation findings (history — RESOLVED)

Adversarial review of the edge's entire lifecycle (front end → graph → resolver → branch/
skip → consumption → sub-workflow). The two findings **inside PR 1** (F3 parity with an empty parent;
F12 policy for a missing `from_key`) were fixed/documented above. The pre-existing ones
below were the prioritized backlog; **all have already been implemented** — the table is historical.
The `Sintoma` (Symptom) column describes the ORIGINAL bug (pre-fix); the `Corrigido em` (Fixed in) column points to the
CURRENT code (the backlog's old line numbers no longer apply).

| # | Sev | Symptom (original) | Fixed in | Status |
|---|-----|--------------------|--------------|--------|
| F1 | **high** | Orphan edge (nonexistent source/target) → `KeyError` in `compute_order`/instantiation brought down the run. Real case: the front end deletes a node and leaves the edge; sub-workflow expansion. | `flow/core/graph.py:44-58` (discards+logs) and `:70-79` | ✅ resolved (PR-A) |
| F2 | **high** | Diamond/merge: `_propagate_skip` zeroed `pending` and skipped the node even with a LIVE parent having delivered data — dependent on the batch order. | `flow/executor/core.py:558,662,711` (`has_live_input`) | ✅ resolved (PR-B) |
| F7 | medium | Any node that emitted a boolean `branch` key hijacked routing; edges without `condition` became inactive → downstream skipped. | `flow/executor/core.py:639-646` (gate on branch edges) | ✅ resolved (PR-C) |
| F8 | medium | An edge without a bool `condition` leaving a fork node was always deactivated (`None != branch`). Same block as F7. | `flow/executor/core.py:643-646` | ✅ resolved (PR-C) |
| F5 | medium | A nonexistent `from_key` fell back to the 1st value: a Switch (`dynamic_output`) with an empty bucket crossed in data from the wrong bucket, silently. | `flow/executor/edge_resolver.py:78-92` (omits; returns `{}`) + `switch.py:145-172` (emits empty buckets) | ✅ resolved (PR-D) |
| F14 | low | Skipped parent + edge with `from_key` injected a named `None` into the merge. Same cascade as F5. | `flow/executor/core.py:593` (drops the edge) + `edge_resolver.py:78-92` | ✅ resolved (PR-D) |
| F11 | medium | `schema == []` (e.g. `SubWorkflowInput/Output`, `static_output:[]`) → `IndexError` in the simulation marked the child as `error` and cascaded. | `flow/executor/core.py:850-851` (normalizes an empty list) | ✅ resolved (PR-E backend) |
| F9 | medium | Switching `from_key` via the badge did not update `sourceHandle`: after a reload the multi-output edge was redrawn from the wrong port. | `web/.../custom-edges/index.tsx:117,127` (`sourceHandleDaChave`) | ✅ resolved (PR-E) |
| F10 | medium | No baseline snapshot on load: the FIRST edge edit was not undoable. | `web/app/hooks/workflow/useCanvasHistory.ts` (post-hydration baseline) | ✅ resolved (PR-E) |

Front-end items that REMAIN open (see §6): enable the `from_key` picker on branch
edges (`custom-edges/index.tsx:99`); visual marking of an ambiguous edge on the canvas; type
`AtlansEdgeData`; and the hygiene of the "branch is born without from_key" comments in
`conditional.py`/`jinja_branch.py`/`change_detector.py` (PR-C).
