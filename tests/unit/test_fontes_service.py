# tests/unit/test_fontes_service.py
"""The source catalog service: probing, key, search, merge, validation,
learning, per-endpoint verification and Vault import.

A real in-memory database (SQLite, only the `fontes_de_dados` table) — the `LIKE`
search, the ordering and the upsert are exactly what we want to prove, and a
mock of `db.execute` would only prove the mock. The network is doubled at TWO points,
the only ones through which the service goes out: `validate_url_ssrf` and `safe_httpx_request`.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import FonteInvalidaError
from app.models.base import Base
from app.models.fonte_de_dados import FonteDeDados
from app.services import fontes_service as fs

VAULT = Path(__file__).resolve().parents[1] / "fixtures" / "vault"
WS = "11111111-1111-4111-8111-111111111111"
WS_OUTRO = "22222222-2222-4222-8222-222222222222"
FUNAI = "https://geoserver.funai.gov.br/geoserver/ows"

CAPS_2 = """<?xml version="1.0" encoding="UTF-8"?>
<wfs:WFS_Capabilities version="2.0.0" xmlns:wfs="http://www.opengis.net/wfs/2.0" xmlns:ows="http://www.opengis.net/ows/1.1">
  <wfs:FeatureTypeList>
    <wfs:FeatureType>
      <wfs:Name>Funai:tis_poligonais</wfs:Name>
      <wfs:Title>Terras indígenas (poligonais)</wfs:Title>
      <wfs:Abstract>Limites das terras indígenas.</wfs:Abstract>
      <ows:Keywords><ows:Keyword>terras</ows:Keyword><ows:Keyword>indígenas</ows:Keyword></ows:Keywords>
      <wfs:DefaultCRS>urn:ogc:def:crs:EPSG::4674</wfs:DefaultCRS>
      <ows:WGS84BoundingBox><ows:LowerCorner>-73.99 -33.75</ows:LowerCorner><ows:UpperCorner>-28.84 5.27</ows:UpperCorner></ows:WGS84BoundingBox>
    </wfs:FeatureType>
    <wfs:FeatureType>
      <wfs:Name>Funai:aldeias_pontos</wfs:Name>
      <wfs:Title>Aldeias</wfs:Title>
      <wfs:DefaultCRS>EPSG:4326</wfs:DefaultCRS>
    </wfs:FeatureType>
  </wfs:FeatureTypeList>
</wfs:WFS_Capabilities>"""

CAPS_1 = """<?xml version="1.0"?>
<WFS_Capabilities version="1.0.0" xmlns="http://www.opengis.net/wfs">
  <FeatureTypeList>
    <FeatureType><Name>APONDS:aponds_ibge</Name><Title>Aponds IBGE</Title><SRS>EPSG:4674</SRS>
      <LatLongBoundingBox minx="-73" miny="-33" maxx="-28" maxy="5"/></FeatureType>
  </FeatureTypeList>
</WFS_Capabilities>"""

XSD = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:Funai="https://geoserver.funai.gov.br/funai" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xsd="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" targetNamespace="https://geoserver.funai.gov.br/funai">
  <xsd:import namespace="http://www.opengis.net/gml/3.2" schemaLocation="http://x/gml.xsd"/>
  <xsd:complexType name="tis_poligonaisType">
    <xsd:complexContent><xsd:extension base="gml:AbstractFeatureType"><xsd:sequence>
      <xsd:element maxOccurs="1" minOccurs="0" name="gid" nillable="false" type="xsd:int"/>
      <xsd:element maxOccurs="1" minOccurs="0" name="terrai_nome" nillable="true" type="xsd:string"/>
      <xsd:element maxOccurs="1" minOccurs="0" name="the_geom" nillable="true" type="gml:MultiSurfacePropertyType"/>
    </xsd:sequence></xsd:extension></xsd:complexContent>
  </xsd:complexType>
  <xsd:element name="tis_poligonais" substitutionGroup="gml:AbstractFeature" type="Funai:tis_poligonaisType"/>
</xsd:schema>"""


@pytest.fixture
async def fabrica():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[FonteDeDados.__table__])
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.fixture
def sem_rede(monkeypatch):
    """No test here goes out to the internet — whoever probes without a double breaks."""
    async def _proibido(*a, **k):
        raise AssertionError("sondagem sem dublê")
    monkeypatch.setattr(fs, "safe_httpx_request", _proibido)
    monkeypatch.setattr(fs, "validate_url_ssrf", lambda url: ("1.2.3.4", "host"))


def _rede(monkeypatch, respostas: dict[str, str | Exception]):
    """`safe_httpx_request` doubled: picks the response by a piece of the URL."""
    monkeypatch.setattr(fs, "validate_url_ssrf", lambda url: ("1.2.3.4", "host"))

    async def _falso(method, url, **kw):
        for trecho, resposta in respostas.items():
            if trecho in url:
                if isinstance(resposta, Exception):
                    raise resposta
                return httpx.Response(200, text=resposta, request=httpx.Request(method, url))
        return httpx.Response(404, request=httpx.Request(method, url))
    monkeypatch.setattr(fs, "safe_httpx_request", _falso)


async def _upsert(db, **kw):
    campos = dict(
        workspace_id=None, tipo="wfs", url=FUNAI, type_name="Funai:tis_poligonais",
        propriedades={"sortBy": "gid", "version": "2.0.0"}, origem="vault", estado="ok",
        titulo="Terras indígenas (poligonais)", descricao="FUNAI. Terras indígenas.",
        temas=["FUNAI", "Funai"], instituicao="FUNAI", grupo="Funai",
        esquema={"columns": [{"name": "gid"}, {"name": "uf_sigla"}], "columns_source": "vault"},
    )
    campos.update(kw)
    fonte, desfecho = await fs.upsert_fonte(db, **campos)
    await db.commit()
    return fonte, desfecho


