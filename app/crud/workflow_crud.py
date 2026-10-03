# app/crud/workflow_crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Boolean
from sqlalchemy.exc import IntegrityError

from app.models.models import Workflow, WorkflowVersion
from app.core.exceptions import WorkflowVersionConflictError
from app.core.utils.logger import get_logger

# The name of the UNIQUE (workflow_hash, version_number). Stable in the three
# places that define it: `app/models/workflow_version.py`, the initial migration
# and `scripts/init_schema.sql`.
_NOME_DA_UNIQUE_DE_VERSAO = "uq_workflow_version"


def _e_colisao_de_versao(exc: IntegrityError) -> bool:
    """Is the violation the one from the UNIQUE (workflow_hash, version_number)?

    Two ways to recognize it, because the two databases say different things:

        PostgreSQL  duplicate key value violates unique constraint "uq_workflow_version"
        SQLite      UNIQUE constraint failed: workflow_versions.workflow_hash, ...

    SQLite does **not** cite the constraint name — it cites the columns.
    Matching only by name would make the retry work in production and never in
    the tests, which is the worst possible combination: the fix would look
    untested when it is right, or the suite would pass through a path that
    production does not take.

    Measured, not assumed — the two messages above came from a real violation
    in each database.
    """
    texto = str(getattr(exc, "orig", exc)).lower()
    if _NOME_DA_UNIQUE_DE_VERSAO in texto:
        return True
    return "unique" in texto and "version_number" in texto

# Three attempts cover real contention (simultaneous saves of the same workflow).
# Exhausting all three is not "more bad luck": it signals something else, and becomes a 409.
_TENTATIVAS_DE_VERSAO = 3

def _tem_node(nome: str, rotulo: str):
    """Listing flag: the definition mentions a node with this name.

    Searches the text of `definition['nodes']` — does not bring the JSON into
    Python, which is the point of doing it in the query and not in code.

    Known limitation: it is a substring search on the serialized JSON, so a
    node whose NICKNAME is the name searched for, or a script that mentions the
    name in a comment, flags the workflow. Verified: both cases come out
    positive. The outcome is one extra badge in a list, and the exact
    alternative (`cast(... AS
    jsonb) @> '[{"name": "..."}]'`) ties the query to PostgreSQL and takes
    these tests off SQLite. If precision ever matters, that is the trade-off.

    The `coalesce` is not overcaution: a `definition` without the `nodes` key
    makes `->>` return NULL, `LIKE` propagates NULL, and Pydantic refuses None
    in a `bool` field — the whole GET /workflows/ response became a 500, not
    just that workflow's row. The column is `nullable=False`, but nothing
    guarantees the shape inside the JSON.
    """
    return cast(
        func.coalesce(Workflow.definition["nodes"].as_string().contains(nome), False),
        Boolean,
    ).label(rotulo)


_has_publish_map_expr = _tem_node("PublishMap", "has_publish_map")

# A workflow that exists to be CALLED by another: it declares the public
# sub-workflow output. `SubWorkflowOutput` is the only mandatory node of the
# contract (see validate_subworkflow_references_against_db) — the input is
# optional, because a sub-workflow may receive nothing.
#
# Worth flagging in the listing because a sub-workflow usually has NO trigger:
# running it alone from the list's button does not do what one expects.
_e_subfluxo_expr = _tem_node("SubWorkflowOutput", "is_subworkflow")

# Triggers, by the same mechanism. They are the workflow's nature ("how it
# fires"), not execution — that is why they go in the listing and not in metrics.
# The names are the ones registered in `flow/nodes/trigger/*` (`get_definition()['name']`).
#
# Accepted substring collisions, besides the general ones of `_tem_node`: a node
# whose name CONTAINS the one searched for also flags — "GeofenceTrigger" matches
# the `GeofenceTriggerNode` class if the registered name ever changes to it, which
# is the desired result; today there is no registered node that contains
# "FileTrigger", "WebhookTrigger" or "ScheduleTrigger" without being the trigger itself.
_has_webhook_trigger_expr = _tem_node("WebhookTrigger", "has_webhook_trigger")
_has_schedule_trigger_expr = _tem_node("ScheduleTrigger", "has_schedule_trigger")
_has_file_trigger_expr = _tem_node("FileTrigger", "has_file_trigger")
_has_geofence_trigger_expr = _tem_node("GeofenceTrigger", "has_geofence_trigger")

