# tests/unit/test_arestas_strict.py
"""
Semântica strict das arestas (PR-D): sem "primeiro valor" cego.

- Switch emite TODOS os baldes possíveis (fallback + saídas das regras), mesmo
  vazios, para que uma aresta from_key='output_N' sempre resolva.
- from_key que não existe no output do pai NÃO cruza dados de outro balde (F5).
- pai skipado com aresta from_key não injeta None no merge (F14).
"""
import asyncio

import geopandas as gpd
from shapely.geometry import Point
from unittest.mock import MagicMock

from flow.nodes.control.switch import Switch
from flow.executor.core import WorkflowExecutor


def _publisher():
    pub = MagicMock()
    pub.publish_event = MagicMock()
    return pub


def _gdf(cats):
    return gpd.GeoDataFrame(
        {"cat": list(cats)},
        geometry=[Point(i, i) for i in range(len(cats))],
        crs="EPSG:4326",
    )


# ── Switch emite todos os baldes ──────────────────────────────────────────────

def test_switch_emite_todos_os_baldes_declarados_mesmo_vazios():
    # Regras mandam para output_1 e output_2; dados só casam output_1. output_0
    # (fallback) e output_2 devem existir VAZIOS no resultado, não sumir.
    sw = Switch(node_id="s", parameters={
        "rules": [
            {"field": "cat", "operator": "==", "value": "A", "output": "output_1"},
            {"field": "cat", "operator": "==", "value": "B", "output": "output_2"},
        ],
        "fallback_output": "output_0",
    })
    out = asyncio.run(sw.execute({"data": _gdf("AAA")}))  # só 'A' → só output_1
    assert set(out) == {"output_0", "output_1", "output_2"}
    assert len(out["output_1"]) == 3
    assert len(out["output_0"]) == 0 and len(out["output_2"]) == 0


# ── from_key para balde vazio não cruza dados (F5) ────────────────────────────

def _node(nid, name="Merge", ntype="control", **props):
    return {"id": nid, "type": ntype, "name": name, "properties": props or {"strategy": "first"}}


def test_from_key_para_balde_vazio_do_switch_nao_cruza_dados():
    # Consumidor ligado a output_2 (vazio) NÃO pode receber os registros de
    # output_1. Antes: from_key ausente → primeiro valor → dados de output_1.
    definition = {
        "nodes": [
            {"id": "T", "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}},
            {"id": "S", "type": "control", "name": "Switch", "properties": {
                "rules": [
                    {"field": "cat", "operator": "==", "value": "A", "output": "output_1"},
                    {"field": "cat", "operator": "==", "value": "B", "output": "output_2"},
                ],
                "fallback_output": "output_0",
            }},
            _node("D"),
        ],
        "edges": [
            {"source": "T", "target": "S"},
            {"source": "S", "target": "D", "from_key": "output_2"},  # balde vazio
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f5", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf("AAA")}}))  # nada casa output_2
    saida_d = final["D"].get("output")
    # D recebeu o balde vazio (0 feições), NÃO os 3 registros de output_1.
    assert saida_d is not None and len(saida_d) == 0


# ── pai skipado com from_key não injeta None (F14) ────────────────────────────

def _branch(nid):
    return {"id": nid, "type": "control", "name": "Conditional",
            "properties": {"metric": "count", "operator": ">", "compareTo": "1"}}


def test_pai_skipado_com_from_key_nao_injeta_none_no_merge():
    #   T → A(Conditional, branch=True)
    #        ├true→ V ─(from_key output)→ D
    #        └false→ C ─(from_key output)→ D   (C skipado)
    # D roda por causa de V (vivo). A aresta de C (skipada) não pode injetar
    # {output: None} — antes o from_key-miss sobre {} caía em None.
    definition = {
        "nodes": [
            {"id": "T", "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}},
            _branch("A"), _node("V"), _node("C"), _node("D", strategy="first"),
        ],
        "edges": [
            {"source": "T", "target": "A"},
            {"source": "A", "target": "V", "condition": True},
            {"source": "A", "target": "C", "condition": False},
            {"source": "V", "target": "D", "from_key": "output", "to_key": "output"},
            {"source": "C", "target": "D", "from_key": "output", "to_key": "output"},
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f14", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf("AAA")}}))
    assert ex.node_stats["C"]["status"] == "skipped"
    assert ex.node_stats["D"]["status"] != "skipped"
    # D não pode ter recebido None de C: Merge 'first' devolveria o dado de V.
    assert final["D"].get("output") is not None
