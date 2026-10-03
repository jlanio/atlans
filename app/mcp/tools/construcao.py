# app/mcp/tools/construcao.py
"""
Building tools: validate, create, update, (de)activate and publish.

These are the five tools that WRITE to the collection — and, for that reason,
the ones that carry three precautions the read tools do not need:

1. **Secrets do not get in.** Every definition received goes through
   `definition_contains_secret` BEFORE anything else. A password in
   `connectionString` or an `Authorization` in `headers` saved in the definition
   would be encrypted in the database, but would still be a secret that
   traveled through a transport, a client history and a log — and that the
   output redaction would later erase, giving the false impression that it is
   not there. The refusal cites the field's PATH and never the value
   (`erros.secret_error`).
2. **Validating before saving is the default.** `validate_first=True` runs the
   validation core (`validate_service.validar_definicao`) and refuses the save
   when the report contains errors. `force=True` overrides ordinary errors —
   but never the FATAL ones (nonexistent node, duplicate id, cycle,
   `credential_id` that is not a UUID): `validar_definicao` raises those as
   `InvalidDefinitionError` before building any report, and saving a
   definition that the executor cannot even build would be creating a workflow
   that can only fail.
3. **Authorship comes from the identity, never from the body.** `created_by_id`
   and `updated_by_id` are stamped with the token's owner. `WorkflowCreate` is
   not `extra="forbid"` and has `id_hash` with a default, so throwing a client
   dictionary into it would let the caller choose the workflow's id and the
   name of whoever created it; here what comes from the client are named
   parameters and what goes to the service is an allowlist.

The order "session → resolve → role → close → validate → session → save" is
deliberate: `validar_definicao` opens its OWN session, and keeping it nested
inside ours would stack two sessions on the same connection. The cost is a
minimal window between the role check and the write, which the database closes
anyway (the keys and the unique index apply on INSERT).
"""
from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.authorization.workflow_access import exigir_papel, get_workspace_member_role
from app.core.rbac import ROLE_EDITOR
from app.core.utils.redacao import definition_contains_secret, params_schema_contains_secret
from app.mcp import infra
from app.mcp.erros import erro, secret_error
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow, resolve_workspace
from app.mcp.saida import envelope, sanitize
from app.mcp.tools.base import anotacoes, ferramenta
# `_share_url` belongs to the same family of tools and is the ONLY definition of
# the portal's absolute URL. Copying it here because of the underscore would
# create two truths about the same address — and the one that went stale would
# be discovered by whoever clicked it.
from app.mcp.tools.workflows import _share_url
from app.models.workflow_version import WorkflowVersion
from app.schemas.workflow import WorkflowUpdate
from app.services import validate_service
from app.services.workflow_service import WorkflowService

_ROLE_MESSAGE = "Requer papel 'editor' ou superior neste workspace."

# The three portal states, in the same order the screen offers them. It is the
# same list as the `pattern` of `PortalSettingsSchema` in REST.
PORTAL_ACCESS_MODES = ("disabled", "public", "private")

# Ceiling of shape-error items passed on to the client: a very wrong body
# yields dozens of items, and the whole list only drowns the first line, which
# is the one that matters.
_MAX_SHAPE_ERRORS = 20


def _shape_errors(exc: ValidationError) -> list:
    """`[{path, message}]` from a Pydantic error — without the value received.

    Pydantic's `str(exc)` echoes the INPUT of each failed field, and the input
    here is the definition the client sent: returning it whole would make a
    password saved in the wrong place take one more trip through the transport
    and the SDK log. Path and reason are enough to fix it.
    """
    itens = []
    for detalhe in exc.errors()[:_MAX_SHAPE_ERRORS]:
        caminho = ".".join(str(parte) for parte in detalhe.get("loc", ()))
        itens.append({"path": caminho, "message": str(detalhe.get("msg", ""))})
    return itens


def _recusar_segredo(definition: Any) -> None:
    """Refuses a definition that carries a secret in plaintext.

    Only a dict is inspected: a body of another type (a `params_schema` that is
    a string) is a SHAPE error, and the Pydantic validation further on answers
    it with the field's path — here it used to bring down the tool with an
    internal error.
    """
    if not isinstance(definition, dict):
        return
    caminhos = definition_contains_secret(definition)
    if caminhos:
        raise secret_error(caminhos)