# ── Shape: URL, key, search text, synonyms ───────────────────────────────────


def test_normalizar_url_normaliza_como_o_no_e_recusa_o_que_nunca_e_fonte():
    assert fs.normalizar_url("<https://h/geoserver/ows?service=WFS&request=GetCapabilities>") == "https://h/geoserver/ows"
    assert fs.normalizar_url("https://h/geoserver/wfs/") == "https://h/geoserver/wfs"
    for ruim in ("", "ftp://h/x", "naourl", "https://user:senha@h/ows", "https://" + "a" * 2050):  # pragma: allowlist secret
        with pytest.raises(FonteInvalidaError):
            fs.normalizar_url(ruim)


def test_chave_distingue_plataforma_de_workspace_e_ignora_query_string():
    plataforma = fs.chave_da_fonte(None, "wfs", fs.normalizar_url(FUNAI + "?x=1"), "Funai:tis")
    assert plataforma == fs.chave_da_fonte(None, "wfs", FUNAI, "Funai:tis")
    assert plataforma != fs.chave_da_fonte(WS, "wfs", FUNAI, "Funai:tis")
    assert len(plataforma) == 64


def test_texto_de_busca_junta_tudo_sem_acento():
    texto = fs.texto_de_busca(
        instituicao="Ministério da Saúde", grupo="IDE-MS", titulo="Estabelecimentos", type_name="ms:cnes_estab",
        url=FUNAI, descricao="Saúde pública.", temas=["saúde"],
        esquema={"columns": [{"name": "nome_fantasia"}, "cnes"]},
    )
    for pedaco in ("ministerio da saude", "ide-ms", "estabelecimentos", "ms:cnes_estab", "ms cnes estab",
                   "geoserver.funai.gov.br", "saude publica", "nome_fantasia", "cnes"):
        assert pedaco in texto, pedaco


def test_termos_expandem_por_sinonimos_padrao_e_do_vault():
    fs.definir_sinonimos({"Cadastro Ambiental Rural": ["CAR", "imóveis rurais"]})
    try:
        termos = fs.termos_da_consulta("focos de calor")
        assert len(termos) == 2  # "focos" and "calor"; "de" is a connective
        assert {"focos de calor", "queimadas", "hotspot"} <= termos[0]
        assert "calor" in termos[1] and "focos de calor" in termos[1]
        # From the Vault, in both directions.
        assert "car" in fs.sinonimos_de("cadastro ambiental rural")
        assert "cadastro ambiental rural" in fs.sinonimos_de("CAR")
        assert fs.termos_da_consulta("  ") == []
    finally:
        fs.definir_sinonimos({})


# ── Parsers ───────────────────────────────────────────────────────────────────


def test_parsear_capabilities_2_0_0_e_1_0_0():
    caps = fs.parsear_capabilities(CAPS_2)
    assert caps.version == "2.0.0"
    tis = caps.por_nome()["Funai:tis_poligonais"]
    assert tis.title == "Terras indígenas (poligonais)"
    assert tis.abstract == "Limites das terras indígenas."
    assert tis.keywords == ("terras", "indígenas")
    assert tis.crs == "EPSG:4674"
    assert tis.bbox == (-73.99, -33.75, -28.84, 5.27)
    assert caps.por_nome()["Funai:aldeias_pontos"].crs == "EPSG:4326"

    antiga = fs.parsear_capabilities(CAPS_1)
    assert antiga.version == "1.0.0"
    ibge = antiga.layers[0]
    assert ibge.name == "APONDS:aponds_ibge" and ibge.crs == "EPSG:4674" and ibge.bbox == (-73.0, -33.0, -28.0, 5.0)


def test_parsear_capabilities_recusa_dtd_e_exception_report():
    with pytest.raises(fs.SondagemError) as exc:
        fs.parsear_capabilities('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><x/>')
    assert exc.value.codigo == "xml"
    with pytest.raises(fs.SondagemError) as exc:
        fs.parsear_capabilities('<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception><ows:ExceptionText>Service unavailable</ows:ExceptionText></ows:Exception></ows:ExceptionReport>')
    assert exc.value.codigo == "http_status" and "Service unavailable" in exc.value.mensagem
    with pytest.raises(fs.SondagemError):
        fs.parsear_capabilities("isto não é xml <")


def test_parsear_describe_feature_type_le_a_sequence_e_acha_a_geometria():
    esquema = fs.parsear_describe_feature_type(XSD)
    assert esquema["columns_source"] == "describe_feature_type"
    assert [c["name"] for c in esquema["columns"]] == ["gid", "terrai_nome", "the_geom"]
    assert esquema["columns"][0] == {"name": "gid", "type": "int", "xsd": "xsd:int", "nullable": False}
    assert esquema["geometry_column"] == "the_geom" and esquema["geometry_type"] == "MultiPolygon"


# ── The network, translated into closed codes ─────────────────────────────────


@pytest.mark.parametrize(
    "falha,codigo,status_http",
    [
        (httpx.ReadTimeout("t"), "timeout", 504),
        (ValueError("Resposta excedeu o limite de 10 bytes."), "tamanho", 502),
        (RuntimeError("Não foi possível validar o certificado TLS"), "tls", 502),
        (ConnectionError("recusada"), "rede", 502),
    ],
)
async def test_falhas_de_rede_viram_sondagem_error(monkeypatch, falha, codigo, status_http):
    _rede(monkeypatch, {"GetCapabilities": falha})
    with pytest.raises(fs.SondagemError) as exc:
        await fs.listar_camadas_wfs(FUNAI)
    assert exc.value.codigo == codigo
    assert exc.value.como_http()[0] == status_http


