# tests/unit/test_pin_varias_camadas.py
"""
A pinned node with more than one DataFrame output gets every one of them back.

The pin stored only the FIRST DataFrame of the output as an object in storage.
Every other value went into the ref's `__pin_extra__`, and a second DataFrame
went in as the raw object: `json.dumps(v, default=str)` "succeeds" for anything,
so nothing complained. On the way to the server the WebSocket serializer
turned it into the text "<DataFrame RxC>", that text was persisted in
`workflows.pinned_outputs`, and the next pinned run delivered it in place of
the layer. RemoveDuplicates (`removed`), FilterByGeometryType (`lines`,
`polygons`, `other`) and FileTrigger (`file_b`) are nodes whose second output
came back as a string.

The trip below is the real one: the executor writes the ref, `_dumps_result`
serializes it onto the WebSocket, the consumer rewrites it (`_safe_pin_ref`,
which derives every object name on its own) and the next run downloads what
the server stored. Only MinIO and the presign HTTP calls are fakes.
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from geopandas.testing import assert_geodataframe_equal
from pandas.testing import assert_frame_equal
from shapely.geometry import LineString, Point

from flow.executor import pin
from flow.executor.core import WorkflowExecutor
from flow.nodes.base import BaseNode

WS = "ws-alvo"
TASK = "task-atual"


class _Resposta:
    def __init__(self, dados: dict | None = None, conteudo: bytes | None = None, erro: bool = False):
        self._dados, self.content, self._erro = dados, conteudo, erro

    def raise_for_status(self):
        if self._erro:
            raise RuntimeError("404 Not Found")

    def json(self):
        return self._dados


class _MinIO:
    """The bucket in memory: what `upload_pin_to_minio` writes, the presigned GET reads."""

    def __init__(self):
        self.objetos: dict[str, bytes] = {}

    def upload(self, content, s3_key, content_type):
        # Parquet arrives as the path of a temporary file, which the real
        # function reads and removes.
        if isinstance(content, str):
            with open(content, "rb") as f:
                dados = f.read()
            os.unlink(content)
            content = dados
        self.objetos[s3_key] = content

    def post(self, url, json=None, **kwargs):
        return _Resposta(dados={"download_url": f"memoria://{json['s3_key']}"})

    def get(self, url, **kwargs):
        chave = url.removeprefix("memoria://")
        if chave not in self.objetos:
            return _Resposta(erro=True)
        return _Resposta(conteudo=self.objetos[chave])


@pytest.fixture
def minio(monkeypatch):
    import httpx

    falso = _MinIO()
    monkeypatch.setattr(pin, "upload_pin_to_minio", falso.upload)
    monkeypatch.setattr(httpx, "post", falso.post)
    monkeypatch.setattr(httpx, "get", falso.get)
    # Local server: `get_agent_http_config` does not look for the mTLS certificate.
    monkeypatch.setenv("EXECUTOR_SERVER_URL", "http://localhost:8000")
    return falso


def _gdf(n: int, crs: str = "EPSG:4674") -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"id": list(range(n)), "nome": [f"f{i}" for i in range(n)]},
        geometry=[Point(-56.0 + i, -15.0 - i) for i in range(n)],
        crs=crs,
    )


def _saidas() -> dict:
    """What RemoveDuplicates/FilterByGeometryType return, plus a plain table."""
    linhas = gpd.GeoDataFrame(
        {"id": [7, 8]},
        geometry=[LineString([(0, 0), (1, 1)]), LineString([(2, 2), (3, 5)])],
        crs="EPSG:31982",
    )
    return {
        "output": _gdf(3),
        "removed": linhas,
        "tabela": pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}),
        "other": _gdf(3).iloc[0:0],   # empty: FilterByGeometryType's usual case
        "removed_count": 2,
    }


def _ida_e_volta(nid: str, ref: dict) -> dict:
    """The ref the NEXT run receives: executor -> WebSocket -> consumer -> database -> dispatch."""
    from app.core import run_result_consumer as rrc
    from executor.connection import _dumps_result

    recebido = json.loads(_dumps_result({"stats": {"__updated_pinned_outputs__": {nid: ref}}}))
    run = SimpleNamespace(workspace_id=WS, task_id=TASK)
    gravado = rrc._safe_pin_ref(run, nid, recebido["stats"]["__updated_pinned_outputs__"][nid])
    assert gravado is not None, "o servidor recusou um pin legítimo"
    return json.loads(json.dumps(gravado))


def test_todas_as_camadas_voltam_do_pin_com_o_tipo_e_o_conteudo(minio):
    saidas = _saidas()

    ref = _ida_e_volta("n1", pin.upload_pin_artifact("n1", saidas, WS, TASK))
    de_volta = pin.download_pin_artifact(ref)

    assert list(de_volta) == list(saidas)
    em_texto = {k: v for k, v in de_volta.items() if isinstance(v, str)}
    assert not em_texto, f"camadas que voltaram como texto: {em_texto}"
    assert_geodataframe_equal(de_volta["output"], saidas["output"])
    assert_geodataframe_equal(de_volta["removed"], saidas["removed"])
    assert_frame_equal(de_volta["tabela"], saidas["tabela"])
    assert_geodataframe_equal(de_volta["other"], saidas["other"])
    assert de_volta["removed_count"] == 2


class _Destino(BaseNode):
    recebido: dict = {}

    @classmethod
    def description(cls):
        return {"name": "TestePinDestino", "type": "action", "properties": [],
                "outputs": [{"name": "output", "type": "any"}]}

    async def execute(self, inputs):
        _Destino.recebido = dict(inputs)
        return {"output": len(inputs)}


@pytest.fixture
def destino():
    from flow.registry import NODE_REGISTRY

    NODE_REGISTRY["TestePinDestino"] = _Destino
    _Destino.recebido = {}
    try:
        yield _Destino
    finally:
        NODE_REGISTRY.pop("TestePinDestino", None)


def test_aresta_da_segunda_camada_de_um_no_fixado_entrega_a_camada(minio, destino):
    """The defect as the user sees it: RemoveDuplicates pinned, an edge out of
    `removed`. The run that writes the pin delivers the layer; the next one, served
    from the pin, delivered the text "<DataFrame 1x2>" to the target."""
    definition = {
        "nodes": [
            {"id": "T", "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}},
            {"id": "rd", "type": "action", "name": "RemoveDuplicates", "properties": {}},
            {"id": "D", "type": "action", "name": "TestePinDestino", "properties": {}},
        ],
        "edges": [
            {"source": "T", "target": "rd"},
            {"source": "rd", "target": "D", "from_key": "removed", "to_key": "removidos"},
        ],
    }
    camada = gpd.GeoDataFrame(
        {"nome": ["a", "a", "b"]},
        geometry=[Point(0, 0), Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    metadata = {"rd": {"pinned_at": "2026-01-01T00:00:00"}}

    def _rodar(task_id, pinned):
        ex = WorkflowExecutor(definition, task_id=task_id, publisher=MagicMock(),
                              workspace_id=WS, pinned_outputs=pinned, pin_metadata=metadata)
        asyncio.run(ex.run(initial_inputs={"T": {"output": camada}}))
        return ex

    gravou = _rodar(TASK, {"rd": {}})
    ref = _ida_e_volta("rd", gravou.updated_pin_refs["rd"])
    destino.recebido = {}
    fixado = _rodar("task-seguinte", {"rd": ref})

    assert fixado.node_stats["rd"]["status"] == "pinned"
    removidos = destino.recebido["removidos"]
    assert isinstance(removidos, gpd.GeoDataFrame), removidos
    assert_geodataframe_equal(removidos, camada.iloc[[1]].reset_index(drop=True))


def test_a_ref_que_vai_ao_servidor_nao_carrega_objeto_cru(minio, caplog):
    """Whatever is not JSON is converted HERE, the way the WebSocket would — so the
    value stored for a date or a numpy integer is the same one stored before. What
    can only become text says so in the log, once per output."""
    saidas = {
        **_saidas(),
        "quando": datetime(2026, 1, 2, 3, 4, 5),
        "soma": np.int64(5),
        "pontos": [Point(0, 0), Point(1, 2)],
    }

    with caplog.at_level(logging.WARNING, logger=pin.logger.name):
        ref = pin.upload_pin_artifact("n1", saidas, WS, TASK)

    json.dumps(ref)   # no `default`: a raw object anywhere in the ref raises here
    assert ref["__pin_extra__"] == {
        "removed_count": 2,
        "quando": "2026-01-02T03:04:05",
        "soma": 5,
        "pontos": ["POINT (0 0)", "POINT (1 2)"],
    }
    avisos = [r.getMessage() for r in caplog.records if "sem forma JSON" in r.getMessage()]
    assert len(avisos) == 1 and "'pontos'" in avisos[0], avisos


def test_saidas_que_sanitizam_para_o_mesmo_texto_tem_objetos_distintos(minio):
    """'área'/'area' and 'a b'/'a_b' become the same text once reduced to an
    S3-safe name. A name taken from the sanitized text alone would make the
    second layer overwrite the first one in storage."""
    saidas = {"output": _gdf(1), "área": _gdf(2), "area": _gdf(3), "a b": _gdf(4), "a_b": _gdf(5)}

    ref = _ida_e_volta("n1", pin.upload_pin_artifact("n1", saidas, WS, TASK))
    de_volta = pin.download_pin_artifact(ref)

    assert len(minio.objetos) == 5
    assert all(
        re.fullmatch(rf"pin-cache/{WS}/{TASK}/[A-Za-z0-9_-]+\.(parquet|geojson)", chave)
        for chave in minio.objetos
    ), sorted(minio.objetos)
    assert {k: len(v) for k, v in de_volta.items()} == {
        "output": 1, "área": 2, "area": 3, "a b": 4, "a_b": 5,
    }


def test_saida_com_camadas_demais_nao_vira_pin_nem_sobe_objetos(minio):
    """Above the ceiling the server drops the pin: uploading anyway would cost every
    layer, on every run, for a ref that is never stored. The node just stays unpinned
    (core logs "Auto-pin falhou")."""
    saidas = {f"camada_{i}": _gdf(1) for i in range(100)}

    with pytest.raises(ValueError):
        pin.upload_pin_artifact("n1", saidas, WS, TASK)
    assert minio.objetos == {}


def test_ref_antiga_sem_camadas_extras_e_lida_como_antes(minio, tmp_path):
    """Refs already in `pinned_outputs` (no `__pin_frames__`) keep working."""
    gdf = _gdf(2)
    arquivo = tmp_path / "n1_pin.parquet"
    gdf.to_parquet(arquivo, index=False)
    chave = f"pin-cache/{WS}/task-antiga/n1_pin.parquet"
    minio.objetos[chave] = arquivo.read_bytes()

    de_volta = pin.download_pin_artifact({
        "__pin_s3_key__": chave,
        "__pin_format__": "parquet",
        "__pin_geo_key__": "output",
        "__pin_filename__": "n1_pin.parquet",
        "__pin_extra__": {"removed_count": 0},
    })

    assert list(de_volta) == ["output", "removed_count"]
    assert_geodataframe_equal(de_volta["output"], gdf)
    assert de_volta["removed_count"] == 0


def test_pin_antigo_com_camada_gravada_como_texto_se_regrava(minio, tmp_path):
    """A pin written before one object per layer holds "<DataFrame RxC>" where
    the second layer should be. Its first object exists, so nothing else would
    ever call it broken: it is, and the node runs to rewrite it."""
    arquivo = tmp_path / "n1_pin.parquet"
    _gdf(2).to_parquet(arquivo, index=False)
    chave = f"pin-cache/{WS}/task-antiga/n1_pin.parquet"
    minio.objetos[chave] = arquivo.read_bytes()
    ref = {
        "__pin_s3_key__": chave, "__pin_format__": "parquet", "__pin_geo_key__": "output",
        "__pin_filename__": "n1_pin.parquet",
        "__pin_extra__": {"removed": "<DataFrame 2x2>", "removed_count": 2},
    }
    assert pin.download_pin_artifact(ref) == {}

    # The same text NESTED in a list (a value that could only become text) and
    # anything that is not exactly the serializer's form stay as they are.
    for valor in (["<DataFrame 2x2>"], "<DataFrame 2x2> e mais", "DataFrame 2x2"):
        ref["__pin_extra__"] = {"removed": valor}
        assert pin.download_pin_artifact(ref)["removed"] == valor


def test_camada_extra_sumida_do_storage_faz_o_no_rodar_de_novo(minio):
    """One missing layer is a broken pin, not a pin without that output: the edge
    leaving it would deliver nothing and the target would fail far from the cause.
    The node runs and auto-pin rewrites the cache in the same run."""
    ref = _ida_e_volta("n1", pin.upload_pin_artifact("n1", _saidas(), WS, TASK))
    assert len(minio.objetos) == 4
    extra = sorted(k for k in minio.objetos if k != ref["__pin_s3_key__"])[0]
    del minio.objetos[extra]

    assert pin.download_pin_artifact(ref) == {}

    ex = WorkflowExecutor.__new__(WorkflowExecutor)
    ex.pinned_outputs = {"n1": ref}
    ex.pin_metadata = {"n1": {"pinned_at": "2026-01-01T00:00:00"}}
    ex.updated_pin_refs = {}
    ex.logger = logging.getLogger("test-pin-camadas")
    assert asyncio.run(ex._resolve_pin_data("n1")) is None
    assert ex.pinned_outputs["n1"] == {}
