# app/services/workflow_move_service.py
"""Moving a workflow between workspaces.

The tenant change does not go through `PUT /workflows/{id}`: `WorkflowUpdate`
excludes `workspace_id` on purpose, because there authorization is resolved
against the workspace PRIOR to the change — someone editing their own workflow
could push it into somebody else's workspace. This is the dedicated route that
comment asks for, and it requires the admin/owner role on BOTH sides (see the
router).

The move never fails because of a broken dependency: whatever stops working at
the destination comes out as a warning (`workflow_move_report`). In exchange,
whatever is a deterministic consequence of the tenant change is applied here,
without asking — schedule turned off, portal disabled, group and pins cleared.
"""

import copy
from uuid import uuid4

from sqlalchemy import select as sa_select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    WorkflowMoveTargetError,
    WorkflowNameConflictError,
    WorkflowNotFoundError,
)
from app.core.scheduling.hooks import disable_schedule_node
from app.core.utils.encryption import decrypt_workflow_connections, encrypt_workflow_connections
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.models import Schedule, Workflow
from app.services.workflow_move_report import collect_warnings, warn

_logger = get_logger(__name__)


async def nomes_no_workspace(db, workspace_id: str) -> set[str]:
    """Names already taken in the workspace. Shared with duplication."""
    return {
        n for (n,) in (
            await db.execute(
                sa_select(Workflow.name).where(
                    Workflow.workspace_id == workspace_id,
                    Workflow.deleted_at.is_(None),
                )
            )
        ).all()
    }


# `workflows.name` is String(255). A disambiguation suffix on a name already at
# the limit would overflow the column, and DataError is not IntegrityError — it
# would escape the retry as a 500, precisely in the operation that promises not
# to fail.
_MAX_NOME = 255


def _com_sufixo(base: str, sufixo: str) -> str:
    """`base (suffix)`, shortening the base if the result exceeds 255 chars."""
    excedente = len(base) + len(sufixo) + 3 - _MAX_NOME
    if excedente > 0:
        base = base[: max(1, len(base) - excedente)]
    return f"{base} ({sufixo})"


def nome_livre(base: str, existentes: set[str]) -> str:
    """First free name starting from `base`: "X", "X (2)", "X (3)"…

    There is a UniqueConstraint(name, workspace_id): without disambiguation,
    moving to a workspace that already has a workflow with the same name would
    blow up with IntegrityError — and the contract of this feature is that the
    move does not fail because of that.

    The ceiling and the random suffix repeat what `_nome_de_copia` already does
    for duplication: an ugly name is preferable to a 409 in the user's face.
    """
    base = base[:_MAX_NOME]
    if base not in existentes:
        return base
    for i in range(2, 100):
        tentativa = _com_sufixo(base, str(i))
        if tentativa not in existentes:
            return tentativa
    return _com_sufixo(base, uuid4().hex[:6])


