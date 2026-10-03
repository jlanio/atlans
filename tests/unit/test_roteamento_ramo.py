# tests/unit/test_roteamento_ramo.py
"""
Branch routing gated by a BRANCH EDGE, not by the raw "branch" output
(F7 / F8).

The old trigger was `if "branch" in outputs and isinstance(outputs["branch"], bool)`
— it did not look at the edges. Two defects:

- F7: ANY node (not only control nodes) whose output had a boolean 'branch' key
  hijacked the routing. Since normal edges have no `condition`,
  `condition == branch` was False for ALL of them → no active edge → the whole
  downstream was skipped.
- F8: `condition != branch` also caught the DATA edges (condition=None):
  None != True and None != False. A data edge leaving a fork node had its target
  skipped — impossible to route unconditional data from it.

Now: it only routes when there are branch edges (condition bool) AND output.branch
bool; data edges are always active; only branch edges with condition != branch
are deactivated.
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


class _NodeWithIncidentalBranch(BaseNode):
    """Ordinary (non-control) node whose output CONTAINS a boolean 'branch' key.
    It is not a routing node — it just emits the data and, by chance, a 'branch'."""

    @classmethod
    def description(cls):
        return {"name": "TesteBranchIncidental", "type": "action", "properties": []}

    async def execute(self, inputs):
        return {"output": inputs.get("output"), "branch": True}


@pytest.fixture
def _registra_no():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["TesteBranchIncidental"] = _NodeWithIncidentalBranch
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


def test_f7_plain_node_with_incidental_branch_does_not_hijack_routing(_registra_no):
    # N emits branch=True but only has a DATA edge (no condition). The child D
    # must run — before it was skipped because no edge matched condition==True.
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "N", "type": "action", "name": "TesteBranchIncidental", "properties": {}},
                  _merge("D")],
        "edges": [
            {"source": "T", "target": "N"},
            {"source": "N", "target": "D"},   # DATA edge, no condition
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f7", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["D"]["status"] != "skipped", "N não é nó de ramo — não pode skipar D"
    assert "D" in final and final["D"]


def test_f8_data_edge_leaving_a_branch_node_stays_active():
    # A (Conditional, branch=True) with a BRANCH edge (true→B) and a DATA edge
    # (→E, no condition). E must run; before it was skipped (None != True).
    definition = {
        "nodes": [_trigger("T"), _branch("A"), _merge("B"), _merge("E")],
        "edges": [
            {"source": "T", "target": "A"},
            {"source": "A", "target": "B", "condition": True},   # branch edge
            {"source": "A", "target": "E"},                       # data edge
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f8", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["B"]["status"] != "skipped", "ramo tomado (true) deve rodar"
    assert ex.node_stats["E"]["status"] != "skipped", "aresta de dado não pode ser desativada"
    assert "B" in final and "E" in final


def test_normal_routing_keeps_working():
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
