# app/services/workflow_service.py
# Facade that delegates to specialized services, keeping the original public interface.

from app.core.utils.logger import get_logger

import copy
from datetime import datetime, timezone
from typing import Iterable, Optional
from uuid import uuid4

from fastapi import Request
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import REDIS_TTL_24H
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    CredentialAccessDeniedError,
    WorkflowDecryptionError,
    WorkflowInactiveError,
    WorkflowNameConflictError,
    WorkflowNotFoundError,
)
from app.core.scheduling.hooks import (
    apply_schedule_if_needed,
    disable_schedule_node,
    extract_schedule_node,
    sync_schedules_with_workflow_state,
)
from app.core.utils.encryption import decrypt_workflow_connections, encrypt_workflow_connections
from app.crud.workflow_crud import WorkflowCRUD
from app.models.models import Schedule, Workflow
from app.models.user import User
from app.schemas.workflow import WorkflowUpdate
from app.services.workflow_execution_service import (
    DispatchResult,
    _collect_credential_ids,
    _dispatch_job,
    _get_redis,
    _load_workflow,
    _resolve_candidates,
    _safe_pinned_outputs,
    _validate_trigger_credentials_only,
    _validate_trigger_inputs,
)
from app.core.authorization.credential_loader import (
    assert_credentials_accessible,
    resolve_credentials_from_ids,
)
from app.services.workflow_move_service import (
    _with_suffix,
    move_workflow as _move_workflow,
    free_name as _free_name,
    names_in_workspace as _names_in_workspace,
)
from app.services.workflow_version_service import (
    _has_substantial_changes,
    list_versions as _ver_list_versions,
    restore_version as _ver_restore_version,
)

_logger = get_logger(__name__)


async def _cleanup_redis_pattern(pattern: str, contexto: str) -> int:
    """Removes from Redis all keys matching `pattern`.

    Idempotent — no-op if no key exists. Best-effort: a Redis failure only
    logs a WARN and does not propagate (it does not block the delete that
    triggered it). Returns the number of keys removed.
    """
    removed = 0
    try:
        from app.core.redis import get_redis_pool
        rc = get_redis_pool()
        async for key in rc.scan_iter(match=pattern, count=200):
            await rc.delete(key)
            removed += 1
        if removed:
            _logger.info("ChangeDetector: %d key(s) removida(s) no %s", removed, contexto)
    except Exception as exc:
        _logger.warning(
            "ChangeDetector: falha ao limpar keys no %s (ignorando): %s",
            contexto, exc,
        )
    return removed


async def _cleanup_change_detector_keys(workflow_id_hash: str) -> int:
    """Remove keys `change_detector:wf:{workflow_hash}:*` do Redis."""
    return await _cleanup_redis_pattern(
        f"change_detector:wf:{workflow_id_hash}:*",
        f"delete do workflow {workflow_id_hash}",
    )


async def _cleanup_change_detector_ws_keys(workspace_id: str) -> int:
    """Removes the `change_detector:ws:{workspace_id}:*` keys from Redis.

    Called on workspace delete. Workspace-scoped keys (shared_key) do not
    belong to any workflow, so the per-workflow cleanup does not reach them —
    and with ttl_hours=0 they would live forever. A workspace restore does NOT
    bring this state back: the first run after the restore is a "first
    execution", acceptable for a change-detection cache.
    """
    return await _cleanup_redis_pattern(
        f"change_detector:ws:{workspace_id}:*",
        f"delete do workspace {workspace_id}",
    )


async def soft_delete_workspace_workflows(
    db: AsyncSession, workspace_id: str, when: datetime,
) -> dict:
    """Soft-deletes a workspace's workflows and deactivates their schedules.

    Called on workspace DELETE. Without this the workflows stayed active and
    invisible: the listing is always by accessible workspace, so they vanished
    from the UI, but the AsyncScheduler kept firing their schedules (the tick
    filters only by Schedule.active, without looking at workflow or workspace).
    Running orphaned, they lost the workspace's dedicated executor —
    _resolve_candidates does not find the row and falls back to the default
    pool — and the webhook allowlist, which becomes an empty list and stops
    being enforced.

    `when` is the same timestamp written to Workspace.deleted_at: it is what
    lets the restore tell the workflows that went down because of the workspace
    delete from those that had already been deleted before.

    Does not commit — but do not count on that for atomicity: the caller runs
    `schedule_workspace_data_expiry` right after, and it commits internally
    (via purge_workspace_storage). That is why delete_workspace sets
    Workspace.deleted_at BEFORE calling this function, not after.
    """
    from app.models.models import Schedule

    rows = (await db.execute(
        sa_select(Workflow.id_hash, Workflow.deleted_at).where(
            Workflow.workspace_id == workspace_id
        )
    )).all()

    all_ids = [r[0] for r in rows]
    if not all_ids:
        return {"workflows": 0, "schedules": 0}

    pending_ids = [r[0] for r in rows if r[1] is None]

    if pending_ids:
        await db.execute(
            Workflow.__table__.update()
            .where(Workflow.id_hash.in_(pending_ids))
            .values(deleted_at=when, flag_ative=False)
        )

    # Covers all of the workspace's workflows, not just the freshly deleted ones:
    # a schedule may have stayed active through paths predating this cascade.
    sched_result = await db.execute(
        Schedule.__table__.update()
        .where(Schedule.workflow_hash.in_(all_ids), Schedule.active.is_(True))
        .values(active=False)
    )

    for wf_id in pending_ids:
        await _cleanup_change_detector_keys(wf_id)

    # Workspace-scoped keys (ws:*) do not belong to any workflow — without this
    # line, a ChangeDetector with shared_key and ttl_hours=0 left orphaned state
    # in Redis forever after the workspace delete.
    await _cleanup_change_detector_ws_keys(workspace_id)

    return {"workflows": len(pending_ids), "schedules": sched_result.rowcount or 0}


