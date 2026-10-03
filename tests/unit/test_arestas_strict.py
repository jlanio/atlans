# tests/unit/test_arestas_strict.py
"""
Strict edge semantics (PR-D): no blind "first value".

- Switch emits ALL possible buckets (fallback + rule outputs), even empty
  ones, so that an edge with from_key='output_N' always resolves.
- A from_key that does not exist in the parent's output does NOT cross data
  from another bucket (F5).
- A skipped parent with a from_key edge does not inject None into the merge (F14).
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


# ── Switch emits all buckets ──────────────────────────────────────────────────

def test_switch_emits_all_declared_buckets_even_empty():
    # Rules send to output_1 and output_2; the data only matches output_1. output_0
    # (fallback) and output_2 must exist EMPTY in the result, not disappear.
    sw = Switch(node_id="s", parameters={
        "rules": [
            {"field": "cat", "operator": "==", "value": "A", "output": "output_1"},
            {"field": "cat", "operator": "==", "value": "B", "output": "output_2"},
        ],
        "fallback_output": "output_0",
    })
    out = asyncio.run(sw.execute({"data": _gdf("AAA")}))  # only 'A' → only output_1
    assert set(out) == {"output_0", "output_1", "output_2"}
    assert len(out["output_1"]) == 3
    assert len(out["output_0"]) == 0 and len(out["output_2"]) == 0


# ── from_key to an empty bucket does not cross data (F5) ──────────────────────

def _node(nid, name="Merge", ntype="control", **props):
    return {"id": nid, "type": ntype, "name": name, "properties": props or {"strategy": "first"}}


def test_from_key_to_empty_switch_bucket_does_not_cross_data():
    # A consumer wired to output_2 (empty) must NOT receive the records from
    # output_1. Before: missing from_key → first value → data from output_1.
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
    output_d = final["D"].get("output")
    # D received the empty bucket (0 features), NOT the 3 records from output_1.
    assert output_d is not None and len(output_d) == 0


# ── skipped parent with from_key does not inject None (F14) ───────────────────

def _branch(nid):
    return {"id": nid, "type": "control", "name": "Conditional",
            "properties": {"metric": "count", "operator": ">", "compareTo": "1"}}


def test_skipped_parent_with_from_key_does_not_inject_none_into_merge():
    #   T → A(Conditional, branch=True)
    #        ├true→ V ─(from_key output)→ D
    #        └false→ C ─(from_key output)→ D   (C skipped)
    # D runs because of V (alive). C's edge (skipped) must not inject
    # {output: None} — before, the from_key miss over {} fell to None.
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
    # D must not have received None from C: Merge 'first' would return V's data.
    assert final["D"].get("output") is not None
