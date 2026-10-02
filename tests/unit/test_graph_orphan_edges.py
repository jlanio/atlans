# tests/unit/test_graph_orphan_edges.py
"""
Robustez do grafo contra arestas ÓRFÃS (F1).

Uma aresta cujo source e/ou target não existe em node_defs é cruft real: o
canvas deletou um nó e deixou a aresta pendurada, ou o JSON foi importado/editado
à mão. Antes, isso derrubava o run inteiro:
  - target órfão → KeyError cru em compute_order (predecessors é dict comum);
  - source órfão → o id fantasma vazava por static_order() e estourava depois na
    instanciação (os filtros só removem CHAVES, nunca o valor).

WorkflowGraph agora descarta a aresta órfã (indexação e ordenação) em vez de
estourar.
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
    # Antes: 'ghost' entrava em predecessors[b] como valor e saía em static_order,
    # depois estourava na instanciação (node_defs['ghost']).
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
            {"source": "a", "target": "b"},        # válida
            {"source": "a", "target": "ghost"},    # target órfão
            {"source": "ghost2", "target": "b"},   # source órfão
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
    # Guarda contra falso positivo: nenhuma aresta legítima pode ser descartada.
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