async def restore_workspace_workflows(
    db: AsyncSession, workspace_id: str, when: datetime,
) -> int:
    """Undoes the cascading soft delete of a restored workspace.

    Restores only the workflows whose `deleted_at` matches the workspace's
    exactly — those that had already been deleted before stay deleted.

    Returns the workflows DEACTIVATED (`flag_ative` stays False), for the same
    reason the schedules are not turned back on: the cascade zeroes
    `flag_ative` for everyone, so there is no way to know who was already
    deactivated on purpose before the delete. Reactivating in bulk would
    resurrect precisely the workflow the owner had turned off — willingly, and
    without warning. The owner turns back on whatever still makes sense.

    (`flag_ative` is still the real execution lock: portal_router,
    webhook_router, schedule_service, drive_service and workflow_groups_router
    filter by it without looking at `deleted_at`. That is why the cascade has
    to zero it, and why the restore cannot hand it back on a guess.)

    Does not commit: the caller closes the transaction together with the
    workspace restore.
    """
    # The name index is PARTIAL (it only applies among the live ones), so a name
    # that was "held" by a workflow of this cascade may have been taken again
    # while the workspace was in the trash. It is narrow — a workspace in the
    # trash does not show up in listings —, but the batch UPDATE would fail
    # ENTIRELY and bring down the workspace restore with it. Renaming whoever
    # comes back is better than returning nothing.
    returning = (await db.execute(
        sa_select(Workflow.id_hash, Workflow.name).where(
            Workflow.workspace_id == workspace_id,
            Workflow.deleted_at == when,
        )
    )).all()

    if returning:
        ocupados = await _names_in_workspace(db, workspace_id)
        vistos = set()
        for id_hash, nome in returning:
            livre = _free_name(nome, ocupados | vistos)
            vistos.add(livre)
            if livre != nome:
                _logger.warning(
                    "Restore do workspace %s: nome '%s' foi reocupado — o workflow %s volta como '%s'.",
                    workspace_id, nome, id_hash, livre,
                )
                await db.execute(
                    Workflow.__table__.update()
                    .where(Workflow.id_hash == id_hash)
                    .values(name=livre)
                )

    result = await db.execute(
        Workflow.__table__.update()
        .where(Workflow.workspace_id == workspace_id, Workflow.deleted_at == when)
        .values(deleted_at=None)
    )
    return result.rowcount or 0


# Backward compatibility: re-exports the exceptions so existing importers don't break.
__all__ = [
    "WorkflowService",
    "WorkflowNotFoundError",
    "WorkflowInactiveError",
    "WorkflowDecryptionError",
    "DispatchResult",
    "soft_delete_workspace_workflows",
    "restore_workspace_workflows",
    "_safe_pinned_outputs",
    "_has_substantial_changes",
    "_get_redis",
    "_validate_trigger_credentials_only",
]


# ── Listing merge (schedule and authorship) ──────────────────────────────────
#
# The Projects listing comes out of the CRUD as a RowMapping (immutable) with
# the light columns; what comes from OTHER tables — the schedule summary and
# the names of who created/changed it — is fetched here, batched per page, and
# merged into dicts. That is 3 queries per listing, all indexed; never one per
# row.
#
# The helpers `_as_utc` and `_nomes_de_usuarios` are twins of the ones in
# `app/services/observability/`. They stay local on purpose: importing that
# package just for two five-line functions would couple the workflow listing to
# the entire metrics service (and its import time) for no gain.

# Schedule columns the list shows — `WorkflowScheduleSummary`.
_SCHEDULE_COLUMNS = (
    Schedule.workflow_hash,
    Schedule.active,
    Schedule.next_run_at,
    Schedule.last_run_at,
    Schedule.strategy,
    Schedule.cron_expression,
    Schedule.interval,
    Schedule.unit,
    Schedule.rrule_expression,
    Schedule.timezone,
)


def _as_utc(valor: Optional[datetime]) -> Optional[datetime]:
    """`next_run_at`/`last_run_at` are stored as NAIVE UTC (see `_to_utc_naive`
    in the scheduler). Without the tzinfo, Pydantic serializes without an offset
    and the web app reads the time as local — "next 06:00" would become
    "next 03:00" in Cuiabá."""
    if valor is None or valor.tzinfo is not None:
        return valor
    return valor.replace(tzinfo=timezone.utc)


def _preference_order(linha) -> tuple:
    """When a workflow has more than one schedule, the list shows only one: the
    active one with the smallest `next_run_at` (the one that will fire first);
    an active one with no computed next run after that; with none active, any
    of them."""
    return (
        not linha.active,
        linha.next_run_at is None,
        linha.next_run_at or datetime.min,
    )


