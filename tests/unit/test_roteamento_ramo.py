# tests/unit/test_roteamento_ramo.py
"""
Roteamento de ramo gateado por ARESTA DE RAMO, não pelo output cru "branch"
(F7 / F8).

O gatilho antigo era `if "branch" in outputs and isinstance(outputs["branch"], bool)`
— não olhava as arestas. Dois defeitos:

- F7: QUALQUER nó (não só de controle) cujo output tivesse uma chave booleana
  'branch' sequestrava o roteamento. Como arestas normais não têm `condition`,
  `condition == branch` dava False para TODAS → nenhuma aresta ativa → todo o
  downstream era skipado.
- F8: `condition != branch` capturava também as arestas de DADO (condition=None):
  None != True e None != False. Uma aresta de dado saindo de um nó de bifurcação
  tinha o alvo skipado — impossível rotear dado incondicional a partir dele.

Agora: só roteia quando há arestas de ramo (condition bool) E output.branch bool;
arestas de dado ficam sempre ativas; só arestas de ramo com condition != branch
são desativadas.
"""

import asyncio
import geopandas as gpd
import pytest
from shapely.geometry import Point
from unittest.mock import MagicMock

from flow.nodes.base import BaseNode
from flow.executor.core import WorkflowExecutor


def _publisher():
    pub = MagicMock()
    pub.publish_event = MagicMock()
    return pub


def _gdf():
    return gpd.GeoDataFrame(
        {"n": list("abc")},
        geometry=[Point(i, i) for i in range(3)],
        crs="EPSG:4326",
    )


class _NoComBranchIncidental(BaseNode):
    """Nó comum (não-controle) cujo output CONTÉM uma chave booleana 'branch'.
    Não é um nó de roteamento — só emite o dado e, por acaso, um 'branch'."""

    @classmethod
    def description(cls):
        return {"name": "TesteBranchIncidental", "type": "action", "properties": []}

    async def execute(self, inputs):
        return {"output": inputs.get("output"), "branch": True}


@pytest.fixture
def _registra_no():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["TesteBranchIncidental"] = _NoComBranchIncidental
    try:
        yield
    finally:
        NODE_REGISTRY.pop("TesteBranchIncidental", None)


def _trigger(nid):
    return {"id": nid, "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}}


def _merge(nid):
    return {"id": nid, "type": "control", "name": "Merge", "properties": {"strategy": "first"}}


def _branch(nid):
    return {"id": nid, "type": "control", "name": "Conditional",
            "properties": {"metric": "count", "operator": ">", "compareTo": "1"}}


def test_f7_no_comum_com_branch_incidental_nao_sequestra_roteamento(_registra_no):
    # N emite branch=True mas só tem aresta de DADO (sem condition). O filho D
    # deve rodar — antes era skipado porque nenhuma aresta casava condition==True.
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "N", "type": "action", "name": "TesteBranchIncidental", "properties": {}},
                  _merge("D")],
        "edges": [
            {"source": "T", "target": "N"},
            {"source": "N", "target": "D"},   # aresta de DADO, sem condition
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f7", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["D"]["status"] != "skipped", "N não é nó de ramo — não pode skipar D"
    assert "D" in final and final["D"]


def test_f8_aresta_de_dado_saindo_de_no_de_ramo_permanece_ativa():
    # A (Conditional, branch=True) com uma aresta de RAMO (true→B) e uma aresta
    # de DADO (→E, sem condition). E deve rodar; antes era skipado (None != True).
    definition = {
        "nodes": [_trigger("T"), _branch("A"), _merge("B"), _merge("E")],
        "edges": [
            {"source": "T", "target": "A"},
            {"source": "A", "target": "B", "condition": True},   # aresta de ramo
            {"source": "A", "target": "E"},                       # aresta de dado
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f8", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["B"]["status"] != "skipped", "ramo tomado (true) deve rodar"
    assert ex.node_stats["E"]["status"] != "skipped", "aresta de dado não pode ser desativada"
    assert "B" in final and "E" in final


def test_roteamento_normal_continua_funcionando():
    # Guarda: com true/false wired, branch=True → ramo true roda, false skipado.
    definition = {
        "nodes": [_trigger("T"), _branch("A"), _merge("V"), _merge("F")],
        "edges": [
            {"source": "T", "target": "A"},
            {"source": "A", "target": "V", "condition": True},
            {"source": "A", "target": "F", "condition": False},
        ],
    }
    ex = WorkflowExecutor(definition, task_id="rota", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["V"]["status"] != "skipped", "ramo true deve rodar"
    assert ex.node_stats["F"]["status"] == "skipped", "ramo false deve ser skipado"
    assert "V" in final and "F" not in final
