# tests/unit/test_amostra_de_saida.py
"""
The data sample a node sends to the editor's Entradas/Saídas panels
(flow/executor/sample.py, docs/specs/node-data-panels.md §5).

It must be small and safe whatever the node returns: the first rows only,
geometries summarized, every cut flagged, live secrets and sensitive columns
masked, and the whole thing under the byte budget.
"""
import json
from datetime import datetime

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, Polygon

from flow.executor.sample import BUDGET_BYTES, build_output_sample
from flow.utils.segredos_vivos import in_use


def _quadrado(x: float, y: float, n: int = 4) -> Polygon:
    return Polygon([(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)])


def test_geodataframe_vira_tabela_com_tipos_crs_e_geometria_resumida():
    gdf = gpd.GeoDataFrame(
        {"cd_mun": [f"15{i:05d}" for i in range(30)], "area": np.arange(30, dtype=float),
         "pop": np.arange(30, dtype=np.int64), "ativo": [True] * 30},
        geometry=[_quadrado(i, 0) for i in range(30)], crs="EPSG:4674",
    )
    out = build_output_sample({"output": gdf})["outputs"]["output"]

    assert out["kind"] == "table"
    assert out["rows_total"] == 30
    assert len(out["rows"]) == 20
    assert out["truncated"] == {"rows": True, "columns": False, "cells": False}
    assert out["crs"] == "EPSG:4674"
    assert [c["name"] for c in out["columns"]] == ["cd_mun", "area", "pop", "ativo", "geometry"]
    assert [c["type"] for c in out["columns"]] == ["str", "float", "int", "bool", "geometry:Polygon"]
    assert out["columns"][-1]["geometry"] is True
    geom = out["rows"][0][-1]
    assert geom["type"] == "Polygon" and geom["vertices"] == 5
    assert geom["wkt"].startswith("POLYGON")
    assert out["rows"][1][:4] == ["1500001", 1.0, 1, True]


def test_geometria_grande_tem_wkt_curto_e_tipos_mistos():
    grande = Point(0, 0).buffer(10, quad_segs=2000)  # ~8000 vertices
    gdf = gpd.GeoDataFrame({"n": [1, 2]}, geometry=[grande, LineString([(0, 0), (1, 1)])])
    out = build_output_sample({"output": gdf})["outputs"]["output"]
    assert out["columns"][-1]["type"] == "geometry:mixed"
    cel = out["rows"][0][-1]
    assert cel["vertices"] > 7000
    assert len(cel["wkt"]) <= 81
    assert "crs" not in out


def test_dataframe_com_nan_datas_e_numpy():
    df = pd.DataFrame({
        "v": [1.5, np.nan], "d": [datetime(2026, 11, 1, 8, 30), pd.NaT],
        "o": [{"a": 1}, None], "b": [b"\x00\x01", None],
    })
    out = build_output_sample({"tabela": df})["outputs"]["tabela"]
    assert out["kind"] == "table"
    assert "crs" not in out
    assert out["rows"][0][0] == 1.5 and out["rows"][1][0] is None
    assert out["rows"][0][1] == "2026-11-01T08:30:00" and out["rows"][1][1] is None
    assert out["rows"][0][2] == "{'a': 1}"
    assert out["rows"][0][3] == "<bytes 2>"
    json.dumps(out)  # always serializable


def test_celula_longa_e_colunas_demais_sao_cortadas():
    df = pd.DataFrame({f"c{i}": ["x" * 500] for i in range(60)})
    out = build_output_sample({"output": df})["outputs"]["output"]
    assert len(out["columns"]) == 40
    assert out["truncated"]["columns"] is True
    assert out["truncated"]["cells"] is True
    assert out["rows"][0][0] == "x" * 120 + "…"


