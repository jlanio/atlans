# tests/unit/test_graph_orphan_edges.py
"""
Graph robustness against ORPHAN edges (F1).

An edge whose source and/or target does not exist in node_defs is real cruft: the
canvas deleted a node and left the edge dangling, or the JSON was imported/edited
by hand. Before, this brought down the whole run:
  - orphan target → raw KeyError in compute_order (predecessors is a plain dict);
  - orphan source → the ghost id leaked through static_order() and blew up later at
    instantiation (the filters only remove KEYS, never the value).

WorkflowGraph now discards the orphan edge (indexing and ordering) instead of
blowing up.
"""

from flow.core.graph import WorkflowGraph


def _nd(*ids):
    return {i: {"id": i, "type": "x"} for i in ids}


def test_target_orfao_nao_estoura_compute_order():
    # Antes: KeyError('ghost') em predecessors[edge['target']].
    g = WorkflowGraph(
        _nd("a", "b"),
        [{"source": "a", "target": "b"}, {"source": "b", "target": "ghost"}],
        filter_trigger_reachable=False,
    )
    order = g.compute_order()
    assert set(order) == {"a", "b"}
    assert "ghost" not in order


def test_source_orfao_nao_vaza_para_a_ordem():
    # Before: 'ghost' went into predecessors[b] as a value and came out in static_order,
    # then blew up at instantiation (node_defs['ghost']).
    g = WorkflowGraph(
        _nd("a", "b"),
        [{"source": "a", "target": "b"}, {"source": "ghost", "target": "b"}],
        filter_trigger_reachable=False,
    )
    order = g.compute_order()
    assert set(order) == {"a", "b"}
    assert "ghost" not in order


def test_aresta_orfa_nao_entra_no_incoming_outgoing():
    g = WorkflowGraph(
        _nd("a", "b"),
        [
            {"source": "a", "target": "b"},        # valid
            {"source": "a", "target": "ghost"},    # orphan target
            {"source": "ghost2", "target": "b"},   # orphan source
        ],
    )
    assert dict(g.outgoing) == {"a": [{"source": "a", "target": "b"}]}
    assert dict(g.incoming) == {"b": [{"source": "a", "target": "b"}]}
    assert "ghost" not in g.incoming and "ghost" not in g.outgoing
    assert "ghost2" not in g.outgoing
    assert len(g.orphan_edges) == 2


def test_aresta_com_os_dois_endpoints_orfaos_e_descartada():
    g = WorkflowGraph(
        _nd("a", "b"),
        [{"source": "a", "target": "b"}, {"source": "x", "target": "y"}],
        filter_trigger_reachable=False,
    )
    assert set(g.compute_order()) == {"a", "b"}
    assert len(g.orphan_edges) == 1


def test_grafo_valido_permanece_intacto():
    # Guard against false positives: no legitimate edge may be discarded.
    g = WorkflowGraph(
        _nd("a", "b", "c"),
        [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
        filter_trigger_reachable=False,
    )
    assert g.orphan_edges == []
    order = g.compute_order()
    assert order.index("a") < order.index("b") < order.index("c")


def test_orfa_logada_uma_vez(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="flow.core.graph"):
        WorkflowGraph(
            _nd("a", "b"),
            [{"source": "a", "target": "b"}, {"source": "a", "target": "ghost"}],
        )
    avisos = [r for r in caplog.records if "órfã" in r.getMessage()]
    assert len(avisos) == 1
    assert "a->ghost" in avisos[0].getMessage()
