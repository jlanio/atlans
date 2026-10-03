# tests/unit/test_mcp_fontes.py
"""The four source catalog tools, and the decisions around them.

- **Search and describe** read the table: workspace scope, lightweight items with
  human-written text in `untrusted_data`, the record with the snippet ready to paste.
- **Probe and register** talk to the internet — stubbed here in
  `fontes_service.sondar_wfs`, the only point through which the tool goes out —
  and are the server's only two open-world tools; they are born WITHOUT a click
  on the Home screen and enabled in the editor by the owner's decision.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.mcp import infra
from app.mcp.guardas import GUARDAS
from app.mcp.tools.fontes import describe_source, probe_source, register_source, search_sources
from app.models.base import Base
from app.models.fonte_de_dados import DataSource
from app.models.workspace_member import WorkspaceMember
from app.services import assistente_superficie as ag
from app.services import assistente_service as cs
from app.services import fontes_service as fs
from tests.unit._mcp_harness import TABLES, create_user, create_workspace, fake_ctx, fake_scope, session_from

WS_1 = "11111111-1111-4111-8111-111111111111"
WS_2 = "22222222-2222-4222-8222-222222222222"
FUNAI = "https://geoserver.funai.gov.br/geoserver/ows"


def corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


def ctx(**kw):
    campos = {"scopes": {"workflows:read", "workflows:write"}, "workspace_ids": {WS_1}}
    campos.update(kw)
    return fake_ctx(fake_scope(**campos))


@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[*TABLES, DataSource.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(infra, "sessao", session_from(fabrica))
    async with fabrica() as db:
        await create_user(db, "usr-1", "ana")
        await create_user(db, "usr-2", "bruno")
        await create_workspace(db, WS_1, "usr-1", "Principal")
        await create_workspace(db, WS_2, "usr-2", "De outra conta")
        # ana is only a viewer in bruno's workspace.
        db.add(WorkspaceMember(workspace_id=WS_2, user_id="usr-1", role="viewer"))
        await db.commit()
        # Platform: one Vault source; workspace 1: one registered; workspace 2: someone else's.
        await fs.upsert_source(
            db, workspace_id=None, tipo="wfs", url=FUNAI, type_name="Funai:tis_poligonais",
            propriedades={"sortBy": "gid", "version": "2.0.0"}, origem="vault", estado="ok",
            titulo="Terras indígenas (poligonais)", descricao="FUNAI. Terras indígenas.",
            temas=["FUNAI", "terras indígenas"], dicas="Filtre por uf_sigla em maiúsculas.",
            instituicao="FUNAI", grupo="Funai", prioridade=1,
            esquema={"columns": [{"name": f"c{i}", "type": "string"} for i in range(60)],
                     "columns_source": "vault", "geometry_type": "MultiPolygon", "crs": "EPSG:4674"},
        )
        await fs.upsert_source(
            db, workspace_id=WS_1, tipo="wfs", url="https://geoserver.exemplo.gov.br/ows", type_name="queimadas:focos_24h",
            propriedades={}, origem="manual", estado="nao_verificada", titulo="Focos de calor (24 h)",
            temas=["queimadas"], instituicao="geoserver.exemplo.gov.br",
        )
        await fs.upsert_source(
            db, workspace_id=WS_2, tipo="wfs", url="https://geoserver.exemplo.gov.br/ows", type_name="privada:x",
            propriedades={}, origem="manual", estado="ok", titulo="Só do outro", temas=[],
        )
        await db.commit()
    try:
        yield fabrica
    finally:
        await engine.dispose()


def _probe(url, type_name=None, version="2.0.0", *, camadas=("Funai:tis_poligonais", "Funai:aldeias_pontos")):
    caps = fs.Capabilities(version="2.0.0", layers=tuple(
        fs.ServiceLayer(name=n, title=n.split(":")[1].replace("_", " "), abstract="Resumo.", keywords=("kw",), crs="EPSG:4674")
        for n in camadas
    ))
    sondagem = fs.Probe(url=url, version=version, capabilities=caps)
    if type_name:
        camada = caps.by_name()[type_name]
        sondagem.camada = camada
        sondagem.esquema = {"columns": [{"name": "gid", "type": "int"}, {"name": "uf_sigla", "type": "string"}],
                            "columns_source": "describe_feature_type", "geometry_type": "MultiPolygon",
                            "crs": "EPSG:4674", "bbox": [-73.99, -33.75, -28.84, 5.27]}
    return sondagem


# ── Guards and surfaces ───────────────────────────────────────────────────────


def test_the_two_probing_tools_are_the_only_open_world_and_pay_the_probe_bucket():
    abertas = {n for n, g in GUARDAS.items() if g.open_world}
    assert abertas == {"probe_source", "register_source"}
    for nome in abertas:
        assert GUARDAS[nome].cota == "probe" and GUARDAS[nome].read_only is False
    for nome in ("search_sources", "describe_source"):
        assert GUARDAS[nome].read_only is True and GUARDAS[nome].cota is None and GUARDAS[nome].open_world is False


async def test_published_annotations_match_the_table():
    from app.mcp.servidor import create_mcp_server

    tools = {t.name: t for t in await create_mcp_server().list_tools()}
    for nome in ("search_sources", "describe_source", "probe_source", "register_source"):
        guarda = GUARDAS[nome]
        assert tools[nome].annotations.read_only_hint is guarda.read_only, nome
        assert tools[nome].annotations.open_world_hint is guarda.open_world, nome
        assert tools[nome].annotations.idempotent_hint is True, nome
        assert "ctx" not in tools[nome].input_schema["properties"], nome
    assert tools["register_source"].input_schema["required"] == ["url", "type_name"]
    assert tools["probe_source"].input_schema["required"] == ["url"]


def test_probe_and_register_are_free_on_home_and_editor():
    """Owner's decision: catalog first, but probing and saving don't require a click."""
    assert {"probe_source", "register_source"} <= ag.ESCRITAS_SEM_CLIQUE
    assert not ({"probe_source", "register_source"} & ag.CONFIRMAVEIS_SEMPRE)
    assert not cs.bloqueada_no_editor("probe_source")
    assert not cs.bloqueada_no_editor("register_source")


# ── search_sources ────────────────────────────────────────────────────────────


async def test_search_returns_light_items_with_human_text_set_apart(banco):
    saida = await search_sources(ctx(), query="terras indígenas")
    assert saida["total"] == 1 and saida["workspace_ids"] == [WS_1]
    item = saida["items"][0]
    assert item["type_name"] == "Funai:tis_poligonais" and item["scope"] == "platform"
    assert item["state"] == "ok" and item["priority"] == 1 and item["host"] == "geoserver.funai.gov.br"
    assert item["untrusted_data"] == {"title": "Terras indígenas (poligonais)", "tags": ["FUNAI", "terras indígenas"]}
    assert "title" not in item and "hint" not in saida


async def test_search_respects_the_scope_and_warns_when_nothing_matches(banco):
    tudo = await search_sources(ctx())
    assert {i["type_name"] for i in tudo["items"]} == {"Funai:tis_poligonais", "queimadas:focos_24h"}
    # Workspace 2 is outside the token: the private source doesn't show, even when requested.
    with pytest.raises(ToolError) as exc:
        await search_sources(ctx(), workspace_id=WS_2)
    assert corpo(exc.value)["code"] == "forbidden"
    vazio = await search_sources(ctx(), query="xyzzy")
    assert vazio["items"] == [] and "probe_source" in vazio["hint"]
    # Synonym: "focos de calor" finds the "queimadas" one; the ceiling is trimmed.
    focos = await search_sources(ctx(), query="focos de calor", limit=999)
    assert [i["type_name"] for i in focos["items"]] == ["queimadas:focos_24h"] and focos["limit"] == 50


async def test_search_requires_read_scope(banco):
    with pytest.raises(ToolError) as exc:
        await search_sources(ctx(scopes={"drive:read"}))
    assert corpo(exc.value)["code"] == "forbidden_scope"


# ── describe_source ───────────────────────────────────────────────────────────


async def test_describe_carries_the_ready_snippet_the_trimmed_schema_and_the_hints(banco):
    item = (await search_sources(ctx(), query="terras"))["items"][0]
    ficha = await describe_source(ctx(), item["id"])
    # `version` stays in the catalog, not in the snippet: the node doesn't declare it yet.
    assert ficha["node_snippet"] == {
        "name": "WFS", "type": "datasource",
        "properties": {"url": FUNAI, "typeName": "Funai:tis_poligonais", "sortBy": "gid"},
    }
    assert ficha["schema"]["columns_total"] == 60 and len(ficha["schema"]["columns"]) == 50
    assert ficha["schema"]["crs"] == "EPSG:4674" and ficha["schema"]["geometry_type"] == "MultiPolygon"
    assert ficha["origin"] == "vault" and ficha["state"] == "ok" and ficha["last_error"] is None
    assert ficha["untrusted_data"]["hints"] == "Filtre por uf_sigla em maiúsculas."
    assert ficha["untrusted_data"]["description"].startswith("FUNAI.")


async def test_describe_of_source_out_of_reach_is_not_found(banco):
    async with infra.sessao() as db:
        # The id is read inside the session: the `finally` rollback expires the object.
        private_source_id = (await fs.buscar(db, [WS_2], query="privada"))[0][0].id_hash
    with pytest.raises(ToolError) as exc:
        await describe_source(ctx(), private_source_id)
    assert corpo(exc.value)["code"] == "not_found"
    with pytest.raises(ToolError):
        await describe_source(ctx(), "nao-existe")


# ── probe_source ──────────────────────────────────────────────────────────────


async def test_probe_lists_the_layers_and_warns_the_endpoint_is_already_cataloged(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v)))
    saida = await probe_source(ctx(), FUNAI + "?service=WFS&request=GetCapabilities")
    assert saida["outcome"] == "layers_listed" and saida["url"] == FUNAI and saida["layer_count"] == 2
    assert saida["untrusted_data"]["layers"] == [
        {"name": "Funai:tis_poligonais", "title": "tis poligonais"},
        {"name": "Funai:aldeias_pontos", "title": "aldeias pontos"},
    ]
    assert "já está catalogado com 1 camada" in saida["catalog_hint"]


async def test_probe_does_not_trigger_the_discarded_search(banco, monkeypatch):
    """Mutation: bring back the discarded `fontes_service.buscar` call in
    `_endpoint_sources`. It doesn't filter by URL and the result was unused —
    it only cost two extra queries per probe. The endpoint's count stays right."""
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v)))
    espiao = AsyncMock(wraps=fs.buscar)
    monkeypatch.setattr(fs, "buscar", espiao)

    saida = await probe_source(ctx(), FUNAI + "?service=WFS&request=GetCapabilities")

    espiao.assert_not_called()
    assert "já está catalogado com 1 camada" in saida["catalog_hint"]


