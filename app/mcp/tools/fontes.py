# app/mcp/tools/fontes.py
"""
Sources: the catalog of pre-mapped sources — what the assistant consults BEFORE
prospecting any external data.

The problem this domain solves has a number: without a catalog, the model
guesses a WFS's `url`/`typeName`, validation passes (it does not touch the
network), and the error only shows up in `run_workflow` — each guess costs three
turns of the loop and up to three minutes of wall clock. With the catalog,
"terras indígenas" (Indigenous lands) becomes `search_sources` →
`describe_source` → pasting the `node_snippet`, with no network and in under a
second.

Four decisions shape the module:

- **Catalog first, network later.** `search_sources` and `describe_source` are
  pure reads of the table. Only when the catalog does not have the source does
  `probe_source` probe the URL — and it talks to the internet
  (`open_world=True` in the guard, `probe` bucket) and updates the state of an
  already cataloged source: it is not read-only, just as `validate_workflow`
  is not. The order is in the guide (`sources`) and in the playbooks; the tool
  does not enforce it, but `probe_source` warns (`catalog_hint`) when the
  endpoint is already cataloged.
- **Free probing, registration without a click — by the owner's decision.**
  `register_source` writes to the workspace's collection (`editor` role, the
  same yardstick as Drive) and is born in `ESCRITAS_SEM_CLIQUE` on Home and in
  `ESCREVEM_MAS_PASSAM` in the editor: registering is cheap and reversible,
  and asking for a click for every new source would bring back the cost the
  catalog came to remove.
- **What the model pastes is what the node declares.** `node_snippet` carries
  only the properties `WFSNode` knows today (`fontes_service.node_snippet`);
  `version` stays in the catalog until the node declares it.
- **Human-written text goes down in `untrusted_data`.** Title, description,
  hints and tags are written by people (in the Vault or in `register_source`);
  URL, typeName, columns and CRS stay at the top, sanitized, like the Drive
  columns in `list_drive_files` — the model needs to copy them.
"""
from __future__ import annotations

from typing import Any, Optional

from mcp.server.mcpserver import Context

from app.core.authorization.workflow_access import (
    _has_min_workspace_role,
    exigir_papel,
    get_workspace_member_role,
)
from app.core.rbac import ROLE_EDITOR
from app.core.utils.datetime_utils import utc_now_naive
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import resolve_workspace
from app.mcp.saida import envelope, sanitize, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.services import fontes_service
from app.services.fontes_vault import SORTBY_CANDIDATES

# Context-budget ceilings — the same reasons as the other listings.
DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_COLUMNS = 50
MAX_LAYERS = 50

_WRITE_ROLE_MESSAGE = (
    "Requer papel 'editor' ou superior neste workspace — registrar uma fonte é mexer no acervo."
)


async def _require_editor_to_update(db, escopo, ws) -> None:
    """Requires the editor role for the probe to WRITE to the catalog.

    Workspace source: editor in that workspace. Platform source (ws=None,
    global, with no single workspace to check): editor in at least one
    workspace within the call's reach — the same yardstick as writing, without
    letting a viewer mutate the catalog by probing.
    """
    if ws is not None:
        papel = await get_workspace_member_role(db, ws, escopo.user_id)
        exigir_papel(papel, ROLE_EDITOR, _WRITE_ROLE_MESSAGE)
        return
    for w in sorted(escopo.workspace_ids):
        papel = await get_workspace_member_role(db, w, escopo.user_id)
        if _has_min_workspace_role(papel, ROLE_EDITOR):
            return
    exigir_papel(None, ROLE_EDITOR, _WRITE_ROLE_MESSAGE)  # none: 403


# ── Formas ────────────────────────────────────────────────────────────────────


def _source_scope(fonte) -> str:
    return "platform" if fonte.workspace_id is None else "workspace"