def test_saidas_que_nao_sao_tabela_viram_json():
    sample = build_output_sample({
        "metadata": {"url": "https://exemplo", "features": 58, "nivel": {"a": {"b": {"c": {"d": 1}}}}},
        "lista": list(range(50)),
        "texto": "y" * 10_000,
        "corpo": b"\x89PNG" * 10,
        "n": np.int64(7),
    })["outputs"]
    assert sample["metadata"]["kind"] == "json"
    assert sample["metadata"]["value"]["features"] == 58
    assert sample["metadata"]["value"]["nivel"]["a"]["b"]["c"] == "<dict 1 chaves>"
    assert sample["metadata"]["truncated"] is True
    assert len(sample["lista"]["value"]) == 20 and sample["lista"]["truncated"] is True
    assert len(sample["texto"]["value"]) == 121 and sample["texto"]["truncated"] is True
    assert sample["corpo"]["value"] == "<bytes 40>"
    assert sample["n"]["value"] == 7


def test_dataframe_dentro_de_dict_e_chaves_de_envelope():
    df = pd.DataFrame({"a": [1]})
    sample = build_output_sample({
        "output": {"camada": df}, "__artifact__": {"id": "x"}, "__response__": {"status": 200},
        "grande": {"__spilled__": True, "path": "/tmp/x.parquet"},
    })
    assert sample["outputs"]["output"]["value"] == {"camada": "<DataFrame 1x1>"}
    assert sorted(sample["skipped"]) == ["__artifact__", "__response__", "grande"]
    assert set(sample["outputs"]) == {"output"}


def test_saida_que_nao_e_dict_vira_output():
    sample = build_output_sample([1, 2, 3])
    assert sample["outputs"]["output"]["value"] == [1, 2, 3]


def test_segredo_em_uso_e_colunas_sensiveis_saem_mascarados():
    df = pd.DataFrame({"url": ["https://wfs?authkey=abcdef123456"], "api_key": ["k-999999"],
                       "Senha": ["segredo1"], "nome": ["ok"]})
    with in_use("abcdef123456"):  # pragma: allowlist secret
        sample = build_output_sample({
            "output": df,
            "cfg": {"token": "t-123456789", "host": "db.local", "nota": "chave abcdef123456"},
        })["outputs"]
    linha = sample["output"]["rows"][0]
    assert linha == ["https://wfs?authkey=***", "***", "***", "ok"]
    assert sample["cfg"]["value"] == {"token": "***", "host": "db.local", "nota": "chave ***"}