async def test_probe_with_layer_describes_and_updates_the_cataloged_source(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v)))
    saida = await probe_source(ctx(), FUNAI, type_name="Funai:tis_poligonais")
    assert saida["outcome"] == "layer_described" and saida["layer"] == "Funai:tis_poligonais"
    assert saida["schema"]["columns_source"] == "describe_feature_type" and saida["schema"]["bbox"] == [-73.99, -33.75, -28.84, 5.27]
    assert saida["node_snippet"]["properties"] == {"url": FUNAI, "typeName": "Funai:tis_poligonais", "sortBy": "gid"}
    assert saida["catalog"]["scope"] == "platform" and saida["catalog"]["state"] == "ok"
    assert saida["untrusted_data"]["title"] == "tis poligonais" and "hint" not in saida
    async with infra.sessao() as db:
        fonte = await fs.get_by_key(db, fs.source_key(None, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert fonte.esquema["columns_source"] == "describe_feature_type" and fonte.verificada_em is not None

    nova = await probe_source(ctx(), FUNAI, type_name="Funai:aldeias_pontos")
    assert nova["catalog"] is None and "register_source" in nova["hint"]


async def test_probe_refuses_to_update_workspace_source_without_editor_role(banco, monkeypatch):
    """Mutation: remove exigir_papel from the probe (go back to only checking scope).

    Probing UPDATES the catalog: a viewer in the source's workspace cannot mutate.
    The source 'privada:x' belongs to WS_2, where ana is only a viewer.
    """
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(
        side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v, camadas=("privada:x",))))
    exemplo = "https://geoserver.exemplo.gov.br/ows"
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(workspace_ids={WS_2}), exemplo, type_name="privada:x")
    assert corpo(exc.value)["code"] == "forbidden"
    async with infra.sessao() as db:
        fonte = await fs.get_by_key(db, fs.source_key(WS_2, "wfs", exemplo, "privada:x"))
        assert fonte.verificada_em is None


