# app/mcp/guardas.py
"""
The tool → guard table: the single source of who may call what.

Each tool has exactly one row here, and that row is read by three consumers:
`list_tools` (hides from the catalog what the token does not reach),
`call_tool` (refuses the call with `forbidden_scope` and applies the quota) and
the documentation. Keeping them reading the SAME structure is what prevents the
classic case — the tool disappears from the list but remains callable, or the
doc promises one scope and the code requires another.

Fields:
- `escopo`: the required PAT scope (None = none; no tool without a scope exists
  today, but the field is optional for the case of a purely informational tool);
- `papel`: MINIMUM role in the workspace. The guard does not enforce it — what
  knows the call's workspace is the tool, which calls `exigir_papel`. The field
  stays here for the documentation and for the parity tests.
  One exception, and it is deliberate: `cancel_run` does not call
  `exigir_papel`, because the check lives inside
  `workflow_execution_service.cancel_run`, next to the SELECT that loads the
  run. It was moved there on purpose — before, it lived only in the REST route,
  and any other caller (a tool here, a script, a job) could cancel any
  account's run. Repeating it in the tool would cost one more query and reopen
  the chance of the two copies diverging. What guarantees it stays there is
  `test_cancelar_com_papel_de_viewer_e_recusado_pelo_servico_de_verdade`, the
  only cancellation test that does not stub the service;
- `cota`: extra rate limit bucket ("validate", "run"); None = only the general one;
- `read_only` / `idempotente`: become `readOnlyHint`/`idempotentHint` in the
  tool's annotations. `destructive_hint` is always False: the Atlans MCP
  deletes nothing;
- `open_world`: becomes `openWorldHint`. False for everything except the two
  source catalog tools that PROBE a WFS (`probe_source`, `register_source`) —
  they talk to the open internet, through the server, with an SSRF guard, a
  byte ceiling and the `probe` bucket. Lying `False` there would misinform a
  client that decides by the hint.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Guarda:
    escopo: str | None
    papel: str | None
    cota: str | None
    read_only: bool
    idempotente: bool
    # Default at the end: the existing rows remain intact.
    open_world: bool = False


# The 42 tools, in eight blocks: catalog reading (11), building (5),
# execution (7, of which three write — `run_workflow`, `cancel_run` and
# `retry_run`), collection (5, of which two write — `restore_workflow_version`
# and `duplicate_workflow`), pins (3, of which two write), triggers (4, of
# which three write), Drive writing (3, all writes) and sources (4, of
# which one writes — `register_source`). Adding
# here without registering the tool (or the other way around) breaks the parity
# test, which is exactly the point.
#
# Reading runs (`get_run`, `list_runs`, `get_run_artifacts`) requires
# `workflows:read` + member, and not `runs:execute`: it is the same requirement
# as REST, where `/observability` only requires being a member of the run's workspace.
# Requiring `runs:execute` to READ would force granting permission to fire to
# those who only follow along — and a scope wider than necessary is the opposite
# of what the table exists to guarantee.
GUARDAS: dict[str, Guarda] = {
    "list_workspaces":        Guarda("workflows:read",  None,       None,       True,  True),
    "list_workflows":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_workflow":           Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_workflow_contract":  Guarda("workflows:read",  "viewer",   None,       True,  True),
    "search_nodes":           Guarda("workflows:read",  None,       None,       True,  True),
    "describe_node":          Guarda("workflows:read",  None,       None,       True,  True),
    "list_credentials":       Guarda("workflows:read",  "viewer",   None,       True,  True),
    "list_drive_files":       Guarda("drive:read",      "viewer",   None,       True,  True),
    # Not idempotent: each call signs a new URL, with its own validity.
    "get_drive_download_url": Guarda("drive:read",      "viewer",   None,       True,  False),
    "get_portal_info":        Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_authoring_guide":    Guarda("workflows:read",  None,       None,       True,  True),
    # Building. `validate_workflow` stores nothing, but it simulates the workflow
    # (reads credentials, builds the executor payload) — that is why it is not
    # read_only and pays the `validate` bucket, which is what prevents sweeping
    # the platform by brute-force validation. Create and update are not
    # idempotent: repeating the call creates another workflow or another version.
    "validate_workflow":      Guarda("workflows:write", "editor",   "validate", False, True),
    "create_workflow":        Guarda("workflows:write", "editor",   "validate", False, False),
    "update_workflow":        Guarda("workflows:write", "editor",   "validate", False, False),
    "set_workflow_active":    Guarda("workflows:write", "editor",   None,       False, True),
    "set_portal_access":      Guarda("workflows:write", "editor",   None,       False, True),
    # Execution. The `run` bucket adds to the general one, and the wait (`wait`)
    # also goes through the simultaneous wait ceiling — dispatching is the most
    # expensive call the server offers.
    "run_workflow":           Guarda("runs:execute",    "operator", "run",      False, False),
    "get_run":                Guarda("workflows:read",  "viewer",   None,       True,  True),
    "list_runs":              Guarda("workflows:read",  "viewer",   None,       True,  True),
    # Not idempotent: the artifact URLs are signed on the spot, with an expiry.
    "get_run_artifacts":      Guarda("workflows:read",  "viewer",   None,       True,  False),
    # Phase 2 — runs. Reading the log is a read, like the rest of observability.
    # Canceling and re-running touch what is running: they require `runs:execute`
    # and `operator`, the same pair as firing.
    "get_run_events":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    # Idempotent by EFFECT, not by response: asking the same executor for the
    # interruption twice does not interrupt twice. The response may vary — a run
    # already delivered is closed back by the executor, so both calls usually
    # answer `requested`, and neither of them is the end. read_only is False
    # because the call interrupts real work.
    "cancel_run":             Guarda("runs:execute",    "operator", None,       False, True),
    # Not idempotent, and that is the point: each call FIRES another run. Pays the
    # `run` bucket for the same reason as `run_workflow` — it is a dispatch.
    "retry_run":              Guarda("runs:execute",    "operator", "run",      False, False),
    # Phase 2 — collection. Reading the history and what the runs produced is a
    # read, like the rest; restoring and duplicating write, and require `editor`.
    "list_workflow_versions": Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_workflow_version":   Guarda("workflows:read",  "viewer",   None,       True,  True),
    # Not idempotent, and the reason is the auto-snapshot: each call stores a new
    # version before swapping. Restoring twice in a row leads to the same state,
    # but leaves two snapshots in the history — the effect on the database differs.
    "restore_workflow_version": Guarda("workflows:write", "editor", None,       False, False),
    # Not idempotent for the same reason as `create_workflow`: each call
    # produces a new workflow, with a new id.
    "duplicate_workflow":     Guarda("workflows:write", "editor",   None,       False, False),
    # Not idempotent: the download URLs are signed on the spot, with an expiry —
    # same reason as `get_run_artifacts`.
    "list_artifacts":         Guarda("workflows:read",  "viewer",   None,       True,  False),

    # ── Pins ────────────────────────────────────────────────────────────────
    # The two write tools ARE idempotent, unlike the server's other writes:
    # pinning an already pinned node rewrites the same entry, and unpinning an
    # already unpinned node does nothing. Neither accumulates state on each
    # call — that is what sets these apart from `restore_workflow_version`,
    # which leaves a new snapshot in the history every time.
    #
    # `pin_node_output` rewrites `pinned_at`/`expires_at` on each call, but
    # that is the VALUE of the same field and not a new row: repeating the call
    # still leads to the same state, which is what the hint promises to whoever
    # decides whether it is safe to repeat.
    "list_pins":              Guarda("workflows:read",  "viewer",   None,       True,  True),
    "pin_node_output":        Guarda("workflows:write", "editor",   None,       False, True),
    "unpin_node_output":      Guarda("workflows:write", "editor",   None,       False, True),

    # ── Triggers ────────────────────────────────────────────────────────────
    # The three write tools require `operator`, not `editor`: SCHEDULING IS
    # EXECUTING. A one-minute schedule fires the workflow with the owner's
    # credentials, indefinitely — it is the same yardstick as `run_workflow`, and
    # the same one the REST route applies (`workflow_com_papel(ROLE_OPERATOR)` in
    # `schedules_router`).
    #
    # `create_schedule` is not idempotent: each call creates a new `job_id`, and
    # repeating after a network error would leave TWO schedules firing the
    # same workflow. The other two address a `job_id` that already exists, so
    # repeating leads to the same state.
    "list_schedules":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    "create_schedule":        Guarda("triggers:manage", "operator", None,       False, False),
    "update_schedule":        Guarda("triggers:manage", "operator", None,       False, True),
    "delete_schedule":        Guarda("triggers:manage", "operator", None,       False, True),

    # ── Drive writing ───────────────────────────────────────────────────────
    # `editor`, not `operator`: adding and removing files is changing the
    # workspace's collection, not firing a run. Same yardstick the REST route
    # applies (`exigir_papel_no_workspace(..., ROLE_EDITOR)` in `drive_router`).
    #
    # `create_drive_upload_url` is not idempotent because each call creates a new
    # pending ROW and signs a new URL — repeating after a network error would
    # leave orphan pending records until the cleanup runs. The other two
    # address a `file_id` that already exists.
    "create_drive_upload_url": Guarda("drive:write",     "editor",   None,       False, False),
    "confirm_drive_upload":    Guarda("drive:write",     "editor",   None,       False, True),
    "delete_drive_file":       Guarda("drive:write",     "editor",   None,       False, True),

    # ── Sources ─────────────────────────────────────────────────────────────
    # The catalog of pre-mapped sources: what the assistant consults BEFORE
    # prospecting. Searching and describing are pure reads, no network.
    # `probe_source` does not create a source, but it UPDATES the state/schema of
    # an already cataloged one and talks to the internet (one of the server's only
    # two open-world tools): that is why it is not read-only, requires
    # `workflows:write` and pays the `probe` bucket — the same logic as
    # `validate_workflow`, which also stores nothing and is also not read-only.
    # `register_source` probes AND stores in the workspace's collection:
    # `editor`, the Drive writing yardstick. All four are idempotent — the
    # same URL+layer lands on the same row, and probing twice reads the same.
    "search_sources":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    "describe_source":        Guarda("workflows:read",  "viewer",   None,       True,  True),
    "probe_source":           Guarda("workflows:write", "editor",   "probe",    False, True, open_world=True),
    "register_source":        Guarda("workflows:write", "editor",   "probe",    False, True, open_world=True),
}