def _light_item(fonte) -> dict:
    """What is enough to choose: id, state, priority, institution, layer."""
    return envelope(
        {
            "id": fonte.id_hash,
            "kind": fonte.tipo,
            "node": fonte.no,
            "scope": _source_scope(fonte),
            "workspace_id": fonte.workspace_id,
            "state": fonte.estado,
            "verified_at": iso(fonte.verificada_em),
            "uses": int(fonte.usos or 0),
            "priority": int(fonte.prioridade or 2),
            "institution": sanitize(fonte.instituicao),
            "group": sanitize(fonte.grupo),
            "type_name": fonte.type_name,
            "host": _host(fonte.url),
        },
        title=fonte.titulo,
        tags=list(fonte.temas or []),
    )


def _host(url: str | None) -> str | None:
    from urllib.parse import urlparse

    try:
        return urlparse(url or "").hostname
    except ValueError:
        return None


def _summarized_schema(bruto: Any) -> dict | None:
    """CRS, extent, geometry, count and the first columns — never the whole list."""
    if not isinstance(bruto, dict):
        return None
    colunas = bruto.get("columns")
    resumo: dict[str, Any] = {
        "crs": bruto.get("crs"),
        "bbox": bruto.get("bbox"),
        "geometry_type": bruto.get("geometry_type"),
        "geometry_column": bruto.get("geometry_column"),
        "feature_count": bruto.get("feature_count"),
        "columns_source": bruto.get("columns_source"),
    }
    if isinstance(colunas, list):
        resumo["columns"] = sanitize([
            {k: c.get(k) for k in ("name", "type") if c.get(k) is not None} if isinstance(c, dict) else c
            for c in colunas[:MAX_COLUMNS]
        ])
        resumo["columns_total"] = len(colunas)
    return {chave: valor for chave, valor in resumo.items() if valor is not None}


def _source_sheet(fonte, **extras: Any) -> dict:
    """The full record: the node snippet, the schema, the state — and the human-written text set apart."""
    return envelope(
        {
            "id": fonte.id_hash,
            "kind": fonte.tipo,
            "node": fonte.no,
            "scope": _source_scope(fonte),
            "workspace_id": fonte.workspace_id,
            "state": fonte.estado,
            "origin": fonte.origem,
            "verified_at": iso(fonte.verificada_em),
            "uses": int(fonte.usos or 0),
            "priority": int(fonte.prioridade or 2),
            "institution": sanitize(fonte.instituicao),
            "group": sanitize(fonte.grupo),
            "node_snippet": sanitize(fontes_service.node_snippet(fonte)),
            "schema": _summarized_schema(fonte.esquema),
            "last_error": sanitize(fonte.ultimo_erro) if fonte.estado == "falhando" else None,
            **extras,
        },
        title=fonte.titulo,
        description=fonte.descricao,
        hints=fonte.dicas,
        tags=list(fonte.temas or []),
    )


def _probe_error(exc: fontes_service.ProbeError):
    dica = {
        "timeout": "o servidor não respondeu a tempo; tente de novo mais tarde ou confira a URL",
        "ssrf": "endereços privados, loopback e link-local são recusados; use a URL pública do serviço",
        "camada_inexistente": "escolha um dos candidates (o nome inclui o prefixo do namespace)",
        "sem_camadas": "o endpoint respondeu sem FeatureTypes; confira se é mesmo um WFS",
    }.get(exc.codigo, "confira a URL com quem pediu; a sondagem só entende WFS (GeoServer, MapServer, ArcGIS WFSServer)")
    extras: dict[str, Any] = {"reason": exc.codigo}
    if exc.status is not None:
        extras["http_status"] = exc.status
    if exc.candidates:
        extras["candidates"] = exc.candidates
    return erro("source_unreachable", exc.mensagem, dica, **extras)


async def _endpoint_sources(db, url: str, workspace_ids) -> int:
    # Count directly by URL: `buscar` does not filter by URL (it only pages), so
    # it is not worth it — each use of this function is a single query, not three.
    from sqlalchemy import func, select

    from app.models.fonte_de_dados import DataSource

    resultado = await db.execute(
        select(func.count()).select_from(DataSource).where(
            DataSource.url == url,
            DataSource.deleted_at.is_(None),
            fontes_service._in_scope(workspace_ids),
        )
    )
    return int(resultado.scalar_one())


