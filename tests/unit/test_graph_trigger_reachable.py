# tests/unit/test_graph_trigger_reachable.py
"""
Reach from triggers + closure over DEPENDENCIES (ancestors).

The run is defined by the triggers: it executes what "flows down" from them. But a lateral
SOURCE — a `datasource` that feeds a reachable node without being on the trigger's
path (e.g. WFS→Filtro→Caixa, with the trigger connected only to Caixa) — also has
to run, otherwise the join node runs without its input.

Before, the filter only looked forward (reachable from the trigger) and pruned the source.
The pruning removed only the KEYS of the unreachable ones, so the join's DIRECT
predecessor leaked as a value into the TopologicalSorter and entered the ORDER — but the
executor counts parents per edge (Kahn), and the parent left out of the run never
decremented that counter: the join and the whole branch got STUCK and did not run (only
the trigger did). Now the filter closes the input cone: reachable-from-trigger ∪
their ancestors.
"""
import pytest

from flow.core.graph import WorkflowGraph


def nd(**tipos):
    """node_defs a partir de id=tipo, ex.: nd(trig="trigger", wfs="datasource")."""
    return {i: {"id": i, "type": t} for i, t in tipos.items()}


def e(source, target):
    return {"source": source, "target": target}


def ordem(node_defs, edges):
    return WorkflowGraph(node_defs, edges).compute_order()


# ── Fonte lateral (o caso reportado) ────────────────────────────────────────────

def test_side_source_runs_the_whole_branch():
    """WFS→Filtro→Caixa with the trigger connected only to Caixa: the whole branch runs."""
    o = ordem(
        nd(trig="trigger", wfs="datasource", filtro="action", caixa="spatial"),
        [e("wfs", "filtro"), e("filtro", "caixa"), e("trig", "caixa")],
    )
    assert set(o) == {"trig", "wfs", "filtro", "caixa"}
    # Topological order: the source before whoever consumes it; the join last.
    assert o.index("wfs") < o.index("filtro") < o.index("caixa")
    assert o.index("trig") < o.index("caixa")


def test_side_source_two_levels():
    """A deeper lateral chain (WFS→f1→f2→Caixa) also goes in whole."""
    o = ordem(
        nd(trig="trigger", wfs="datasource", f1="action", f2="action", caixa="spatial"),
        [e("wfs", "f1"), e("f1", "f2"), e("f2", "caixa"), e("trig", "caixa")],
    )
    assert set(o) == {"trig", "wfs", "f1", "f2", "caixa"}
    assert o.index("wfs") < o.index("f1") < o.index("f2") < o.index("caixa")


def test_every_predecessor_of_a_kept_node_is_also_kept():
    """Leak regression: every predecessor of a kept node is also kept.

    Before, `filtro` came out in the ORDER without `wfs`; since the executor counts parents per
    edge (Kahn), the join got stuck and the whole branch did not run. Here we guarantee the
    invariant that prevents this: no node stays in the order with a dependency from outside.
    """
    node_defs = nd(trig="trigger", wfs="datasource", filtro="action", caixa="spatial")
    edges = [e("wfs", "filtro"), e("filtro", "caixa"), e("trig", "caixa")]
    o = set(ordem(node_defs, edges))
    # For every edge whose target runs, the source also runs.
    for aresta in edges:
        if aresta["target"] in o:
            assert aresta["source"] in o, (
                f"{aresta['target']} roda mas sua fonte {aresta['source']} ficou de fora"
            )


# ── What does NOT change ─────────────────────────────────────────────────────────

def test_fully_detached_tree_is_dropped():
    """No path to the trigger and not feeding anything that runs: still pruned."""
    o = ordem(
        nd(trig="trigger", a="action", b="datasource", c="action"),
        [e("trig", "a"), e("b", "c")],  # b→c is an island
    )
    assert set(o) == {"trig", "a"}
    assert "b" not in o and "c" not in o


def test_two_triggers_converging_on_a_merge():
    o = ordem(
        nd(t1="trigger", t2="trigger", m="action"),
        [e("t1", "m"), e("t2", "m")],
    )
    assert set(o) == {"t1", "t2", "m"}
    assert o.index("t1") < o.index("m") and o.index("t2") < o.index("m")


def test_cycle_raises_valueerror():
    with pytest.raises(ValueError, match="[Cc]iclo"):
        ordem(
            nd(trig="trigger", a="action", b="action"),
            [e("trig", "a"), e("a", "b"), e("b", "a")],
        )


def test_without_trigger_the_filter_is_not_applied():
    """With no trigger at all (e.g. an isolated unit test), everything that has an edge runs."""
    o = ordem(
        nd(a="datasource", b="action"),
        [e("a", "b")],
    )
    assert set(o) == {"a", "b"}
    assert o.index("a") < o.index("b")


def test_isolated_node_stays_dropped_even_with_trigger():
    """The isolated-node filter (no edge at all) still applies alongside the new closure."""
    o = ordem(
        nd(trig="trigger", caixa="spatial", solto="datasource"),
        [e("trig", "caixa")],  # `solto` has no edge at all
    )
    assert set(o) == {"trig", "caixa"}
    assert "solto" not in o
