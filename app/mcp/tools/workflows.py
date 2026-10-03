# app/mcp/tools/workflows.py
"""Workflow tools. The guards for each one are in app/mcp/guardas.py."""
from __future__ import annotations

from typing import Any, Mapping

from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from app.core import config
from app.core.authorization.workflow_access import exigir_papel
from app.core.rbac import ROLE_VIEWER
from app.core.utils.redacao import compactar_definition, redigir_definition
from app.mcp import infra
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow, resolver_workspace
from app.mcp.saida import envelope, iso, resumo_definition
from app.mcp.tools.base import ferramenta
from app.services.workflow_service import WorkflowService
from flow.utils.workflow_contract import extract_contract

# Listing ceiling. It is not about saving the database: it is the context budget
# of whoever reads on the other side — 200 items are already ~40 KB of response.
LIMITE_MAXIMO = 200

_MENSAGEM_PAPEL = "Requer papel 'viewer' ou superior neste workspace."


def _share_url(wf) -> str | None:
    """The portal URL, ABSOLUTE.

    REST returns `/share/{id}` because its consumer is the application's own
    browser. An MCP client has no base at all to complete it with: a relative
    URL would reach the person as a path that opens nowhere.
    """
    if not wf.portal_access or wf.portal_access == "disabled":
        return None
    return f"{str(config.FRONTEND_URL).rstrip('/')}/share/{wf.id_hash}"


def _resumo_de_agendamento(bruto: Any) -> dict | None:
    """The schedule in closed fields — no raw dates and no extra keys."""
    if not isinstance(bruto, Mapping):
        return None
    return {
        "active": bool(bruto.get("active")),
        "strategy": bruto.get("strategy"),
        "cron_expression": bruto.get("cron_expression"),
        "interval": bruto.get("interval"),
        "unit": bruto.get("unit"),
        "timezone": bruto.get("timezone"),
        "next_run_at": iso(bruto.get("next_run_at")),
        "last_run_at": iso(bruto.get("last_run_at")),
    }


def _casa_com_a_busca(item: Mapping[str, Any], termo: str) -> bool:
    alvo = termo.casefold()
    return alvo in str(item.get("name") or "").casefold() or alvo in str(
        item.get("description") or ""
    ).casefold()


@ferramenta
async def list_workflows(
    ctx: Context,
    workspace_id: str | None = None,
    search: str | None = None,
    only_active: bool = False,
    limit: int = 100,
    incluir_do_assistente: bool | None = None,
) -> dict:
    """Lists the workflows of the workspaces within the token's reach.

    `search` and `only_active` are applied in-process, not in the query: the
    core's lightweight listing does not have those parameters, and adding them
    there just for MCP would change a query the whole application uses. The
    cost is acceptable because the query is already per workspace and does not
    load definitions.

    `incluir_do_assistente` mirrors REST's `?assistente=1`. Left as `None`, it
    is resolved by the scope: the Home assistant stamps `origem="assistente"`
    on everything it creates, and with the `False` default it could not see
    its OWN workflows — in a new chat, "roda de novo aquele do desmatamento"
    (run that deforestation one again) found nothing and a duplicate workflow
    was born on every recurring question. For a regular PAT the default stays
    `False`, and each item's `origem` field makes explicit what was omitted.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")
    teto = max(1, min(int(limit), LIMITE_MAXIMO))
    se_assistente = (
        bool(incluir_do_assistente)
        if incluir_do_assistente is not None
        else getattr(escopo, "origem_dos_fluxos", None) == "assistente"
    )

    async with infra.sessao() as db:
        if workspace_id is not None:
            alcance = [await resolver_workspace(db, escopo, workspace_id)]
        else:
            alcance = sorted(escopo.workspace_ids)
        if not alcance:
            return {"items": [], "total": 0, "limit": teto}
        brutos = await WorkflowService(db).list_workflows_metadata_by_ids(
            alcance, incluir_do_assistente=se_assistente
        )

    filtrados = [
        item
        for item in brutos
        if (not only_active or bool(item.get("flag_ative")))
        and (not search or _casa_com_a_busca(item, search))
    ]
    pagina = sorted(filtrados, key=lambda i: str(i.get("updated_at") or ""), reverse=True)[:teto]

    itens = [
        envelope(
            {
                "id": item.get("id_hash"),
                "workspace_id": item.get("workspace_id"),
                "is_active": bool(item.get("flag_ative")),
                # The origin distinguishes what the assistant created from what the
                # person created — and, with it, whether an action on that
                # workflow will ask for the confirmation click on Home.
                "origem": item.get("origem") or "usuario",
                "is_subworkflow": bool(item.get("is_subworkflow")),
                "has_webhook_trigger": bool(item.get("has_webhook_trigger")),
                "has_schedule_trigger": bool(item.get("has_schedule_trigger")),
                "has_file_trigger": bool(item.get("has_file_trigger")),
                "has_geofence_trigger": bool(item.get("has_geofence_trigger")),
                "has_publish_map": bool(item.get("has_publish_map")),
                "portal_access": item.get("portal_access"),
                "schedule": _resumo_de_agendamento(item.get("schedule")),
                "updated_at": iso(item.get("updated_at")),
            },
            name=item.get("name"),
            description=item.get("description"),
        )
        for item in pagina
    ]
    return {"items": itens, "total": len(filtrados), "limit": teto}


@ferramenta
async def get_workflow(
    ctx: Context, workflow_id: str, include_definition: bool = False
) -> dict:
    """A workflow in detail: parameters, triggers, portal and topology.

    The definition only goes out on request (`include_definition=true`) and is
    always REDACTED: the workflow is loaded without decrypting and what is
    handed over goes through `redigir_definition` (secrets become
    `<REDACTED>`) and `compactar_definition` (position and viewport, which
    only serve the canvas, do not travel).
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL)
        versoes = await WorkflowService(db).list_versions(wf.id_hash)
        segura = compactar_definition(redigir_definition(wf.definition or {}))
        dados = {
            "id": wf.id_hash,
            "workspace_id": wf.workspace_id,
            "is_active": bool(wf.flag_ative),
            "my_role": papel,
            "versions_count": len(versoes or []),
            "portal": {"access": wf.portal_access, "share_url": _share_url(wf)},
            "created_at": iso(wf.created_at),
            "updated_at": iso(wf.updated_at),
        }
        resumo = resumo_definition(segura, pin_metadata=wf.pin_metadata)
        nome, descricao = wf.name, wf.description
        # Raw: sanitizing is the `envelope`'s job, once, on output.
        esquema = wf.params_schema if wf.params_schema else None

    dados["pins"] = resumo["pins"]
    dados["node_count"] = resumo["node_count"]
    dados["edge_count"] = resumo["edge_count"]
    # Everything that came from the definition or the parameter schema is text
    # from whoever edits the workflow: the nodes' nicknames in `summary`, the
    # triggers' NAME, and the keys and descriptions of `params_schema` (which
    # the client shows to whoever will fill them in). None of that rises to
    # the top — the top is for values the platform generates.
    # An empty list STILL appears: `envelope` only omits null keys, and the
    # difference matters here — `triggers: []` is "this workflow does not fire
    # on its own", an answer; the key's absence would be "I didn't ask".
    # `params_schema` is the opposite: with no filled-in column there is no
    # schema to describe, so it stays `None` and disappears.
    return envelope(
        dados,
        name=nome,
        description=descricao,
        params_schema=esquema,
        triggers=resumo["triggers"],
        summary={"nodes": resumo["nodes"], "edges": resumo["edges"]},
        definition=segura if include_definition else None,
    )