def _sort_by(esquema: dict | None) -> str | None:
    nomes = {str(c.get("name", "")).lower(): c.get("name") for c in (esquema or {}).get("columns", []) if isinstance(c, dict)}
    for candidato in SORTBY_CANDIDATES:
        if candidato in nomes:
            return nomes[candidato]
    return None


# ── Reading (no network) ──────────────────────────────────────────────────────


@ferramenta
async def search_sources(
    ctx: Context,
    query: Optional[str] = None,
    workspace_id: Optional[str] = None,
    kind: Optional[str] = None,
    institution: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Searches the catalog of pre-mapped sources — WITHOUT touching the network.

    Call it BEFORE filling in the `url`/`typeName` of an external-data node.
    Search by TOPIC in 2–3 words ("terras indígenas", "focos de calor",
    "hidrografia"), with no place or date: the search matches each word (and
    its synonyms) against institution, title, layer, description, themes and
    column names. With no result, try another spelling before asking the user
    for the URL or probing with `probe_source`.

    Items come back light; the record with the snippet ready to paste comes
    from `describe_source(id)`. `state` says whether the source responded at
    the last check (`ok`, `falhando`, `nao_verificada`); `priority` 1 is the
    preferred one among similar ones.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    teto = max(1, min(int(limit), MAX_LIMIT))
    async with infra.sessao() as db:
        if workspace_id is not None:
            alcance = [await resolve_workspace(db, escopo, workspace_id)]
        else:
            alcance = sorted(escopo.workspace_ids)
        fontes, total = await fontes_service.buscar(
            db, alcance, query=query, kind=kind, institution=institution, limit=teto,
        )
        itens = [_light_item(f) for f in fontes]

    saida: dict[str, Any] = {
        "items": itens,
        "total": total,
        "limit": teto,
        "workspace_ids": alcance,
    }
    if not itens:
        saida["hint"] = (
            "nenhuma fonte catalogada casa com a busca. Tente menos palavras ou um sinônimo "
            "(\"queimadas\" para \"focos de calor\"); se ainda assim nada, peça a URL do serviço a "
            "quem está usando ou sonde com probe_source"
        )
    elif total > teto:
        saida["hint"] = f"há {total} fontes; refine a busca (tema mais específico ou institution=...)"
    return saida


@ferramenta
async def describe_source(ctx: Context, source_id: str) -> dict:
    """A source's record: the node ready to paste (`node_snippet`), the schema
    (CRS, extent, geometry, columns) and the state at the last check.

    Paste `node_snippet.properties` into the definition's `WFS` node as they
    are — the URL already comes normalized the way the node uses it, and
    `sortBy` (when present) is what allows paging the layer. `schema.columns`
    are the names an `AttributeFilter` or an expression can reference.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        fonte = await fontes_service.obter(db, source_id, escopo.workspace_ids)
        if fonte is None:
            raise erro(
                "not_found",
                "Nenhuma fonte com este identificador está ao alcance do token.",
                "use search_sources para achar o id",
            )
        return _source_sheet(fonte)


# ── Probing (the only read that talks to the internet) ────────────────────────


@ferramenta
async def probe_source(
    ctx: Context, url: str, type_name: Optional[str] = None, version: str = "2.0.0"
) -> dict:
    """Probes a WFS that is NOT in the catalog: lists the layers (GetCapabilities)
    and, with `type_name`, the layer's schema (DescribeFeatureType). No feature
    is downloaded and no source is created; if the layer is already in the
    catalog, the probe updates its state and schema.

    Use it AFTER `search_sources` comes back empty. If the endpoint is already
    cataloged, the response carries `catalog_hint` — prefer the catalog. To
    avoid probing the same source twice, save it with `register_source`.

    `version` is the WFS one (2.0.0 by default; 1.0.0/1.1.0 for old servers).
    The probed server must be public: private addresses are refused.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    endereco = fontes_service.normalize_url(url)
    versao = fontes_service.normalize_version(version)
    camada = (type_name or "").strip() or None
    try:
        sondagem = await fontes_service.sondar_wfs(endereco, camada, versao)
    except fontes_service.ProbeError as exc:
        raise _probe_error(exc)

    async with infra.sessao() as db:
        already_cataloged = await _endpoint_sources(db, endereco, escopo.workspace_ids)
        in_catalog = None
        if sondagem.camada is not None:
            # If this layer is already in the catalog within reach, the probe updates
            # it: it is the same work the check loop would do, for free.
            for ws in (*sorted(escopo.workspace_ids), None):
                chave = fontes_service.source_key(ws, fontes_service.KIND_WFS, endereco, sondagem.camada.name)
                fonte = await fontes_service.get_by_key(db, chave)
                if fonte is not None and fonte.deleted_at is None:
                    # Updating state/schema/verificada_em IS a WRITE to the catalog:
                    # it requires the editor role, like register_source. The
                    # probe_source guard declares 'editor', but the guard does not
                    # enforce roles — whoever knows the call's workspace and the
                    # tool does (see app/mcp/guardas.py). The workflows:write scope
                    # alone is not enough. Workspace source: editor in that
                    # workspace. Platform source (ws=None, global, with no single
                    # workspace to check): editor in at least one workspace within
                    # reach.
                    await _require_editor_to_update(db, escopo, ws)
                    fonte.estado, fonte.ultimo_erro = "ok", None
                    fonte.esquema = fontes_service.merge_schema(fonte.esquema, sondagem.esquema)
                    fonte.verificada_em = utc_now_naive()
                    fontes_service._recompute_search(fonte)
                    await db.commit()
                    in_catalog = {"source_id": fonte.id_hash, "scope": _source_scope(fonte), "state": fonte.estado}
                    break

    dados: dict[str, Any] = {
        "url": endereco,
        "version": sondagem.version,
        "server_version": sondagem.capabilities.version,
        "layer_count": len(sondagem.capabilities.layers),
    }
    if already_cataloged:
        dados["catalog_hint"] = (
            f"este endpoint já está catalogado com {already_cataloged} camada(s) ao seu alcance: "
            "search_sources com o tema (ou institution=...) evita a sondagem"
        )
    if sondagem.camada is None:
        camadas = [{"name": c.name, "title": c.title or c.name} for c in sondagem.capabilities.layers[:MAX_LAYERS]]
        dados["outcome"] = "layers_listed"
        if len(sondagem.capabilities.layers) > MAX_LAYERS:
            dados["hint"] = (
                f"só as {MAX_LAYERS} primeiras de {len(sondagem.capabilities.layers)} camadas; "
                "chame de novo com type_name quando souber a camada"
            )
        return envelope(dados, layers=camadas)

    dados["outcome"] = "layer_described"
    dados["layer"] = sondagem.camada.name
    dados["schema"] = _summarized_schema(sondagem.esquema)
    dados["catalog"] = in_catalog
    dados["node_snippet"] = sanitize({
        "name": fontes_service.NO_WFS,
        "type": "datasource",
        "properties": {
            k: v for k, v in {
                "url": endereco, "typeName": sondagem.camada.name, "sortBy": _sort_by(sondagem.esquema),
            }.items() if v
        },
    })
    if in_catalog is None:
        dados["hint"] = "fonte fora do catálogo: register_source(url, type_name) a guarda para a próxima vez"
    return envelope(dados, title=sondagem.camada.title, description=sondagem.camada.abstract,
                    keywords=list(sondagem.camada.keywords) or None)


# ── Escrita ───────────────────────────────────────────────────────────────────


@ferramenta
async def register_source(
    ctx: Context,
    url: str,
    type_name: str,
    workspace_id: Optional[str] = None,
    version: str = "2.0.0",
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    hints: Optional[str] = None,
) -> dict:
    """Probes a WFS layer and saves it in the workspace's catalog, so the next
    request (yours or any member's) finds it through `search_sources`.

    It registers what the probe confirmed: the layer must exist in
    GetCapabilities, and the schema comes from DescribeFeatureType. `title`,
    `description`, `tags` and `hints` are what helps search and use — `hints`
    is the tip that `describe_source` returns to whoever uses the source
    ("filtre por `estado` em maiúsculas"). Idempotent: the same URL+layer
    updates the row instead of duplicating it.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    endereco = fontes_service.normalize_url(url)
    versao = fontes_service.normalize_version(version)
    camada = (type_name or "").strip()
    if not camada:
        raise erro("validation", "Informe type_name: a camada que o nó WFS vai ler.",
                   "use probe_source(url) para listar as camadas do serviço")

    async with infra.sessao() as db:
        ws = await resolve_workspace(db, escopo, workspace_id)
        papel = await get_workspace_member_role(db, ws, escopo.user_id)
        exigir_papel(papel, ROLE_EDITOR, _WRITE_ROLE_MESSAGE)

        try:
            sondagem = await fontes_service.sondar_wfs(endereco, camada, versao)
        except fontes_service.ProbeError as exc:
            raise _probe_error(exc)

        assert sondagem.camada is not None
        propriedades = {"version": versao}
        sort_order = _sort_by(sondagem.esquema)
        if sort_order:
            propriedades["sortBy"] = sort_order
        fonte, desfecho = await fontes_service.upsert_source(
            db,
            workspace_id=ws,
            tipo=fontes_service.KIND_WFS,
            url=endereco,
            type_name=sondagem.camada.name,
            propriedades=propriedades,
            origem="manual",
            estado="ok",
            esquema=sondagem.esquema,
            titulo=(title or "").strip() or sondagem.camada.title,
            descricao=(description or "").strip() or sondagem.camada.abstract,
            temas=[*(tags or []), *sondagem.camada.keywords],
            dicas=(hints or "").strip() or None,
            instituicao=_host(endereco),
            created_by=escopo.user_id,
            verificada_em=utc_now_naive(),
        )
        await db.commit()
        return _source_sheet(fonte, outcome=desfecho)


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="search_sources",
        title="Buscar fontes catalogadas",
        description=(
            "Busca no catálogo de fontes pré-mapeadas (camadas WFS já conhecidas: URL, camada, "
            "esquema e estado) SEM tocar a rede. Chame ANTES de preencher url/typeName de um nó "
            "de dado externo; busque pelo tema em 2–3 palavras, com sinônimos. O `id` devolvido "
            "vai em describe_source."
        ),
        annotations=anotacoes("search_sources"),
    )(search_sources)

    server.tool(
        name="describe_source",
        title="Ficha de uma fonte",
        description=(
            "A ficha de uma fonte do catálogo: o nó pronto para colar na definição "
            "(node_snippet, com url, typeName e sortBy), o esquema (CRS, extensão, geometria, "
            "colunas) e o estado da última verificação."
        ),
        annotations=anotacoes("describe_source"),
    )(describe_source)

    server.tool(
        name="probe_source",
        title="Sondar um WFS",
        description=(
            "Lista as camadas de um WFS fora do catálogo (GetCapabilities) e, com type_name, o "
            "esquema da camada (DescribeFeatureType). Só metadados; não cria fonte (atualiza a "
            "já catalogada). Use depois de search_sources voltar vazio — e register_source para "
            "guardar o que encontrou."
        ),
        annotations=anotacoes("probe_source"),
    )(probe_source)

    server.tool(
        name="register_source",
        title="Registrar fonte no catálogo",
        description=(
            "Sonda uma camada WFS e a guarda no catálogo do workspace, com título, descrição, "
            "temas e dicas de uso, para search_sources encontrá-la da próxima vez. Idempotente: a "
            "mesma URL+camada atualiza a linha."
        ),
        annotations=anotacoes("register_source"),
    )(register_source)
