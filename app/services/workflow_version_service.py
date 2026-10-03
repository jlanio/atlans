# app/services/workflow_version_service.py
# Workflow version management.

import copy

from sqlalchemy.orm.attributes import set_committed_value

from app.core.utils.logger import get_logger

from app.core.exceptions import WorkflowNotFoundError
from app.core.scheduling.hooks import apply_schedule_if_needed
from app.core.utils.encryption import (
    decrypt_workflow_connections,
    encrypt_workflow_connections,
)
from app.core.utils.redacao import redigir_definition
from app.crud.workflow_crud import WorkflowCRUD
from flow.utils.workflow_contract import _node_properties

_logger = get_logger(__name__)


def _has_substantial_changes(old_def: dict, new_def: dict) -> bool:
    """Returns True only if there were substantial changes to the workflow definition:
    nodes added/removed, connections changed or properties modified.
    Moving nodes (position) is not considered substantial.
    """
    old_nodes: dict = {n["id"]: n for n in old_def.get("nodes", [])}
    new_nodes: dict = {n["id"]: n for n in new_def.get("nodes", [])}

    # Nodes added or removed
    if set(old_nodes.keys()) != set(new_nodes.keys()):
        return True

    # Connections (edges) changed
    def _edge_key(e: dict) -> tuple:
        return (e.get("source"), e.get("target"), e.get("sourceHandle"), e.get("targetHandle"))

    old_edges = {_edge_key(e) for e in old_def.get("edges", [])}
    new_edges = {_edge_key(e) for e in new_def.get("edges", [])}
    if old_edges != new_edges:
        return True

    # Properties of some node changed. The PERSISTED/PUT definition is flat
    # (`{id, name, type, properties, position}` — no `data` wrapper, see
    # `montarPayloadDoGrafo` in the web app), so reading `node["data"]["properties"]`
    # on each side saw `{}` vs `{}` and a property-only edit (changing the cron,
    # the URL of an HttpRequest, the SQL, the credential_id) never became a
    # version. `_node_properties` accepts both formats (the flat production one
    # and the `data.properties` that only the fixtures build).
    for node_id, new_node in new_nodes.items():
        old_props = _node_properties(old_nodes[node_id])
        new_props = _node_properties(new_node)
        if old_props != new_props:
            return True

    return False


async def list_versions(crud: WorkflowCRUD, id_hash: str):
    """Lists all versions of a workflow."""
    wf = await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")
    return await crud.get_versions(id_hash)


async def get_version(crud: WorkflowCRUD, id_hash: str, version_number: int):
    """Returns a specific version with the definition REDACTED.

    Whoever consumes this (today the MCP `get_workflow_version` tool; before,
    the `GET /workflows/{id}/versions/{n}` route) requires no role beyond
    belonging to the workspace — so it handed the `connectionString` in plain
    text to any `viewer`. Reading the history is legitimate for read-only
    users; knowing the production database password is not, and restoring a
    version does not need it either (`restore` copies the encrypted blob
    without opening it).

    Decryption still happens, and before redaction, for one reason: it is what
    exposes a corrupted token with an explicit error. Redacting the encrypted
    value directly would hide the corruption until the next execution.

    SEC: none of this touches the session's LIVE row. It used to be a direct
    assignment (`v.definition = decrypt(...)`) — any later commit in the same
    request would write the connection string in plain text to the versions
    table, undoing the encryption at rest of a history nobody ever rewrites.
    `set_committed_value` stores the value as if it had come from the database
    that way: the flush sees no difference at all and emits no UPDATE.

    The `deepcopy` covers the other half: `decrypt_workflow_connections` writes
    into the dict it receives, and that dict is the same object the loaded row
    holds — the same one `restore_version` goes as far as assigning directly to
    the workflow. Working on a copy leaves the original encrypted for any place
    that already holds a reference to it.

    And the `expunge` closes the last one: without it the redaction would be
    written into the LIVE instance of the identity map, and a `restore_version`
    in the SAME session would get that same instance back and write
    `"<REDACTED>"` into the workflow's definition — trading the credential leak
    for its silent DESTRUCTION. Today the REST API does not reach this (each
    request has its own session, and no route does both things), but the MCP
    server tools open ONE session and chain operations on it: reading a version
    and restoring it is exactly the pair that would fall into this trap.
    Detached, the row serializes the same and a following `get_version`
    re-reads the encrypted value from the database.
    """
    v = await crud.get_version(id_hash, version_number)
    if not v:
        raise WorkflowNotFoundError(
            f"Versão {version_number} do workflow {id_hash} não encontrada"
        )
    try:
        em_claro = decrypt_workflow_connections(copy.deepcopy(v.definition))
    except Exception as e:
        _logger.error(
            "Falha ao descriptografar versão %s do workflow %s: %s",
            version_number, id_hash, e
        )
        raise ValueError(
            f"Não foi possível descriptografar a versão {version_number} do workflow {id_hash}."
        ) from e
    crud.db.expunge(v)
    set_committed_value(v, "definition", redigir_definition(em_claro))
    return v


