# app/mcp/tools/workflows.py
"""Tools de workflows. As guardas de cada uma estão em app/mcp/guardas.py."""
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

# Teto da listagem. Não é economia de banco: é o orçamento de contexto de quem
# lê do outro lado — 200 itens já são ~40 KB de resposta.
LIMITE_MAXIMO = 200

_MENSAGEM_PAPEL = "Requer papel 'viewer' ou superior neste workspace."


def _share_url(wf) -> str | None:
    """A URL do portal, ABSOLUTA.

    A REST devolve `/share/{id}` porque quem a consome é o próprio navegador da
    aplicação. Um cliente MCP não tem base nenhuma para completar: uma URL
    relativa chegaria à pessoa como um caminho que não abre em lugar algum.
    """
    if not wf.portal_access or wf.portal_access == "disabled":
        return None
    return f"{str(config.FRONTEND_URL).rstrip('/')}/share/{wf.id_hash}"


def _resumo_de_agendamento(bruto: Any) -> dict | None:
    """O agendamento em campos fechados — sem datas cruas e sem chave extra."""
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
    """Lista os workflows dos workspaces ao alcance do token.

    `search` e `only_active` são aplicados em processo, e não na consulta: a
    listagem leve do núcleo não tem esses parâmetros, e acrescentá-los lá só
    para o MCP mudaria uma consulta que a aplicação inteira usa. O custo é
    aceitável porque a consulta já é por workspace e não carrega definitions.

    `incluir_do_assistente` espelha o `?assistente=1` da REST. Deixado em `None`,
    ele se resolve pelo escopo: o assistente da Home carimba
    `origem="assistente"` em tudo que cria, e com o default `False` ele não
    enxergava os PRÓPRIOS fluxos — num chat novo, «roda de novo aquele do
    desmatamento» não encontrava nada e nascia um fluxo duplicado a cada
    pergunta recorrente. Para um PAT comum o default segue `False`, e o campo
    `origem` de cada item deixa explícito o que foi omitido.
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
                # A origem distingue o que o assistente criou do que a pessoa
                # criou — e, com ela, se a ação sobre esse fluxo vai pedir o
                # clique de confirmação na Home.
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
    """Um workflow em detalhe: parâmetros, gatilhos, portal e topologia.

    A definition só sai sob pedido (`include_definition=true`) e sai sempre
    REDIGIDA: o workflow é carregado sem decifrar e o que se entrega passa por
    `redigir_definition` (segredo vira `<REDACTED>`) e `compactar_definition`
    (posição e viewport, que só servem ao canvas, não viajam).
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
        # Cru: quem higieniza é o `envelope`, uma vez só, na saída.
        esquema = wf.params_schema if wf.params_schema else None

    dados["pins"] = resumo["pins"]
    dados["node_count"] = resumo["node_count"]
    dados["edge_count"] = resumo["edge_count"]
    # Tudo que veio da definition ou do schema de parâmetros é texto de quem
    # edita o fluxo: o apelido dos nós em `summary`, o NOME dos gatilhos, e as
    # chaves e descrições de `params_schema` (que o cliente exibe a quem vai
    # preencher). Nada disso sobe ao topo — o topo é para valor que a
    # plataforma gera.
    # Lista vazia CONTINUA aparecendo: `envelope` só omite chave nula, e a
    # diferença importa aqui — `triggers: []` é "este fluxo não dispara
    # sozinho", uma resposta; a ausência da chave seria "não perguntei".
    # `params_schema` é o contrário: sem coluna preenchida não há schema a
    # descrever, então segue `None` e some.
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
    """As entradas e saídas declaradas do workflow como sub-fluxo.

    É o que responde "posso chamar este fluxo de dentro de outro, e com quais
    chaves?". Lê só as portas declaradas nos nós de contrato — nenhuma
    propriedade sensível é tocada, e por isso a definition não precisa ser
    decifrada.
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
            # Fechados e gerados pela leitura da definition, não escritos:
            # ficam no topo, que é o que o cliente pode obedecer.
            "has_input_node": bool(contrato.get("has_input_node")),
            "has_output_node": bool(contrato.get("has_output_node")),
            "input_node_count": int(contrato.get("input_node_count") or 0),
            "output_node_count": int(contrato.get("output_node_count") or 0),
        }

    # O NOME de cada porta é texto da definition — quem edita o fluxo escolhe.
    # Lista vazia aparece do mesmo jeito (`envelope` só omite chave nula): um
    # fluxo sem nó de contrato responde `inputs: []`, e não silêncio.
    return envelope(
        dados,
        inputs=contrato.get("inputs") or [],
        outputs=contrato.get("outputs") or [],
    )


@ferramenta
async def get_portal_info(ctx: Context, workflow_id: str) -> dict:
    """Como este workflow está publicado no portal, e em que endereço."""
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

    # `portal_shared_with` é uma coluna de texto livre que QUALQUER editor do
    # workflow preenche — o canal mais curto entre uma pessoa e o cliente que
    # lê esta resposta. Uma frase de comando escrita ali sai como dado, dentro
    # de `untrusted_data`, nunca ao lado dos campos que a plataforma gera.
    # Lista vazia continua aparecendo: "compartilhado com ninguém" é resposta.
    return envelope(dados, shared_with=com_quem)


_SOMENTE_LEITURA = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def registrar(server) -> None:
    """Registra as tools deste domínio."""
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