# Light columns for listing — excludes definition, pinned_outputs, pin_metadata,
# params_schema. `deleted_at` is also left out: both queries that use this
# list filter `deleted_at IS NULL`, so the column was always null.
_METADATA_COLUMNS = [
    Workflow.id,
    Workflow.id_hash,
    Workflow.name,
    Workflow.flag_ative,
    Workflow.description,
    Workflow.version,
    Workflow.priority,
    Workflow.workspace_id,
    Workflow.group_id,
    Workflow.notification_url,
    Workflow.portal_access,
    Workflow.portal_shared_with,
    _has_publish_map_expr,
    _e_subfluxo_expr,
    _has_webhook_trigger_expr,
    _has_schedule_trigger_expr,
    _has_file_trigger_expr,
    _has_geofence_trigger_expr,
    Workflow.created_at,
    Workflow.updated_at,
    Workflow.created_by_id,
    Workflow.updated_by_id,
    Workflow.origem,
]

logger = get_logger(__name__)

class WorkflowCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_hash(self, id_hash: str) -> Workflow | None:
        stmt = (
            select(Workflow)
            .where(Workflow.id_hash == id_hash)
        )
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        return workflow
    
    # The two methods below carried `OR workspace_id IS NULL` so as not to
    # hide legacy workflows. The side effect was delivering them in the listing
    # of EVERY authenticated user, of any tenant. The column is NOT NULL since
    # migration 20260828_0001, which assigned those legacy ones to the right
    # workspace — there is no more legacy to accommodate, and the filter is now
    # just the tenant's.

    async def get_all_metadata(
        self, workspace_id: str | None = None, *, incluir_do_assistente: bool = False,
    ):
        """Returns workflows WITHOUT the heavy JSON fields (definition, pinned_outputs, etc.).
        Ideal for listing — saves ~10KB per workflow.

        By default hides the assistant's workflows (`origem = "assistente"`):
        they are a delivery vehicle for Home, not items the owner manages. Who
        passes `incluir_do_assistente=True` today: `ActiveRunsContext` (needs
        the names for the run badge), the `list_workflows` tool when the caller
        is the assistant itself, and the `GET /workflows?assistente=1` route.

        WARNING — the Projects screen does NOT YET have the toggle that would
        use that route, and observability (Dashboard inventory, group counts)
        does not filter by `origem`. Until both sides agree, an assistant
        workflow shows up in History and in metrics without existing in
        Projects. Its schedules show up on purpose, with a badge — see
        `schedule_service.listar_agendamentos_de`."""
        stmt = select(*_METADATA_COLUMNS).where(Workflow.deleted_at.is_(None))
        if not incluir_do_assistente:
            stmt = stmt.where(Workflow.origem != "assistente")
        if workspace_id:
            stmt = stmt.where(Workflow.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.mappings().all()

    async def get_all_metadata_by_workspace_ids(
        self, workspace_ids: list[str], *, incluir_do_assistente: bool = False,
    ):
        """Returns workflows (metadata only) from the given workspaces.

        Hides the assistant's workflows by default — see `get_all_metadata`."""
        stmt = select(*_METADATA_COLUMNS).where(
            Workflow.deleted_at.is_(None),
            Workflow.workspace_id.in_(workspace_ids),
        )
        if not incluir_do_assistente:
            stmt = stmt.where(Workflow.origem != "assistente")
        result = await self.db.execute(stmt)
        return result.mappings().all()

    async def create(self, name: str, definition: dict, **kwargs) -> Workflow:
        wf = Workflow(name=name, definition=definition, **kwargs)
        self.db.add(wf)
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    async def update(self, wf: Workflow, updates: dict) -> Workflow:
        for key, value in updates.items():
            setattr(wf, key, value)
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    async def soft_delete_by_hash(self, id_hash: str) -> Workflow | None:
        """Soft delete: sets deleted_at and deactivates the workflow without removing it from the database."""
        from app.core.utils.datetime_utils import utc_now_naive
        stmt = select(Workflow).where(Workflow.id_hash == id_hash)
        result = await self.db.execute(stmt)
        wf = result.scalars().first()

        if wf is None:
            return None

        wf.deleted_at = utc_now_naive()
        wf.flag_ative = False
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    # ------------------------------------------------------------------ #
    # Workflow Versioning                                                  #
    # ------------------------------------------------------------------ #

    async def create_version(
        self,
        workflow_hash: str,
        definition: dict,
        change_note: str | None = None,
        *,
        tentativas: int = _TENTATIVAS_DE_VERSAO,
    ) -> WorkflowVersion:
        """Automatic snapshot: saves the CURRENT version before an update.

        The version number is read-modify-write — it reads the current maximum
        and adds 1 —, and the UNIQUE `uq_workflow_version` is the only arbiter
        of a tie. Two simultaneous saves of the same workflow read the same
        maximum, and the second INSERT violates it.

        **The window is not that of one INSERT.** Since this function only does
        `flush()` (the commit belongs to the caller, on purpose — see
        `workflow_move_service._aplicar`, which depends on it to undo everything
        together), it runs from the `SELECT max()` to the commit further on,
        covering everything the caller does in between.

        Why a SAVEPOINT and not a bare `try`: in PostgreSQL a constraint
        violation poisons the WHOLE transaction, and this one runs inside
        someone else's transaction, which will still commit unrelated work.
        Without `begin_nested`, catching the error does not fix it — it only
        swaps the 500 for a `PendingRollbackError` on the next commit. Same
        reason, and same mold, as `_upsert_pin_artifact`
        (`app/core/run_result_consumer.py`), `api_token_service.marcar_uso` and
        `credential_loader`.

        Why NOT `SELECT ... FOR UPDATE` on the workflow row: `FOR UPDATE`
        conflicts with the `FOR KEY SHARE` that every INSERT with an FK requests
        on the referenced row, and `WorkflowVersion.workflow_hash` is an FK to
        `workflows.id_hash`. The comment in `app/core/async_scheduler.py` (at
        `with_for_update`) records the self-deadlock this has already cost here,
        and `api_token_service` records discarding the same feature for cost.

        The retry **re-reads** the maximum instead of incrementing the number
        that failed: two simultaneous losers that incremented would collide
        with each other again.
        """
        for _ in range(max(1, tentativas)):
            max_ver_result = await self.db.execute(
                select(func.max(WorkflowVersion.version_number)).where(
                    WorkflowVersion.workflow_hash == workflow_hash
                )
            )
            current_max = max_ver_result.scalar() or 0
            version = WorkflowVersion(
                workflow_hash=workflow_hash,
                version_number=current_max + 1,
                definition=definition,
                change_note=change_note,
            )
            try:
                async with self.db.begin_nested():
                    self.db.add(version)
                    await self.db.flush()   # gets the ID without a separate commit
                return version
            except IntegrityError as exc:
                if not _e_colisao_de_versao(exc):
                    raise
                # There is no `expunge(version)` here, and its absence is measured: the
                # SAVEPOINT rollback already removes from the session the object
                # added inside it, and calling `expunge` afterwards raises
                # `InvalidRequestError: Instance is not present in this Session`.
                # Each turn of the loop creates a new `WorkflowVersion`, so nothing
                # from the failed INSERT survives to be re-emitted.
                logger.info(
                    "Colisão de version_number no workflow %s; relendo o máximo.",
                    workflow_hash,
                )

        raise WorkflowVersionConflictError(
            "Outra gravação deste workflow está em andamento. Tente salvar de novo."
        )

    async def get_versions(self, workflow_hash: str) -> list[WorkflowVersion]:
        result = await self.db.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_hash == workflow_hash)
            .order_by(WorkflowVersion.version_number.desc())
        )
        return result.scalars().all()

    async def get_version(self, workflow_hash: str, version_number: int) -> WorkflowVersion | None:
        result = await self.db.execute(
            select(WorkflowVersion).where(
                WorkflowVersion.workflow_hash == workflow_hash,
                WorkflowVersion.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()