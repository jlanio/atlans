"""Regression for the engine's 4 fixes (audit: workflow/correctness).

Each test fails WITHOUT the fix; the docstring names the mutation that breaks
ONLY it. Two fixes are BEHAVIOR CHANGES (gather cancels siblings; retry only on
transient errors) and are marked as such.
"""
import asyncio

import geopandas as gpd
import pytest
from shapely.geometry import Point
from unittest.mock import MagicMock

from flow.nodes.base import BaseNode
from flow.executor.core import WorkflowExecutor
from flow.executor.spill import _load_from_disk


def _publisher():
    pub = MagicMock()
    pub.publish_event = MagicMock()
    return pub


def _gdf():
    return gpd.GeoDataFrame({"n": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")


# Observable state of the side-effect nodes and of the attempt counting.
EFFECTS: list = []
CALLS: dict = {}


class _Branch(BaseNode):
    """Control node that emits branch=False (the True branch is not taken)."""
    @classmethod
    def description(cls):
        return {"name": "TesteRamo", "type": "control", "properties": []}

    async def execute(self, inputs):
        return {"output": inputs.get("output"), "branch": False}


class _Source(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteFonte", "type": "action", "properties": []}

    async def execute(self, inputs):
        return {"output": _gdf()}


class _Coletor(BaseNode):
    """Merge that reports the KEYS it received — that is how we see the leak."""
    @classmethod
    def description(cls):
        return {"name": "TesteColetor", "type": "control", "properties": []}

    async def execute(self, inputs):
        return {"chaves": sorted(inputs.keys())}


class _FastFailure(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "TesteFalhaRapida", "type": "action", "properties": []}

    async def execute(self, inputs):
        raise RuntimeError("falhei rapido")


class _SlowEffect(BaseNode):
    """Runs ~0.2 s and ONLY THEN commits the effect — simulates computing and then writing."""
    @classmethod
    def description(cls):
        return {"name": "TesteEfeitoLento", "type": "action", "properties": []}

    async def execute(self, inputs):
        await asyncio.sleep(0.2)
        EFFECTS.append("Y")  # the "commit" that must not happen if canceled
        return {"output": None}


class _ClassifiedFailure(BaseNode):
    """Raises ValueError (non-retryable) or ConnectionError (transient),
    depending on the `tipo` parameter, counting the attempts."""
    @classmethod
    def description(cls):
        return {"name": "TesteFalhaClassificada", "type": "action", "properties": []}

    async def execute(self, inputs):
        CALLS[self.node_id] = CALLS.get(self.node_id, 0) + 1
        if self.get_param("tipo", "user") == "transient":
            raise ConnectionError("rede caiu")
        raise ValueError("dado ruim")


@pytest.fixture
def _registra():
    from flow.registry import NODE_REGISTRY
    novos = {
        "TesteRamo": _Branch, "TesteFonte": _Source, "TesteColetor": _Coletor,
        "TesteFalhaRapida": _FastFailure, "TesteEfeitoLento": _SlowEffect,
        "TesteFalhaClassificada": _ClassifiedFailure,
    }
    NODE_REGISTRY.update(novos)
    EFFECTS.clear(); CALLS.clear()
    try:
        yield
    finally:
        for n in novos:
            NODE_REGISTRY.pop(n, None)


def _trigger(nid):
    return {"id": nid, "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}}


# ── F-audit: an edge from a branch NOT taken does not inject into the surviving merge ──

def test_edge_from_disabled_branch_does_not_inject_into_merge(_registra):
    """Mutation: remove the `id(edge) in self._deactivated_edge_ids` check when
    assembling inputs.

    Ramo emits branch=False → the edge Ramo→C(True) is deactivated; but C has
    another LIVE edge (Fonte→C), so C RUNS (has_live_input). Without the fix,
    the assembly iterates over ALL of C's edges and, since Ramo is 'completed'
    (not 'skipped'), injects the output of the REJECTED branch — the 'branch'
    key leaks into C.
    """
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "Fonte", "type": "action", "name": "TesteFonte", "properties": {}},
                  {"id": "Ramo", "type": "control", "name": "TesteRamo", "properties": {}},
                  {"id": "C", "type": "control", "name": "TesteColetor", "properties": {}}],
        "edges": [
            {"source": "T", "target": "Fonte"},
            {"source": "T", "target": "Ramo"},
            {"source": "Fonte", "target": "C"},               # data edge
            {"source": "Ramo", "target": "C", "condition": True},  # branch NOT taken
        ],
    }
    ex = WorkflowExecutor(definition, task_id="fa", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert ex.node_stats["C"]["status"] != "skipped", "C tem dado vivo de Fonte: roda"
    assert "branch" not in final["C"]["chaves"], "o ramo rejeitado NÃO pode injetar em C"
    assert "output" in final["C"]["chaves"], "o dado de Fonte deve chegar"


# ── F-audit: gather cancels the siblings on the 1st failure (BEHAVIOR CHANGE) ──

async def test_gather_cancels_siblings_on_first_failure(_registra):
    """Mutation: go back to `results = await asyncio.gather(*tasks)` without canceling.

    X fails fast; Y computes ~0.2 s and ONLY THEN commits the effect. With the
    fix, X's failure cancels Y before the commit. Without the fix, Y stays alive
    (gather does not cancel) and commits during the wait below.
    """
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "X", "type": "action", "name": "TesteFalhaRapida", "properties": {}},
                  {"id": "Y", "type": "action", "name": "TesteEfeitoLento", "properties": {}}],
        "edges": [{"source": "T", "target": "X"}, {"source": "T", "target": "Y"}],
    }
    ex = WorkflowExecutor(definition, task_id="ga", publisher=_publisher())
    with pytest.raises(Exception):
        await ex.run(initial_inputs={"T": {"output": _gdf()}})
    await asyncio.sleep(0.5)  # gives Y time to commit IF it was not canceled
    assert EFFECTS == [], "o irmão não pode commitar efeito após a falha do batch"