def _refuse_secret_in_schema(params_schema: Any) -> None:
    """Refuses a `params_schema` that stores a secret as the VALUE of a parameter
    (`params_schema.token.default`). Declaring a `token` parameter with no
    value, as the lint itself suggests, passes."""
    caminhos = params_schema_contains_secret(params_schema)
    if caminhos:
        raise secret_error(caminhos)


def _report(saida: Any) -> dict:
    """The validation's `__report__` — an empty dict when the output lacks it."""
    relatorio = saida.get("__report__") if isinstance(saida, dict) else None
    return relatorio if isinstance(relatorio, dict) else {}


def _validation_summary(relatorio: dict) -> dict:
    """What fits at the top level of the response: the verdict and the counts.

    The report's MESSAGES are left out on purpose — they cite node names and
    text written by whoever builds the workflow, and the `untrusted_data` block
    is where that kind of text may appear.
    """
    return {
        "ok": bool(relatorio.get("ok")),
        "error_count": len(relatorio.get("errors") or []),
        "warning_count": len(relatorio.get("warnings") or []),
    }


def _schedule_warnings(wf) -> list:
    """`schedule_notices` (a transient attribute of the service) as dicts.

    They are Pydantic objects: without this, the response does not serialize
    and the failure would only show up when the workflow had a
    `ScheduleTrigger`.
    """
    brutos = getattr(wf, "schedule_notices", None) or []
    avisos = []
    for aviso in brutos:
        if hasattr(aviso, "model_dump"):
            avisos.append(aviso.model_dump())
        elif isinstance(aviso, dict):
            avisos.append(dict(aviso))
    return avisos


async def _count_versions(db, workflow_hash: str) -> int:
    """How many snapshots the workflow has. A count, and not `list_versions`: the
    listing brings each version's definition, and here only the number is
    wanted."""
    resultado = await db.execute(
        select(func.count())
        .select_from(WorkflowVersion)
        .where(WorkflowVersion.workflow_hash == workflow_hash)
    )
    return int(resultado.scalar() or 0)


async def _validate(definition: Any, *, user_id: str, workspace_id: str) -> dict:
    """`validar_definicao` with a malformed body translated.

    A `pydantic.ValidationError` — a node without `id`, an edge without
    `target`, `nodes` that is not a list — would go up as an unexpected error
    ("internal error"), which is the worst possible answer for a body the
    client can fix on its own.
    """
    try:
        return await validate_service.validar_definicao(
            definition or {}, user_id=user_id, workspace_id=workspace_id
        )
    except ValidationError as exc:
        raise erro(
            "validation",
            "O corpo de definition não tem a forma esperada.",
            "cada nó precisa de id, name e type; cada aresta, de source e target",
            errors=_shape_errors(exc),
        ) from exc


async def _validate_before_saving(
    definition: Any, *, user_id: str, workspace_id: str, force: bool
) -> dict:
    """Validates and refuses the save when there are errors — unless `force`.

    The FATAL case does not get here even with `force=True`:
    `validar_definicao` raises it as `InvalidDefinitionError`, which the
    decorator translates into `validation` with the same report. That is the
    asymmetry we want — `force` exists for judgment errors (a node the
    simulation cannot exercise without real data), not for saving a graph the
    executor cannot even build.
    """
    relatorio = _report(await _validate(definition, user_id=user_id, workspace_id=workspace_id))
    erros = relatorio.get("errors") or []
    if erros and not force:
        raise erro(
            "validation",
            f"A definição tem {len(erros)} erro(s) de validação e não foi gravada.",
            "corrija os itens de report.errors ou repita com force=true",
            # The report goes out sanitized: `erro()` redacts the strings it
            # receives at the top level, but does not descend into a nested
            # structure, and a `simulate_error` message repeats what the node
            # tried to do — including a URL the simulation built.
            report=sanitize(relatorio),
        )
    return relatorio


async def _editable_workspace(db, escopo, workspace_id: str | None) -> str:
    """The call's workspace, with the minimum editor role already checked."""
    alvo = await resolve_workspace(db, escopo, workspace_id)
    papel = await get_workspace_member_role(db, alvo, escopo.user_id)
    exigir_papel(papel, ROLE_EDITOR, _ROLE_MESSAGE)
    return alvo


# ── Ferramentas ───────────────────────────────────────────────────────────────


