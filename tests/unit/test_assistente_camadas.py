"""GET /assistente/camadas/{id} and /assistente/tiles/... — layers of the Home globe.

Real database (SQLite) behind the real app; the conftest's `client` authenticates
as `usr-test-001` in workspace `ws-test-001` (via `mock_workspace_ids`). What is
asserted is the contract: MEMBER gate (403 for an artifact from another workspace),
the geojson/mvt/unavailable resolution, the CRS guard, and the tiles with a member
gate (uniform 404, `private`, no `Access-Control-Allow-Origin`).

`presigned_get_async` and `tile_mvt` are doubled: the first would talk to MinIO,
the second runs `ST_AsMVT` (PostGIS only) — neither exists in SQLite.
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
    monkeypatch.setattr(limiter, "enabled", False)  # the 60/min counts per IP across tests
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
    # bbox in native CRS is not included (the web can't frame with it).
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


# ── `baixavel`: the download button of the layers panel ──────────────────────
# It says whether `GET /artifacts/{id}/download` WOULD DELIVER the file, not
# whether there is a preview on the globe (`available`). The web hides the
# action when it is false: a live button that returns 409/404 is worse than a
# missing button.


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
    # `keepLocal`: the download responds 409 because serving the file would require
    # the server to fetch it from the executor — exactly what the flag forbids.
    await _artefato(sessao, content_location="executor", s3_key=None)
    assert (await api.get("/assistente/camadas/art-1")).json()["baixavel"] is False


@pytest.mark.asyncio
async def test_publicada_sem_arquivo_no_storage_nao_e_baixavel(api, sessao):
    # The case that motivates the field: the layer SHOWS UP on the globe (MVT,
    # content in PostGIS) and still there is no file to download. `available` and
    # `baixavel` diverge here, and only here.
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
    # Never shared across origins: it is an unpublished layer.
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
    """Two layers in the same run: match by layer_key, not by physical order.

    Without the discriminator, `.first()` without ORDER BY delivered the OTHER
    node's layer — the person asked for "rios" and the globe drew "municipios".
    """
    await _artefato(sessao, filename="rios.geojson", output_key="rios", is_published=True)
    # "municipios" goes in FIRST, so that a naive `.first()` would pick it.
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
    """The `portal_layers` row is rewritten in place on every publication.

    `portal_router._publicar` UPSERTs on `(workflow_hash, layer_key)`: the row's
    geojson, bbox, geometry_type and run_id become those of the LATEST run.
    Matching only by `layer_key` made the old run's artifact serve the tiles and
    bbox of the new run, labeled with the old artifact's name.
    """
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.presigned_get_async",
        AsyncMock(return_value="https://s3.atlans.example.org/focos.geojson?sig=abc"),
    )
    await _artefato(sessao, is_published=True)  # filename "focos.geojson", run-1
    await _metrics(sessao)                      # bbox/crs of run-1
    # Same layer_key derived from the filename, but already rewritten by a LATER
    # run — with a different bbox and a different geometry.
    sessao.add(PortalLayer(
        workflow_hash="wf-1", run_id="run-5", layer_key="focos",
        geojson_data={"type": "FeatureCollection", "features": []},
        title="Focos", bbox=[-74.0, -34.0, -34.0, 5.0], geometry_type="LineString",
    ))
    await sessao.commit()

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    # Falls back to the artifact's own GeoJSON — the correct data for that run.
    assert c["tipo"] == "geojson"
    assert c["mvt"] is None
    # And neither the bbox nor the geometry of the new run leak.
    assert c["bbox"] == [-64.0, -12.0, -60.0, -8.0]
    assert c["geometry_type"] == "Polygon"


@pytest.mark.asyncio
async def test_camada_ambigua_nao_e_adivinhada(api, sessao, monkeypatch):
    """Two layers in the run and none matching by name: does not pick silently."""
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
    # Falls back to the GeoJSON path instead of returning the wrong layer.
    assert r.json()["tipo"] == "geojson"


@pytest.mark.asyncio
async def test_no_com_varias_saidas_nao_leva_bbox_de_outra(api, sessao, monkeypatch):
    """`NodeRunMetrics` is per NODE: with two outputs, the stored bbox is the last one's."""
    monkeypatch.setattr(
        "app.api.routers.assistente_camadas_router.presigned_get_async",
        AsyncMock(return_value="https://s3.atlans.example.org/a.geojson?sig=abc"),
    )
    await _artefato(sessao, id_hash="art-1", output_key="adicionados", filename="adicionados.geojson")
    await _artefato(sessao, id_hash="art-2", output_key="removidos", filename="removidos.geojson")
    await _metrics(sessao)  # a single row for (run-1, n1)

    r = await api.get("/assistente/camadas/art-1")
    assert r.status_code == 200
    c = r.json()
    assert c["tipo"] == "geojson"          # segue desenhavel (o crs continua valendo)
    assert c["bbox"] is None               # but does not frame by another output's extent
    assert c["geometry_type"] is None      # nor label the geometry of another output


@pytest.mark.asyncio
async def test_tiles_de_fluxo_apagado_e_404(api, sessao, monkeypatch):
    """Deleting the workflow has to take the layer offline, even for whoever has the URL."""
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