# ── F-audit: retry so em erro transient (MUDANCA DE COMPORTAMENTO) ─────────

def test_retry_does_not_retry_deterministic_error(_registra):
    """Mutation: remove the `is_retryable(classify_error(...))` gate.

    ValueError is 'user' (non-retryable): execute must run ONCE, not 3 times.
    """
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "R", "type": "action", "name": "TesteFalhaClassificada",
                   "properties": {"tipo": "user", "retry_count": 2, "retry_delay_s": 0}}],
        "edges": [{"source": "T", "target": "R"}],
    }
    ex = WorkflowExecutor(definition, task_id="rt1", publisher=_publisher())
    with pytest.raises(Exception):
        asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert CALLS.get("R") == 1, "erro determinístico não pode ser retentado"


def test_retry_retries_transient_error(_registra):
    """ConnectionError is 'transient': execute runs 1 + 2 retries = 3 times."""
    definition = {
        "nodes": [_trigger("T"),
                  {"id": "R", "type": "action", "name": "TesteFalhaClassificada",
                   "properties": {"tipo": "transient", "retry_count": 2, "retry_delay_s": 0}}],
        "edges": [{"source": "T", "target": "R"}],
    }
    ex = WorkflowExecutor(definition, task_id="rt2", publisher=_publisher())
    with pytest.raises(Exception):
        asyncio.run(ex.run(initial_inputs={"T": {"output": _gdf()}}))
    assert CALLS.get("R") == 3, "erro transitório deve ser retentado até esgotar"


# ── F-audit: a spill that does not restore fails loudly, does not deliver the sentinel ──

def test_unrestored_spill_raises(tmp_path):
    """Mutation: go back to just logging the warning and leaving the sentinel reference.

    Without the fix, the consuming node would receive {'__spilled__': True, ...}
    as if it were data. Now it fails loudly with the real cause.
    """
    outputs = {"gdf": {"__spilled__": True, "__spill_path__": str(tmp_path / "nao_existe.parquet")}}
    with pytest.raises(RuntimeError):
        _load_from_disk(outputs)
