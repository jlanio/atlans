# Run-scoped storage access (security follow-up)

**Status:** open — plan agreed, not implemented.

## Problem

The executor's storage endpoints authorize by the **executor's workspace**, not
by the **run's workspace**. Since `get_agent_workspace_ids` returns *all*
workspaces when `is_default=True` (`app/services/user_executor_service.py`) and
every workflow without `target_agent_id` is routed to the default executor, the check is
always true on that path. In practice the file's `id_hash` (or the `s3_key`)
works as a portable credential: whoever knows it can read it — from any workspace.

There is no validation of the id's origin: `driveFileId` goes raw from the workflow's JSON
definition to the node. The only place in `app/` that even inspects the field is the
move report (`app/services/workflow_move_report.py`, which defines
`_DRIVE_ID_PROP = "driveFileId"` and emits `drive_refs_out_of_scope`) — at no
point in reading a file is the id validated against the run's workspace.

### Scenario without guessing ids

1. A person is a member of workspaces **X** and **Y** and legitimately sees, in Y's
   UI, the ids of the Drive files.
2. They create a workflow **in X** with the `driveFileId` of a file from **Y**, wired
   to a `DataOutput`.
3. X's run requests the file; the server delivers it (default executor → all
   workspaces); Y's data becomes an artifact **of X**, visible to members of X who
   never had access to Y.

Variant: the person is **removed from Y** and the ids they wrote down keep working
from any workflow in X — revoking access revokes nothing.

### Interaction with the workflow move

`POST /workflows/{id}/move` makes this path easier to exercise **without ill
intent**: a legitimate workflow, with the `driveFileId` of files from workspace A,
starts running in workspace B and keeps reading A's files — because the
default executor sees every workspace. The move warns about this
(`drive_refs_out_of_scope`), but the warning is informational: whoever ignores it ends up with a
workflow that reads data outside its own tenant.

This does not change the fix proposed below, it only increases the chance of the scenario
showing up in normal use. When per-run enforcement lands, these workflows will start
failing visibly — which is the desired behavior.

### Historical note

The correct rule used to exist in the code: `wf.workspace_id != workspace_id →
PermissionError`, inside `_resolve_server` in the `drive_resolver`. It was in two
wrong places — in an unreachable branch (the engine never runs on the server) and on
the client side, where the executor checked itself. The branch was
removed in the cleanup of the in-server mode; the intent needs to come back, now on the
server and derived from data that the client does not choose.

## Affected endpoints

All in `app/api/routers/drive_router.py`:

| Endpoint | Current authorization | Used by |
|---|---|---|
| `GET /drive/executor-download/{id_hash}` | `wf.workspace_id in executor._resolved_ws_ids` | Drive readers, DataInput |
| `GET /drive/executor-download-artifact/{id_hash}` | `artifact.workspace_id in ...` | DataInput (Artifacts context) |
| `POST /drive/executor-presign-download` | `svc.presign_download` — its own check (workspace segment for `pin-cache/`+`artifacts/`, lookup in `WorkspaceFile` for `drive/`) | pin cache, send_email (link mode) |
| `POST /drive/executor-presign-upload` | `_validate_agent_s3_key` (workspace segment in the s3_key) | pin cache, response_node, artifacts |
| `POST /drive/executor-upload-url` | `_validate_agent_s3_key` + `ws_id in ...` | DataOutput with a Drive entry |

## Proposed fix

The executor sends the run (`task_id`, already available as `self._task_id` in every node
— see `flow/nodes/base.py`) and the server derives the authorization from the
`WorkflowRun` row itself, without trusting the value sent for anything beyond the lookup:

1. load the `WorkflowRun` by `task_id`;
2. check that `run.host == f"executor:{executor.id_hash}"` — the run was dispatched
   to *this* executor (the same cross-check that `_query_run_belongs_to_agent` already does
   in `executor_ws_router.py`);
3. check that the resource belongs to `run.workspace_id` (instead of "some
   workspace of the executor").

> Key layout (anchor for step 3): the accepted prefixes are `drive/`,
> `pin-cache/` and `artifacts/`, all in the format `{prefixo}/{workspace_id}/…`
> (artifacts as `artifacts/{workspace_id}/{task_id}/arquivo`). It is this embedded
> `{workspace_id}` — today compared against "some workspace of the executor" —
> that the per-run check will compare against `run.workspace_id`.

The reference pattern already exists in `_authorize_key`
(`app/api/routers/change_detector_router.py`), which resolves the workflow's workspace
before releasing the key.

## Rollout

Executors are external/on-premise and update independently: if the
server starts **requiring** the `task_id` right away, every executor that has not yet
upgraded breaks on any Drive read. Three steps:

1. The **executor** starts sending the `task_id` (header or query) on the five endpoints.
2. The **server** accepts the field as optional: when present, it applies the per-run
   check; when absent, it keeps the current behavior and logs at `warning` with
   the `executor_id` and the `executor_version` from the handshake.
3. **Enforcement** once the logs show the fleet has been updated — the
   `executor_version` arrives in the handshake (`executor_ws_router.py`), so it is possible to
   gate on a minimum version instead of a date.

## Related minor items

- `local_fallback=True` (in `flow/utils/artifact_helpers.py`) returns the MinIO
  `s3_key` even when the upload failed and the artifact stayed only on the executor's
  disk. The server records an `Artifact` pointing to a nonexistent object.
  The flag is informational today — the server could use it to mark the artifact.
- `count_orphaned_pinned_artifacts` (`app/core/storage_reconciliation.py`) only
  audits orphaned pins of deleted workflows; it does not remove them.