def test_segredos_por_padrao_saem_mesmo_fora_de_in_use():
    """The sample is built after the node returns: `in_use` is over by then, so
    the log's pattern redaction is what catches a DSN, a Bearer or a `token=`."""
    df = pd.DataFrame({"dsn": ["postgresql://geo:hunter2hunter2@db/gis"],  # pragma: allowlist secret
                       "url": ["https://api?token=abcdef123456&x=1"]})  # pragma: allowlist secret
    sample = build_output_sample({
        "output": df,
        "resp": {"msg": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123"},  # pragma: allowlist secret
    })["outputs"]
    dsn, url = sample["output"]["rows"][0]
    assert "hunter2hunter2" not in dsn and dsn.startswith("postgresql://geo:")
    assert "abcdef123456" not in url  # pragma: allowlist secret
    assert "abcdefghijklmnopqrstuvwxyz0123" not in sample["resp"]["value"]["msg"]


def test_chave_sensivel_mascara_lista_dict_e_cookie():
    sample = build_output_sample({"resp": {
        "token": ["abc123456"],  # pragma: allowlist secret
        "credentials": {"user": "u", "pass": "p"},  # pragma: allowlist secret
        "headers": {"Set-Cookie": "sessionid=xyz987654", "Content-Type": "application/json"},
        "vazio": None,
    }})["outputs"]["resp"]["value"]
    assert sample["token"] == "***"
    assert sample["credentials"] == "***"
    assert sample["headers"] == {"Set-Cookie": "***", "Content-Type": "application/json"}
    assert sample["vazio"] is None


def test_geometria_grande_nao_escreve_o_wkt_inteiro(monkeypatch):
    import shapely
    grande = Point(0, 0).buffer(10, quad_segs=2000)
    esperado = shapely.to_wkt(grande, rounding_precision=5, trim=True)[:80]

    def proibido(*_a, **_k):
        raise AssertionError("to_wkt chamado numa geometria grande")

    monkeypatch.setattr(shapely, "to_wkt", proibido)
    gdf = gpd.GeoDataFrame({"n": [1]}, geometry=[grande])
    cel = build_output_sample({"output": gdf})["outputs"]["output"]["rows"][0][-1]
    assert cel["vertices"] > 7000
    assert cel["wkt"] == esperado + "…"


def test_cabe_no_orcamento_cortando_linhas_depois_colunas_depois_saidas():
    largas = pd.DataFrame({f"c{i}": ["z" * 120] * 20 for i in range(40)})
    sample = build_output_sample({"a": largas, "b": largas.copy()})
    assert len(json.dumps(sample)) <= BUDGET_BYTES
    a = sample["outputs"]["a"]
    assert a["kind"] == "table"
    assert len(a["rows"]) < 20 and a["truncated"]["rows"] is True

    # One cell no cut can shrink enough: the largest output leaves whole.
    sample = build_output_sample({"a": largas, "meta": {"ok": True}}, budget_bytes=300)
    assert len(json.dumps(sample)) <= 300
    assert sample["outputs"]["a"] == {"kind": "omitted", "reason": "too_large"}
    assert sample["outputs"]["meta"]["value"] == {"ok": True}


def test_um_valor_estranho_nao_derruba_as_outras_saidas():
    class Explode:
        def __str__(self):
            raise RuntimeError("boom")

    sample = build_output_sample({"ruim": Explode(), "bom": 1})["outputs"]
    assert sample["ruim"] == {"kind": "omitted", "reason": "error"}
    assert sample["bom"]["value"] == 1


@pytest.mark.parametrize("vazio", [pd.DataFrame(), gpd.GeoDataFrame(geometry=[])])
def test_tabela_vazia(vazio):
    out = build_output_sample({"output": vazio})["outputs"]["output"]
    assert out["kind"] == "table" and out["rows_total"] == 0 and out["rows"] == []


def test_tabela_com_geometria_traz_o_mapa_da_amostra():
    from shapely.geometry import MultiPolygon
    grande = Point(0, 0).buffer(10, quad_segs=2000)
    gdf = gpd.GeoDataFrame(
        {"n": range(4)},
        geometry=[grande, Point(30, 5), LineString([(0, 0), (40, 20)]),
                  MultiPolygon([Point(50, 50).buffer(3), Point(60, 40).buffer(2)])],
        crs="EPSG:4674",
    )
    mapa = build_output_sample({"output": gdf})["outputs"]["output"]["map"]
    assert max(mapa["w"], mapa["h"]) == 1000
    tipos = [("p" if "p" in f else ("area" if f["area"] else "line")) for f in mapa["features"]]
    assert tipos == ["area", "p", "line", "area"]
    # Simplified and capped: the 8,000-vertex circle does not travel whole.
    assert len(json.dumps(mapa)) < 15_000
    for f in mapa["features"]:
        coords = f["p"] if "p" in f else [int(v) for v in f["d"].replace("M", " ").replace("Z", " ").split()]
        assert all(0 <= v <= 1000 for v in coords)


def test_tabela_sem_geometria_nao_tem_mapa():
    out = build_output_sample({"output": pd.DataFrame({"a": [1, 2]})})["outputs"]["output"]
    assert "map" not in out


def test_mapa_sai_antes_das_linhas_quando_estoura_o_orcamento():
    gdf = gpd.GeoDataFrame(
        {"texto": ["z" * 120] * 20},
        geometry=[Point(i, i).buffer(1, quad_segs=200) for i in range(20)],
    )
    cheio = build_output_sample({"output": gdf})["outputs"]["output"]
    assert "map" in cheio
    sem_folga = len(json.dumps(build_output_sample({"output": gdf}))) - len(json.dumps(cheio["map"])) + 100
    out = build_output_sample({"output": gdf}, budget_bytes=sem_folga)["outputs"]["output"]
    assert "map" not in out
    assert len(out["rows"]) == 20