@ferramenta
async def validate_workflow(
    ctx: Context, definition: dict, workspace_id: str | None = None
) -> dict:
    """Validates a definition without saving anything.

    `workspace_id` is required here, unlike in the core, where it is optional:
    the workspace decides which credentials enter the simulation's scope, which
    nodes are disabled and which sub-workflows exist. Without it validation
    would start lying by omission — it would approve a definition that the run
    later refuses. When the token reaches a single workspace, omitting it still
    works (the parameter resolves to that one).

    The secret refusal happens here in the SAME place as in the sibling tools —
    right after the scope and before everything that touches the database —,
    even though this one saves nothing. The core's lint also flags
    `secret_in_definition`, but only as an item of `report.errors`, and letting
    it give the answer would cost three things: (a) the refusal is the only
    check that speaks solely about the body the caller themselves sent, and
    doing it first prevents the password from reaching the validation path,
    which opens its own session and simulates the nodes; (b) a
    `secret_in_definition` error with the fields' PATHS is a better diagnosis
    than an item buried in a report dozens of lines long; (c) the promise in
    `docs/mcp.md` — refusal at the entrance, before any validation — comes to
    hold for all three tools that receive a definition, not for two of them.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")
    _recusar_segredo(definition)

    async with infra.sessao() as db:
        alvo = await _editable_workspace(db, escopo, workspace_id)

    saida = await _validate(definition, user_id=escopo.user_id, workspace_id=alvo)
    relatorio = _report(saida)
    # The validate body is `{node_id: {...}}` plus the reserved `__*` keys.
    # Here it comes out separated into two parts, and both are text from
    # whoever writes the definition: the nodes' id and label, the lint
    # messages, the `suggested_params_schema`.
    by_node = {
        chave: valor for chave, valor in saida.items() if not str(chave).startswith("__")
    }
    dados = {"workspace_id": alvo}
    dados.update(_validation_summary(relatorio))
    return envelope(
        dados,
        report=relatorio,
        nodes=by_node,
        edge_diagnostics=saida.get("__edge_diagnostics__"),
    )


@ferramenta
async def create_workflow(
    ctx: Context,
    name: str,
    definition: dict,
    workspace_id: str | None = None,
    description: str | None = None,
    params_schema: dict | None = None,
    validate_first: bool = True,
    force: bool = False,
) -> dict:
    """Creates a workflow in the given workspace.

    The secret refusal comes BEFORE everything that touches the database: it is
    the only check that speaks solely about the body the caller themselves
    sent, and doing it first guarantees that a plaintext password does not even
    reach the validation path.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")
    _recusar_segredo(definition)
    # `params_schema` is a sibling column and goes raw to the database (it
    # does not go through `encrypt_workflow_connections`): the same refusal as
    # REST — only on what the schema stores as a value, and not on
    # `required: true` of a `token`.
    _refuse_secret_in_schema(params_schema)

    async with infra.sessao() as db:
        alvo = await _editable_workspace(db, escopo, workspace_id)

    relatorio: dict = {}
    if validate_first:
        relatorio = await _validate_before_saving(
            definition, user_id=escopo.user_id, workspace_id=alvo, force=force
        )

    # Allowlist: only these columns reach the service, and authorship is always
    # the token owner's. `WorkflowCreate` accepts extra fields and has `id_hash`
    # with a default — passing on what the client sent would let it choose the
    # workflow's id and forge who created it.
    extras: dict = {
        "created_by_id": escopo.user_id,
        "updated_by_id": escopo.user_id,
        # Provenance stamped by the IDENTITY, never by a body argument:
        # "usuario" for PAT and assistant, "assistente" for the Home assistant.
        "origem": escopo.origem_dos_fluxos,
    }
    if description is not None:
        extras["description"] = description
    if params_schema is not None:
        extras["params_schema"] = params_schema

    async with infra.sessao() as db:
        wf = await WorkflowService(db).create_workflow(
            name=name, definition=definition or {}, workspace_id=alvo, **extras
        )
        # The CRUD has already committed the workflow; this commit closes
        # whatever the scheduling may have added. `infra.sessao` rolls back in
        # the finally — what is not committed here does not exist.
        await db.commit()
        dados = {
            "id": wf.id_hash,
            "workspace_id": wf.workspace_id,
            "is_active": bool(wf.flag_ative),
            "created_by_id": wf.created_by_id,
            "validated": bool(validate_first),
        }
        nome = wf.name

    if validate_first:
        dados["validation"] = _validation_summary(relatorio)
    return envelope(dados, name=nome, validation_report=relatorio or None)


