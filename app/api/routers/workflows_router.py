from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.workflow import (
    WorkflowRead, WorkflowUpdate, WorkflowCreate,
    WorkflowVersionMeta, WorkflowListItem, WorkflowDuplicate,
    WorkflowMove, WorkflowMoveResult,
)

from app.core.exceptions import AtlasBaseError, CredentialAccessDeniedError
from app.services.workflow_service import WorkflowService, WorkflowInactiveError
from app.core.exceptions import WorkflowNameConflictError
from app.api.dependencies import (
    get_workflow_service, get_current_user, get_user_workspace_ids,
    verify_workspace_access, workflow_com_papel, require_workspace_role,
    get_db,
)
from app.core.rate_limiter import limiter
from app.core.rbac import ROLE_ADMIN, ROLE_EDITOR, ROLE_OPERATOR, ROLE_VIEWER
from app.core.utils.logger import get_logger
from app.core.utils.redacao import definition_contains_secret, params_schema_contains_secret
from app.services import pin_service
from app.services.pin_service import MAX_TTL_HOURS

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])

class ExecutePayload(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Initial inputs for trigger nodes")
    debug_mode: bool = Field(default=False, description="Se true, o executor pausa em cada nó e emite dados intermediários no WebSocket")

class PortalSettingsSchema(BaseModel):
    portal_access: str = Field(..., pattern="^(disabled|public|private)$")
    portal_shared_with: Optional[List[str]] = None

def _recusar_segredo(definition: Any, *, schema: bool = False) -> None:
    """Rejects a definition that carries a LITERAL secret written into it.

    A credential lives in `credentials`, encrypted; the definition stores the
    `credential_id` and the server injects the value into a COPY at dispatch
    (`credential_resolver`). A secret written here would be encrypted in the database,
    but it would already have traveled through transport and logs — and output
    redaction would erase it later, giving the false impression that it is not there.

    The MCP server's edge already rejected it (`app/mcp/tools/construcao.py`); REST,
    which is where the editor saves, did not. Production survey (2026-09-14):
    286 nodes, 56 with `credential_id`, ZERO saved secrets — the refusal makes
    invariant a state that was already true by convention.

    Cites the field's PATH and never the value: the refusal message cannot be
    the leak it prevents.
    """
    caminhos = (
        params_schema_contains_secret(definition) if schema
        else definition_contains_secret(definition or {})
    )
    if caminhos:
        raise HTTPException(
            status_code=422,
            detail=(
                "Segredo gravado na definição. Use uma credencial (`credential_id`) "
                "em vez do valor literal. Um valor `<REDACTED>` veio de uma leitura redigida: "
                "restaure o original ou não envie o campo.\nCampos:\n- " + "\n- ".join(caminhos)
            ),
        )


@router.post("", status_code=201, summary="Create a new workflow definition")
@limiter.limit("30/minute")
async def create_workflow(
    request: Request,
    payload: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # The workspace comes from the body, not the path: that is why the check is here, and not
    # in the `workflow_com_papel` dependency of the `/{id_hash}` routes.
    await require_workspace_role(
        db, payload.workspace_id, current_user.id_hash, ROLE_EDITOR,
        "Requer role 'editor' ou superior para criar workflows.",
    )

    _recusar_segredo(payload.definition)
    # `params_schema` is a sibling column, writable in the same body, and — unlike the
    # definition — it does NOT go through `encrypt_workflow_connections`: it goes raw to
    # the database. MCP output already redacts `params_schema.token`, so leaving it out
    # of the guard would break the redaction module's own rule: detection cannot
    # be narrower than delivery.
    _recusar_segredo(payload.params_schema, schema=True)

    # The definition's credentials (SEG-12) are checked by the service in
    # `create_workflow`, via `created_by_id` — same guard as MCP.

    # Cross-workflow validation: referenced SubWorkflows must exist,
    # be active, in the same workspace and with a contract compatible with the mapping.
    from flow.utils.workflow_contract import validate_subworkflow_references_against_db
    cross_errors = await validate_subworkflow_references_against_db(
        payload.definition or {}, db, workspace_id=payload.workspace_id,
    )
    if cross_errors:
        # detail as a string for the front end to show in the toast (resolveAxiosError
        # reads `detail`). Concatenated error list — one per line.
        raise HTTPException(
            status_code=422,
            detail="Sub-workflows invalidos:\n- " + "\n- ".join(cross_errors),
        )

    try:
        # Stamps the author on INSERT: without this `created_by_id`/`updated_by_id`
        # were born null and "criado há X por Y" (created X ago by Y) in the listing
        # never showed the name (the field was only filled on the first edit, via update_workflow).
        wf = await service.create_workflow(
            payload.name,
            payload.definition,
            workspace_id=payload.workspace_id,
            created_by_id=current_user.id_hash,
            updated_by_id=current_user.id_hash,
        )
        logger.info(f"Workflow '{payload.name}' criado por '{current_user.id_hash}'.")
        return {"id": wf.id_hash, "name": wf.name}
    except ValueError as e:
        logger.error(f"Erro ao criar workflow: {e}")
        raise HTTPException(status_code=400, detail="Não foi possível criar o workflow. Verifique os dados informados.")

@router.get("", summary="List all registered workflows", response_model=List[WorkflowListItem])
async def list_workflows(
    workspace_id: str | None = None,
    assistente: bool = False,
    service: WorkflowService = Depends(get_workflow_service),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """Returns a lightweight listing of workflows (without definition and other heavy JSON fields).

    `assistente=1` includes the workflows created by the Home assistant (hidden
    by default): the "mostrar os do assistente" (show the assistant's) toggle on the
    Projects screen and `ActiveRunsContext` pass this parameter."""
    if workspace_id:
        verify_workspace_access(workspace_id, workspace_ids)
        return await service.list_workflows_metadata(
            workspace_id=workspace_id, include_from_assistant=assistente,
        )
    # Without workspace_id: returns workflows from all of the user's workspaces in a single query
    return await service.list_workflows_metadata_by_ids(
        workspace_ids, include_from_assistant=assistente,
    )

@router.get(
    "/{id_hash}",
    response_model=WorkflowRead,
    summary="Get Workflow by id_hash",
    description="Retorna todos os campos de um workflow existente a partir do seu id_hash.",
    responses={
        200: {"description": "Workflow encontrado"},
        403: {"description": "Acesso negado"},
        404: {"description": "Workflow não encontrado"},
        422: {"description": "Validation Error"},
    },
)
async def read_workflow(
    wf=Depends(workflow_com_papel(None)),   # read: belonging to the workspace is enough
):
    # Audit (SEG-67): the definition comes with the legacy connectionString ALREADY
    # decrypted, and the route is accessible to viewer. Redacts the secrets in a
    # COPY (redact_definition) before responding — without touching the ORM object,
    # so the "<REDACTED>" marker is never written by a flush of the GET. Modern
    # workflows use credential_id (resolved only at dispatch) and expose nothing.
    from app.core.utils.redacao import redact_definition
    dados = WorkflowRead.model_validate(wf)
    if isinstance(dados.definition, dict) and dados.definition:
        return dados.model_copy(update={"definition": redact_definition(dados.definition)})
    return dados

@router.get(
    "/{id_hash}/contract",
    summary="Contrato (API publica) do workflow para uso como sub-fluxo",
    description=(
        "Retorna as chaves declaradas via SubWorkflowInput (entradas) e "
        "SubWorkflowOutput (saidas). Usado pelo canvas para renderizar portas "
        "nomeadas no node SubWorkflow e validar inputsMapping em design-time."
    ),
    responses={
        200: {"description": "Contrato extraido."},
        403: {"description": "Acesso negado."},
        404: {"description": "Workflow nao encontrado."},
    },
)
async def get_workflow_contract(wf=Depends(workflow_com_papel(None))):
    from flow.utils.workflow_contract import extract_contract
    from app.core.utils.encryption import decrypt_workflow_connections

    # decrypt_workflow_connections only touches credentials — nodes/edges
    # stay exposed as they are. extract_contract reads only the graph.
    try:
        definition = decrypt_workflow_connections(wf.definition or {})
    except Exception:
        definition = wf.definition or {}
    contract = extract_contract(definition)
    # is_active lets the canvas mark a SubWorkflow pointing to a deactivated
    # target with a visual badge even before trying to save.
    contract["is_active"] = bool(wf.flag_ative)
    return contract


@router.delete("/{id_hash}", status_code=200)
@limiter.limit("20/minute")
async def delete_workflow(
    request: Request,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
):
    await service.delete_workflow(wf.id_hash)
    return {"message": f"Workflow '{wf.name}' desativado com sucesso."}

@router.post("/{id_hash}/duplicate", status_code=201, summary="Duplica um workflow no mesmo workspace")
@limiter.limit("20/minute")
async def duplicate_workflow(
    request: Request,
    payload: WorkflowDuplicate | None = None,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(
        ROLE_EDITOR, "Requer role 'editor' ou superior para duplicar workflows.",
    )),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """The copy stays in the SAME workspace as the original.

    `workflow_com_papel` already blocks whoever cannot reach the workflow, and since the
    destination is its workspace, access to the original plus `editor` cover the operation —
    there is no way to use this route to plant a workflow in someone else's workspace.
    """
    # Same check as POST / and PUT: a referenced SubWorkflow may have
    # been deactivated or removed after the original was saved. Without this, the
    # copy would be born broken and would only fail at run time, with an error far
    # less clear than the list of invalid references.
    from flow.utils.workflow_contract import validate_subworkflow_references_against_db
    cross_errors = await validate_subworkflow_references_against_db(
        wf.definition or {}, db, workspace_id=wf.workspace_id,
    )
    if cross_errors:
        raise HTTPException(
            status_code=422,
            detail="Sub-workflows invalidos:\n- " + "\n- ".join(cross_errors),
        )

    # Audit (SEG-12): the copy cannot carry a credential the duplicator
    # cannot access — the service checks, via `duplicated_by`.
    try:
        copia = await service.duplicate_workflow(
            wf.id_hash, payload.name if payload else None,
            duplicated_by=current_user.id_hash,
        )
    except WorkflowNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info("Workflow '%s' duplicado como '%s'.", wf.name, copia.name)
    return {"id": copia.id_hash, "name": copia.name}


# ── Move between workspaces ──────────────────────────────────────────────────
#
# Requires admin (or owner) in BOTH workspaces. Moving crosses the tenant
# boundary: it carries the definition — which holds `credential_id` in plain text and
# Drive file ids — into another workspace, and starts producing data
# there. The editor role, which is enough to create and duplicate within one's own
# workspace, does not cover that.
#
# Requiring it on both sides closes the two symmetric abuses: pulling a workflow out of a
# workspace where one only has partial access, and planting a workflow inside
# someone else's workspace. It is exactly the gap the `WorkflowUpdate` comment
# describes when rejecting `workspace_id` in the PUT.
#
# The origin is checked by the route's dependency (`workflow_com_papel`), the
# destination — which comes from the body — in `_move`. The destination message is the
# same for "not a member", "workspace does not exist" and "workspace in the trash":
# `get_workspace_member_role` returns None in all three, and distinguishing them would
# allow enumerating other people's workspaces by id.
_MOVE_SOURCE = "Requer role 'admin' ou 'owner' no workspace de origem para mover workflows."
_MOVE_DESTINATION = "Requer role 'admin' ou 'owner' no workspace de destino para mover workflows."


async def _move(
    payload: WorkflowMove,
    service: WorkflowService,
    wf,
    db: AsyncSession,
    current_user,
    *,
    dry_run: bool,
) -> WorkflowMoveResult:
    """Common body of /move and /move/preview — only `dry_run` changes."""
    # Only authorization and serialization live here: "destination ≠ origin" is an
    # invariant of the operation and lives in the service (WorkflowMoveTargetError → 400).
    await require_workspace_role(
        db, payload.target_workspace_id, current_user.id_hash, ROLE_ADMIN, _MOVE_DESTINATION,
    )

    resultado = await service.move_workflow(
        wf.id_hash,
        payload.target_workspace_id,
        new_name=payload.name,
        moved_by_id=current_user.id_hash,
        dry_run=dry_run,
    )
    if not dry_run:
        logger.info(
            "Workflow '%s' movido de '%s' para '%s' por '%s' (%d aviso(s)).",
            wf.id_hash, resultado["from_workspace_id"], resultado["to_workspace_id"],
            current_user.id_hash, len(resultado["warnings"]),
        )
    return WorkflowMoveResult(**resultado)


@router.post(
    "/{id_hash}/move",
    response_model=WorkflowMoveResult,
    summary="Move um workflow para outro workspace",
)
@limiter.limit("10/minute")
async def move_workflow(
    request: Request,
    payload: WorkflowMove,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_ADMIN, _MOVE_SOURCE)),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowMoveResult:
    """Changes the workflow's workspace, preserving the `id_hash`.

    The operation does NOT fail because of a broken dependency: what stops working in
    the destination comes back in `warnings` — credentials that no longer resolve,
    sub-workflows and Drive files left behind, executor change.

    What always changes: the schedule arrives turned off, the portal goes back to "disabled",
    group and pins are cleared. History (runs, artifacts, metrics)
    stays in the origin workspace.
    """
    return await _move(payload, service, wf, db, current_user, dry_run=False)


@router.post(
    "/{id_hash}/move/preview",
    response_model=WorkflowMoveResult,
    summary="Simula a movimentação e devolve os impactos, sem gravar",
)
@limiter.limit("30/minute")
async def preview_move_workflow(
    request: Request,
    payload: WorkflowMove,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_ADMIN, _MOVE_SOURCE)),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowMoveResult:
    """Same report as the move, without writing anything.

    Feeds the dialog before confirming. Requires the same permission as the real move
    so as not to become an oracle about the contents of other people's workspaces.
    """
    return await _move(payload, service, wf, db, current_user, dry_run=True)


@router.put("/{id_hash}", response_model=WorkflowRead, summary="Atualiza um workflow existente")
@limiter.limit("30/minute")
async def update_workflow(
    request: Request,
    workflow_in: WorkflowUpdate,
    change_note: str | None = None,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Updates fields of an existing workflow.
    Only the fields sent in the payload are changed.
    If `definition` is changed, the current version is saved automatically as a snapshot.
    """
    # If the definition changed, validate cross-workflow references against the DB.
    # `WorkflowUpdate` is partial: an absent `definition` means "do not touch it",
    # and refusing there would block even renaming a workflow.
    new_schema = getattr(workflow_in, "params_schema", None)
    if new_schema is not None:
        _recusar_segredo(new_schema, schema=True)   # same reason as the POST

    new_def = getattr(workflow_in, "definition", None)
    if new_def is not None:
        _recusar_segredo(new_def)
        # The credentials (SEG-12) are checked by the service in `update_workflow`.

        from flow.utils.workflow_contract import validate_subworkflow_references_against_db
        cross_errors = await validate_subworkflow_references_against_db(
            new_def, db, workspace_id=wf.workspace_id,
        )
        if cross_errors:
            raise HTTPException(
                status_code=422,
                detail="Sub-workflows invalidos:\n- " + "\n- ".join(cross_errors),
            )

    try:
        return await service.update_workflow(
            wf.id_hash, workflow_in, change_note=change_note,
            updated_by_id=current_user.id_hash,
        )
    except (HTTPException, CredentialAccessDeniedError):
        raise
    except Exception as e:
        logger.error("Erro ao atualizar workflow '%s': %s", wf.id_hash, e)
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o workflow.")


# ------------------------------------------------------------------ #
# Direct execution                                                   #
# ------------------------------------------------------------------ #

@router.post(
    "/{id_hash}/execute",
    status_code=202,
    summary="Executa um workflow imediatamente",
)
@limiter.limit("20/minute")
async def execute_workflow(
    request: Request,
    payload: ExecutePayload,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(
        ROLE_OPERATOR, "Requer role 'operator' ou superior para executar workflows.",
    )),
    current_user=Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Dispatches the workflow for immediate execution via an executor.

    **Idempotency**: send the `Idempotency-Key: <uuid>` header to ensure
    that duplicate requests (e.g. network retry) do not trigger extra runs.
    The same key, for the SAME user and the SAME workflow, returns the `task_id`
    of the original run for 24h (the key does not collide between users).
    """
    try:
        async_result = await service.start_analysis(
            wf.id_hash,
            inputs=payload.inputs,
            request=request,
            debug_mode=payload.debug_mode,
            idempotency_key=idempotency_key,
            # The authorization dependency already loaded and decrypted this
            # workflow: without passing the object along, the dispatch redid the SELECT and
            # deserialized the entire `definition` again (~1.7 MB in a large
            # workflow) only to discard the result.
            workflow=wf,
            # Credential scope (option D): who triggered is one of the two
            # dimensions — the credentials of THIS user are resolved, plus those
            # shared with the workflow's workspace.
            triggered_by=current_user.id_hash,
            trigger_source="manual",
            # Whoever gets here has already passed through the session and has the operator role. The
            # trigger token authenticates an EXTERNAL CALL to the webhook endpoint;
            # requiring it here only compared the user's JWT with the token and
            # responded "Token inválido" (invalid token), without preventing anything.
            autenticar_entrada=False,
        )
        return {"task_id": async_result.id, "workflow": wf.id_hash}
    except (HTTPException, AtlasBaseError):
        raise
    except Exception as e:
        logger.error("Erro ao executar workflow '%s': %s", wf.id_hash, e)
        raise HTTPException(status_code=400, detail="Não foi possível executar o workflow.")


@router.post(
    "/runs/{run_id}/cancel",
    summary="Cancela uma execução em andamento",
)
@limiter.limit("30/minute")
async def cancel_run(
    request: Request,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Interrupts a run in progress.

    Until then a triggered workflow only ended on its own or by executor
    timeout — the user had no way to stop an expensive or stuck job.

    Requires the `operator` role or higher in the RUN's workspace, the same needed
    to have started it.
    """
    from app.services.workflow_execution_service import cancel_run as _cancel

    # The authorization (`operator` role in the RUN's workspace, with a global
    # administrator shortcut) now lives inside `cancel_run`, next to the SELECT
    # that loads the run: it was a route-only rule, so the service would cancel
    # any account's run for whoever called it directly. No such caller
    # exists today — the route is the only one —, but the MCP server's tools
    # do not go through here, and it is for them that the guard had to move down.
    # This route stopped repeating it so that there are not two versions of the same
    # rule diverging over time.
    #
    # Domain errors bubble up to the global handler (app/main.py), which already maps
    # each one to its status: 404 for a nonexistent run, 403 for an insufficient
    # role. Catching them here would collapse both into a generic code.
    # An executor being down is no longer an error: the run is closed on the server and the
    # outcome comes back "cancelled".
    outcome = await _cancel(
        db,
        run_id,
        user_id=current_user.id_hash,
        como_admin=getattr(current_user, "role", None) == ROLE_ADMIN,
    )
    return {"run_id": run_id, "outcome": outcome}


# ------------------------------------------------------------------ #
# Workflow Versioning                                                  #
# ------------------------------------------------------------------ #

@router.get(
    "/{id_hash}/versions",
    response_model=List[WorkflowVersionMeta],
    summary="Lista o histórico de versões de um workflow (somente metadados)",
)
async def list_versions(
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(None)),   # read: belonging to the workspace is enough
):
    return await service.list_versions(wf.id_hash)


@router.post(
    "/{id_hash}/versions/{version_number}/restore",
    response_model=WorkflowRead,
    summary="Restaura o workflow para uma versão anterior",
)
@limiter.limit("10/minute")
async def restore_version(
    request: Request,
    version_number: int,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    current_user=Depends(get_current_user),
):
    # Audit (SEG-12): restoring an old version cannot reintroduce a
    # credential the person restoring cannot access — the service checks.
    return await service.restore_version(
        wf.id_hash, version_number, restored_by=current_user.id_hash,
    )

# ------------------------------------------------------------------ #
# Run retry                                                          #
# ------------------------------------------------------------------ #

@router.post(
    "/{id_hash}/runs/{run_id}/retry",
    status_code=202,
    summary="Dispara uma nova execução do workflow que produziu esta run",
)
@limiter.limit("10/minute")
async def retry_run(
    request: Request,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(
        ROLE_OPERATOR, "Requer role 'operator' ou superior para executar workflows.",
    )),
    current_user=Depends(get_current_user),
):
    """
    Dispatches a NEW run of the workflow, with its CURRENT definition.

    Important, because the name suggests something else: it is not a replay of the
    given run. `WorkflowRun` does not store the input parameters, so
    re-running exactly that run is not possible today — and promising it in the
    response would be lying to whoever depends on the result.

    The path's `run_id` is VALIDATED, not decorative: it must exist and
    belong to this workflow. Before, it was received and ignored, so any
    string passed and the route triggered the run all the same, even with
    the id of a run from another workflow — the caller thought it was re-running one
    thing and was triggering another.
    """
    from app.models.models import WorkflowRun as _Run

    run = (await db.execute(
        select(_Run.task_id).where(
            _Run.task_id == run_id,
            _Run.workflow_hash == wf.id_hash,
        )
    )).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Execução não encontrada para este workflow.",
        )

    try:
        # Same case as POST /execute: already authenticated, role already checked.
        async_result = await service.start_analysis(
            wf.id_hash, autenticar_entrada=False, workflow=wf,
            triggered_by=current_user.id_hash,
            # "retry" and not "manual": in History, a sequence of re-runs
            # of the same workflow tells a different story from one-off triggers.
            trigger_source="retry",
        )
        return {"task_id": async_result.id, "message": "Execução reenfileirada com sucesso."}
    except WorkflowInactiveError:
        raise HTTPException(status_code=403, detail="Workflow está desativado.")


# ------------------------------------------------------------------ #
# Sharing portal                                                     #
# ------------------------------------------------------------------ #

@router.patch("/{id_hash}/portal", summary="Configura acesso ao portal público do workflow")
@limiter.limit("30/minute")
async def update_portal_settings(
    request: Request,
    body: PortalSettingsSchema,
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Sets portal_access (disabled/public/private) and the list of allowed users."""
    wf.portal_access = body.portal_access
    wf.portal_shared_with = body.portal_shared_with if body.portal_access == "private" else None
    await db.commit()
    share_url = f"/share/{wf.id_hash}" if body.portal_access != "disabled" else None
    return {
        "portal_access": wf.portal_access,
        "portal_shared_with": wf.portal_shared_with,
        "share_url": share_url,
    }


# ── Pin Data ─────────────────────────────────────────────────────────────────

class PinOutputPayload(BaseModel):
    # `node_id` is still accepted and still IGNORED — the path always won, and
    # `PUT /pin/A` with `{"node_id": "B"}` wrote to A, silently. It is no longer
    # required (no caller needs to repeat what is already in the URL) and cannot
    # simply disappear: with `extra="forbid"`, a client that still
    # sends it would start getting 422 on a call that used to work.
    node_id: Optional[str] = Field(
        None, description="Ignorado — o nó é o do caminho da URL. Mantido por compatibilidade.",
    )
    outputs: Dict[str, Any]
    ttl_hours: Optional[int] = Field(
        None,
        ge=1,
        le=MAX_TTL_HOURS,
        description=(
            "Validade do pin em horas, de 1 a 8760 (um ano). Nulo = sem expiração. "
            "O 0 é recusado de propósito: antes ele virava 'sem expiração', o "
            "oposto do que quem o digita está pedindo."
        ),
    )

    model_config = ConfigDict(extra="forbid")


@router.put("/{id_hash}/pin/{node_id}", summary="Pin (fix) output of a node")
async def pin_node_output(
    id_hash: str,
    node_id: str,
    body: PinOutputPayload,
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Pins a node's output for reuse in future runs."""
    try:
        # `exigir_no_existente=False`: pinning an id the definition does not have is
        # useless, but rejecting it would change the contract of a route the screen uses.
        # The OUTPUT node gate is another story and applies here — the pin it
        # rejects never worked.
        return await pin_service.fixar_saida(
            db, wf, node_id,
            outputs=body.outputs,
            ttl_hours=body.ttl_hours,
            user_id=getattr(user, "id_hash", None),
            exigir_no_existente=False,
        )
    except pin_service.PinOnOutputNodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{id_hash}/pin/{node_id}", summary="Unpin output of a node")
async def unpin_node_output(
    id_hash: str,
    node_id: str,
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Removes a node's pinned output and deletes the cache artifact from MinIO."""
    return await pin_service.unpin_output(db, wf, node_id)


@router.get("/{id_hash}/pins", summary="List pinned nodes")
async def list_pinned_nodes(
    id_hash: str,
    wf=Depends(workflow_com_papel(
        ROLE_VIEWER, "Requer role 'viewer' ou superior para ver os pins.",
    )),
    _user=Depends(get_current_user),
):
    """Lists the nodes with pinned output and their metadata.

    Requires `viewer`, and not just workspace membership. It was the only one of the
    three pin routes with no role at all — the sibling `PUT`/`DELETE` ask for `editor`
    —, and the MCP `list_pins` tool already required `viewer` (`app/mcp/guardas.py`).
    The same read answered by two standards depending on the entry point.
    """
    # No `existing_node_ids`: the route keeps listing everything that is
    # saved, including the pin of an already deleted node. It is MCP that filters by the nodes
    # the definition still has — the screen needs to see the orphan to clean it up.
    pins = pin_service.listar_pins(wf.pin_metadata, wf.pinned_outputs)
    return {"pinned_nodes": pins, "total": len(pins)}
