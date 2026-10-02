# app/mcp/tools/fontes.py
"""
Fontes: o catálogo de fontes pré-mapeadas — o que o assistente consulta ANTES
de prospectar qualquer dado externo.

O problema que este domínio resolve tem número: sem catálogo, o modelo chuta
`url`/`typeName` de um WFS, a validação passa (ela não toca a rede), e o erro
só aparece em `run_workflow` — cada chute custa três voltas do laço e até três
minutos de relógio. Com o catálogo, "terras indígenas" vira `search_sources` →
`describe_source` → colar o `node_snippet`, sem rede e em menos de um segundo.

Quatro decisões moldam o módulo:

- **Catálogo primeiro, rede depois.** `search_sources` e `describe_source` são
  leitura pura da tabela. Só quando o catálogo não tem a fonte é que
  `probe_source` sonda a URL — e ela fala com a internet (`open_world=True`
  na guarda, balde `probe`) e atualiza o estado de uma fonte já catalogada:
  não é read-only, como `validate_workflow` não é. A ordem está no guia
  (`sources`) e nos roteiros; a tool não a impõe, mas `probe_source` avisa
  (`catalog_hint`) quando o endpoint já está catalogado.
- **Sondagem livre, registro sem clique — por decisão do dono.**
  `register_source` grava no acervo do workspace (papel `editor`, a mesma
  régua do Drive) e nasce em `ESCRITAS_SEM_CLIQUE` na Home e em
  `ESCREVEM_MAS_PASSAM` no editor: registrar é barato e reversível, e pedir
  clique a cada fonte nova devolveria o custo que o catálogo veio tirar.
- **O que o modelo cola é o que o nó declara.** `node_snippet` traz só as
  propriedades que o `WFSNode` conhece hoje (`fontes_service.trecho_do_no`);
  `version` fica no catálogo até o nó a declarar.
- **Texto de gente desce em `untrusted_data`.** Título, descrição, dicas e
  tags são escritos por pessoas (no Vault ou em `register_source`); URL,
  typeName, colunas e CRS ficam no topo, higienizados, como as colunas do
  Drive em `list_drive_files` — o modelo precisa copiá-los.
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
from app.mcp.resolucao import resolver_workspace
from app.mcp.saida import envelope, higienizar, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.services import fontes_service
from app.services.fontes_vault import CANDIDATOS_A_SORTBY

# Tetos de orçamento de contexto — os mesmos motivos das outras listagens.
LIMITE_PADRAO = 20
LIMITE_MAXIMO = 50
MAX_COLUNAS = 50
MAX_CAMADAS = 50

_MENSAGEM_PAPEL_ESCRITA = (
    "Requer papel 'editor' ou superior neste workspace — registrar uma fonte é mexer no acervo."
)


async def _exigir_editor_para_atualizar(db, escopo, ws) -> None:
    """Exige papel de editor para a sondagem ESCREVER no catálogo.

    Fonte de workspace: editor naquele workspace. Fonte de plataforma (ws=None,
    global, sem um workspace único para checar): editor em ao menos um workspace
    do alcance da chamada — a mesma régua da escrita, sem deixar um viewer mutar
    o catálogo por sondagem.
    """
    if ws is not None:
        papel = await get_workspace_member_role(db, ws, escopo.user_id)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)
        return
    for w in sorted(escopo.workspace_ids):
        papel = await get_workspace_member_role(db, w, escopo.user_id)
        if _has_min_workspace_role(papel, ROLE_EDITOR):
            return
    exigir_papel(None, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)  # nenhum: 403


# ── Formas ────────────────────────────────────────────────────────────────────


def _escopo_de_fonte(fonte) -> str:
    return "platform" if fonte.workspace_id is None else "workspace"


def _item_leve(fonte) -> dict:
    """O que basta para escolher: id, estado, prioridade, instituição, camada."""
    return envelope(
        {
            "id": fonte.id_hash,
            "kind": fonte.tipo,
            "node": fonte.no,
            "scope": _escopo_de_fonte(fonte),
            "workspace_id": fonte.workspace_id,
            "state": fonte.estado,
            "verified_at": iso(fonte.verificada_em),
            "uses": int(fonte.usos or 0),
            "priority": int(fonte.prioridade or 2),
            "institution": higienizar(fonte.instituicao),
            "group": higienizar(fonte.grupo),
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


def _esquema_resumido(bruto: Any) -> dict | None:
    """CRS, extensão, geometria, contagem e as primeiras colunas — nunca a lista inteira."""
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
        resumo["columns"] = higienizar([
            {k: c.get(k) for k in ("name", "type") if c.get(k) is not None} if isinstance(c, dict) else c
            for c in colunas[:MAX_COLUNAS]
        ])
        resumo["columns_total"] = len(colunas)
    return {chave: valor for chave, valor in resumo.items() if valor is not None}


def _ficha(fonte, **extras: Any) -> dict:
    """A ficha completa: o trecho do nó, o esquema, o estado — e o texto de gente à parte."""
    return envelope(
        {
            "id": fonte.id_hash,
            "kind": fonte.tipo,
            "node": fonte.no,
            "scope": _escopo_de_fonte(fonte),
            "workspace_id": fonte.workspace_id,
            "state": fonte.estado,
            "origin": fonte.origem,
            "verified_at": iso(fonte.verificada_em),
            "uses": int(fonte.usos or 0),
            "priority": int(fonte.prioridade or 2),
            "institution": higienizar(fonte.instituicao),
            "group": higienizar(fonte.grupo),
            "node_snippet": higienizar(fontes_service.trecho_do_no(fonte)),
            "schema": _esquema_resumido(fonte.esquema),
            "last_error": higienizar(fonte.ultimo_erro) if fonte.estado == "falhando" else None,
            **extras,
        },
        title=fonte.titulo,
        description=fonte.descricao,
        hints=fonte.dicas,
        tags=list(fonte.temas or []),
    )


def _erro_de_sondagem(exc: fontes_service.SondagemError):
    dica = {
        "timeout": "o servidor não respondeu a tempo; tente de novo mais tarde ou confira a URL",
        "ssrf": "endereços privados, loopback e link-local são recusados; use a URL pública do serviço",
        "camada_inexistente": "escolha um dos candidates (o nome inclui o prefixo do namespace)",
        "sem_camadas": "o endpoint respondeu sem FeatureTypes; confira se é mesmo um WFS",
    }.get(exc.codigo, "confira a URL com quem pediu; a sondagem só entende WFS (GeoServer, MapServer, ArcGIS WFSServer)")
    extras: dict[str, Any] = {"reason": exc.codigo}
    if exc.status is not None:
        extras["http_status"] = exc.status
    if exc.candidatas:
        extras["candidates"] = exc.candidatas
    return erro("source_unreachable", exc.mensagem, dica, **extras)


async def _fontes_do_endpoint(db, url: str, workspace_ids) -> int:
    # Conta direto por URL: `buscar` não filtra por URL (só pagina), então não
    # vale a pena — cada uso desta função é uma consulta só, não três.
    from sqlalchemy import func, select

    from app.models.fonte_de_dados import FonteDeDados

    resultado = await db.execute(
        select(func.count()).select_from(FonteDeDados).where(
            FonteDeDados.url == url,
            FonteDeDados.deleted_at.is_(None),
            fontes_service._no_escopo(workspace_ids),
        )
    )
    return int(resultado.scalar_one())


def _sort_by(esquema: dict | None) -> str | None:
    nomes = {str(c.get("name", "")).lower(): c.get("name") for c in (esquema or {}).get("columns", []) if isinstance(c, dict)}
    for candidato in CANDIDATOS_A_SORTBY:
        if candidato in nomes:
            return nomes[candidato]
    return None


# ── Leitura (sem rede) ────────────────────────────────────────────────────────


@ferramenta
async def search_sources(
    ctx: Context,
    query: Optional[str] = None,
    workspace_id: Optional[str] = None,
    kind: Optional[str] = None,
    institution: Optional[str] = None,
    limit: int = LIMITE_PADRAO,
) -> dict:
    """Busca no catálogo de fontes pré-mapeadas — SEM tocar a rede.

    Chame ANTES de preencher `url`/`typeName` de um nó de dado externo. Procure
    pelo TEMA em 2–3 palavras ("terras indígenas", "focos de calor",
    "hidrografia"), sem lugar nem data: a busca casa cada palavra (e os
    sinônimos dela) com instituição, título, camada, descrição, temas e nomes
    de coluna. Sem resultado, tente outra grafia antes de pedir a URL a quem
    está usando ou sondar com `probe_source`.

    Os itens vêm leves; a ficha com o trecho pronto para colar vem de
    `describe_source(id)`. `state` diz se a fonte respondeu na última
    verificação (`ok`, `falhando`, `nao_verificada`); `priority` 1 é a
    preferida entre parecidas.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    teto = max(1, min(int(limit), LIMITE_MAXIMO))
    async with infra.sessao() as db:
        if workspace_id is not None:
            alcance = [await resolver_workspace(db, escopo, workspace_id)]
        else:
            alcance = sorted(escopo.workspace_ids)
        fontes, total = await fontes_service.buscar(
            db, alcance, query=query, kind=kind, institution=institution, limit=teto,
        )
        itens = [_item_leve(f) for f in fontes]

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
    """A ficha de uma fonte: o nó pronto para colar (`node_snippet`), o esquema
    (CRS, extensão, geometria, colunas) e o estado da última verificação.

    Cole `node_snippet.properties` no nó `WFS` da definição como estão — a URL
    já vem normalizada como o nó a usa, e `sortBy` (quando existe) é o que
    permite paginar a camada. `schema.columns` são os nomes que um
    `AttributeFilter` ou uma expressão podem referenciar.
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
        return _ficha(fonte)


# ── Sondagem (a única leitura que fala com a internet) ────────────────────────


@ferramenta
async def probe_source(
    ctx: Context, url: str, type_name: Optional[str] = None, version: str = "2.0.0"
) -> dict:
    """Sonda um WFS que NÃO está no catálogo: lista as camadas (GetCapabilities)
    e, com `type_name`, o esquema da camada (DescribeFeatureType). Nenhuma
    feição é baixada e nenhuma fonte é criada; se a camada já estiver no
    catálogo, a sondagem atualiza o estado e o esquema dela.

    Use DEPOIS de `search_sources` voltar vazio. Se o endpoint já estiver
    catalogado, a resposta traz `catalog_hint` — prefira o catálogo. Para não
    sondar a mesma fonte duas vezes, guarde-a com `register_source`.

    `version` é a do WFS (2.0.0 por padrão; 1.0.0/1.1.0 para servidores
    antigos). O servidor sondado precisa ser público: endereços privados são
    recusados.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    endereco = fontes_service.normalizar_url(url)
    versao = fontes_service.normalizar_versao(version)
    camada = (type_name or "").strip() or None
    try:
        sondagem = await fontes_service.sondar_wfs(endereco, camada, versao)
    except fontes_service.SondagemError as exc:
        raise _erro_de_sondagem(exc)

    async with infra.sessao() as db:
        ja_catalogadas = await _fontes_do_endpoint(db, endereco, escopo.workspace_ids)
        no_catalogo = None
        if sondagem.camada is not None:
            # Se esta camada já está no catálogo ao alcance, a sondagem a atualiza:
            # é o mesmo trabalho que o laço de verificação faria, de graça.
            for ws in (*sorted(escopo.workspace_ids), None):
                chave = fontes_service.chave_da_fonte(ws, fontes_service.TIPO_WFS, endereco, sondagem.camada.name)
                fonte = await fontes_service.obter_por_chave(db, chave)
                if fonte is not None and fonte.deleted_at is None:
                    # Atualizar estado/esquema/verificada_em e ESCRITA no catalogo:
                    # exige papel de editor, como register_source. A guarda de
                    # probe_source declara 'editor', mas a guarda nao aplica papel
                    # — quem conhece o workspace da chamada e a tool (ver
                    # app/mcp/guardas.py). O escopo workflows:write sozinho nao
                    # basta. Fonte de workspace: editor naquele workspace. Fonte
                    # de plataforma (ws=None, global, sem um workspace unico para
                    # checar): editor em ao menos um workspace do alcance.
                    await _exigir_editor_para_atualizar(db, escopo, ws)
                    fonte.estado, fonte.ultimo_erro = "ok", None
                    fonte.esquema = fontes_service.fundir_esquema(fonte.esquema, sondagem.esquema)
                    fonte.verificada_em = utc_now_naive()
                    fontes_service._recalcular_busca(fonte)
                    await db.commit()
                    no_catalogo = {"source_id": fonte.id_hash, "scope": _escopo_de_fonte(fonte), "state": fonte.estado}
                    break

    dados: dict[str, Any] = {
        "url": endereco,
        "version": sondagem.version,
        "server_version": sondagem.capabilities.version,
        "layer_count": len(sondagem.capabilities.layers),
    }
    if ja_catalogadas:
        dados["catalog_hint"] = (
            f"este endpoint já está catalogado com {ja_catalogadas} camada(s) ao seu alcance: "
            "search_sources com o tema (ou institution=...) evita a sondagem"
        )
    if sondagem.camada is None:
        camadas = [{"name": c.name, "title": c.title or c.name} for c in sondagem.capabilities.layers[:MAX_CAMADAS]]
        dados["outcome"] = "layers_listed"
        if len(sondagem.capabilities.layers) > MAX_CAMADAS:
            dados["hint"] = (
                f"só as {MAX_CAMADAS} primeiras de {len(sondagem.capabilities.layers)} camadas; "
                "chame de novo com type_name quando souber a camada"
            )
        return envelope(dados, layers=camadas)

    dados["outcome"] = "layer_described"
    dados["layer"] = sondagem.camada.name
    dados["schema"] = _esquema_resumido(sondagem.esquema)
    dados["catalog"] = no_catalogo
    dados["node_snippet"] = higienizar({
        "name": fontes_service.NO_WFS,
        "type": "datasource",
        "properties": {
            k: v for k, v in {
                "url": endereco, "typeName": sondagem.camada.name, "sortBy": _sort_by(sondagem.esquema),
            }.items() if v
        },
    })
    if no_catalogo is None:
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
    """Sonda uma camada WFS e a guarda no catálogo do workspace, para o próximo
    pedido (seu ou de qualquer membro) encontrá-la por `search_sources`.

    Registra o que a sondagem confirmou: a camada precisa existir no
    GetCapabilities, e o esquema vem do DescribeFeatureType. `title`,
    `description`, `tags` e `hints` são o que ajuda a busca e o uso — `hints`
    é a dica que `describe_source` devolve a quem for usar a fonte ("filtre
    por `estado` em maiúsculas"). Idempotente: a mesma URL+camada atualiza a
    linha em vez de duplicar.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    endereco = fontes_service.normalizar_url(url)
    versao = fontes_service.normalizar_versao(version)
    camada = (type_name or "").strip()
    if not camada:
        raise erro("validation", "Informe type_name: a camada que o nó WFS vai ler.",
                   "use probe_source(url) para listar as camadas do serviço")

    async with infra.sessao() as db:
        ws = await resolver_workspace(db, escopo, workspace_id)
        papel = await get_workspace_member_role(db, ws, escopo.user_id)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)

        try:
            sondagem = await fontes_service.sondar_wfs(endereco, camada, versao)
        except fontes_service.SondagemError as exc:
            raise _erro_de_sondagem(exc)

        assert sondagem.camada is not None
        propriedades = {"version": versao}
        ordenacao = _sort_by(sondagem.esquema)
        if ordenacao:
            propriedades["sortBy"] = ordenacao
        fonte, desfecho = await fontes_service.upsert_fonte(
            db,
            workspace_id=ws,
            tipo=fontes_service.TIPO_WFS,
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
        return _ficha(fonte, outcome=desfecho)


def registrar(server) -> None:
    """Registra as tools deste domínio."""
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
