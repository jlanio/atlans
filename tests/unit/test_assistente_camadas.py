"""GET /assistente/camadas/{id} e /assistente/tiles/... — camadas do globo da Home.

Banco real (SQLite) atras da app real; o `client` do conftest autentica como
`usr-test-001` no workspace `ws-test-001` (via `mock_workspace_ids`). O que se
afirma e o contrato: portao de MEMBRO (403 para artefato de outro workspace),
a resolucao geojson/mvt/indisponivel, a guarda de CRS, e os tiles com portao de
membro (404 uniforme, `private`, sem `Access-Control-Allow-Origin`).

`presigned_get_async` e `tile_mvt` sao dublados: o primeiro falaria com o MinIO,
o segundo roda `ST_AsMVT` (so PostGIS) — nenhum dos dois existe no SQLite.
"""
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.rate_limiter import limiter
from app.models.artifact import Artifact
from app.models.base import Base
from app.models.models import Workflow
from app.models.portal_layer import PortalLayer
from app.models.run_metrics import NodeRunMetrics

TABELAS = [
    Artifact.__table__, Workflow.__table__,
    PortalLayer.__table__, NodeRunMetrics.__table__,
]
MEU_WS = "ws-test-001"       # o mock_workspace_ids do conftest
OUTRO_WS = "ws-outro"


@pytest_asyncio.fixture
async def sessao():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def api(client, sessao, monkeypatch):
    from app.api.dependencies import get_db
    from app.main import app

    async def _db():
        yield sessao

    app.dependency_overrides[get_db] = _db
    monkeypatch.setattr(limiter, "enabled", False)  # o 60/min conta por IP entre testes
    yield client
    app.dependency_overrides.pop(get_db, None)


async def _artefato(sessao, **campos):
    base = dict(
        id_hash="art-1", workspace_id=MEU_WS, workflow_hash="wf-1",
        run_id="run-1", node_id="n1", output_key="saida",
        filename="focos.geojson", format="geojson", content_location="minio",
        s3_key="drive/focos.geojson",
    )
    base.update(campos)
    art = Artifact(**base)
    sessao.add(art)
    await sessao.commit()
    return art


async def _metrics(sessao, *, crs="EPSG:4326", run_id="run-1", node_id="n1"):
    sessao.add(NodeRunMetrics(
        run_id=run_id, node_id=node_id, node_name="SaveGeoJSON", status="success",
        geometry_type="Polygon", crs=crs, bbox=[-64.0, -12.0, -60.0, -8.0],
    ))
    await sessao.commit()


# ── GET /assistente/camadas/{id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_membro_recebe_geojson_com_bbox_e_url(api, sessao, monkeypatch):
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.presigned_get_async",
        AsyncMock(return_value="https://s3.atlans.example.org/focos.geojson?sig=abc"),
    )
    await _artefato(sessao)
    await _metrics(sessao)

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    assert c["tipo"] == "geojson"
    assert c["available"] is True
    assert c["download_url"].startswith("https://s3.atlans.example.org/")
    assert c["url_expires_in"] == 900
    assert c["bbox"] == [-64.0, -12.0, -60.0, -8.0]
    assert c["crs"] == "EPSG:4326"
    assert c["geometry_type"] == "Polygon"


@pytest.mark.asyncio
async def test_artefato_de_outro_workspace_e_403(api, sessao):
    await _artefato(sessao, workspace_id=OUTRO_WS)
    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_inexistente_e_404(api, sessao):
    r = await api.get("/assistente/camadas/nao-existe")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_executor_local_e_indisponivel_com_hint(api, sessao):
    await _artefato(sessao, content_location="executor", s3_key=None)
    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    assert c["tipo"] == "indisponivel"
    assert c["available"] is False
    assert "executor" in c["hint"].lower()


@pytest.mark.asyncio
async def test_crs_diferente_de_4326_e_indisponivel(api, sessao):
    await _artefato(sessao)
    await _metrics(sessao, crs="EPSG:31982")  # SIRGAS 2000 / UTM 22S
    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    assert c["tipo"] == "indisponivel"
    assert "4326" in c["hint"]
    # bbox em CRS nativo nao acompanha (a web nao enquadra com ele).
    assert c["bbox"] is None


@pytest.mark.asyncio
async def test_publicado_vira_mvt(api, sessao):
    await _artefato(sessao, is_published=True)
    sessao.add(PortalLayer(
        workflow_hash="wf-1", run_id="run-1", layer_key="camada_focos",
        geojson_data={"type": "FeatureCollection", "features": []},
        title="Focos", bbox=[-64.0, -12.0, -60.0, -8.0], geometry_type="Point",
    ))
    await sessao.commit()

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    assert c["tipo"] == "mvt"
    assert c["available"] is True
    assert c["mvt"] == {"workflow_id": "wf-1", "layer_key": "camada_focos"}