async def test_probe_updates_workspace_source_with_editor_role(banco, monkeypatch):
    """An editor in the source's workspace can update it through probing (WS_1)."""
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(
        side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v, camadas=("queimadas:focos_24h",))))
    exemplo = "https://geoserver.exemplo.gov.br/ows"
    saida = await probe_source(ctx(), exemplo, type_name="queimadas:focos_24h")
    assert saida["catalog"]["scope"] == "workspace" and saida["catalog"]["state"] == "ok"
    async with infra.sessao() as db:
        fonte = await fs.get_by_key(db, fs.source_key(WS_1, "wfs", exemplo, "queimadas:focos_24h"))
        assert fonte.verificada_em is not None


async def test_probe_refuses_to_update_platform_source_without_editor_in_reach(banco, monkeypatch):
    """Mutation: not requiring editor within reach for a platform source.

    The FUNAI source is a platform one (global). A user who is only a viewer
    within their reach (ana in WS_2) cannot mutate it through probing.
    """
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v)))
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(workspace_ids={WS_2}), FUNAI, type_name="Funai:tis_poligonais")
    assert corpo(exc.value)["code"] == "forbidden"
    async with infra.sessao() as db:
        fonte = await fs.get_by_key(db, fs.source_key(None, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert fonte.verificada_em is None


async def test_probe_translates_the_probe_failure(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=fs.ProbeError(
        "camada_inexistente", "Camada 'x' não encontrada no servidor WFS.", candidates=["Funai:tis_poligonais"],
    )))
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(), FUNAI, type_name="x")
    erro = corpo(exc.value)
    assert erro["code"] == "source_unreachable" and erro["reason"] == "camada_inexistente"
    assert erro["candidates"] == ["Funai:tis_poligonais"]


