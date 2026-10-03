# tests/unit/test_validate_edges.py
"""
Static edge diagnostics in /validate (PR-E) and the empty-schema guard in the
simulation (F11).

The strict run OMITS the port of a missing from_key (it does not bring down the
workflow because of an optional/dynamic output). The "stale from_key is an
error" enforcement lives here, in static validation, which has the
hand-declared schema.
"""
import asyncio

import pytest
from unittest.mock import MagicMock

from flow.nodes.base import BaseNode
from flow.executor.core import WorkflowExecutor


def _executor(nodes, edges):
    pub = MagicMock()
    pub.publish_event = MagicMock()
    return WorkflowExecutor({"nodes": nodes, "edges": edges}, task_id="ve", publisher=pub)


def _n(nid, name="Merge", ntype="control"):
    return {"id": nid, "type": ntype, "name": name, "properties": {"strategy": "first"}}


def _schema(*names):
    return [{"fields": [{"name": n, "type": "any"} for n in names]}]


# ── validate_edges ────────────────────────────────────────────────────────────

def test_stale_from_key_becomes_error():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "nope"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    diag = ex.validate_edges()
    assert len(diag) == 1
    assert diag[0]["severity"] == "error" and diag[0]["from_key"] == "nope"
    assert diag[0]["source"] == "a" and diag[0]["target"] == "b"


def test_valid_from_key_produces_no_diagnostic():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "output"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output", "meta")}}
    assert ex.validate_edges() == []


def test_spread_from_multi_output_source_becomes_warning():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b"}])  # no from_key/to_key
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("x", "y")}}
    diag = ex.validate_edges()
    assert len(diag) == 1 and diag[0]["severity"] == "warning"


def test_spread_from_single_output_source_does_not_warn():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert ex.validate_edges() == []


def test_branch_edge_is_not_ambiguous():
    # bool condition → it is a branch edge, not an ambiguous spread.
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "condition": True}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("x", "y")}}
    assert ex.validate_edges() == []


def test_source_without_known_schema_is_not_diagnosed():
    # No declared outputs (a dynamic one that did not simulate) → cannot flag a typo.
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "qualquer"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": []}}
    assert ex.validate_edges() == []


# ── F11: schema == [] does not cascade an error in the preview ───────────────

class _ParentWithoutOutput(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "PaiSemSaida", "type": "action", "properties": [], "outputs": []}

    async def execute(self, inputs):
        return {}


class _DynamicChild(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "FilhoDinamico", "type": "action", "properties": [], "dynamic_output": True}

    @classmethod
    async def simulate(cls, params, inputs):
        return [{"fields": [{"name": "ok", "type": "any"}]}]

    async def execute(self, inputs):
        return {}


@pytest.fixture
def _register_nodes():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["PaiSemSaida"] = _ParentWithoutOutput
    NODE_REGISTRY["FilhoDinamico"] = _DynamicChild
    try:
        yield
    finally:
        NODE_REGISTRY.pop("PaiSemSaida", None)
        NODE_REGISTRY.pop("FilhoDinamico", None)


def test_empty_parent_schema_does_not_cascade_error(_register_nodes):
    # Parent with outputs=[] (like SubWorkflowInput/Output). Before:
    # schema[0] on [] → IndexError → child marked 'error' and a cascade. Now ok.
    ex = _executor(
        [{"id": "p", "type": "action", "name": "PaiSemSaida", "properties": {}},
         {"id": "c", "type": "action", "name": "FilhoDinamico", "properties": {}}],
        [{"source": "p", "target": "c", "from_key": "x"}],
    )
    asyncio.run(ex.simulate_runner())
    assert ex.simulated_outputs["c"]["status"] == "ok", ex.simulated_outputs["c"]