@ferramenta
async def update_workflow(
    ctx: Context,
    workflow_id: str,
    definition: dict | None = None,
    name: str | None = None,
    description: str | None = None,
    params_schema: dict | None = None,
    change_note: str | None = None,
    validate_first: bool = True,
    force: bool = False,
) -> dict:
    """Updates an existing workflow. Only the fields sent change.

    Activating and deactivating does NOT go through here: `flag_ative` has its
    own tool (`set_workflow_active`), because turning a workflow on is an
    operations decision, not an editing one, and mixing it into an `update`
    would make a call that only wanted to rename turn on the schedule as well.

    Changing the definition may generate a snapshot in `workflow_versions` (the
    rule belongs to the core: only a substantial change creates a version) —
    the response says whether it did.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")
    if definition is not None:
        _recusar_segredo(definition)
    if params_schema is not None:
        _refuse_secret_in_schema(params_schema)

    campos: dict = {}
    for chave, valor in (
        ("definition", definition),
        ("name", name),
        ("description", description),
        ("params_schema", params_schema),
    ):
        if valor is not None:
            campos[chave] = valor
    if not campos:
        raise erro(
            "validation",
            "Nada a atualizar: nenhum campo foi enviado.",
            "envie definition, name, description ou params_schema",
        )

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _ROLE_MESSAGE)
        id_hash = wf.id_hash
        workspace_id = wf.workspace_id
        versions_before = await _count_versions(db, id_hash)

    relatorio: dict = {}
    if definition is not None and validate_first:
        relatorio = await _validate_before_saving(
            definition, user_id=escopo.user_id, workspace_id=workspace_id, force=force
        )

    try:
        # `WorkflowUpdate` is `extra="forbid"` and exposes neither
        # `workspace_id` nor `updated_by_id`: changing tenant or forging
        # authorship does not go through here.
        workflow_in = WorkflowUpdate(**campos)
    except ValidationError as exc:
        raise erro(
            "validation",
            "Campos inválidos para a atualização.",
            "confira os tipos em errors[] e repita",
            errors=_shape_errors(exc),
        ) from exc

    async with infra.sessao() as db:
        atualizado = await WorkflowService(db).update_workflow(
            id_hash, workflow_in, change_note=change_note, updated_by_id=escopo.user_id
        )
        await db.commit()
        avisos = _schedule_warnings(atualizado)
        versions_after = await _count_versions(db, id_hash)
        dados = {
            "id": atualizado.id_hash,
            "workspace_id": atualizado.workspace_id,
            "is_active": bool(atualizado.flag_ative),
            "updated_fields": sorted(campos),
            "version_snapshot": versions_after > versions_before,
            "versions_count": versions_after,
            # The notice code is closed and generated by the platform; the
            # message, which cites the schedule expression written by people,
            # goes in the untrusted block.
            "schedule_notice_codes": [str(a.get("code")) for a in avisos],
        }
        nome = atualizado.name

    if definition is not None and validate_first:
        dados["validation"] = _validation_summary(relatorio)
    return envelope(
        dados,
        name=nome,
        schedule_notices=avisos or None,
        validation_report=relatorio or None,
    )


@ferramenta
async def set_workflow_active(ctx: Context, workflow_id: str, active: bool) -> dict:
    """Turns the workflow on or off — the only path to `flag_ative`.

    Turning it off is not just a field: the core syncs the schedules with the
    new state, so that a deactivated workflow does not keep being fired by the
    scheduler. The notices from that sync come back in the response.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _ROLE_MESSAGE)
        atualizado = await WorkflowService(db).update_workflow(
            wf.id_hash,
            WorkflowUpdate(flag_ative=bool(active)),
            updated_by_id=escopo.user_id,
        )
        await db.commit()
        avisos = _schedule_warnings(atualizado)
        dados = {
            "id": atualizado.id_hash,
            "workspace_id": atualizado.workspace_id,
            "is_active": bool(atualizado.flag_ative),
            "schedule_notice_codes": [str(a.get("code")) for a in avisos],
        }
        nome = atualizado.name

    return envelope(dados, name=nome, schedule_notices=avisos or None)


