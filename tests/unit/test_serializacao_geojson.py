# tests/unit/test_serializacao_geojson.py
"""
GDF -> GeoJSON in a single place (`geo_helpers.gdf_para_geojson`).

The serialization was repeated in eight places, and the copies had diverged
in both directions:

  MUTATION  SaveGeoJSON, DataOutput, PublishMap and SendEmail's automatic
            attachment passed the GDF through `stringify_datetime_cols`, which
            replaced the datetime columns with TEXT in the object itself. And the
            object was the output of the PREVIOUS node: `get_first_gdf` returns
            the parent's and `ensure_gdf_crs` returns the same one when the CRS
            already matches. Siblings in the same batch (they run in parallel, in
            threads) and `$Alias` expressions started reading the column as a string.

  DATETIME  SaveToS3, SendWebhook, HttpRequest (POST with the GDF in the body) and
            the pin's GeoJSON fallback called `to_json` directly, which fails with
            "Object of type Timestamp is not JSON serializable".

And the text the already working nodes produced must not change: it is still
`astype(str)` on the datetime columns, only on a copy.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from geopandas.testing import assert_geodataframe_equal
from shapely.geometry import Point

RAIZ = Path(__file__).resolve().parents[2]


def _gdf_com_datas() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "id": [1, 2],
            "nome": ["Sé", "b"],
            "quando": pd.to_datetime(["2024-01-01 10:00", None]),
            "utc": pd.to_datetime(["2024-03-05 12:30", "2024-03-06 00:00"]).tz_localize("UTC"),
        },
        geometry=[Point(-46.6, -23.5), Point(-43.2, -22.9)],
        crs="EPSG:4326",
    )


# The text SaveGeoJSON/DataOutput/PublishMap/SendEmail already produced for the
# GDF above (old path: ensure_gdf_crs + in-place astype(str) + to_json).
# NaT becomes "NaT" and the time zone stays in the text — that is the contract
# whoever consumes the file already knows.
GEOJSON_ESPERADO = (
    '{"type": "FeatureCollection", "features": ['
    '{"id": "0", "type": "Feature", "properties": {"id": 1, "nome": "S\\u00e9", '
    '"quando": "2024-01-01 10:00:00", "utc": "2024-03-05 12:30:00+00:00"}, '
    '"geometry": {"type": "Point", "coordinates": [-46.6, -23.5]}}, '
    '{"id": "1", "type": "Feature", "properties": {"id": 2, "nome": "b", '
    '"quando": "NaT", "utc": "2024-03-06 00:00:00+00:00"}, '
    '"geometry": {"type": "Point", "coordinates": [-43.2, -22.9]}}]}'
)

# The four places that serialized with raw `to_json` (SaveToS3, SendWebhook,
# HttpRequest, pin fallback) deliver the missing date as `null` — that is what
# already came out for an all-empty date column, the only one raw `to_json` accepted.
GEOJSON_ESPERADO_NULO = GEOJSON_ESPERADO.replace('"quando": "NaT"', '"quando": null')


@pytest.fixture(autouse=True)
def _servidor_como_localidade(monkeypatch):
    """Sending machine: the output nodes follow the normal upload path."""
    monkeypatch.delenv("EXECUTOR_SYNC_MODE", raising=False)


# ── The four nodes that converted datetime (and mutated the parent's GDF) ────

async def _save_geojson(gdf) -> str:
    from flow.nodes.outputs.save_geojson import SaveGeoJSON

    no = SaveGeoJSON("n1", {"label": "saida", "crs": "EPSG:4326"})
    no._workspace_id, no._task_id = "ws-1", "task-1"
    capturado: dict = {}

    def _persistir(**kwargs):
        capturado.update(kwargs)
        return "k", {}

    with patch("flow.nodes.outputs.save_geojson.persistir_artefato", side_effect=_persistir):
        await no.execute({"pai": gdf})
    return capturado["content"].decode("utf-8")


async def _data_output(gdf) -> str:
    from flow.nodes.outputs.data_output import DataOutput

    no = DataOutput("n1", {"label": "saida"})
    no._workspace_id, no._task_id = "ws-1", "task-1"
    capturado: dict = {}

    def _upload(**kwargs):
        capturado.update(kwargs)
        return "k", {}

    with patch("flow.nodes.outputs.data_output.upload_artifact_to_minio", side_effect=_upload):
        await no.execute({"pai": gdf})
    return capturado["content"].decode("utf-8")


async def _publish_map(gdf) -> str:
    from flow.nodes.outputs.publish_map import PublishMap

    no = PublishMap("n1", {"title": "Camada"})
    no._workspace_id, no._task_id, no._workflow_hash = "ws-1", "task-1", "wf-1"
    publicar = AsyncMock(return_value="layer-1")
    with patch.object(PublishMap, "_publish_to_api", publicar):
        await no.execute({"pai": gdf})
    return publicar.await_args.kwargs["geojson_str"]


async def _send_email_anexo(gdf) -> str:
    from flow.nodes.outputs.send_email import SendEmailNode

    no = SendEmailNode("n1", {"artifactLabel": "saida", "artifactFormat": "geojson"})
    no._workspace_id, no._task_id = "ws-1", "task-1"
    capturado: dict = {}

    def _upload(**kwargs):
        capturado.update(kwargs)
        return "k", {}

    with patch("flow.utils.artifact_helpers.upload_artifact_to_minio", side_effect=_upload):
        await no._auto_save_artifact({"pai": gdf})
    return capturado["content"].decode("utf-8")


NOS_QUE_CONVERTIAM = pytest.mark.parametrize(
    "rodar",
    [_save_geojson, _data_output, _publish_map, _send_email_anexo],
    ids=["SaveGeoJSON", "DataOutput", "PublishMap", "SendEmail-anexo"],
)


@NOS_QUE_CONVERTIAM
async def test_no_de_saida_nao_altera_o_gdf_do_no_anterior(rodar):
    """The input GDF is the parent's output, which siblings and `$Alias` still read."""
    gdf = _gdf_com_datas()
    intacto = gdf.copy()

    await rodar(gdf)

    assert str(gdf["quando"].dtype) == "datetime64[ns]", (
        "a coluna datetime do no anterior virou texto depois do no de saida"
    )
    assert_geodataframe_equal(gdf, intacto)