@ferramenta
async def get_workflow_contract(ctx: Context, workflow_id: str) -> dict:
    """The workflow's declared inputs and outputs as a sub-workflow.

    It is what answers "can I call this workflow from inside another, and with
    which keys?". It reads only the ports declared in the contract nodes — no
    sensitive property is touched, and that is why the definition does not
    need to be decrypted.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL)
        contrato = extract_contract(wf.definition or {})
        dados = {
            "id": wf.id_hash,
            "workspace_id": wf.workspace_id,
            "is_active": bool(wf.flag_ative),
            # Closed and generated by reading the definition, not written: they
            # stay at the top, which is what the client can obey.
            "has_input_node": bool(contrato.get("has_input_node")),
            "has_output_node": bool(contrato.get("has_output_node")),
            "input_node_count": int(contrato.get("input_node_count") or 0),
            "output_node_count": int(contrato.get("output_node_count") or 0),
        }

    # Each port's NAME is definition text — whoever edits the workflow picks it.
    # An empty list shows up just the same (`envelope` only omits null keys): a
    # workflow with no contract node answers `inputs: []`, not silence.
    return envelope(
        dados,
        inputs=contrato.get("inputs") or [],
        outputs=contrato.get("outputs") or [],
    )


@ferramenta
async def get_portal_info(ctx: Context, workflow_id: str) -> dict:
    """How this workflow is published on the portal, and at which address."""
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL)
        compartilhado = wf.portal_shared_with or []
        dados = {
            "id": wf.id_hash,
            "workspace_id": wf.workspace_id,
            "portal_access": wf.portal_access,
            "share_url": _share_url(wf),
        }
        com_quem = list(compartilhado) if isinstance(compartilhado, list) else []

    # `portal_shared_with` is a free-text column that ANY editor of the
    # workflow fills in — the shortest channel between a person and the client
    # reading this response. A command sentence written there goes out as data,
    # inside `untrusted_data`, never alongside the fields the platform generates.
    # An empty list still appears: "shared with no one" is an answer.
    return envelope(dados, shared_with=com_quem)


_SOMENTE_LEITURA = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="list_workflows",
        title="Listar workflows",
        description=(
            "Lista os workflows dos workspaces ao alcance do token, com gatilhos, "
            "agendamento e estado do portal. Filtre por `workspace_id`, por texto "
            "(`search`, sobre nome e descrição) e por `only_active`."
        ),
        annotations=_SOMENTE_LEITURA,
    )(list_workflows)

    server.tool(
        name="get_workflow",
        title="Detalhar workflow",
        description=(
            "Detalha um workflow (id ou nome): parâmetros de execução, gatilhos, pins, "
            "portal, número de versões e a topologia (nós e arestas). Com "
            "`include_definition=true` devolve também a definição completa, sempre "
            "redigida — segredos saem como <REDACTED>."
        ),
        annotations=_SOMENTE_LEITURA,
    )(get_workflow)

    server.tool(
        name="get_workflow_contract",
        title="Contrato do workflow",
        description=(
            "Entradas e saídas declaradas do workflow como sub-fluxo, para encadear um "
            "fluxo dentro de outro."
        ),
        annotations=_SOMENTE_LEITURA,
    )(get_workflow_contract)

    server.tool(
        name="get_portal_info",
        title="Portal do workflow",
        description=(
            "Estado de publicação do workflow no portal: acesso (disabled/public/private), "
            "endereço absoluto de compartilhamento e com quem foi compartilhado."
        ),
        annotations=_SOMENTE_LEITURA,
    )(get_portal_info)