async def _resumos_de_agendamento(db: AsyncSession, hashes: Iterable[str]) -> dict[str, dict]:
    """One summary per workflow_hash, with the instants already in aware UTC."""
    hashes = [h for h in set(hashes) if isinstance(h, str)]
    if not hashes:
        return {}
    result = await db.execute(
        sa_select(*_SCHEDULE_COLUMNS).where(Schedule.workflow_hash.in_(hashes))
    )
    escolhido: dict[str, object] = {}
    for linha in result.all():
        atual = escolhido.get(linha.workflow_hash)
        if atual is None or _preference_order(linha) < _preference_order(atual):
            escolhido[linha.workflow_hash] = linha
    return {
        hash_: {
            "active": bool(linha.active),
            "next_run_at": _as_utc(linha.next_run_at),
            "last_run_at": _as_utc(linha.last_run_at),
            "strategy": linha.strategy,
            "cron_expression": linha.cron_expression,
            "interval": linha.interval,
            "unit": linha.unit,
            "rrule_expression": linha.rrule_expression,
            "timezone": linha.timezone,
        }
        for hash_, linha in escolhido.items()
    }


async def _nomes_de_usuarios(db: AsyncSession, user_ids: Iterable[Optional[str]]) -> dict[str, str]:
    """id_hash -> username. An id without a row in `users` does not appear in
    the dict (the listing returns None and the web app shows just "changed X
    ago"). A user deleted by the admin is a soft delete: the row remains, so
    the name keeps showing — the same attribution the History shows."""
    ids = [i for i in set(user_ids) if isinstance(i, str)]
    if not ids:
        return {}
    result = await db.execute(sa_select(User.id_hash, User.username).where(User.id_hash.in_(ids)))
    return {r.id_hash: r.username for r in result.all()}


async def _merge_listing(db: AsyncSession, linhas) -> list[dict]:
    """Converts the CRUD rows into dicts and adds `schedule`,
    `created_by_username` and `updated_by_username`."""
    itens = [dict(linha) for linha in linhas]
    if not itens:
        return itens
    agendamentos = await _resumos_de_agendamento(db, (i["id_hash"] for i in itens))
    nomes = await _nomes_de_usuarios(
        db, [i.get("created_by_id") for i in itens] + [i.get("updated_by_id") for i in itens],
    )
    for item in itens:
        item["schedule"] = agendamentos.get(item["id_hash"])
        item["created_by_username"] = nomes.get(item.get("created_by_id"))
        item["updated_by_username"] = nomes.get(item.get("updated_by_id"))
    return itens


_FOREIGN_CREDENTIAL_MESSAGE = (
    "A definição referencia credencial que você não pode usar. "
    "Use uma credencial sua ou compartilhada com o workspace."
)


async def assert_definition_credentials(
    db: AsyncSession, definition: object, *, user_id: str, workspace_id: str | None,
) -> None:
    """Refuses to save a definition that references a credential the author
    cannot access (audit SEG-12 — confused deputy).

    Without this, an editor would insert into a shared workflow a node with
    another member's PRIVATE `credential_id` and a `url` of their own; when the
    victim ran it, the dispatch resolved the credential (triggered_by = victim)
    and sent the token to the attacker's server. We validate ALL nodes with a
    `credential_id` (not just the new ones): changing the URL of an existing
    node would also slip through. One's own credential or one shared with the
    workspace passes; another member's private one does not.

    It lives in the service, not at the edge, because there were two edges: the
    REST one checked and the MCP one skipped with `validate_first=False`, on
    duplicate and on version restore. The four writes of `WorkflowService` call
    it against the author, who is MANDATORY in them (`created_by_id`,
    `updated_by_id`, `duplicated_by`, `restored_by`: keyword-only, no default,
    and empty is refused by `_require_author`) — the author is the one who needs
    to reach the credentials. When the author was optional, a caller that
    forgot it silently skipped the guard.

    Raises `CredentialAccessDeniedError` (403 in the REST domain handler,
    `forbidden` in the MCP).
    """
    if not isinstance(definition, dict):
        return
    ids = _collect_credential_ids(definition)
    if not ids:
        return
    try:
        await assert_credentials_accessible(db, ids, user_id, shared_workspace_id=workspace_id)
    except CredentialAccessDeniedError as exc:
        raise CredentialAccessDeniedError(_FOREIGN_CREDENTIAL_MESSAGE) from exc