@NOS_QUE_CONVERTIAM
async def test_texto_geojson_dos_nos_que_ja_funcionavam_nao_muda(rodar):
    assert await rodar(_gdf_com_datas()) == GEOJSON_ESPERADO


# ── The four places that did not handle datetime ─────────────────────────────

async def test_save_to_s3_serializa_gdf_com_datetime():
    from flow.nodes.outputs.save_to_s3 import SaveToS3Node

    no = SaveToS3Node("n1", {"key": "saida/a.geojson", "bucketName": "bucket"})
    enviado: dict = {}

    def _upload(json_str, bucket, key, **_kwargs):
        enviado["json"] = json_str

    gdf = _gdf_com_datas()
    with patch("flow.nodes.outputs.save_to_s3._upload_to_s3", side_effect=_upload):
        await no.execute({"pai": gdf})

    assert enviado["json"] == GEOJSON_ESPERADO_NULO
    assert str(gdf["quando"].dtype) == "datetime64[ns]"


async def test_send_webhook_serializa_gdf_com_datetime():
    from flow.nodes.outputs.send_webhook import SendWebhookNode

    no = SendWebhookNode("n1", {"url": "http://hook.example.com", "method": "POST"})
    enviar = AsyncMock(return_value=MagicMock(status_code=200))
    gdf = _gdf_com_datas()
    with patch("flow.nodes.outputs.send_webhook.safe_httpx_request", new=enviar):
        await no.execute({"pai": gdf})

    assert enviar.await_args.kwargs["json"]["data"] == json.loads(GEOJSON_ESPERADO_NULO)
    assert str(gdf["quando"].dtype) == "datetime64[ns]"


async def test_http_request_post_serializa_gdf_com_datetime():
    from flow.nodes.action.http_request import HttpRequestNode

    no = HttpRequestNode("n1", {"url": "https://api.exemplo.com/x", "method": "POST"})
    resposta = MagicMock(status_code=200, headers={}, is_redirect=False)
    resposta.json.return_value = {"ok": True}
    enviar = AsyncMock(return_value=resposta)
    gdf = _gdf_com_datas()
    with patch("flow.nodes.action.http_request.safe_httpx_request", new=enviar):
        await no.execute({"pai": gdf})

    assert enviar.await_args.kwargs["json"] == json.loads(GEOJSON_ESPERADO_NULO)
    assert str(gdf["quando"].dtype) == "datetime64[ns]"


def test_pin_fallback_geojson_serializa_gdf_com_datetime(monkeypatch):
    """The pin's GeoJSON is plan B when Parquet fails — and it failed along with it."""
    from flow.executor import pin

    def _parquet_falha(self, *args, **kwargs):
        raise ValueError("parquet indisponivel")

    enviado: dict = {}
    monkeypatch.setattr(gpd.GeoDataFrame, "to_parquet", _parquet_falha)
    monkeypatch.setattr(
        pin, "upload_pin_to_minio",
        lambda content, s3_key, content_type: enviado.update(content=content),
    )
    gdf = _gdf_com_datas()

    ref = pin.upload_pin_artifact("n1", {"output": gdf}, "ws-1", "task-1")

    assert ref["__pin_format__"] == "geojson"
    assert enviado["content"].decode("utf-8") == GEOJSON_ESPERADO_NULO
    assert str(gdf["quando"].dtype) == "datetime64[ns]"