@pytest.mark.asyncio
async def test_formato_nao_geojson_sem_publicacao_e_indisponivel(api, sessao):
    await _artefato(sessao, format="shapefile", filename="focos.zip", s3_key="drive/focos.zip")
    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    assert r.json()["tipo"] == "indisponivel"


# ── `baixavel`: o botao de baixar do painel de camadas ───────────────────────
# Ele diz se `GET /artifacts/{id}/download` ENTREGARIA o arquivo, e nao se ha
# previa no globo (`available`). A web esconde a acao quando e falso: um botao
# vivo que devolve 409/404 e pior que um botao ausente.


@pytest.mark.asyncio
async def test_geojson_no_storage_e_baixavel(api, sessao, monkeypatch):
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.presigned_get_async",
        AsyncMock(return_value="https://s3.atlans.example.org/focos.geojson?sig=abc"),
    )
    await _artefato(sessao)
    await _metrics(sessao)
    assert (await api.get("/assistente/camadas/art-1")).json()["baixavel"] is True


@pytest.mark.asyncio
async def test_executor_local_nao_e_baixavel(api, sessao):
    # `keepLocal`: o download responde 409 porque servir o arquivo exigiria que o
    # servidor o buscasse no executor — exatamente o que a marcacao proibe.
    await _artefato(sessao, content_location="executor", s3_key=None)
    assert (await api.get("/assistente/camadas/art-1")).json()["baixavel"] is False


@pytest.mark.asyncio
async def test_publicada_sem_arquivo_no_storage_nao_e_baixavel(api, sessao):
    # O caso que motiva o campo: a camada APARECE no globo (MVT, conteudo no
    # PostGIS) e mesmo assim nao ha arquivo para baixar. `available` e `baixavel`
    # divergem aqui, e so aqui.
    await _artefato(sessao, is_published=True, s3_key=None)
    sessao.add(PortalLayer(
        workflow_hash="wf-1", run_id="run-1", layer_key="camada_focos",
        geojson_data={"type": "FeatureCollection", "features": []},
        title="Focos", bbox=[-64.0, -12.0, -60.0, -8.0], geometry_type="Point",
    ))
    await sessao.commit()

    c = (await api.get("/assistente/camadas/art-1")).json()
    assert c["tipo"] == "mvt"
    assert c["available"] is True
    assert c["baixavel"] is False


# ── GET /assistente/tiles/{wf}/{layer}/{z}/{x}/{y}.pbf ───────────────────────────


async def _com_camada(sessao, *, workspace_id=MEU_WS):
    sessao.add(Workflow(
        id_hash="wf-1", name="Fluxo", workspace_id=workspace_id,
        definition={"nodes": [], "edges": []}, flag_ative=True,
    ))
    sessao.add(PortalLayer(
        workflow_hash="wf-1", layer_key="camada_focos",
        geojson_data={"type": "FeatureCollection", "features": []}, title="Focos",
    ))
    await sessao.commit()