def _require_author(autor: object, parametro: str) -> str:
    """The author of a write: a user id, never empty.

    The four authorship parameters are already mandatory in the signature;
    this closes off an explicit `None` — a careless
    `getattr(user, "id_hash", None)` —, which would skip the guard just like
    the forgotten argument. There is no system write without a user today: the
    one that comes will have to decide against whom the definition is checked,
    and say so here, instead of passing empty.
    """
    if not isinstance(autor, str) or not autor:
        raise TypeError(
            f"Escrita de workflow sem autor (`{parametro}`): a guarda de credenciais "
            "(SEG-12) confere a definition contra quem grava."
        )
    return autor


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.crud = WorkflowCRUD(db)

    async def create_workflow(
        self, name: str, definition: dict, workspace_id: str | None = None, *,
        created_by_id: str, **extras,
    ):
        """`extras` are additional Workflow columns (description, params_schema…).

        It exists for duplication: creation through the UI only sends name and
        definition, but copying a workflow has to carry along what defines how
        it behaves — `params_schema`, for example, is what makes the screen
        ask for the parameters before running.

        `created_by_id` is mandatory: it is against it that the credential
        guard (SEG-12) checks the definition.
        """
        autor = _require_author(created_by_id, "created_by_id")

        # 0. Credentials in the definition within reach of whoever writes (SEG-12).
        #    Duplication goes through here with `created_by_id` = who duplicated.
        await assert_definition_credentials(
            self.crud.db, definition, user_id=autor, workspace_id=workspace_id,
        )

        # 1. Encrypts sensitive data
        secure_definition = encrypt_workflow_connections(definition)

        # 2. Creates the workflow in the database (workspace_id binds it to the active workspace)
        kwargs = dict(extras, created_by_id=autor)
        if workspace_id:
            kwargs["workspace_id"] = workspace_id
        try:
            workflow = await self.crud.create(name, secure_definition, **kwargs)
        except IntegrityError as exc:
            await self.crud.db.rollback()
            if "uq_workflow_name_workspace" in str(exc.orig):
                # Quotes the name: the message reaches the user as a toast, far from
                # the field, and "this name" does not say which one when the
                # name was chosen by the server (duplication).
                raise WorkflowNameConflictError(
                    f"Já existe um workflow chamado '{name}' neste workspace."
                ) from exc
            raise

        # 3. Applies the schedule, if there is a ScheduleTrigger
        if extract_schedule_node(definition):
            try:
                await apply_schedule_if_needed(workflow, definition, self.crud.db)
            except Exception as exc:
                _logger.warning("Falha ao criar agendamento para workflow %s: %s", workflow.id_hash, exc)

        return workflow

    async def duplicate_workflow(
        self, id_hash: str, novo_nome: str | None = None, *, duplicated_by: str,
    ) -> Workflow:
        """Creates a copy of the workflow in the SAME workspace.

        What does NOT come along with the copy, and why:

        - `pinned_outputs`/`pin_metadata` point to artifacts from runs of the
          original workflow; inheriting them would make the copy serve data it
          never produced, with nothing on screen saying so.
        - `portal_access` goes back to "disabled": publishing a copy because
          the original was published exposes content without anyone asking.
        - the version history starts empty — the original's versions describe
          edits that did not happen in this copy.

        The schedule comes along, but TURNED OFF: duplicating usually precedes
        an edit, and being born firing on its own would double the load and
        the writes to Drive silently. Turning it off in the definition itself
        (and not just in the database) keeps canvas and schedule consistent —
        `apply_schedule_if_needed` reads the node's `active`, so what the user
        sees on the canvas is what counts.

        It stays in the same workspace on purpose: a `credential_id` in the
        definition only resolves for those with access to the workspace, and
        referenced sub-workflows need to live in it. Copying to another
        workspace would produce a workflow that looks intact and fails when run.
        """
        autor = _require_author(duplicated_by, "duplicated_by")
        original = await self.get_workflow_by_hash(id_hash)

        # Deep copy: `encrypt_workflow_connections` writes into the dict it receives,
        # and the one in `original.definition` is the object SQLAlchemy watches —
        # mutating it would mark the origin workflow as dirty.
        definition = copy.deepcopy(original.definition or {})

        disable_schedule_node(definition)

        requested_name = novo_nome.strip() if novo_nome and novo_nome.strip() else None

        # Everything that comes from `original` is read NOW, while the session is clean.
        #
        # A name collision makes `create_workflow` call `rollback()`, and the
        # rollback expires every object in the session — including this
        # `original`, which did not even take part in the write. Reading any of
        # its attributes after that triggers a lazy refresh, and in an
        # AsyncSession that is not an extra SELECT: it is `MissingGreenlet`. The
        # retry below would turn the 409 into a 500 — exactly on the path that
        # exists so as never to fail.
        original_name = original.name
        workspace_id = original.workspace_id
        # What defines HOW the workflow behaves comes along with the copy.
        # `params_schema` in particular: it is what makes the screen ask for the
        # parameters before running (see handleRunClick in the front end) —
        # without it the copy would fire straight away, silently, with an empty
        # schema.
        inherited = dict(
            description=original.description,
            params_schema=original.params_schema,
            group_id=original.group_id,
            priority=original.priority,
            notification_url=original.notification_url,
            # The copy inherits the original's provenance: duplicating an assistant
            # workflow without this would create a "usuario" (user) copy that
            # leaks into the listings the assistant was supposed to keep hidden.
            origem=original.origem,
        )
        # Authorship of the COPY belongs to whoever copied it, not to the original's
        # owner: the copy is a new workflow, and the person who clicked is the
        # one accountable for it. Without this the copy was born with no owner
        # at all — `created_by_id` null —, and the Projects screen, which shows
        # authorship, had nothing to show.
        #
        # The MCP `duplicate_workflow` tool already stamped it (`app/mcp/tools/
        # acervo.py`); this was the divergence recorded as debt in #96.
        # `duplicated_by` is mandatory: it is also against it that
        # `create_workflow` checks the copy's credentials (SEG-12).
        inherited["created_by_id"] = autor
        inherited["updated_by_id"] = autor

        async def _create(nome: str) -> Workflow:
            return await self.create_workflow(
                nome, definition, workspace_id=workspace_id, **inherited,
            )

        # A name hand-picked by the user: a collision is an answer, not an accident.
        # Renaming on our own would create "Meu Fluxo (2)" for whoever typed
        # "Meu Fluxo" — better to return the 409 and let the person decide.
        if requested_name:
            return await _create(requested_name)

        # Derived name: the promise of duplication is "click, copied". A collision
        # here is our failure, not the user's choice, so we resolve it ourselves.
        #
        # `_copy_name` queries the taken names and the INSERT comes after:
        # the window between the two is real (two simultaneous duplications read
        # the same set). The `move` already handled this — duplication did not,
        # and the 409 went all the way up to the screen. See
        # workflow_move_service._apply.
        nome = await self._copy_name(original_name, workspace_id)
        try:
            return await _create(nome)
        except WorkflowNameConflictError:
            # `create_workflow` has already rolled back. Recomputing is the first
            # bet: the new read sees the name that caused the collision and
            # returns the next free one — "(2)" is still a better name than a hex.
            _logger.warning(
                "Colisão de nome ao duplicar o workflow %s (nome '%s'); recalculando.",
                id_hash, nome,
            )
            nome = await self._copy_name(original_name, workspace_id)
            try:
                return await _create(nome)
            except WorkflowNameConflictError as exc:
                # Colliding twice in a row indicates a persistent race. The
                # random suffix does not compete with anyone.
                nome = _with_suffix(f"Cópia de {original_name}", uuid4().hex[:6])
                _logger.warning(
                    "Segunda colisão ao duplicar o workflow %s; usando sufixo único '%s'.",
                    id_hash, nome,
                )
                try:
                    return await _create(nome)
                except WorkflowNameConflictError:
                    raise WorkflowNameConflictError(
                        "Não foi possível encontrar um nome livre para a cópia neste workspace."
                    ) from exc

    async def move_workflow(
        self,
        id_hash: str,
        target_workspace_id: str,
        *,
        new_name: str | None = None,
        moved_by_id: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Moves the workflow to another workspace (see workflow_move_service).

        Authorization — admin/owner in BOTH workspaces — lives in the router,
        which is the one holding the requester's identity.
        """
        return await _move_workflow(
            self.crud, id_hash, target_workspace_id,
            new_name=new_name, moved_by_id=moved_by_id, dry_run=dry_run,
        )

    async def _copy_name(self, base_name: str, workspace_id: str | None) -> str:
        """"Cópia de X", "Cópia de X (2)", ... — the first free one in the workspace.

        There is a UniqueConstraint(name, workspace_id): without disambiguation,
        duplicating the same workflow twice returned 409 and the user had to
        come up with a name before seeing the copy.
        """
        # Same query and same free-name search used by the move — only the base
        # changes. Duplicating the criterion would make duplicate and move
        # diverge when the scope of "taken name" changes (soft-delete, inactive
        # workflows…).
        existentes = await _names_in_workspace(self.crud.db, workspace_id)
        return _free_name(f"Cópia de {base_name}", existentes)

    async def get_workflow_by_hash(self, id_hash: str) -> Workflow:
        wf = await self.crud.get_by_hash(id_hash)
        if not wf:
            raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

        # Descriptografa a definition (caso contenha connectionString criptografada)
        if wf.definition:
            try:
                wf.definition = decrypt_workflow_connections(wf.definition)
            except Exception as e:
                _logger.error("Falha ao descriptografar definition do workflow %s: %s", id_hash, e)
                raise WorkflowDecryptionError(
                    f"Não foi possível descriptografar a definição do workflow {id_hash}."
                ) from e

        return wf

    async def start_analysis(
        self,
        id_hash: str,
        inputs: dict = None,
        request: Request = None,
        debug_mode: bool = False,
        idempotency_key: str | None = None,
        autenticar_entrada: bool = True,
        workflow: Workflow | None = None,
        triggered_by: str | None = None,
        trigger_source: str = "manual",
        schedule_id: int | None = None,
    ) -> DispatchResult:
        """Dispatches an execution.

        `autenticar_entrada` says whether the webhook trigger's token must
        authenticate THIS call. The default is `True` on purpose: a new caller
        that forgets the parameter ends up requiring the token (the usual
        behavior), instead of opening the public endpoint without
        authentication. Paths already authenticated by session or by the
        scheduler pass `False`.

        `workflow` is the object the caller has already loaded — see
        `_load_workflow`. HTTP triggers pass what the authorization dependency
        has just fetched; the scheduler, which only has the hash, leaves it None.

        `triggered_by` is the id_hash of WHO triggered it (on authenticated HTTP
        routes). It is the owner dimension of the credential scope (see step 5):
        only that person's credentials — or those shared with the workflow's
        workspace — are resolved. Cron/webhook have no user and leave None,
        reaching only the shared ones.

        `trigger_source` and `schedule_id` are just labels on the run
        (docs/specs/metrics-history.md §2): "manual" | "retry" | "webhook"
        | "schedule" | "mcp". They take no part in any dispatch decision — they
        exist so the History can tell "scheduled at 03:00" from "manual · so-and-so".
        The "manual" default keeps old callers working.
        """
        # ── 1. Idempotency ────────────────────────────────────────────────
        # The key is per USER and per WORKFLOW: it used to be global to the
        # installation, and two users sending `Idempotency-Key: 1` got each
        # other's task_id (cross-tenant). Callers without a user (cron/webhook
        # do not pass a key today) fall into "-". Old keys in Redis stay
        # orphaned for up to 24 h — harmless.
        cache_key: str | None = None
        if idempotency_key:
            cache_key = f"idempotency:wf_execute:{triggered_by or '-'}:{id_hash}:{idempotency_key}"
            _redis = _get_redis()
            existing = await _redis.get(cache_key)
            if existing:
                return DispatchResult(id=existing)

        # ── 2. Carregar e descriptografar ─────────────────────────────────
        wf, definition = await self._load_workflow(id_hash, request, workflow=workflow)

        # ── 2a. Validar inputs contra payload_schema dos triggers ────────
        _validate_trigger_inputs(definition, inputs)

        # ── 2b. Block if the workflow uses nodes disabled by the admin ────
        from app.services.disabled_nodes_service import disabled_names
        from app.services.workflow_execution_service import (
            _validate_no_disabled_nodes,
        )
        from flow.utils.workflow_contract import (
            collect_subworkflow_definitions_recursive,
        )

        disabled_now = await disabled_names(self.crud.db)
        _validate_no_disabled_nodes(definition, disabled_now)

        # ── 3. Resolve candidate executors (fail-fast) ────────────────────
        # Moved earlier on purpose: it is the ONLY check from here on that can
        # abort everything with 503, and it used to come LAST. With no executor
        # online, the server collected sub-workflows and decrypted credentials —
        # several round-trips to the database and tens of milliseconds of CPU —
        # only to throw it all away. It still comes AFTER the disabled-nodes
        # check so as not to swap the precedence of the error messages: that
        # check now comes from the cache and costs no round-trip at all.
        #
        # SEC: it is only moved earlier when the caller is ALREADY
        # authenticated — execute, retry and cron pass
        # `autenticar_entrada=False`. What authenticates the caller of a
        # protected webhook is step 5 (the WebhookTrigger token); moving the
        # 503 earlier on that path too made an ANONYMOUS caller receive
        # "Nenhum executor disponível (pool padrão vazio ou todos offline)" (no
        # executor available) before any 401/403 — an oracle on the tenant's
        # execution fleet, which also let one tell "infra down" from "my token
        # is wrong" without presenting any credential. For the webhook the
        # fail-fast runs right AFTER the token validation, before the dispatch.
        candidates = None
        if not autenticar_entrada:
            candidates = await self._resolve_candidates(wf)

        # ── 4. Pre-resolve the sub-workflow chain ─────────────────────────
        # Goes in the envelope: the executor has no access to the server's DB.
        subworkflow_defs = await collect_subworkflow_definitions_recursive(
            definition, self.crud.db, workspace_id=wf.workspace_id,
        )

        # ── 5. Resolve credentials ONCE (used by validate + inject) ───────
        # The scope is the workflow's workspace: only credentials of those with
        # access to it are resolved. Without this, a credential_id copied from
        # the definition (plain text, readable by any member) worked in ANY
        # workflow, of any workspace. Applies to every trigger — including cron
        # and webhook, which have no identified user.
        # Includes the sub-workflow chain: their credentials go in the same
        # envelope and are resolved with the SAME workspace scope — the
        # collector above already discards sub-workflows from other workspaces.
        all_cred_ids = _collect_credential_ids(definition, *subworkflow_defs.values())
        pre_resolved: dict = {}
        if all_cred_ids:
            if not wf.workspace_id:
                raise CredentialAccessDeniedError(
                    f"Workflow '{id_hash}' usa credenciais mas não tem workspace — "
                    "não há como autorizar o acesso a elas."
                )
            # Scope D: only the credentials OF WHOEVER TRIGGERED it are resolved
            # (triggered_by) OR those explicitly shared with the workflow's
            # workspace. Being merely a MEMBER of the workspace is not enough —
            # otherwise a member would use another's PRIVATE credential just by
            # copying the credential_id (plain text in the definition). A
            # trigger without a user (cron/webhook) has triggered_by=None and
            # reaches only the shared ones; if a trigger requires a private
            # credential, the _validate_trigger_credentials_only below returns
            # a clear 403.
            pre_resolved = await resolve_credentials_from_ids(
                all_cred_ids,
                allowed_owner_ids={triggered_by} if triggered_by else set(),
                shared_workspace_id=wf.workspace_id,
                # The request's session goes along: without it the resolver opened a
                # SECOND connection from the same pool without releasing the
                # first, and under concurrency the dispatch hung on pool_timeout.
                db=self.crud.db,
            )
        await _validate_trigger_credentials_only(
            definition, request=request, pre_resolved=pre_resolved,
            autenticar_entrada=autenticar_entrada,
        )

        # ── 5b. Webhook fail-fast (see step 3) ────────────────────────────
        # The caller has already identified itself: from here on the 503 leaks
        # nothing it could not find out by triggering the workflow.
        if candidates is None:
            candidates = await self._resolve_candidates(wf)

        # ── 6. Dispatch job ───────────────────────────────────────────────
        # disabled_nodes and subworkflow_definitions go in the envelope so the
        # executor can validate/resolve sub-workflows without querying the
        # server's DB.
        result = await self._dispatch_job(
            wf, definition, candidates, inputs, debug_mode,
            pre_resolved=pre_resolved,
            disabled_nodes=sorted(disabled_now),
            subworkflow_definitions=subworkflow_defs,
            trigger_source=trigger_source,
            triggered_by=triggered_by,
            schedule_id=schedule_id,
        )

        # ── 7. Record idempotency (TTL: 24h) ─────────────────────────────
        if cache_key:
            try:
                _redis = _get_redis()
                await _redis.set(cache_key, result.id, ex=REDIS_TTL_24H)
            except Exception as exc:
                _logger.warning("Falha ao registrar chave de idempotência no Redis: %s", exc)

        return result

    # Wrappers that delegate to the functions of the workflow_execution_service module.
    # They exist as methods so tests can replace them via
    # `service._load_workflow = AsyncMock(...)` and per-instance patches.
    async def _load_workflow(
        self, id_hash: str, request: Request | None = None,
        *, workflow: Workflow | None = None,
    ):
        return await _load_workflow(self.crud, id_hash, request, workflow)

    async def _resolve_candidates(self, wf: Workflow):
        return await _resolve_candidates(self.crud.db, wf)

    async def _dispatch_job(
        self,
        wf: Workflow,
        definition: dict,
        candidates: list,
        inputs: dict | None,
        debug_mode: bool,
        *,
        pre_resolved: dict | None = None,
        disabled_nodes: list[str] | None = None,
        subworkflow_definitions: dict | None = None,
        trigger_source: str | None = None,
        triggered_by: str | None = None,
        schedule_id: int | None = None,
    ) -> DispatchResult:
        return await _dispatch_job(
            wf, definition, candidates, inputs, debug_mode,
            db=self.crud.db,
            pre_resolved=pre_resolved,
            disabled_nodes=disabled_nodes,
            subworkflow_definitions=subworkflow_definitions,
            trigger_source=trigger_source,
            triggered_by=triggered_by,
            schedule_id=schedule_id,
        )

    async def list_workflows_metadata(
        self, workspace_id: str | None = None, *, include_from_assistant: bool = False,
    ) -> list[dict]:
        """Light listing — metadata without definition, plus the schedule
        summary and the authorship names (see `_merge_listing`).

        `include_from_assistant` passes along the screen's toggle: by default
        the assistant's workflows are left out."""
        linhas = await self.crud.get_all_metadata(
            workspace_id=workspace_id, include_from_assistant=include_from_assistant,
        )
        return await _merge_listing(self.crud.db, linhas)

    async def list_workflows_metadata_by_ids(
        self, workspace_ids: list[str], *, include_from_assistant: bool = False,
    ) -> list[dict]:
        """Light listing by workspace IDs — same merge as `list_workflows_metadata`."""
        linhas = await self.crud.get_all_metadata_by_workspace_ids(
            workspace_ids, include_from_assistant=include_from_assistant,
        )
        return await _merge_listing(self.crud.db, linhas)

    async def delete_workflow(self, id_hash: str) -> None:
        """Soft delete: desativa o workflow e seus schedules associados."""
        from app.models.models import Schedule

        wf = await self.crud.soft_delete_by_hash(id_hash)
        if not wf:
            raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

        # Deactivates linked schedules so they don't fire executions
        result = await self.crud.db.execute(
            sa_select(Schedule).where(Schedule.workflow_hash == id_hash)
        )
        for sched in result.scalars().all():
            sched.active = False
        await self.crud.db.commit()

        # Clears ChangeDetector state — the workflow no longer runs. If it is
        # restored, the first run will be "Mudou" (changed; safe). Best-effort:
        # a Redis failure does not block the delete.
        await _cleanup_change_detector_keys(id_hash)

        return wf

    async def update_workflow(
        self,
        id_hash: str,
        workflow_in: WorkflowUpdate,
        change_note: str | None = None,
        *,
        updated_by_id: str,
    ) -> Workflow:
        autor = _require_author(updated_by_id, "updated_by_id")

        # 1. Ensures the workflow exists — uses get_by_hash (no decrypt) so as not to
        #    mark the definition as dirty in the SQLAlchemy session and keep the
        #    subsequent commit from saving the decrypted definition to the database.
        wf = await self.crud.get_by_hash(id_hash)
        if not wf:
            raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

        # 2. Extracts only the payload fields
        updates: dict = workflow_in.model_dump(exclude_unset=True)
        previous_flag_ative = bool(wf.flag_ative)

        # 2a. Authorship comes from the authenticated identity, never from the body —
        #     `WorkflowUpdate` no longer exposes `updated_by_id` precisely so that
        #     the client cannot forge who edited it.
        updates["updated_by_id"] = autor

        # 2b. Credentials of the new definition within reach of the editor (SEG-12),
        #     before any write — including the snapshot below.
        if "definition" in updates:
            await assert_definition_credentials(
                self.crud.db, updates["definition"],
                user_id=autor, workspace_id=wf.workspace_id,
            )

        # 3. If the definition is going to change and there were substantial changes, creates a snapshot
        if "definition" in updates:
            # The COPY is not overcaution: `decrypt_workflow_connections` MUTATES the
            # dict it receives and returns the same object. Decrypting
            # `wf.definition` directly, it would leave here in plain text and the
            # snapshot right below would write the credential in readable form
            # to `workflow_versions` — a history nobody ever rewrites.
            old_def = decrypt_workflow_connections(copy.deepcopy(wf.definition))
            if _has_substantial_changes(old_def, workflow_in.definition):
                # And step 1's `get_by_hash` is NOT enough for the snapshot to come
                # out encrypted. The route's dependency
                # (`get_accessible_workflow_with_role`) has already called
                # `get_workflow_by_hash`, which does
                # `wf.definition = decrypt_workflow_connections(...)` — an
                # in-place mutation on the live row. Since the session is the
                # same, `get_by_hash` returns the SAME Python object, already in
                # plain text, and copying it only duplicates the plain text.
                # Encrypting explicitly is what closes it:
                # `encrypt_workflow_connections` is idempotent (it skips what
                # already starts with `gAAAA`), so it covers both possible
                # states of the session. Same remedy, and for the same reason,
                # as `workflow_move_service._apply`.
                #
                # This call sits OUTSIDE the `try/except IntegrityError` right
                # below, and that is deliberate — but it fools a hasty reader.
                # `create_version` only does `flush()`, so the INSERT goes out
                # here, and a `version_number` collision would blow up twenty
                # lines before the `try`. The `except` below is for the NAME
                # conflict, which comes from `crud.update`.
                #
                # There is no leak because the version collision is handled by
                # `create_version` itself, at the source: savepoint and
                # reconvergence. If someone ever removes that handling, the hole
                # reopens HERE — as a 500 that loses the user's save —, and not
                # in the `except` below, which has no way of reaching it.
                await self.crud.create_version(
                    workflow_hash=id_hash,
                    definition=encrypt_workflow_connections(copy.deepcopy(wf.definition or {})),
                    change_note=change_note,
                )
            updates["definition"] = encrypt_workflow_connections(updates["definition"])

        # 4. Applies updates to the database
        #
        # The name is read from the object BEFORE the commit: `crud.update` does
        # setattr and commits, and the except's `rollback()` expires the whole
        # session. Reading `wf.name` afterwards triggers a lazy refresh — which
        # in an AsyncSession is not one more SELECT, it is `MissingGreenlet`,
        # that is, this message's 409 would become a 500 precisely on the error
        # path.
        attempted_name = updates.get("name") or wf.name
        try:
            wf = await self.crud.update(wf, updates)
        except IntegrityError as exc:
            await self.crud.db.rollback()
            if "uq_workflow_name_workspace" in str(exc.orig):
                raise WorkflowNameConflictError(
                    f"Já existe um workflow chamado '{attempted_name}' neste workspace."
                ) from exc
            raise

        # 5. Syncs schedules whenever the definition changes — the function
        # apply_schedule_if_needed removes old schedules and only creates a new
        # one if there is a ScheduleTrigger. Without this unconditional sync,
        # removing the ScheduleTrigger from the workflow left the old Schedule
        # active in the database and the async_scheduler kept firing the
        # workflow in a loop.
        schedule_notices = []
        if "definition" in updates:
            try:
                schedule_notices = await apply_schedule_if_needed(wf, workflow_in.definition, self.crud.db)
            except Exception as exc:
                _logger.warning("Falha ao sincronizar agendamento para workflow %s: %s", wf.id_hash, exc)

        # 6. The "Ativado/Inativo" (enabled/inactive) switch in the projects list
        # sends `flag_ative` ALONE — without a definition, step 5 does not even
        # run. Deactivating the workflow left the Schedule active pointing at
        # it, and the AsyncScheduler tried to fire it on every cron occurrence
        # until someone read the log. Runs after step 5 on purpose:
        # `apply_schedule_if_needed` returns early when the workflow is
        # deactivated (it preserves the old config), and it is this sync that
        # has the final say on `active`.
        if bool(wf.flag_ative) != previous_flag_ative:
            try:
                await sync_schedules_with_workflow_state(wf, self.crud.db)
            except Exception as exc:
                _logger.warning(
                    "Falha ao sincronizar agendamento com flag_ative do workflow %s: %s",
                    wf.id_hash, exc,
                )

        # Schedule notices travel in the response as a transient attribute
        # (not a column): `WorkflowRead.schedule_notices` reads them and the
        # editor turns them into a toast. Always set — empty in the normal case.
        wf.schedule_notices = schedule_notices
        return wf

    async def list_versions(self, id_hash: str):
        return await _ver_list_versions(self.crud, id_hash)

    async def restore_version(
        self, id_hash: str, version_number: int, *, restored_by: str,
    ) -> Workflow:
        """Restores the version. First checks the version's credentials against
        `restored_by` (SEG-12): restoring must not reintroduce a credential
        that the person restoring cannot access. A nonexistent version raises
        `WorkflowNotFoundError` right here — the error is not swallowed to
        "skip" the guard."""
        autor = _require_author(restored_by, "restored_by")

        # The RAW version, without decrypting: `credential_id` is not encrypted, and
        # opening the blob would make a version with a `connectionString` that
        # no longer decrypts (rotated key) fail here — the restore itself only
        # copies the blob, without opening it.
        versao = await self.crud.get_version(id_hash, version_number)
        if not versao:
            raise WorkflowNotFoundError(
                f"Versão {version_number} do workflow {id_hash} não encontrada"
            )
        wf = await self.crud.get_by_hash(id_hash)
        await assert_definition_credentials(
            self.crud.db, versao.definition,
            user_id=autor, workspace_id=wf.workspace_id if wf else None,
        )
        return await _ver_restore_version(self.crud, id_hash, version_number)