def _share_list(shared_with: Any) -> list | None:
    """The list of who sees the private portal, sanitized.

    `None` stays `None` ("with nobody yet"), which is what REST saves when the
    body does not bring the list. Anything else that is not a list is refused
    instead of coerced: saving `"ana"` as `["a","n","a"]` is the kind of silent
    fix that only shows up when someone opens the portal.
    """
    if shared_with is None:
        return None
    if not isinstance(shared_with, (list, tuple)):
        raise erro(
            "validation",
            "shared_with precisa ser uma lista de identificadores.",
            'exemplo: ["ana", "bruno"]',
        )
    return [str(item).strip() for item in shared_with if str(item).strip()]


@ferramenta
async def set_portal_access(
    ctx: Context, workflow_id: str, access: str, shared_with: list[str] | None = None
) -> dict:
    """Publishes (or unpublishes) the workflow on the portal.

    `private` is the only state in which the sharing list means anything: in
    `public` and `disabled` it is CLEARED, and not merely ignored. Keeping it
    "for when it becomes private again" would leave in the database a list of
    people nobody sees on screen and that would become valid again without new
    approval.

    The URL returned is absolute — an MCP client has no base to complete a
    relative path.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    alvo = str(access or "").strip().lower()
    if alvo not in PORTAL_ACCESS_MODES:
        raise erro(
            "validation",
            "access precisa ser disabled, public ou private.",
            "use private com shared_with para restringir a pessoas",
            allowed=list(PORTAL_ACCESS_MODES),
        )
    lista = _share_list(shared_with) if alvo == "private" else None

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _ROLE_MESSAGE)
        # Direct write in the ORM, like `PATCH /workflows/{id}/portal`:
        # `WorkflowUpdate` has no `portal_access` (and must not have it —
        # changing the publication state through the generic PUT would hide
        # the decision inside a "save").
        wf.portal_access = alvo
        wf.portal_shared_with = lista
        dados = {
            "id": wf.id_hash,
            "workspace_id": wf.workspace_id,
            "portal_access": alvo,
            "share_url": _share_url(wf),
        }
        shared_with_list = list(lista or [])
        nome = wf.name
        await db.commit()

    # An empty list still shows up: "shared with nobody" is an answer.
    return envelope(dados, name=nome, shared_with=shared_with_list)


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="validate_workflow",
        title="Validar definição",
        description=(
            "Valida uma definição de workflow sem gravar nada: erros e avisos do lint, "
            "schema de saída de cada nó, nós desabilitados, referências de sub-fluxo e "
            "sugestão de params_schema. Informe `workspace_id` (obrigatório) para que "
            "credenciais, nós desabilitados e sub-fluxos sejam conferidos. Recusa na "
            "entrada, sem validar, a definição com segredo em texto claro — referencie "
            "credenciais por `credential_id` (list_credentials)."
        ),
        annotations=anotacoes("validate_workflow"),
    )(validate_workflow)

    server.tool(
        name="create_workflow",
        title="Criar workflow",
        description=(
            "Cria um workflow no workspace indicado. Valida antes de gravar "
            "(`validate_first`, use `force=true` para gravar apesar de erros não fatais) e "
            "recusa definição com segredo em texto claro — referencie credenciais por "
            "`credential_id` (list_credentials)."
        ),
        annotations=anotacoes("create_workflow"),
    )(create_workflow)

    server.tool(
        name="update_workflow",
        title="Atualizar workflow",
        description=(
            "Atualiza um workflow existente (id ou nome). Só os campos enviados mudam; "
            "trocar a definition pode gerar um snapshot de versão, e `change_note` descreve "
            "a mudança. Para ativar ou desativar, use set_workflow_active."
        ),
        annotations=anotacoes("update_workflow"),
    )(update_workflow)

    server.tool(
        name="set_workflow_active",
        title="Ativar ou desativar workflow",
        description=(
            "Ativa ou desativa o workflow, sincronizando os agendamentos com o novo estado. "
            "É o único caminho para mudar `is_active`."
        ),
        annotations=anotacoes("set_workflow_active"),
    )(set_workflow_active)

    server.tool(
        name="set_portal_access",
        title="Acesso ao portal",
        description=(
            "Define a publicação do workflow no portal: disabled, public ou private "
            "(com `shared_with`). Devolve o endereço absoluto de compartilhamento; fora de "
            "`private` a lista de compartilhamento é zerada."
        ),
        annotations=anotacoes("set_portal_access"),
    )(set_portal_access)