def _gdf_data_toda_vazia() -> gpd.GeoDataFrame:
    """A DateTime field with no value in any feature (`dt_cancelamento` with only
    active features), read as an all-NaT datetime64."""
    return gpd.GeoDataFrame(
        {"id": [1, 2], "dt_cancelamento": pd.to_datetime([None, None]).astype("datetime64[ms]")},
        geometry=[Point(-46.6, -23.5), Point(-43.2, -22.9)],
        crs="EPSG:4326",
    )


def test_coluna_de_data_toda_vazia_segue_null_onde_o_to_json_era_cru():
    """SaveToS3, SendWebhook, HttpRequest and the pin already serialized this column
    (raw `to_json` accepts NaT) — as `null`. A daily workflow that used to work
    must not start sending "NaT"."""
    from flow.utils.geo_helpers import gdf_para_geojson

    gdf = _gdf_data_toda_vazia()
    antes = gdf.to_json()
    assert gdf_para_geojson(gdf, nat_como_nulo=True) == antes
    assert json.loads(antes)["features"][0]["properties"]["dt_cancelamento"] is None


async def test_save_to_s3_mantem_null_na_coluna_de_data_toda_vazia():
    from flow.nodes.outputs.save_to_s3 import SaveToS3Node

    no = SaveToS3Node("n1", {"key": "saida/a.geojson", "bucketName": "bucket"})
    enviado: dict = {}
    gdf = _gdf_data_toda_vazia()
    with patch("flow.nodes.outputs.save_to_s3._upload_to_s3",
               side_effect=lambda json_str, *a, **k: enviado.update(json=json_str)):
        await no.execute({"pai": gdf})
    assert enviado["json"] == gdf.to_json()


def test_quem_ja_convertia_segue_gravando_nat():
    """SaveGeoJSON, DataOutput, PublishMap e SendEmail sempre gravaram "NaT"."""
    from flow.utils.geo_helpers import gdf_para_geojson

    propriedades = json.loads(gdf_para_geojson(_gdf_data_toda_vazia()))["features"][0]["properties"]
    assert propriedades["dt_cancelamento"] == "NaT"


# ── O helper ─────────────────────────────────────────────────────────────────

def test_helper_sem_datetime_e_o_to_json_de_sempre():
    from flow.utils.geo_helpers import gdf_para_geojson

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(1, 2)], crs="EPSG:4326")
    assert gdf_para_geojson(gdf) == gdf.to_json()


def test_helper_sem_crs_de_destino_nao_reprojeta():
    from flow.utils.geo_helpers import gdf_para_geojson

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(500000, 7000000)], crs="EPSG:31983")
    coordenadas = json.loads(gdf_para_geojson(gdf))["features"][0]["geometry"]["coordinates"]
    assert coordenadas == [500000.0, 7000000.0]


def test_helper_reprojeta_numa_copia():
    from flow.utils.geo_helpers import gdf_para_geojson

    gdf = gpd.GeoDataFrame(
        {"quando": pd.to_datetime(["2024-01-01 10:00"])},
        geometry=[Point(500000, 7000000)], crs="EPSG:31983",
    )
    intacto = gdf.copy()

    feicao = json.loads(gdf_para_geojson(gdf, "EPSG:4326"))["features"][0]

    lon, lat = feicao["geometry"]["coordinates"]
    assert -46 < lon < -44 and -28 < lat < -26  # UTM 23S -> graus
    assert feicao["properties"]["quando"] == "2024-01-01 10:00:00"
    assert_geodataframe_equal(gdf, intacto)


def test_helper_atribui_o_crs_a_gdf_sem_crs():
    """Same rule as `ensure_gdf_crs`: without a CRS, the target one is assigned."""
    from flow.utils.geo_helpers import gdf_para_geojson

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-46.6, -23.5)])
    coordenadas = json.loads(gdf_para_geojson(gdf, "EPSG:4326"))["features"][0]["geometry"]["coordinates"]
    assert coordenadas == [-46.6, -23.5]
    assert gdf.crs is None


# ── A single copy ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("arquivo", [
    "flow/nodes/outputs/save_geojson.py",
    "flow/nodes/outputs/data_output.py",
    "flow/nodes/outputs/publish_map.py",
    "flow/nodes/outputs/send_email.py",
    "flow/nodes/outputs/save_to_s3.py",
    "flow/nodes/outputs/send_webhook.py",
    "flow/nodes/action/http_request.py",
])
def test_no_serializa_pelo_helper(arquivo):
    fonte = (RAIZ / arquivo).read_text(encoding="utf-8")
    assert "gdf_para_geojson" in fonte, f"{arquivo} deixou de usar o helper"
    assert ".to_json" not in fonte, f"{arquivo} voltou a chamar to_json direto"


def test_conversao_in_place_nao_voltou():
    fonte = (RAIZ / "flow/utils/geo_helpers.py").read_text(encoding="utf-8")
    assert "def stringify_datetime_cols" not in fonte