async def move_workflow(
    crud,
    id_hash: str,
    target_workspace_id: str,
    *,
    new_name: str | None = None,
    moved_by_id: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Moves the workflow to `target_workspace_id` and returns the report.

    With `dry_run=True` nothing is written — it serves the preview the dialog
    shows before confirming.

    MIND THE DEFINITION: `decrypt_workflow_connections` mutates the dict in
    place, and the route's dependency (`get_accessible_workflow_with_role`) has
    already called `get_workflow_by_hash`, which decrypts. Since the session is
    the same, the identity map object may arrive here WITH the connectionString
    in plain text. Today this does not leak because nobody rewrites the column;
    this method does. That is why every write goes through
    `encrypt_workflow_connections`, which is idempotent — swapping
    `get_workflow_by_hash` for `get_by_hash` is not enough.
    """
    db = crud.db

    wf = await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

    origin_ws = wf.workspace_id
    if target_workspace_id == origin_ws:
        # Invariant of the operation, not payload validation: moving to the same
        # workspace would not be a no-op — it would create a version, turn off
        # the schedule, delete pins and disable the portal. It lives here so that
        # any caller (route, batch cleanup, script) inherits the guard.
        raise WorkflowMoveTargetError("O workflow já está neste workspace.")

    # deepcopy BEFORE decrypting: the analysis must not touch the ORM object.
    definition_clara = decrypt_workflow_connections(copy.deepcopy(wf.definition or {}))

    warnings = await collect_warnings(db, wf, definition_clara, origin_ws, target_workspace_id)

    nome_desejado = (new_name or "").strip() or wf.name
    existentes = await nomes_no_workspace(db, target_workspace_id)
    nome_final = nome_livre(nome_desejado, existentes)
    renamed = nome_final != wf.name
    if nome_final != nome_desejado:
        warnings.insert(0, warn(
            "name_conflict",
            f"Já havia um workflow chamado '{nome_desejado}' no destino; "
            f"este foi renomeado para '{nome_final}'.",
            severity="info",
            requested_name=nome_desejado, final_name=nome_final,
        ))

    resultado = {
        "id": wf.id_hash,
        "name": nome_final,
        "renamed": renamed,
        "from_workspace_id": origin_ws,
        "to_workspace_id": target_workspace_id,
        "dry_run": dry_run,
        "warnings": warnings,
    }

    if dry_run:
        return resultado

    # Turn off the schedule in the definition. It goes in the same transaction as
    # the UPDATE on `schedules`, below. `definition_clara` is already a private
    # copy (nothing else reads it after this point), so the in-place mutation is
    # safe.
    disable_schedule_node(definition_clara)

    # `definition` encrypted only once: `encrypt_workflow_connections` mutates the
    # dict it receives, and reusing the result avoids depending on idempotence
    # between the two attempts.
    definition_cifrada = encrypt_workflow_connections(definition_clara)
    # Snapshot of the PREVIOUS state. Being explicit is not redundant: for the
    # reason in the docstring, `wf.definition` may be in plain text in the
    # session, and workflow_versions is a persisted table like any other.
    snapshot = encrypt_workflow_connections(copy.deepcopy(wf.definition or {}))
    pins_para_apagar = _pin_keys(wf.pinned_outputs)

    async def _aplicar(nome: str) -> None:
        """Writes everything that makes up the move. Re-runnable after a rollback.

        `create_version` only does a `flush`, and the UPDATE on `schedules` is
        DML in the same transaction — a rollback undoes both along with the
        workspace change. That is why the retry attempt has to repeat the whole
        block, not just rename: otherwise the workflow would end up moved
        without a version snapshot and, worse, with the schedule still active
        pointing at the new workspace.
        """
        await crud.create_version(
            workflow_hash=id_hash,
            definition=copy.deepcopy(snapshot),
            change_note=f"Movido do workspace {origin_ws} para {target_workspace_id}",
        )

        # Direct UPDATE on the table instead of `apply_schedule_if_needed`: the
        # ScheduleCRUD commits internally (it would break the transaction), the
        # function may delete and recreate the schedule, and `create_schedule`
        # refuses a deactivated workflow. Turning it off in both places is
        # mandatory — the AsyncScheduler ticks on `Schedule.active` in the
        # database, and the canvas reads the node's `active`.
        await db.execute(
            Schedule.__table__.update()
            .where(Schedule.workflow_hash == id_hash)
            .values(active=False, workspace_id=target_workspace_id)
        )

        # The pin's artifact rows follow the objects that will be deleted: they
        # would remain as dead downloads for the origin's members, and
        # `_upsert_pin_artifact` (which looks up by workflow_hash + node_id,
        # without filtering by tenant) would reuse the row for a future pin at
        # the destination, repointing it to an object there without changing
        # the `workspace_id`.
        await db.execute(
            Artifact.__table__.delete().where(
                Artifact.workflow_hash == id_hash,
                Artifact.is_pinned.is_(True),
            )
        )

        alvo = await crud.get_by_hash(id_hash)
        alvo.workspace_id = target_workspace_id
        alvo.name = nome
        alvo.group_id = None                # the group belongs to the origin workspace
        alvo.portal_access = "disabled"     # portal_shared_with lista o tenant antigo
        alvo.portal_shared_with = None
        alvo.pinned_outputs = None          # apontam para pin-cache/{ws_origem}/…
        alvo.pin_metadata = None
        alvo.definition = copy.deepcopy(definition_cifrada)
        if moved_by_id:
            alvo.updated_by_id = moved_by_id
        await db.commit()

    try:
        await _aplicar(nome_final)
    except IntegrityError as exc:
        await db.rollback()
        if "uq_workflow_name_workspace" not in str(exc.orig):
            raise
        # Real race: someone created a workflow with this name at the destination
        # between the check and the commit. A second attempt with a random suffix
        # solves it without returning 409 for an operation that promised not to
        # fail.
        _logger.warning(
            "Colisão de nome ao mover o workflow %s para %s; tentando sufixo único.",
            id_hash, target_workspace_id,
        )
        nome_final = _com_sufixo(nome_desejado[:_MAX_NOME], uuid4().hex[:6])
        try:
            await _aplicar(nome_final)
        except IntegrityError as exc2:
            # Colliding again with a random suffix is unlikely enough to indicate
            # something else; still, a readable 409 is better than letting the
            # IntegrityError escape as a 500.
            #
            # Filtering by the constraint name is not aesthetic symmetry with
            # the `except` above: without it, ANY IntegrityError from this second
            # attempt would become "no free name at the destination" — a
            # factually false message that sends you investigating the wrong
            # place. And it is even more necessary now that `create_version`
            # reconverges on its own: a violation that makes it here is now
            # genuinely unexpected, and labeling it as a name conflict would hide
            # precisely the new case.
            await db.rollback()
            if "uq_workflow_name_workspace" not in str(exc2.orig):
                raise
            raise WorkflowNameConflictError(
                "Não foi possível encontrar um nome livre no workspace de destino."
            ) from exc2
        resultado["name"] = nome_final
        resultado["renamed"] = True

    await _apagar_pins(pins_para_apagar)
    return resultado


def _pin_keys(pinned_outputs) -> list[str]:
    """The pins' s3_keys, for removal after the commit."""
    if not isinstance(pinned_outputs, dict):
        return []
    return [
        ref["__pin_s3_key__"]
        for ref in pinned_outputs.values()
        if isinstance(ref, dict) and isinstance(ref.get("__pin_s3_key__"), str)
    ]


async def _apagar_pins(keys: list[str]) -> None:
    """Removes the pin objects from MinIO. Best-effort, after the commit.

    The keys are under `pin-cache/{workspace_origem}/…` and the workflow no
    longer lives there: keeping them would produce garbage nobody can reach
    anymore, and a future unpin would delete an object from the other
    workspace. A failure here does not undo the move — the worst case is an
    orphaned object, which the storage reconciliation already knows how to
    audit.
    """
    if not keys:
        return
    from app.core import storage as s3
    for key in keys:
        try:
            await s3.delete_async(key)
        except Exception as exc:
            _logger.warning("Falha ao apagar pin '%s' após mover o workflow: %s", key, exc)