@pytest.mark.asyncio
async def test_tiles_de_outro_workspace_e_404(api, sessao):
    await _com_camada(sessao, workspace_id=OUTRO_WS)
    r = await api.get("/assistente/tiles/wf-1/camada_focos/5/10/12.pbf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tiles_sem_camada_e_404(api, sessao):
    sessao.add(Workflow(
        id_hash="wf-1", name="Fluxo", workspace_id=MEU_WS,
        definition={"nodes": [], "edges": []}, flag_ative=True,
    ))
    await sessao.commit()
    r = await api.get("/assistente/tiles/wf-1/inexistente/5/10/12.pbf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tiles_do_membro_200_protobuf_private_sem_cors(api, sessao, monkeypatch):
    await _com_camada(sessao)
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.tile_mvt",
        AsyncMock(return_value=b"\x1a\x0bprotobuf-mvt"),
    )
    r = await api.get("/assistente/tiles/wf-1/camada_focos/5/10/12.pbf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/x-protobuf"
    assert r.headers["cache-control"] == "private, max-age=300"
    # Nunca compartilha entre origens: e camada nao-publicada.
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


@pytest.mark.asyncio
async def test_tiles_vazio_e_204(api, sessao, monkeypatch):
    await _com_camada(sessao)
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.tile_mvt",
        AsyncMock(return_value=None),
    )
    r = await api.get("/assistente/tiles/wf-1/camada_focos/5/10/12.pbf")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_run_com_dois_publishmap_devolve_a_camada_do_artefato_pedido(api, sessao):
    """Duas camadas na mesma execucao: casa pelo layer_key, nao pela ordem fisica.

    Sem o discriminador, `.first()` sem ORDER BY entregava a camada do OUTRO no —
    a pessoa pedia "rios" e o globo desenhava "municipios".
    """
    await _artefato(sessao, filename="rios.geojson", output_key="rios", is_published=True)
    # "municipios" entra PRIMEIRO, para que um `.first()` ingenuo a escolhesse.
    sessao.add(PortalLayer(
        workflow_hash="wf-1", run_id="run-1", layer_key="municipios",
        geojson_data={"type": "FeatureCollection", "features": []},
        title="Municipios", bbox=[-74.0, -34.0, -34.0, 5.0], geometry_type="Polygon",
    ))
    sessao.add(PortalLayer(
        workflow_hash="wf-1", run_id="run-1", layer_key="rios",
        geojson_data={"type": "FeatureCollection", "features": []},
        title="Rios", bbox=[-64.0, -12.0, -60.0, -8.0], geometry_type="LineString",
    ))
    await sessao.commit()

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    assert c["tipo"] == "mvt"
    assert c["mvt"]["layer_key"] == "rios"
    assert c["bbox"] == [-64.0, -12.0, -60.0, -8.0]
    assert c["geometry_type"] == "LineString"


@pytest.mark.asyncio
async def test_republicacao_em_outro_run_nao_serve_a_camada_nova(api, sessao, monkeypatch):
    """A linha de `portal_layers` e reescrita in place a cada publicacao.

    `portal_router._publicar` faz UPSERT em `(workflow_hash, layer_key)`: geojson,
    bbox, geometry_type e run_id da linha passam a ser os da ULTIMA execucao.
    Casar so pelo `layer_key` fazia o artefato da execucao antiga servir os tiles
    e a bbox da execucao nova, rotulados com o nome do artefato antigo.
    """
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.presigned_get_async",
        AsyncMock(return_value="https://s3.atlans.example.org/focos.geojson?sig=abc"),
    )
    await _artefato(sessao, is_published=True)  # filename "focos.geojson", run-1
    await _metrics(sessao)                      # bbox/crs do run-1
    # Mesma layer_key derivada do filename, mas ja reescrita por uma execucao
    # POSTERIOR — com outra bbox e outra geometria.
    sessao.add(PortalLayer(
        workflow_hash="wf-1", run_id="run-5", layer_key="focos",
        geojson_data={"type": "FeatureCollection", "features": []},
        title="Focos", bbox=[-74.0, -34.0, -34.0, 5.0], geometry_type="LineString",
    ))
    await sessao.commit()

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    # Cai para o GeoJSON do proprio artefato — o dado correto daquele run.
    assert c["tipo"] == "geojson"
    assert c["mvt"] is None
    # E nem a bbox nem a geometria da execucao nova vazam.
    assert c["bbox"] == [-64.0, -12.0, -60.0, -8.0]
    assert c["geometry_type"] == "Polygon"


@pytest.mark.asyncio
async def test_camada_ambigua_nao_e_adivinhada(api, sessao, monkeypatch):
    """Duas camadas no run e nenhuma casando pelo nome: nao escolhe em silencio."""
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.presigned_get_async",
        AsyncMock(return_value="https://s3.atlans.example.org/focos.geojson?sig=abc"),
    )
    await _artefato(sessao, is_published=True)  # filename "focos.geojson"
    for chave in ("alfa", "beta"):
        sessao.add(PortalLayer(
            workflow_hash="wf-1", run_id="run-1", layer_key=chave,
            geojson_data={"type": "FeatureCollection", "features": []}, title=chave,
        ))
    await sessao.commit()

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    # Cai para o caminho GeoJSON em vez de devolver a camada errada.
    assert r.json()["tipo"] == "geojson"


@pytest.mark.asyncio
async def test_no_com_varias_saidas_nao_leva_bbox_de_outra(api, sessao, monkeypatch):
    """`NodeRunMetrics` e por NO: com duas saidas, o bbox gravado e o da ultima."""
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.presigned_get_async",
        AsyncMock(return_value="https://s3.atlans.example.org/a.geojson?sig=abc"),
    )
    await _artefato(sessao, id_hash="art-1", output_key="adicionados", filename="adicionados.geojson")
    await _artefato(sessao, id_hash="art-2", output_key="removidos", filename="removidos.geojson")
    await _metrics(sessao)  # uma unica linha para (run-1, n1)

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    assert c["tipo"] == "geojson"          # segue desenhavel (o crs continua valendo)
    assert c["bbox"] is None               # mas nao enquadra pela extensao de outra saida
    assert c["geometry_type"] is None      # nem rotula a geometria de outra saida


@pytest.mark.asyncio
async def test_tiles_de_fluxo_apagado_e_404(api, sessao, monkeypatch):
    """Apagar o fluxo tem de tirar a camada do ar, mesmo para quem tem a URL."""
    from app.core.utils.datetime_utils import utc_now_naive

    await _com_camada(sessao)
    wf = (
        await sessao.execute(select(Workflow).where(Workflow.id_hash == "wf-1"))
    ).scalar_one()
    wf.deleted_at = utc_now_naive()
    await sessao.commit()
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.tile_mvt",
        AsyncMock(return_value=b"\x1a\x0bprotobuf-mvt"),
    )

    r = await api.get("/assistente/tiles/wf-1/camada_focos/5/10/12.pbf")
    assert r.status_code == 404