async def restore_version(crud: WorkflowCRUD, id_hash: str, version_number: int):
    """Restores the workflow definition to an earlier version.

    Restoring swaps the entire definition — including the ScheduleTrigger.
    Without syncing the schedules, going back to a version with a different
    cron (or with no schedule node at all) left the old Schedule in effect in
    the database: the canvas showed one thing and the AsyncScheduler fired on
    another. It is the same "zombie scheduler" that `update_workflow` already
    closes on a normal save.
    """
    v = await crud.get_version(id_hash, version_number)
    if not v:
        raise WorkflowNotFoundError(
            f"Versão {version_number} do workflow {id_hash} não encontrada"
        )
    wf = await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")
    # Snapshot of the current version before restoring.
    #
    # `get_by_hash` (no decrypt) does NOT guarantee that `wf.definition` is
    # encrypted: this route's dependency has already called
    # `get_workflow_by_hash`, which does
    # `wf.definition = decrypt_workflow_connections(...)` — an in-place mutation
    # on the live row. Being the same session, the SAME Python object comes back
    # here, already in plain text, and the snapshot would write the credential in
    # readable form to `workflow_versions`. Encrypting explicitly solves it in
    # both states, because `encrypt_workflow_connections` skips what already
    # starts with `gAAAA`. Same remedy as in `update_workflow` and
    # `workflow_move_service._aplicar`.
    await crud.create_version(
        workflow_hash=id_hash,
        definition=encrypt_workflow_connections(copy.deepcopy(wf.definition or {})),
        change_note=f"Auto-snapshot antes de restaurar para versão {version_number}",
    )
    # Restores: the definition stored in the version is already encrypted
    wf = await crud.update(wf, {"definition": v.definition})

    # The encrypted definition goes to the hook as is, on purpose: it reads only
    # the `properties` of the ScheduleTrigger node, which are not encrypted, and
    # `decrypt_workflow_connections` writes into the dict it receives —
    # decrypting here would mark the row as dirty and the next commit would write
    # the connection string in plain text.
    #
    # Best-effort as in the other call sites: a scheduling failure must not undo
    # a restore that has already been committed.
    #
    # But swallowing it silently is no good either: `update_workflow` returns
    # `schedule_notices` precisely so the screen can say "restored, and the cron
    # did not sync". Without it, whoever restores a version with a schedule sees
    # success and finds out days later that the routine stopped — the symptom of
    # a broken schedule is silence.
    #
    # `schedule_notices` is a TRANSIENT attribute on the ORM object, not a
    # column: a `db.refresh` wipes it. That is why it is set last, and whoever
    # reads it picks it up right away (`WorkflowRead.schedule_notices`).
    schedule_notices = []
    try:
        schedule_notices = await apply_schedule_if_needed(wf, wf.definition, crud.db) or []
    except Exception as exc:
        _logger.warning(
            "Falha ao sincronizar agendamento ao restaurar versão %s do workflow %s: %s",
            version_number, id_hash, exc,
        )
        schedule_notices = [
            "O agendamento não pôde ser sincronizado com a versão restaurada. "
            "Abra e salve o fluxo para tentar de novo."
        ]

    wf.schedule_notices = schedule_notices
    return wf