async def test_status_http_e_ssrf(monkeypatch):
    _rede(monkeypatch, {"GetCapabilities": httpx.Response(500, request=httpx.Request("GET", FUNAI))})

    async def _500(method, url, **kw):
        return httpx.Response(500, request=httpx.Request(method, url))
    monkeypatch.setattr(fs, "safe_httpx_request", _500)
    with pytest.raises(fs.SondagemError) as exc:
        await fs.listar_camadas_wfs(FUNAI)
    assert exc.value.codigo == "http_status" and exc.value.status == 500
    assert exc.value.como_http() == (502, "Servidor WFS retornou HTTP 500.")

    def _bloqueia(url):
        raise ValueError("IP privado")
    monkeypatch.setattr(fs, "validate_url_ssrf", _bloqueia)
    with pytest.raises(fs.SondagemError) as exc:
        await fs.listar_camadas_wfs("https://10.0.0.1/ows")
    assert exc.value.codigo == "ssrf" and exc.value.como_http()[0] == 403


async def test_listar_camadas_e_sondar_com_camada(monkeypatch):
    _rede(monkeypatch, {"GetCapabilities": CAPS_2, "DescribeFeatureType": XSD})
    camadas = await fs.listar_camadas_wfs(FUNAI)
    assert camadas == [
        {"name": "Funai:aldeias_pontos", "title": "Aldeias"},
        {"name": "Funai:tis_poligonais", "title": "Terras indígenas (poligonais)"},
    ]
    sondagem = await fs.sondar_wfs(FUNAI, "tis_poligonais")  # without the prefix: unique → found
    assert sondagem.camada.name == "Funai:tis_poligonais"
    assert sondagem.esquema["crs"] == "EPSG:4674" and sondagem.esquema["bbox"] == [-73.99, -33.75, -28.84, 5.27]
    assert sondagem.esquema["geometry_type"] == "MultiPolygon"

    with pytest.raises(fs.SondagemError) as exc:
        await fs.sondar_wfs(FUNAI, "Funai:nao_existe")
    assert exc.value.codigo == "camada_inexistente"
    assert exc.value.candidatas == ["Funai:tis_poligonais", "Funai:aldeias_pontos"]


async def test_servidor_sem_camadas(monkeypatch):
    _rede(monkeypatch, {"GetCapabilities": '<wfs:WFS_Capabilities version="2.0.0" xmlns:wfs="http://www.opengis.net/wfs/2.0"/>'})
    with pytest.raises(fs.SondagemError) as exc:
        await fs.listar_camadas_wfs(FUNAI)
    assert exc.value.codigo == "sem_camadas" and exc.value.como_http()[0] == 404


# ── Listing with the node's credential (the editor's layer picker) ────────────


