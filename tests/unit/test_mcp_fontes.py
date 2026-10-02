# tests/unit/test_mcp_fontes.py
"""As quatro tools do catálogo de fontes, e as decisões que as cercam.

- **Buscar e descrever** leem a tabela: escopo de workspace, itens leves com o
  texto de gente em `untrusted_data`, a ficha com o trecho pronto para colar.
- **Sondar e registrar** falam com a internet — aqui dubladas em
  `fontes_service.sondar_wfs`, o único ponto por onde a tool sai — e são as
  duas únicas tools open-world do servidor; nascem SEM clique na Home e
  liberadas no editor por decisão do dono.
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
from app.models.fonte_de_dados import FonteDeDados
from app.models.workspace_member import WorkspaceMember
from app.services import assistente_superficie as ag
from app.services import assistente_service as cs
from app.services import fontes_service as fs
from tests.unit._mcp_harness import TABELAS, criar_usuario, criar_workspace, ctx_falso, escopo_falso, sessao_de

WS_1 = "11111111-1111-4111-8111-111111111111"
WS_2 = "22222222-2222-4222-8222-222222222222"
FUNAI = "https://geoserver.funai.gov.br/geoserver/ows"


def corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


def ctx(**kw):
    campos = {"scopes": {"workflows:read", "workflows:write"}, "workspace_ids": {WS_1}}
    campos.update(kw)
    return ctx_falso(escopo_falso(**campos))


@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[*TABELAS, FonteDeDados.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(infra, "sessao", sessao_de(fabrica))
    async with fabrica() as db:
        await criar_usuario(db, "usr-1", "ana")
        await criar_usuario(db, "usr-2", "bruno")
        await criar_workspace(db, WS_1, "usr-1", "Principal")
        await criar_workspace(db, WS_2, "usr-2", "De outra conta")
        # ana é só viewer no workspace de bruno.
        db.add(WorkspaceMember(workspace_id=WS_2, user_id="usr-1", role="viewer"))
        await db.commit()
        # Plataforma: uma fonte do Vault; workspace 1: uma registrada; workspace 2: uma alheia.
        await fs.upsert_fonte(
            db, workspace_id=None, tipo="wfs", url=FUNAI, type_name="Funai:tis_poligonais",
            propriedades={"sortBy": "gid", "version": "2.0.0"}, origem="vault", estado="ok",
            titulo="Terras indígenas (poligonais)", descricao="FUNAI. Terras indígenas.",
            temas=["FUNAI", "terras indígenas"], dicas="Filtre por uf_sigla em maiúsculas.",
            instituicao="FUNAI", grupo="Funai", prioridade=1,
            esquema={"columns": [{"name": f"c{i}", "type": "string"} for i in range(60)],
                     "columns_source": "vault", "geometry_type": "MultiPolygon", "crs": "EPSG:4674"},
        )
        await fs.upsert_fonte(
            db, workspace_id=WS_1, tipo="wfs", url="https://geoserver.exemplo.gov.br/ows", type_name="queimadas:focos_24h",
            propriedades={}, origem="manual", estado="nao_verificada", titulo="Focos de calor (24 h)",
            temas=["queimadas"], instituicao="geoserver.exemplo.gov.br",
        )
        await fs.upsert_fonte(
            db, workspace_id=WS_2, tipo="wfs", url="https://geoserver.exemplo.gov.br/ows", type_name="privada:x",
            propriedades={}, origem="manual", estado="ok", titulo="Só do outro", temas=[],
        )
        await db.commit()
    try:
        yield fabrica
    finally:
        await engine.dispose()


def _sondagem(url, type_name=None, version="2.0.0", *, camadas=("Funai:tis_poligonais", "Funai:aldeias_pontos")):
    caps = fs.Capabilities(version="2.0.0", layers=tuple(
        fs.CamadaDoServico(name=n, title=n.split(":")[1].replace("_", " "), abstract="Resumo.", keywords=("kw",), crs="EPSG:4674")
        for n in camadas
    ))
    sondagem = fs.Sondagem(url=url, version=version, capabilities=caps)
    if type_name:
        camada = caps.por_nome()[type_name]
        sondagem.camada = camada
        sondagem.esquema = {"columns": [{"name": "gid", "type": "int"}, {"name": "uf_sigla", "type": "string"}],
                            "columns_source": "describe_feature_type", "geometry_type": "MultiPolygon",
                            "crs": "EPSG:4674", "bbox": [-73.99, -33.75, -28.84, 5.27]}
    return sondagem


# ── Guardas e superfícies ─────────────────────────────────────────────────────


def test_as_duas_que_sondam_sao_as_unicas_open_world_e_pagam_o_balde_probe():
    abertas = {n for n, g in GUARDAS.items() if g.open_world}
    assert abertas == {"probe_source", "register_source"}
    for nome in abertas:
        assert GUARDAS[nome].cota == "probe" and GUARDAS[nome].read_only is False
    for nome in ("search_sources", "describe_source"):
        assert GUARDAS[nome].read_only is True and GUARDAS[nome].cota is None and GUARDAS[nome].open_world is False


async def test_anotacoes_publicadas_batem_com_a_tabela():
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


def test_sondar_e_registrar_sao_livres_na_home_e_no_editor():
    """Decisão do dono: catálogo primeiro, mas sondar e guardar não pedem clique."""
    assert {"probe_source", "register_source"} <= ag.ESCRITAS_SEM_CLIQUE
    assert not ({"probe_source", "register_source"} & ag.CONFIRMAVEIS_SEMPRE)
    assert not cs.bloqueada_no_editor("probe_source")
    assert not cs.bloqueada_no_editor("register_source")


# ── search_sources ────────────────────────────────────────────────────────────


async def test_search_devolve_itens_leves_com_o_texto_de_gente_a_parte(banco):
    saida = await search_sources(ctx(), query="terras indígenas")
    assert saida["total"] == 1 and saida["workspace_ids"] == [WS_1]
    item = saida["items"][0]
    assert item["type_name"] == "Funai:tis_poligonais" and item["scope"] == "platform"
    assert item["state"] == "ok" and item["priority"] == 1 and item["host"] == "geoserver.funai.gov.br"
    assert item["untrusted_data"] == {"title": "Terras indígenas (poligonais)", "tags": ["FUNAI", "terras indígenas"]}
    assert "title" not in item and "hint" not in saida


async def test_search_respeita_o_escopo_e_avisa_quando_nada_casa(banco):
    tudo = await search_sources(ctx())
    assert {i["type_name"] for i in tudo["items"]} == {"Funai:tis_poligonais", "queimadas:focos_24h"}
    # O workspace 2 está fora do token: a fonte privada não aparece, mesmo pedida.
    with pytest.raises(ToolError) as exc:
        await search_sources(ctx(), workspace_id=WS_2)
    assert corpo(exc.value)["code"] == "forbidden"
    vazio = await search_sources(ctx(), query="xyzzy")
    assert vazio["items"] == [] and "probe_source" in vazio["hint"]
    # Sinônimo: "focos de calor" acha a de "queimadas"; o teto é aparado.
    focos = await search_sources(ctx(), query="focos de calor", limit=999)
    assert [i["type_name"] for i in focos["items"]] == ["queimadas:focos_24h"] and focos["limit"] == 50


async def test_search_exige_escopo_de_leitura(banco):
    with pytest.raises(ToolError) as exc:
        await search_sources(ctx(scopes={"drive:read"}))
    assert corpo(exc.value)["code"] == "forbidden_scope"


# ── describe_source ───────────────────────────────────────────────────────────


async def test_describe_traz_o_trecho_pronto_o_esquema_cortado_e_as_dicas(banco):
    item = (await search_sources(ctx(), query="terras"))["items"][0]
    ficha = await describe_source(ctx(), item["id"])
    # `version` fica no catálogo, não no trecho: o nó ainda não a declara.
    assert ficha["node_snippet"] == {
        "name": "WFS", "type": "datasource",
        "properties": {"url": FUNAI, "typeName": "Funai:tis_poligonais", "sortBy": "gid"},
    }
    assert ficha["schema"]["columns_total"] == 60 and len(ficha["schema"]["columns"]) == 50
    assert ficha["schema"]["crs"] == "EPSG:4674" and ficha["schema"]["geometry_type"] == "MultiPolygon"
    assert ficha["origin"] == "vault" and ficha["state"] == "ok" and ficha["last_error"] is None
    assert ficha["untrusted_data"]["hints"] == "Filtre por uf_sigla em maiúsculas."
    assert ficha["untrusted_data"]["description"].startswith("FUNAI.")


async def test_describe_de_fonte_fora_do_alcance_e_not_found(banco):
    async with infra.sessao() as db:
        # O id sai de dentro da sessão: o rollback do `finally` expira o objeto.
        id_da_privada = (await fs.buscar(db, [WS_2], query="privada"))[0][0].id_hash
    with pytest.raises(ToolError) as exc:
        await describe_source(ctx(), id_da_privada)
    assert corpo(exc.value)["code"] == "not_found"
    with pytest.raises(ToolError):
        await describe_source(ctx(), "nao-existe")


# ── probe_source ──────────────────────────────────────────────────────────────


async def test_probe_lista_as_camadas_e_avisa_que_o_endpoint_ja_esta_no_catalogo(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v)))
    saida = await probe_source(ctx(), FUNAI + "?service=WFS&request=GetCapabilities")
    assert saida["outcome"] == "layers_listed" and saida["url"] == FUNAI and saida["layer_count"] == 2
    assert saida["untrusted_data"]["layers"] == [
        {"name": "Funai:tis_poligonais", "title": "tis poligonais"},
        {"name": "Funai:aldeias_pontos", "title": "aldeias pontos"},
    ]
    assert "já está catalogado com 1 camada" in saida["catalog_hint"]


async def test_probe_nao_dispara_a_busca_descartada(banco, monkeypatch):
    """Mutacao: devolver a chamada `fontes_service.buscar` descartada em
    `_fontes_do_endpoint`. Ela nao filtra por URL e o resultado nao era usado —
    so custava duas queries a mais por probe. O count do endpoint segue certo."""
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v)))
    espiao = AsyncMock(wraps=fs.buscar)
    monkeypatch.setattr(fs, "buscar", espiao)

    saida = await probe_source(ctx(), FUNAI + "?service=WFS&request=GetCapabilities")

    espiao.assert_not_called()
    assert "já está catalogado com 1 camada" in saida["catalog_hint"]


async def test_probe_com_camada_descreve_e_atualiza_a_fonte_catalogada(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v)))
    saida = await probe_source(ctx(), FUNAI, type_name="Funai:tis_poligonais")
    assert saida["outcome"] == "layer_described" and saida["layer"] == "Funai:tis_poligonais"
    assert saida["schema"]["columns_source"] == "describe_feature_type" and saida["schema"]["bbox"] == [-73.99, -33.75, -28.84, 5.27]
    assert saida["node_snippet"]["properties"] == {"url": FUNAI, "typeName": "Funai:tis_poligonais", "sortBy": "gid"}
    assert saida["catalog"]["scope"] == "platform" and saida["catalog"]["state"] == "ok"
    assert saida["untrusted_data"]["title"] == "tis poligonais" and "hint" not in saida
    async with infra.sessao() as db:
        fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(None, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert fonte.esquema["columns_source"] == "describe_feature_type" and fonte.verificada_em is not None

    nova = await probe_source(ctx(), FUNAI, type_name="Funai:aldeias_pontos")
    assert nova["catalog"] is None and "register_source" in nova["hint"]


async def test_probe_recusa_atualizar_fonte_de_workspace_sem_papel_de_editor(banco, monkeypatch):
    """Mutacao: remover o exigir_papel do probe (voltar a so checar o escopo).

    Sondar ATUALIZA o catalogo: um viewer no workspace da fonte nao pode mutar.
    A fonte 'privada:x' e do WS_2, onde ana e apenas viewer.
    """
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(
        side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v, camadas=("privada:x",))))
    exemplo = "https://geoserver.exemplo.gov.br/ows"
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(workspace_ids={WS_2}), exemplo, type_name="privada:x")
    assert corpo(exc.value)["code"] == "forbidden"
    async with infra.sessao() as db:
        fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(WS_2, "wfs", exemplo, "privada:x"))
        assert fonte.verificada_em is None


async def test_probe_atualiza_fonte_de_workspace_com_papel_de_editor(banco, monkeypatch):
    """Editor no workspace da fonte pode atualiza-la pela sondagem (WS_1)."""
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(
        side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v, camadas=("queimadas:focos_24h",))))
    exemplo = "https://geoserver.exemplo.gov.br/ows"
    saida = await probe_source(ctx(), exemplo, type_name="queimadas:focos_24h")
    assert saida["catalog"]["scope"] == "workspace" and saida["catalog"]["state"] == "ok"
    async with infra.sessao() as db:
        fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(WS_1, "wfs", exemplo, "queimadas:focos_24h"))
        assert fonte.verificada_em is not None


async def test_probe_recusa_atualizar_fonte_de_plataforma_sem_editor_no_alcance(banco, monkeypatch):
    """Mutacao: nao exigir editor no alcance para fonte de plataforma.

    A fonte FUNAI e de plataforma (global). Um usuario que so e viewer no seu
    alcance (ana no WS_2) nao pode muta-la pela sondagem.
    """
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v)))
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(workspace_ids={WS_2}), FUNAI, type_name="Funai:tis_poligonais")
    assert corpo(exc.value)["code"] == "forbidden"
    async with infra.sessao() as db:
        fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(None, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert fonte.verificada_em is None


async def test_probe_traduz_a_falha_da_sondagem(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=fs.SondagemError(
        "camada_inexistente", "Camada 'x' não encontrada no servidor WFS.", candidatas=["Funai:tis_poligonais"],
    )))
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(), FUNAI, type_name="x")
    erro = corpo(exc.value)
    assert erro["code"] == "source_unreachable" and erro["reason"] == "camada_inexistente"
    assert erro["candidates"] == ["Funai:tis_poligonais"]


async def test_probe_recusa_url_invalida_sem_sondar(banco, monkeypatch):
    sondar = AsyncMock()
    monkeypatch.setattr(fs, "sondar_wfs", sondar)
    with pytest.raises(ToolError) as exc:
        await probe_source(ctx(), "https://user:senha@h/ows")  # pragma: allowlist secret
    assert corpo(exc.value)["code"] == "validation"
    sondar.assert_not_awaited()


# ── register_source ───────────────────────────────────────────────────────────


async def test_register_sonda_grava_manual_ok_e_e_idempotente(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v)))
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
    de_novo = await register_source(ctx(), FUNAI + "/", "Funai:aldeias_pontos")
    assert de_novo["outcome"] == "updated" and de_novo["id"] == ficha["id"]
    assert (await search_sources(ctx(), query="aldeias"))["total"] == 1


async def test_register_exige_editor_escopo_de_escrita_e_camada(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=lambda u, t=None, v="2.0.0": _sondagem(u, t, v)))
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(workspace_ids={WS_2}), FUNAI, "Funai:aldeias_pontos", workspace_id=WS_2)
    assert corpo(exc.value)["code"] == "forbidden"  # viewer lá
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(scopes={"workflows:read"}), FUNAI, "Funai:aldeias_pontos")
    assert corpo(exc.value)["code"] == "forbidden_scope"
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(), FUNAI, "  ")
    assert corpo(exc.value)["code"] == "validation"


async def test_register_nao_grava_quando_a_sondagem_falha(banco, monkeypatch):
    monkeypatch.setattr(fs, "sondar_wfs", AsyncMock(side_effect=fs.SondagemError("timeout", "Timeout ao conectar ao servidor WFS.")))
    with pytest.raises(ToolError) as exc:
        await register_source(ctx(), "https://fora.do.ar/ows", "x:y")
    assert corpo(exc.value)["reason"] == "timeout"
    assert (await search_sources(ctx(), query="fora.do.ar"))["total"] == 0
