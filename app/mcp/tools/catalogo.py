# app/mcp/tools/catalogo.py
"""Catalog tools. The guards for each one are in app/mcp/guardas.py."""
from __future__ import annotations

from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from app.mcp import guia, infra
from app.mcp.catalogo import descrever, compact_index, catalog_types
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.tools.base import ferramenta
from app.services.node_service import NodeService

# The prefix of the equivalent resource. The tool and the resource deliver the
# SAME text; returning the URI along with it saves the integrator from having to
# build it on their own.
GUIDE_URI = "atlans://guide/authoring/{topic}"


async def _definitions():
    """The current node catalog — already without the nodes disabled by the platform."""
    async with infra.sessao() as db:
        return await NodeService().list_nodes(db)


@ferramenta
async def search_nodes(
    ctx: Context, query: str | None = None, type: str | None = None
) -> dict:
    """Compact index of the available nodes.

    Returns name, type, a one-line description and whether the node requires a
    credential — enough to choose. The configuration sheet comes afterwards,
    through `describe_node`: the whole catalog in detail exceeds 70 KB and does
    not fit in a conversation's context budget.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    definitions = await _definitions()
    itens = compact_index(definitions, query=query, tipo=type)
    return {
        "items": itens,
        "total": len(itens),
        "types": catalog_types(definitions),
    }


# The ceiling of sheets per call. It protects the conversation's context (the
# full sheet is large) without pushing the model back to the one-round-per-node
# pattern.
SHEETS_CEILING = 8


def _find(definitions, pedido: str):
    """The SAME resolution as the old path: name or alias, in catalog order."""
    for d in definitions:
        if d.name == pedido or (d.alias and d.alias == pedido):
            return d
    return None


@ferramenta
async def describe_node(ctx: Context, name: str | list[str], brief: bool = True) -> dict:
    """The sheet of one node — or of SEVERAL in a single call.

    `name` accepts a name or a LIST of names (up to 8): ask for the sheets of
    all the workflow's nodes at once, instead of spending one round per node.
    `brief=true` (the default) brings the essentials for configuring.
    `brief=false` brings the full catalog sheet — use it when the property
    you are looking for does not appear in the summary.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    if isinstance(name, list):
        # Deduplicated preserving order: the model repeats names without
        # noticing, and two identical sheets would only burn context.
        pedidos = list(dict.fromkeys(n for n in (str(item).strip() for item in name) if n))
        if not pedidos:
            raise erro(
                "validation",
                "A lista de `name` veio vazia.",
                "informe ao menos um nome de nó",
            )
        ignorados = pedidos[SHEETS_CEILING:]
        pedidos = pedidos[:SHEETS_CEILING]

        definitions = await _definitions()
        fichas: list[dict] = []
        # An unknown name does NOT bring down the batch: the sheets found come
        # back and `not_found` names the ones that were missing — the model
        # fixes only what it got wrong, without paying another round for the
        # ones it got right. A disabled node answers the same as a nonexistent
        # one, as on the single-name path.
        not_found: list[str] = []
        # Dedupe also by RESOLUTION: a name and an alias of the same node in
        # the list would return the same sheet twice — the context spending
        # this ceiling exists to avoid.
        described: set[str] = set()
        for pedido in pedidos:
            d = _find(definitions, pedido)
            if d is None:
                not_found.append(pedido)
            elif d.name not in described:
                described.add(d.name)
                fichas.append(descrever(d, brief=brief))
        saida: dict = {"nodes": fichas, "total": len(fichas)}
        dicas: list[str] = []
        if not_found:
            saida["not_found"] = not_found
            dicas.append("use search_nodes para conferir os nomes em not_found")
        if ignorados:
            saida["skipped"] = ignorados
            dicas.append(
                f"o teto é {SHEETS_CEILING} nomes por chamada; peça os de skipped na próxima"
            )
        if dicas:
            saida["hint"] = "; ".join(dicas)
        return saida

    wanted = str(name).strip()
    d = _find(await _definitions(), wanted)
    if d is not None:
        return descrever(d, brief=brief)

    # An unknown name is `not_found`, and not a list of suggestions: the
    # index already exists in `search_nodes`, and a node disabled by the
    # platform has to answer the same as a nonexistent node.
    raise erro(
        "not_found",
        f"Nenhum nó chamado '{wanted}' está disponível.",
        "use search_nodes para ver os nós disponíveis",
    )


@ferramenta
async def get_authoring_guide(ctx: Context, topic: str) -> dict:
    """The workflow authoring guide, by topic.

    One topic per call, on purpose: the whole guide at once wastes context on
    what will not be used in that task.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    pedido = str(topic).strip()
    try:
        markdown = guia.ler_topico(pedido)
    except ValueError as exc:
        raise erro(
            "not_found",
            str(exc),
            "escolha um dos tópicos disponíveis em topics",
            topics=list(guia.TOPICS),
        ) from exc
    except OSError as exc:
        # The topic exists in the list but the file could not be read: that is a
        # deployment defect, not an invalid request — and the client needs to
        # know the content is not there, without receiving the file path.
        raise erro(
            "unavailable",
            f"O guia do tópico '{pedido}' não está disponível nesta instalação.",
            "tente outro tópico ou avise quem administra a plataforma",
        ) from exc

    return {
        "topic": pedido,
        "markdown": markdown,
        "resource_uri": GUIDE_URI.replace("{topic}", pedido),
        "topics": list(guia.TOPICS),
    }


_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="search_nodes",
        title="Buscar nós",
        description=(
            "Índice compacto dos nós disponíveis para montar um fluxo: nome, tipo, uma "
            "linha de descrição e se o nó exige credencial. Filtre por texto (`query`, "
            "sobre nome, apelido e descrição) e por `type`."
        ),
        annotations=_READ_ONLY,
    )(search_nodes)

    server.tool(
        name="describe_node",
        title="Detalhar nó",
        description=(
            "Ficha de um nó do catálogo: propriedades aceitas, entradas, saídas e dicas "
            "de uso. `name` aceita um nome ou uma LISTA de nomes (até 8) — peça as fichas "
            "de todos os nós do fluxo numa chamada só. Com `brief=false` devolve a ficha "
            "completa. Use os nomes exatamente como aparecem aqui — propriedade não "
            "declarada falha na validação."
        ),
        annotations=_READ_ONLY,
    )(describe_node)

    server.tool(
        name="get_authoring_guide",
        title="Guia de autoria",
        description=(
            "Guia de como escrever um fluxo do Atlans, por tópico: overview, edges, "
            "credentials, expressions, inputs, sources, sql, pitfalls e recipes. Leia antes "
            "de montar uma definição nova; `sources` diz como achar uma fonte externa sem "
            "adivinhar url/typeName."
        ),
        annotations=_READ_ONLY,
    )(get_authoring_guide)