@pytest.fixture
def fio(monkeypatch):
    """The request that actually goes out: the real `safe_httpx_request`, only the send doubled.

    Doubling the whole `safe_httpx_request` would hide exactly what matters here — httpx's
    `params` REPLACES the URL's query, and the GetCapabilities would go out without
    `service` and `request` without any test noticing.
    """
    import flow.utils.geo_helpers as geo

    monkeypatch.setattr(geo, "validate_url_ssrf", lambda url: ("1.2.3.4", "geoserver.funai.gov.br"))
    monkeypatch.setattr(fs, "validate_url_ssrf", lambda url: ("1.2.3.4", "geoserver.funai.gov.br"))
    enviados: list[httpx.Request] = []

    async def _send(self, request, **kw):
        import logging
        enviados.append(request)
        logging.getLogger("httpx").info("HTTP Request: %s %s", request.method, request.url)  # like httpx
        return httpx.Response(200, text=CAPS_2, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", _send)
    return enviados


def _query(pedido: httpx.Request) -> dict:
    from urllib.parse import parse_qsl
    return dict(parse_qsl(pedido.url.query.decode()))


async def test_authkey_na_url_vai_junto_da_query_do_getcapabilities(fio, caplog):
    import logging
    from flow.utils.credencial_wfs import autenticacao_wfs
    auth = autenticacao_wfs(None, {"type": "geoserver_authkey", "token": "a+b/c=d&e"})
    with caplog.at_level(logging.INFO, logger="httpx"):
        camadas = await fs.listar_camadas_wfs(FUNAI, auth=auth)
    assert "authkey=***" in caplog.text and "a%2Bb%2Fc%3Dd%26e" not in caplog.text  # httpx's log
    assert [c["name"] for c in camadas] == ["Funai:aldeias_pontos", "Funai:tis_poligonais"]
    (pedido,) = fio
    esperado = {"service": "WFS", "request": "GetCapabilities", "version": "2.0.0", "authkey": "a+b/c=d&e"}  # pragma: allowlist secret
    assert _query(pedido) == esperado
    assert pedido.headers["host"] == "geoserver.funai.gov.br"


async def test_authkey_no_cabecalho_nao_vai_na_url(fio):
    from flow.utils.credencial_wfs import autenticacao_wfs
    auth = autenticacao_wfs(None, {"type": "geoserver_authkey", "token": "K-123456", "parameter": "X-Chave", "location": "header"})
    await fs.listar_camadas_wfs(FUNAI, auth=auth)
    (pedido,) = fio
    assert pedido.headers["x-chave"] == "K-123456" and "K-123456" not in str(pedido.url)
    assert _query(pedido) == {"service": "WFS", "request": "GetCapabilities", "version": "2.0.0"}


async def test_usuario_e_senha_vao_por_basic(fio):
    import base64
    from flow.utils.credencial_wfs import autenticacao_wfs
    auth = autenticacao_wfs(None, {"type": "wfs", "username": "leitor", "password": "s3nh@:x"})
    await fs.listar_camadas_wfs(FUNAI, auth=auth)
    (pedido,) = fio
    assert pedido.headers["authorization"] == "Basic " + base64.b64encode(b"leitor:s3nh@:x").decode()
    assert "s3nh" not in str(pedido.url)


async def test_sem_credencial_o_pedido_sai_anonimo(fio):
    await fs.listar_camadas_wfs(FUNAI)
    (pedido,) = fio
    assert "authorization" not in pedido.headers
    assert _query(pedido) == {"service": "WFS", "request": "GetCapabilities", "version": "2.0.0"}


# ── Upsert and merge ──────────────────────────────────────────────────────────


async def test_upsert_cria_e_depois_atualiza_pela_chave(fabrica, sem_rede):
    async with fabrica() as db:
        fonte, desfecho = await _upsert(db)
        assert desfecho == "created" and fonte.busca and "terras indigenas" in fonte.busca
        assert fonte.propriedades["url"] == FUNAI and fonte.propriedades["typeName"] == "Funai:tis_poligonais"
        mesma, desfecho = await _upsert(db, url=FUNAI + "?service=WFS", titulo="Outro título")
        assert desfecho == "updated" and mesma.id == fonte.id
        assert mesma.titulo == "Terras indígenas (poligonais)"  # the empty one is filled in; the written one is not
        assert (await db.execute(select(FonteDeDados))).scalars().all().__len__() == 1


async def test_aprendida_nao_rebaixa_nem_ressuscita_e_conta_uso_so_no_primeiro_fechamento(fabrica, sem_rede):
    async with fabrica() as db:
        fonte, _ = await _upsert(db)
        _, desfecho = await _upsert(db, origem="aprendida", estado="ok", contar_uso=True, propriedades={})
        assert desfecho == "updated" and fonte.origem == "vault" and fonte.usos == 1
        assert fonte.propriedades["sortBy"] == "gid"  # the run does not bring sortBy; the Vault did, so it stays
        await _upsert(db, origem="aprendida", contar_uso=False)
        assert fonte.usos == 1

        fonte.deleted_at = datetime(2026, 9, 19)
        await db.commit()
        _, desfecho = await _upsert(db, origem="aprendida")
        assert desfecho == "deleted" and fonte.deleted_at is not None
        _, desfecho = await _upsert(db, origem="manual")
        assert desfecho == "updated" and fonte.deleted_at is None


def test_fundir_esquema_respeita_a_forca_e_preserva_crs_e_bbox():
    vault = {"columns": [{"name": "gid"}], "columns_source": "vault", "geometry_type": "MultiPolygon"}
    run = {"columns": [{"name": "gid"}, {"name": "x"}], "columns_source": "run", "crs": "EPSG:4674", "bbox": [1, 2, 3, 4], "feature_count": 84}
    fundido = fs.fundir_esquema(vault, run)
    assert fundido["columns_source"] == "vault" and len(fundido["columns"]) == 1
    assert fundido["crs"] == "EPSG:4674" and fundido["bbox"] == [1, 2, 3, 4] and fundido["feature_count"] == 84
    assert fundido["geometry_type"] == "MultiPolygon"

    describe = {"columns": [{"name": "gid", "type": "int"}], "columns_source": "describe_feature_type"}
    assert fs.fundir_esquema(fundido, describe)["columns_source"] == "describe_feature_type"
    assert fs.fundir_esquema(fundido, describe)["crs"] == "EPSG:4674"
    assert fs.fundir_esquema(None, None) is None
    assert fs.fundir_esquema(None, {"crs": "EPSG:4326"}) == {"crs": "EPSG:4326"}


# ── Busca e leitura ───────────────────────────────────────────────────────────


async def _semear(db):
    await _upsert(db)  # FUNAI tis_poligonais, plataforma, ok
    await _upsert(db, type_name="Funai:aldeias_pontos", titulo="Aldeias Indígenas (pontos)", estado="falhando",
                  ultimo_erro="camada não consta no GetCapabilities", prioridade=1,
                  esquema={"columns": [{"name": "cod_aldeia"}], "columns_source": "vault"})
    await _upsert(db, workspace_id=WS, url="https://geoserver.exemplo.gov.br/ows", type_name="queimadas:focos_24h",
                  titulo="Focos de calor (24 h)", descricao="Exemplo.", temas=["queimadas"], instituicao="Exemplo",
                  grupo="queimadas", origem="manual", estado="ok",
                  esquema={"columns": [{"name": "id"}, {"name": "estado"}], "columns_source": "vault"})
    await _upsert(db, workspace_id=WS_OUTRO, url="https://geoserver.exemplo.gov.br/ows", type_name="privada:x",
                  titulo="Só do outro", descricao="", temas=[], instituicao="Outro", origem="manual", estado="ok",
                  esquema=None)


async def test_buscar_respeita_o_escopo_e_expande_sinonimos(fabrica, sem_rede):
    async with fabrica() as db:
        await _semear(db)
        itens, total = await fs.buscar(db, [WS], query="queimadas")
        assert total == 1 and itens[0].type_name == "queimadas:focos_24h"
        # Synonym: "focos de calor" finds the "queimadas" source.
        itens, _ = await fs.buscar(db, [WS], query="focos de calor")
        assert [i.type_name for i in itens] == ["queimadas:focos_24h"]
        # No accents and no case. Both FUNAI rows match (the description of
        # both says "Terras indígenas"); the `ok` one comes first.
        itens, _ = await fs.buscar(db, [WS], query="TERRAS indigenas")
        assert [i.type_name for i in itens] == ["Funai:tis_poligonais", "Funai:aldeias_pontos"]
        # Column names count too: only tis_poligonais has `gid`.
        itens, _ = await fs.buscar(db, [WS], query="gid")
        assert [i.type_name for i in itens] == ["Funai:tis_poligonais"]
        # The OTHER workspace's source does not show up; the platform's shows up for everyone.
        itens, total = await fs.buscar(db, [WS], query=None)
        assert total == 3 and "privada:x" not in {i.type_name for i in itens}
        itens, total = await fs.buscar(db, None, query=None)
        assert total == 2  # platform only
        # AND between terms: "focos indígenas" matches nothing.
        assert (await fs.buscar(db, [WS], query="focos indígenas"))[1] == 0


async def test_buscar_ordena_ok_antes_de_falhando_e_por_prioridade(fabrica, sem_rede):
    async with fabrica() as db:
        await _semear(db)
        itens, _ = await fs.buscar(db, [WS], query="FUNAI")
        # aldeias has priority 1 but is failing: `ok` comes first.
        assert [i.type_name for i in itens] == ["Funai:tis_poligonais", "Funai:aldeias_pontos"]
        itens, _ = await fs.buscar(db, [WS], state="falhando")
        assert [i.type_name for i in itens] == ["Funai:aldeias_pontos"]
        itens, _ = await fs.buscar(db, [WS], institution="funai")
        assert len(itens) == 2
        itens, _ = await fs.buscar(db, [WS], kind="arcgis_rest")
        assert itens == []


async def test_obter_e_trecho_do_no(fabrica, sem_rede):
    async with fabrica() as db:
        await _semear(db)
        fonte = (await fs.buscar(db, [WS], query="tis_poligonais"))[0][0]
        assert (await fs.obter(db, fonte.id_hash, [WS])).id == fonte.id
        privada = (await fs.buscar(db, [WS_OUTRO], query="privada"))[0][0]
        assert await fs.obter(db, privada.id_hash, [WS]) is None  # out of scope
        trecho = fs.trecho_do_no(fonte)
        assert trecho == {
            "name": "WFS", "type": "datasource",
            "properties": {"url": FUNAI, "typeName": "Funai:tis_poligonais", "sortBy": "gid"},
        }  # `version` is left out: the node does not declare it yet


# ── Validation without network ────────────────────────────────────────────────

DESCRITORES = {"WFS": {"source_kind": "wfs"}, "Buffer": {}}


def _no(id_, url, type_name):
    return {"id": id_, "name": "WFS", "type": "datasource", "parameters": {"url": url, "typeName": type_name}}


async def test_conferir_fontes_avisa_desconhecida_e_falhando_e_cala_a_catalogada(fabrica, sem_rede):
    async with fabrica() as db:
        await _semear(db)
        nos = [
            _no("ok", FUNAI + "?service=WFS", "Funai:tis_poligonais"),
            _no("falha", FUNAI, "Funai:aldeias_pontos"),
            _no("nova", "https://outro.gov.br/ows", "x:y"),
            _no("do_ws", "https://geoserver.exemplo.gov.br/ows", "queimadas:focos_24h"),
            {"id": "b", "name": "Buffer", "type": "spatial", "parameters": {"url": "https://ignorada/ows", "typeName": "z"}},
            _no("sem_url", "", "x:y"),
        ]
        avisos = await fs.conferir_fontes_da_definicao(db, nos, DESCRITORES, WS)
        por_no = {a["node_id"]: a for a in avisos}
        assert set(por_no) == {"falha", "nova"}
        assert por_no["nova"]["code"] == "unknown_source" and "search_sources" in por_no["nova"]["message"]
        assert por_no["falha"]["code"] == "failing_source" and "não consta" in por_no["falha"]["message"]
        assert all(a["severity"] == "warning" and a["edge"] is None for a in avisos)
        # From the other workspace the private source does NOT count.
        avisos = await fs.conferir_fontes_da_definicao(db, [_no("x", "https://geoserver.exemplo.gov.br/ows", "queimadas:focos_24h")], DESCRITORES, WS_OUTRO)
        assert [a["code"] for a in avisos] == ["unknown_source"]


async def test_conferir_fontes_falha_aberta(sem_rede):
    class _DbQuebrado:
        async def execute(self, *a, **k):
            raise RuntimeError("banco fora")
    assert await fs.conferir_fontes_da_definicao(_DbQuebrado(), [_no("a", FUNAI, "x")], DESCRITORES, WS) == []


# ── Aprendizado ───────────────────────────────────────────────────────────────


async def test_aprender_de_execucao_registra_so_os_completos_com_o_esquema_do_run(fabrica, sem_rede):
    definition = {"nodes": [
        {"id": "f1", "name": "WFS", "properties": {"url": FUNAI + "?x=1", "typeName": "Funai:tis_poligonais", "maxFeatures": 5000, "version": "2.0.0"}},
        {"id": "f2", "name": "WFS", "data": {"properties": {"url": FUNAI, "typeName": "Funai:aldeias_pontos"}}},
        {"id": "b", "name": "Buffer", "properties": {}},
    ]}
    stats = {
        "f1": {"node_name": "WFS", "status": "completed", "output_columns": {"output": ["gid", "uf_sigla"]}, "output_features": 84},
        "f2": {"node_name": "WFS", "status": "failed", "error": "timeout"},
        "__metrics__": {"nodes": {"f1": {"spatial": {"crs": "EPSG:4674", "bbox": [-61.6, -18.0, -50.2, -7.3], "feature_count": 84}}}},
    }
    run = SimpleNamespace(workspace_id=WS, end_time=datetime(2026, 9, 19, 12, 0))
    async with fabrica() as db:
        assert await fs.aprender_de_execucao(db, run, stats, definition, first_close=True) == 1
        await db.commit()
        fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(WS, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert fonte.origem == "aprendida" and fonte.estado == "ok" and fonte.usos == 1
        assert fonte.verificada_em == datetime(2026, 9, 19, 12, 0)
        assert fonte.propriedades == {"url": FUNAI, "typeName": "Funai:tis_poligonais", "maxFeatures": 5000}
        assert fonte.esquema == {
            "columns": [{"name": "gid", "type": None, "xsd": None, "nullable": True}, {"name": "uf_sigla", "type": None, "xsd": None, "nullable": True}],
            "columns_source": "run", "crs": "EPSG:4674", "bbox": [-61.6, -18.0, -50.2, -7.3], "feature_count": 84,
        }
        # Redelivery: does not count the use again.
        await fs.aprender_de_execucao(db, run, stats, definition, first_close=False)
        await db.commit()
        assert fonte.usos == 1


async def test_camada_lida_com_credencial_nao_entra_no_catalogo(fabrica, sem_rede):
    """Protected: the daily verification would probe it without the key, and the ready-made
    snippet would offer it to someone who has no access."""
    definition = {"nodes": [
        {"id": "f1", "name": "WFS", "properties": {"url": FUNAI, "typeName": "Funai:restrita",
                                                     "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"}},
    ]}
    stats = {"f1": {"node_name": "WFS", "status": "completed", "output_features": 3}}
    run = SimpleNamespace(workspace_id=WS, end_time=datetime(2026, 9, 19, 12, 0))
    async with fabrica() as db:
        assert await fs.aprender_de_execucao(db, run, stats, definition, first_close=True) == 0
        await db.commit()
        assert await fs.obter_por_chave(db, fs.chave_da_fonte(WS, "wfs", FUNAI, "Funai:restrita")) is None


async def test_credencial_so_em_data_properties_tambem_nao_ensina(fabrica, sem_rede):
    """The resolver and the executor read `data.properties` first; the catalog read
    `properties` first. With the credential in only one of them, the run went out
    authenticated and the protected layer entered the catalog."""
    definition = {"nodes": [
        {"id": "f1", "name": "WFS",
         "properties": {"url": FUNAI, "typeName": "Funai:restrita"},
         "data": {"properties": {"url": FUNAI, "typeName": "Funai:restrita",
                                 "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"}}},
    ]}
    stats = {"f1": {"node_name": "WFS", "status": "completed", "output_features": 3}}
    run = SimpleNamespace(workspace_id=WS, end_time=datetime(2026, 9, 19, 12, 0))
    async with fabrica() as db:
        assert await fs.aprender_de_execucao(db, run, stats, definition, first_close=True) == 0


async def test_execucao_com_filtro_ou_bbox_nao_ensina_extensao_nem_contagem(fabrica, sem_rede):
    """A question's slice (uf = 'MT', a bbox) is not the layer: its extent and
    count do not overwrite the source's. The columns still apply."""
    definition = {"nodes": [
        {"id": "f1", "name": "WFS", "properties": {"url": FUNAI, "typeName": "Funai:tis_poligonais",
                                                     "cqlFilter": "uf_sigla = 'MT'"}},
        {"id": "f2", "name": "WFS", "properties": {"url": FUNAI, "typeName": "Funai:aldeias_pontos",
                                                     "bbox": "-61.6,-18.0,-50.2,-7.3"}},
    ]}
    espacial = {"crs": "EPSG:4674", "bbox": [-61.6, -18.0, -50.2, -7.3], "feature_count": 84}
    stats = {
        "f1": {"node_name": "WFS", "status": "completed", "output_columns": {"output": ["gid", "uf_sigla"]}, "output_features": 84},
        "f2": {"node_name": "WFS", "status": "completed", "output_features": 12},
        "__metrics__": {"nodes": {"f1": {"spatial": espacial}, "f2": {"spatial": espacial}}},
    }
    run = SimpleNamespace(workspace_id=WS, end_time=datetime(2026, 9, 19, 12, 0))
    async with fabrica() as db:
        assert await fs.aprender_de_execucao(db, run, stats, definition, first_close=True) == 2
        await db.commit()
        tis = await fs.obter_por_chave(db, fs.chave_da_fonte(WS, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert tis.esquema == {
            "columns": [{"name": "gid", "type": None, "xsd": None, "nullable": True}, {"name": "uf_sigla", "type": None, "xsd": None, "nullable": True}],
            "columns_source": "run", "crs": "EPSG:4674",
        }
        assert "cqlFilter" not in tis.propriedades  # the filter belongs to the question, not to the source
        aldeias = await fs.obter_por_chave(db, fs.chave_da_fonte(WS, "wfs", FUNAI, "Funai:aldeias_pontos"))
        assert aldeias.esquema == {"crs": "EPSG:4674"}


async def test_bbox_que_chega_por_aresta_tambem_e_recorte(fabrica, sem_rede):
    """ComputeBoundingBox → WFS: the node reads `inputs["bbox_string"]` with the
    `bbox` field empty, and the run is a slice just like one with the field filled in."""
    import flow.nodes.spatial.compute_bbox  # noqa: F401 — registers the node (the edge without keys needs the descriptor)

    definition = {
        "nodes": [
            {"id": "c", "name": "ComputeBoundingBox", "properties": {}},
            {"id": "f1", "name": "WFS", "properties": {"url": FUNAI, "typeName": "Funai:tis_poligonais"}},
            {"id": "f2", "name": "WFS", "properties": {"url": FUNAI, "typeName": "Funai:aldeias_pontos"}},
            {"id": "f3", "name": "WFS", "properties": {"url": FUNAI, "typeName": "Funai:outra"}},
        ],
        "edges": [
            {"source": "c", "target": "f1", "from_key": "bbox_string"},
            {"source": "c", "target": "f2"},  # no keys: everything ComputeBoundingBox produces goes in
            {"source": "c", "target": "f3", "from_key": "minx", "to_key": "x"},  # another port: not a slice
        ],
    }
    espacial = {"crs": "EPSG:4674", "bbox": [-61.6, -18.0, -50.2, -7.3], "feature_count": 84}
    stats = {
        "c": {"node_name": "ComputeBoundingBox", "status": "completed"},
        "f1": {"node_name": "WFS", "status": "completed", "output_features": 84},
        "f2": {"node_name": "WFS", "status": "completed", "output_features": 12},
        "f3": {"node_name": "WFS", "status": "completed", "output_features": 84},
        "__metrics__": {"nodes": {"f1": {"spatial": espacial}, "f2": {"spatial": espacial}, "f3": {"spatial": espacial}}},
    }
    run = SimpleNamespace(workspace_id=WS, end_time=datetime(2026, 9, 19, 12, 0))
    async with fabrica() as db:
        assert await fs.aprender_de_execucao(db, run, stats, definition, first_close=True) == 3
        await db.commit()
        for camada in ("Funai:tis_poligonais", "Funai:aldeias_pontos"):
            fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(WS, "wfs", FUNAI, camada))
            assert fonte.esquema == {"crs": "EPSG:4674"}, camada
        outra = await fs.obter_por_chave(db, fs.chave_da_fonte(WS, "wfs", FUNAI, "Funai:outra"))
        assert outra.esquema == {"crs": "EPSG:4674", "bbox": [-61.6, -18.0, -50.2, -7.3], "feature_count": 84}


# ── Per-endpoint verification ─────────────────────────────────────────────────


async def test_verificar_endpoint_marca_todas_as_linhas_da_url_com_um_pedido(fabrica, monkeypatch):
    _rede(monkeypatch, {"GetCapabilities": CAPS_2})
    async with fabrica() as db:
        await _semear(db)
        await _upsert(db, type_name="Funai:sumida", titulo="Sumida", estado="nao_verificada")
        resumo = await fs.verificar_endpoint(db, FUNAI, "2.0.0")
        assert (resumo.ok, resumo.falhando, resumo.erro) == (2, 1, None)
        linhas = {f.type_name: f for f in (await db.execute(select(FonteDeDados).where(FonteDeDados.url == FUNAI))).scalars()}
        assert linhas["Funai:tis_poligonais"].estado == "ok"
        assert linhas["Funai:tis_poligonais"].esquema["crs"] == "EPSG:4674"
        assert linhas["Funai:tis_poligonais"].esquema["bbox"] == [-73.99, -33.75, -28.84, 5.27]
        assert "terras" in linhas["Funai:tis_poligonais"].temas
        assert linhas["Funai:aldeias_pontos"].estado == "ok" and linhas["Funai:aldeias_pontos"].ultimo_erro is None
        assert linhas["Funai:sumida"].estado == "falhando" and "não consta" in linhas["Funai:sumida"].ultimo_erro
        assert all(f.verificada_em is not None for f in linhas.values())
        # Another URL was not touched.
        outra = (await fs.buscar(db, [WS], query="queimadas"))[0][0]
        assert outra.verificada_em is None
        assert sorted(u for u, _ in await fs.endpoints_para_verificar(db)) == sorted([FUNAI, "https://geoserver.exemplo.gov.br/ows"])


async def test_endpoint_fora_do_ar_marca_tudo_falhando(fabrica, monkeypatch):
    _rede(monkeypatch, {"GetCapabilities": httpx.ReadTimeout("t")})
    async with fabrica() as db:
        await _semear(db)
        resumo = await fs.verificar_endpoint(db, FUNAI)
        assert resumo.falhando == 2 and resumo.erro == "Timeout ao conectar ao servidor WFS."
        for f in (await db.execute(select(FonteDeDados).where(FonteDeDados.url == FUNAI))).scalars():
            assert f.estado == "falhando" and "Timeout" in f.ultimo_erro


# ── Vault import ──────────────────────────────────────────────────────────────


async def test_importar_pasta_cria_reimporta_sem_escrever_atualiza_e_remove(fabrica, sem_rede, tmp_path):
    pasta = tmp_path / "vault"
    shutil.copytree(VAULT, pasta)
    async with fabrica() as db:
        resumo = await fs.importar_pasta(db, pasta)
        assert (resumo.criadas, resumo.atualizadas, resumo.iguais, resumo.removidas) == (12, 0, 0, 0)
        assert resumo.ignoradas == {"sem_endpoint_wfs": 2} and resumo.erros == []
        # The Vault synonyms made it into the search.
        assert "hotspot" in fs.sinonimos_de("focos de calor")
        fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(None, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert fonte.origem == "vault" and fonte.estado == "nao_verificada" and fonte.workspace_id is None
        assert fonte.propriedades["sortBy"] == "gid" and fonte.esquema["columns_source"] == "vault"
        assert fonte.vault_hash and fonte.busca

        # Reimporting the same folder: read-only.
        de_novo = await fs.importar_pasta(db, pasta)
        assert (de_novo.criadas, de_novo.atualizadas, de_novo.iguais) == (0, 0, 12)

        # The state the catalog learned survives an update to the note.
        fonte.estado, fonte.usos = "ok", 3
        await db.commit()
        camadas = pasta / "FUNAI" / "Camadas.md"
        camadas.write_text(
            camadas.read_text(encoding="utf-8").replace(
                "- `Funai:tis_poligonais` — Terras indígenas (poligonais)\n", "- `Funai:tis_poligonais` — TIs (poligonais)\n"
            ),
            encoding="utf-8",
        )
        atualizada = await fs.importar_pasta(db, pasta)
        assert (atualizada.atualizadas, atualizada.iguais) == (1, 11)
        await db.refresh(fonte)
        assert fonte.titulo == "TIs (poligonais)" and fonte.estado == "ok" and fonte.usos == 3

        # What disappeared from the Vault leaves the catalog (soft delete); the rest stays.
        shutil.rmtree(pasta / "IBGE")
        removida = await fs.importar_pasta(db, pasta)
        assert removida.removidas == 2 and removida.iguais == 10
        assert (await fs.buscar(db, None, query="aponds"))[1] == 0


async def test_importar_pasta_inexistente_e_por_workspace(fabrica, sem_rede):
    async with fabrica() as db:
        resumo = await fs.importar_pasta(db, "/nao/existe")
        assert resumo.erros and resumo.criadas == 0
        resumo = await fs.importar_pasta(db, VAULT / "FUNAI" and VAULT, workspace_id=WS)
        assert resumo.criadas == 12
        assert (await fs.buscar(db, None, query=None))[1] == 0  # nothing on the platform
        assert (await fs.buscar(db, [WS], query=None))[1] == 12


# ── The overflow that wiped 75 % of the catalog ──────────────────────────────
#
# In production the import died at record 6,779 with
# `StringDataRightTruncationError`: 48 of the 25,492 records in the real catalog have a
# `titulo` over 255 characters (IBGE indicators reach 276), and the
# column was `VARCHAR(255)`. Since the commit is per batch of 500, the exception took
# the whole batch down with it and aborted the rest — 6,500 records were left in the
# database and an ERROR in the log. The assistant was missing three quarters of the
# layers, silently.
#
# The fix has two layers, and these tests pin down both.


async def test_titulo_longo_nao_derruba_a_importacao(fabrica, sem_rede, tmp_path):
    """Layer 1: `titulo` became TEXT, so the text goes in whole.

    The case is the real one — 276 characters, the length of the longest title in the
    production catalog.
    """
    pasta = tmp_path / "vault"
    shutil.copytree(VAULT, pasta)
    # `.strip()` because the Vault parser trims the ends — without it the test
    # would compare against a trailing space that never reaches the database.
    comprido = ("Indicador 17.19.2 — " + "proporção de países " * 13).strip()
    assert len(comprido) > 255, "a premissa do teste caiu"

    camadas = pasta / "FUNAI" / "Camadas.md"
    camadas.write_text(
        camadas.read_text(encoding="utf-8").replace(
            "- `Funai:tis_poligonais` — Terras indígenas (poligonais)\n",
            f"- `Funai:tis_poligonais` — {comprido}\n",
        ),
        encoding="utf-8",
    )

    async with fabrica() as db:
        resumo = await fs.importar_pasta(db, pasta)
        # All 12 go in: none was taken down by the long record.
        assert (resumo.criadas, resumo.erros) == (12, [])
        fonte = await fs.obter_por_chave(db, fs.chave_da_fonte(None, "wfs", FUNAI, "Funai:tis_poligonais"))
        assert fonte.titulo == comprido, "o título tem de entrar INTEIRO, sem corte"


async def test_rotulo_longo_e_cortado_em_vez_de_derrubar_o_lote(fabrica, sem_rede, tmp_path):
    """Layer 2, for the DISPLAY fields.

    `instituicao` and `grupo` are still limited in the database. Cutting them loses the
    tail of a label — the source keeps working and keeps being found.
    Letting them overflow would lose the whole catalog, which is what used to happen.
    """
    limite = fs._limite("instituicao")
    assert limite is not None

    class _Registro:
        instituicao = "I" * (limite + 40)
        grupo = None
        titulo = "t"
        descricao = None
        temas = []
        dicas = None
        prioridade = 2
        esquema = None
        propriedades = {}
        vault_hash = "h"

    from app.core.utils.datetime_utils import utc_now_naive

    fonte = FonteDeDados(url=FUNAI, type_name="a:b", chave="k", propriedades={})
    fs._aplicar_registro(fonte, _Registro(), utc_now_naive())

    assert len(fonte.instituicao) == limite
    assert fonte.instituicao.endswith("…"), "o corte precisa ser visível"


async def test_type_name_longo_PULA_o_registro_em_vez_de_cortar(fabrica, sem_rede, tmp_path):
    """Layer 2, for the FUNCTIONAL fields — and this is where cutting would be worse.

    `type_name` goes literally into the WFS query, and `chave` derives from it.
    A truncated `type_name` is a source pointing to a nonexistent layer:
    it enters the catalog, is found by search, and only fails when someone uses it.
    Better to skip it and say why.
    """
    pasta = tmp_path / "vault"
    shutil.copytree(VAULT, pasta)
    limite = fs._limite("type_name")
    comprido = "Funai:" + ("x" * limite)

    camadas = pasta / "FUNAI" / "Camadas.md"
    camadas.write_text(
        camadas.read_text(encoding="utf-8").replace(
            "- `Funai:tis_poligonais` — Terras indígenas (poligonais)\n",
            f"- `{comprido}` — Camada de nome absurdo\n",
        ),
        encoding="utf-8",
    )

    async with fabrica() as db:
        resumo = await fs.importar_pasta(db, pasta)
        # The other 11 went in: the bad record did not take anyone down with it.
        assert resumo.criadas == 11
        assert len(resumo.erros) == 1
        assert "type_name" in resumo.erros[0] and "pulado" in resumo.erros[0]
        # And it did NOT go in truncated.
        achadas, _ = await fs.buscar(db, None, query="absurdo")
        assert achadas == []


async def test_o_limite_vem_da_COLUNA_e_nao_de_uma_constante():
    """A constant copied here would diverge the day the column changed — and
    the divergence would show up as the same overflow the guard prevents."""
    assert fs._limite("instituicao") == FonteDeDados.__table__.c["instituicao"].type.length
    # `titulo` is TEXT: no limit, and therefore outside the truncation guard.
    assert fs._limite("titulo") is None