async def test_probe_refuses_invalid_url_without_probing(banco, monkeypatch):
    sondar = AsyncMock()
    monkeypatch.setattr(fs, "sondar_wfs", sondar)
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(), "https://user:senha@h/ows")  # pragma: allowlist secret
    assert corpo(exc.value)["code"] == "validation"
    sondar.assert_not_awaited()


# ── register_source ───────────────────────────────────────────────────────────


async def test_register_probes_stores_manual_ok_and_is_idempotent(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v)))
    ficha = await register_source(
        ctx(), FUNAI, "Funai:aldeias_pontos", title="Aldeias", description="Pontos das aldeias.",
        tags=["aldeias", "indígena"], hints="Use nome_aldeia.",
    )
    assert ficha["outcome"] == "created" and ficha["scope"] == "workspace" and ficha["workspace_id"] == WS_1
    assert ficha["origin"] == "manual" and ficha["state"] == "ok"
    assert ficha["node_snippet"]["properties"] == {"url": FUNAI, "typeName": "Funai:aldeias_pontos", "sortBy": "gid"}
    assert ficha["untrusted_data"] == {
        "title": "Aldeias", "description": "Pontos das aldeias.", "hints": "Use nome_aldeia.",
        "tags": ["aldeias", "indígena", "kw"],
    }
    again = await register_source(ctx(), FUNAI + "/", "Funai:aldeias_pontos")
    assert again["outcome"] == "updated" and again["id"] == ficha["id"]
    assert (await search_sources(ctx(), query="aldeias"))["total"] == 1


async def test_register_requires_editor_write_scope_and_layer(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _probe(u, t, v)))
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(workspace_ids={WS_2}), FUNAI, "Funai:aldeias_pontos", workspace_id=WS_2)
    assert corpo(exc.value)["code"] == "forbidden"  # viewer there
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(scopes={"workflows:read"}), FUNAI, "Funai:aldeias_pontos")
    assert corpo(exc.value)["code"] == "forbidden_scope"
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(), FUNAI, "  ")
    assert corpo(exc.value)["code"] == "validation"


async def test_register_does_not_store_when_the_probe_fails(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=fs.ProbeError("timeout", "Timeout ao conectar ao servidor WFS.")))
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(), "https://fora.do.ar/ows", "x:y")
    assert corpo(exc.value)["reason"] == "timeout"
    assert (await search_sources(ctx(), query="fora.do.ar"))["total"] == 0
