"""
Validation of a workflow definition without executing it — the core behind the
MCP server's `validate_workflow` tool and the validation that the building
tools run before saving. There was also the REST shell
`POST /workflows/validate`; it was removed for having no caller (the web never used it, and the
skill that called it was absorbed by the MCP).

Order, and the reason for it:

1. Body (Pydantic) — `properties` is a synonym of `parameters` (the persisted
   definition uses one name, the validate body uses the other), `alias` reaches the
   executor, `position` is ignored, `workspace_id` is optional.
2. Pure lint (`flow/utils/definition_lint.py`), BEFORE building the executor:
   a nonexistent node and a cycle blew up inside `WorkflowExecutor.__init__` and
   became a generic 500 with the cause masked; a duplicate id silently overwrote the
   node. Now all three become **422** with the report in the body
   (`InvalidDefinitionError`) — and a `credential_id` that is not a UUID too (it was
   403; fatal by contract, so that whoever only looks at the HTTP status keeps failing it).
3. Database session only when there is something to check — a credential or `workspace_id`.
   The common case (standalone definition, no credential) still does not open its own
   session: the CI has no Postgres and validation should not pay for a
   connection it does not use. Sub-workflow references are only checked WITH
   `workspace_id`: without proven membership, the lookup by hash would be an
   oracle of the existence, state and ports of other workspaces' workflows.
4. With `workspace_id`: membership first (403 before looking at credentials,
   so as not to reveal the existence of a credential to someone who is not in the
   workspace); credentials shared with the workspace only enter the
   scope for those with the `operator` role or higher — the same required to
   execute, because the DatabaseSpatialQuery simulation CONNECTS to the
   credential's database; below that only the user's own scope applies. Then, the
   checks that need the database (nodes disabled by the admin, sub-workflow
   references).
5. Executor → simulation → edge diagnostics; the result is
   `{node_id: {...}}` + `__edge_diagnostics__` (only when present) + `__report__`
   (always; consumers skip the `__*` keys).

The credential fence is what prevents someone who knows the UUID of someone else's
credential from executing SQL on another user's infrastructure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, model_validator

from app.core.authorization.credential_loader import (
    assert_credentials_accessible,
    credential_scope,
    tipos_e_validades,
)
from app.core.authorization.workflow_access import get_workspace_member_role, has_minimum_role
from app.core.db import get_session_async
from app.core.exceptions import CredentialAccessDeniedError, InvalidDefinitionError
from app.core.rbac import ROLE_OPERATOR
from app.services import fontes_service
from app.services.credential_resolver import receiving_property, accepted_types_from_descriptor
from app.services.disabled_nodes_service import disabled_names
from flow.utils.definition_lint import FATAL_CODES, LintReport, lint_definition
from flow.utils.workflow_contract import validate_subworkflow_references_against_db

HINT_WORKSPACE = (
    "Informe workspace_id para checar nós desabilitados, referências de sub-fluxo "
    "e credenciais compartilhadas com o workspace."
)
HINT_OPERATOR_ROLE = (
    "Credenciais compartilhadas com o workspace só entram na validação com papel "
    "operator ou superior (o mesmo exigido para executar); o escopo ficou só nas suas."
)
HINT_PARAMS_SCHEMA = (
    "suggested_params_schema é heurístico (referências inputs.<nome> em nós trigger e "
    "ports de SubWorkflowInput); revise antes de gravar em params_schema."
)
HINT_SOURCES = (
    "Fontes externas (WFS) não são sondadas aqui — a validação não toca a rede. "
    "unknown_source/failing_source dizem o que o catálogo sabe: use search_sources/"
    "describe_source para uma fonte já mapeada, ou probe_source/register_source para "
    "sondar e registrar esta."
)


# --- MODELOS ---
class NodeParameter(BaseModel):
    id: str
    name: str
    type: str
    parameters: Dict[str, Any] = {}
    # The alias lives at the top of the node in the persisted definition and is what the executor reads
    # (`flow/core/aliases.py`); without it here, the alias lint would have nothing to see.
    alias: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _merge_properties(cls, data: Any) -> Any:
        # The persisted definition uses `properties`; the validate body, `parameters`.
        # Pasting one into the other silently lost all values (extra='ignore').
        # On conflict, `parameters` (this body's format) wins. A `parameters`
        # that is not an object is left as is, so Pydantic reports 422 — a
        # TypeError in here would become a 500.
        if isinstance(data, dict) and isinstance(data.get("properties"), dict):
            atuais = data.get("parameters")
            if atuais is None or isinstance(atuais, dict):
                data = dict(data)
                data["parameters"] = {**data["properties"], **(atuais or {})}
        return data


class EdgeDefinition(BaseModel):
    source: str
    target: str
    # Pydantic discards what is not declared, and `payload = definition.dict()`
    # went straight to the WorkflowExecutor. Without these fields the simulation always fell
    # into the "no from_key" branch (core.py:765) and named the inputs with the parent_id:
    # the preview schema diverged from what the run actually produced. A panel that
    # disagrees with the runtime is worse than no panel at all.
    from_key: Optional[str] = None
    to_key: Optional[str] = None
    condition: Optional[bool] = None


class WorkflowDefinition(BaseModel):
    nodes: List[NodeParameter]
    edges: List[EdgeDefinition]
    # Optional on purpose: without it validation keeps working without a database;
    # with it, the checks that depend on the workspace come in (§4 of the module).
    workspace_id: Optional[str] = None


# --- HELPERS ---
def _payload_para_o_executor(definition: WorkflowDefinition) -> dict:
    """Definition in the format the executor and the server helpers read.

    `parameters` and `properties` point to the SAME dict: `simulate_runner` reads
    `parameters`, `node_props` (server) and `collect_subworkflow_references` read
    `properties`. A single dict, so there is no way for them to diverge.
    """
    nos = []
    for n in definition.nodes:
        params = dict(n.parameters)
        no: dict = {"id": n.id, "name": n.name, "type": n.type, "parameters": params, "properties": params}
        if n.alias:
            no["alias"] = n.alias
        nos.append(no)
    return {"nodes": nos, "edges": [e.model_dump() for e in definition.edges]}


def _valid_credential_ids(nodes: list) -> set:
    """`credential_id` UUIDs that go to the database guard. The malformed ones do not
    reference any credential and have already failed the definition with 422
    (`invalid_credential_id` is fatal in the lint) before getting here — instead of the
    403 from before, which masked a typo; the filter stays as belt and suspenders."""
    ids: set = set()
    for n in nodes:
        cid = (n.get("parameters") or {}).get("credential_id")
        if not cid:
            continue
        try:
            UUID(str(cid))
        except (ValueError, AttributeError, TypeError):
            continue
        ids.add(str(cid))
    return ids


def _check_credentials(lint: LintReport, nodes: list, descriptors: Dict[str, dict], credenciais: dict) -> None:
    """Diagnostics for the credential that the resolution will NOT deliver to the node:
    of a type it does not accept, or that has nowhere to go in it
    (`credential_type_mismatch`), or expired (`credential_expired`).

    Only the screen filters the credential by type; through the API and the assistant
    any one arrives, and the resolution silently leaves it out. Where the node CONSUMES
    the injected secret (WFS, HttpRequest, the database ones — they declare `http_auth`
    or `connectionString`) this is a refused execution: an error (not fatal). Where the
    node uses the id itself (DataOutput and the SaveTo*, with `webhook_token`) the
    execution proceeds and only the artifact download is refused: a warning — an error
    here would prevent the assistant from saving an edit to another node.
    `credenciais` is what `tipos_e_validades` returned for the accessible ids.
    """
    for n in nodes:
        cid = (n.get("parameters") or {}).get("credential_id")
        try:
            chave = str(UUID(str(cid))) if cid else None
        except (ValueError, AttributeError, TypeError):
            chave = None
        if chave is None or chave not in credenciais:
            continue
        tipo, validade, expires_at = credenciais[chave]
        descriptor = descriptors.get(n.get("name")) or {}
        declaradas = {p.get("name") for p in descriptor.get("properties") or [] if isinstance(p, dict)}
        recebe = receiving_property(tipo)
        # SaveToS3 declares `s3_auth` and also accepts the Webhook Token from the
        # old usage (protects the copy): it consumes the secret only when it is the S3 one.
        consome = bool(declaradas & {"http_auth", "connectionString"}) or (
            recebe == "s3_auth" and recebe in declaradas
        )
        registrar = lint.erro if consome else lint.aviso
        desfecho = (
            "o Executar não a resolve e o nó recusa" if consome
            else "o download do artefato protegido por ela será recusado"
        )
        onde = f"nó '{n.get('name')}' (id={n.get('id')})"
        aceitos = accepted_types_from_descriptor(descriptor)
        if aceitos is not None and tipo not in aceitos:
            registrar(
                "credential_type_mismatch",
                f"{onde} aponta uma credencial do tipo '{tipo}', que ele não aceita "
                f"({', '.join(sorted(aceitos))}) — {desfecho}.",
                node_id=n.get("id"),
            )
        elif recebe is not None and declaradas and recebe not in declaradas:
            # With no declared `credential_types` (the database nodes), the SHAPE of the
            # credential decides: an HTTP one has nowhere to go in a node that only
            # receives `connectionString` — the resolution leaves the id and nothing else.
            registrar(
                "credential_type_mismatch",
                f"{onde} aponta uma credencial do tipo '{tipo}', que ele não tem onde receber "
                f"(o nó não declara `{recebe}`) — {desfecho}.",
                node_id=n.get("id"),
            )
        # SaveToS3 uses the SAME `credential_id` for both things: with the
        # S3 credential chosen, the copy registered as an artifact loses the
        # Webhook Token that protected it — download via the link, as in the node without a
        # credential. It is a possible choice, but it cannot be silent.
        if (
            tipo == "s3" and "s3_auth" in declaradas
            and (n.get("parameters") or {}).get("registerArtifact") in (True, "true", "True", 1, "1")
        ):
            lint.aviso(
                "artifact_copy_unprotected",
                f"{onde} usa a credencial S3 e registra a cópia como artefato: a cópia fica "
                "sem token de proteção (download público pelo link). Para protegê-la, use a "
                "cadeia padrão do executor no lugar da credencial S3 e escolha um Webhook Token.",
                node_id=n.get("id"),
            )
        if validade == "expirada":
            registrar(
                "credential_expired",
                f"{onde} aponta uma credencial vencida em {expires_at} — {desfecho}.",
                node_id=n.get("id"),
            )
        elif validade == "invalida":
            registrar(
                "credential_expired",
                f"{onde} aponta uma credencial com validade (expires_at) ilegível: {expires_at!r} — "
                f"ignorada por segurança; {desfecho}.",
                node_id=n.get("id"),
            )


def _item(code: str, severity: str, message: str, *, node_id: Optional[str] = None,
          edge: Optional[dict] = None) -> dict:
    return {"code": code, "severity": severity, "node_id": node_id, "edge": edge, "message": message}


def _build_report(
    lint: LintReport,
    nodes: list,
    *,
    disabled_nodes: Optional[list],
    subworkflow_errors: Optional[list],
    edge_diagnostics: list,
    simulated_outputs: dict,
    hints: list,
    source_warnings: Optional[list] = None,
) -> dict:
    """`__report__`: everything the validation found, in a single format.

    `errors` combines the lint with what depends on the database (disabled node, sub-workflow)
    and with what the simulation produced (edge with a nonexistent `from_key`, node with
    `status: error`). `ok` is "no errors" — warnings do not fail it. `source_warnings`
    are the source catalog warnings (`unknown_source`, `failing_source`):
    also warnings, because validation does not probe the source — it only says what it knows.
    """
    errors = [d.as_dict() for d in lint.errors]
    warnings = [d.as_dict() for d in lint.warnings]
    warnings.extend(source_warnings or [])

    if disabled_nodes:
        desabilitados = set(disabled_nodes)
        for n in nodes:
            if n.get("name") in desabilitados:
                errors.append(_item(
                    "disabled_node", "error",
                    f"nó '{n['name']}' (id={n.get('id')}) está desabilitado pelo admin — "
                    "o run recusa com 422 workflow_has_disabled_nodes.",
                    node_id=n.get("id"),
                ))
    for msg in subworkflow_errors or []:
        errors.append(_item("subworkflow_reference", "error", str(msg)))

    for d in edge_diagnostics:
        edge = {"source": d.get("source"), "target": d.get("target")}
        if d.get("from_key") is not None:
            edge["from_key"] = d["from_key"]
        if d.get("severity") == "error":
            errors.append(_item("edge_from_key_unknown", "error", str(d.get("message", "")), edge=edge))
        else:
            warnings.append(_item("edge_spread_ambiguous", "warning", str(d.get("message", "")), edge=edge))

    for node_id, saida in simulated_outputs.items():
        if str(node_id).startswith("__") or not isinstance(saida, dict):
            continue
        if saida.get("status") == "error":
            errors.append(_item("simulate_error", "error", str(saida.get("error", "")), node_id=node_id))

    sugestao = dict(lint.suggested_params_schema)
    dicas = list(hints)
    if sugestao:
        dicas.append(HINT_PARAMS_SCHEMA)
    if source_warnings:
        dicas.append(HINT_SOURCES)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "disabled_nodes": disabled_nodes,
        "subworkflow_errors": subworkflow_errors,
        "suggested_params_schema": sugestao,
        "hints": dicas,
    }


def _fatal_message(lint: LintReport) -> str:
    fatais = [d.message for d in lint.errors if d.code in FATAL_CODES]
    mensagem = "Definição inválida: " + "; ".join(fatais[:3])
    if len(fatais) > 3:
        mensagem += f" (+{len(fatais) - 3})"
    return mensagem


# --- CORE ---
async def validar_definicao(
    definition: Union[dict, WorkflowDefinition],
    *,
    user_id: str,
    workspace_id: Optional[str],
) -> dict:
    """Lint of the definition, output schema of each node and edge diagnostics.

    Returns `{node_id: {status, schema, schema_source} | {status: "error", error}}`
    + `__edge_diagnostics__` (only when present) + `__report__` (always; `ok` = no
    errors). A `dict` goes through `WorkflowDefinition.model_validate`, with
    `properties` merged into `parameters`; a malformed body propagates as
    `pydantic.ValidationError` for the caller to translate.

    An explicit `workspace_id` wins over the body's: the caller is the one who knows in which
    workspace it is validating (the MCP resolves id-or-name before getting here);
    `None` lets the body's apply, where the field is optional.

    Raises `InvalidDefinitionError` (with `.report`) when the executor would not even
    build — nonexistent node, duplicate id, cycle, a `credential_id` that is not a
    UUID, build error; `HTTPException(403)` when the user is not a member
    of the workspace; `HTTPException(503)` with an empty registry (boot failure, not
    of the definition); `CredentialAccessDeniedError` when some credential is
    out of scope (with the `workspace_id` hint when there was no workspace).
    """
    from flow.executor import WorkflowExecutor
    from flow.registry import NODE_REGISTRY

    if not isinstance(definition, WorkflowDefinition):
        definition = WorkflowDefinition.model_validate(definition)
    if workspace_id is None:
        workspace_id = definition.workspace_id

    if not NODE_REGISTRY:
        # An empty registry is a server boot failure, not a definition one: reporting
        # "nonexistent node" here would send the client to fix a correct name.
        raise HTTPException(status_code=503, detail="Catálogo de nós indisponível neste servidor.")

    payload = _payload_para_o_executor(definition)
    nodes = payload["nodes"]
    nomes = {n["name"] for n in nodes}
    hints: list = [] if workspace_id else [HINT_WORKSPACE]

    descriptors: Dict[str, dict] = {}
    for nome in nomes:
        cls = NODE_REGISTRY.get(nome)
        if cls is None:
            continue
        try:
            descriptors[nome] = cls.description()
        except Exception:  # a broken descriptor cannot bring down the validation
            continue

    lint = lint_definition(nodes, payload["edges"], registry_names=NODE_REGISTRY.keys(), descriptors=descriptors)
    if lint.fatal:
        raise InvalidDefinitionError(_fatal_message(lint), report=_build_report(
            lint, nodes, disabled_nodes=None, subworkflow_errors=None,
            edge_diagnostics=[], simulated_outputs={}, hints=hints,
        ))

    cred_ids = _valid_credential_ids(nodes)
    disabled_nodes: Optional[list] = None
    subworkflow_errors: Optional[list] = None
    shared_scope: Optional[str] = None
    avisos_de_fonte: list = []
    if cred_ids or workspace_id:
        # ONE session, and only here — no Depends(get_db): most validations
        # reference neither a credential nor a workspace and should not pay for a connection.
        async with get_session_async() as db:
            if workspace_id:
                papel = await get_workspace_member_role(db, workspace_id, user_id)
                if papel is None:
                    raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
                if has_minimum_role(papel, ROLE_OPERATOR):
                    shared_scope = workspace_id
                elif cred_ids:
                    hints.append(HINT_OPERATOR_ROLE)
            if cred_ids:
                try:
                    await assert_credentials_accessible(
                        db, cred_ids, user_id, shared_workspace_id=shared_scope,
                    )
                except CredentialAccessDeniedError as exc:
                    if workspace_id:
                        raise
                    # Without a workspace the scope is only the user's: the credential may
                    # be shared and the person just does not know they need to say where.
                    raise CredentialAccessDeniedError(f"{exc.detail} {HINT_WORKSPACE}") from exc
                # Accessible is not usable: the type and the validity decide whether
                # Run resolves it — and it is here, not in the run, that the warning is given.
                _check_credentials(lint, nodes, descriptors, await tipos_e_validades(db, cred_ids))
            desabilitados = await disabled_names(db)
            disabled_nodes = sorted(nomes & set(desabilitados))
            if workspace_id:
                subworkflow_errors = list(
                    await validate_subworkflow_references_against_db(payload, db, workspace_id=workspace_id)
                )
                # The source catalog: no network, one query per definition. Fails
                # OPEN here too — validation does not depend on the catalog.
                try:
                    avisos_de_fonte = await fontes_service.conferir_fontes_da_definicao(
                        db, nodes, descriptors, workspace_id,
                    )
                except Exception:  # pragma: no cover - the service already fails open
                    avisos_de_fonte = []

    try:
        executor = WorkflowExecutor(payload)
    except ValueError as exc:
        # Safety net: the lint covers what is known; any other build
        # error also belongs to the definition, not the server.
        lint.erro("construction_error", str(exc))
        raise InvalidDefinitionError(f"Definição inválida: {exc}", report=_build_report(
            lint, nodes, disabled_nodes=disabled_nodes, subworkflow_errors=subworkflow_errors,
            edge_diagnostics=[], simulated_outputs={}, hints=hints, source_warnings=avisos_de_fonte,
        ))

    # Same scope as the dispatch: the user's credentials plus those shared
    # with the given workspace (for whoever can execute) — and nothing beyond that,
    # even if a new `simulate()` shows up.
    with credential_scope({user_id}, shared_workspace_id=shared_scope):
        await executor.simulate_runner()

    # Edge diagnostics (stale from_key = error; ambiguous spread = warning).
    # Under a reserved key, in the same pattern as __artifacts__/__response__, so as
    # not to be confused with the per-node_id schemas. Only appears when there is something.
    diagnostics = executor.validate_edges()
    saida = executor.simulated_outputs
    if diagnostics:
        saida["__edge_diagnostics__"] = diagnostics
    saida["__report__"] = _build_report(
        lint, nodes, disabled_nodes=disabled_nodes, subworkflow_errors=subworkflow_errors,
        edge_diagnostics=diagnostics, simulated_outputs=saida, hints=hints,
        source_warnings=avisos_de_fonte,
    )
    return saida
