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


@pytest.mark.parametrize("verdadeiro, falso", [
    ("true", "false"),   # `condition` as text (MCP, hand-written JSON)
    (1, 0),
    (..., ...),          # only the branch handle, no `condition`
])
def test_ramo_escrito_sem_bool_json_ainda_roteia(verdadeiro, falso):
    # Any of these passed the MCP validation (or is drawn on the branch by the
    # editor) and ran as DATA edges: the rejected branch ran too.
    e_v = {"source": "A", "target": "V", "source_handle": "true"}
    e_f = {"source": "A", "target": "F", "source_handle": "false"}
    if verdadeiro is not ...:
        e_v["condition"], e_f["condition"] = verdadeiro, falso
    definition = {
        "nodes": [_trigger("T"), _branch("A"), _merge("V"), _merge("F")],
        "edges": [{"source": "T", "target": "A"}, e_v, e_f],
    }
    ex = WorkflowExecutor(definition, task_id="ramo-texto", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["V"]["status"] != "skipped", "ramo true deve rodar"
    assert ex.node_stats["F"]["status"] == "skipped", "ramo false deve ser skipado"
    assert "V" in final and "F" not in final


# ── A stray `condition` the old editor wrote on data edges ────────────────────

class _NodeWithNamedPorts(BaseNode):
    """Two NAMED output handles, one of them a boolean called `branch`. The old
    editor wrote `condition: false` on every edge leaving a named handle."""

    @classmethod
    def description(cls):
        return {"name": "TestePortasNomeadas", "type": "action", "properties": [],
                "outputs": [{"name": "dados", "type": "any", "port": True},
                            {"name": "branch", "type": "boolean", "port": True}]}

    async def execute(self, inputs):
        return {"dados": inputs.get("output"), "branch": True}


class _ScriptRoteador(BaseNode):
    """A Python Script-like node (dynamic outputs, one anonymous handle) that an
    agent wired as a router: `condition` edges with no handle."""

    @classmethod
    def description(cls):
        return {"name": "TesteScriptRoteador", "type": "action", "properties": [],
                "dynamic_output": True, "outputs": [{"name": "result", "type": "any"}]}

    async def execute(self, inputs):
        return {"result": inputs.get("output"), "branch": False}


@pytest.fixture
def _registra_portas():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["TestePortasNomeadas"] = _NodeWithNamedPorts
    NODE_REGISTRY["TesteScriptRoteador"] = _ScriptRoteador
    try:
        yield
    finally:
        NODE_REGISTRY.pop("TestePortasNomeadas", None)
        NODE_REGISTRY.pop("TesteScriptRoteador", None)


def test_condition_espuria_numa_porta_nomeada_nao_desliga_a_aresta(_registra_portas):
    # Read as a branch, `branch: True` switched the edge off and D was skipped.
    definition = {
        "nodes": [_trigger("T"), {"id": "N", "type": "action", "name": "TestePortasNomeadas", "properties": {}}, _merge("D")],
        "edges": [
            {"source": "T", "target": "N"},
            {"source": "N", "target": "D", "source_handle": "dados", "from_key": "dados", "condition": False},
        ],
    }
    ex = WorkflowExecutor(definition, task_id="espuria", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["D"]["status"] != "skipped"
    assert len(final["D"]["output"]) == 3


def test_condition_espuria_e_aresta_de_dado_na_validacao(_registra_portas):
    # A data edge with no key from a node with two outputs spreads both: the
    # ambiguity warning the stray `condition` used to hide.
    ex = WorkflowExecutor(
        {"nodes": [_merge("N"), _merge("D")],
         "edges": [{"source": "N", "target": "D", "source_handle": "dados", "condition": False}]},
        task_id="valida", publisher=_publisher(),
    )
    ex.simulated_outputs = {"N": {"status": "ok", "schema": [{"fields": [{"name": "dados"}, {"name": "branch"}]}]}}
    assert [d["severity"] for d in ex.validate_edges()] == ["warning"]


def test_script_usado_como_roteador_segue_roteando(_registra_portas):
    # Guard: whatever the node, a `condition` with no named port routes. A
    # Python Script an agent wired with condition edges must not run both sides.
    definition = {
        "nodes": [_trigger("T"), {"id": "S", "type": "action", "name": "TesteScriptRoteador", "properties": {}},
                  _merge("SIM"), _merge("NAO")],
        "edges": [
            {"source": "T", "target": "S"},
            {"source": "S", "target": "SIM", "condition": True},
            {"source": "S", "target": "NAO", "condition": False},
        ],
    }
    ex = WorkflowExecutor(definition, task_id="roteador", publisher=_publisher())
    asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["SIM"]["status"] == "skipped"
    assert ex.node_stats["NAO"]["status"] != "skipped"
