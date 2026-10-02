# tests/unit/test_skip_merge_determinismo.py
"""
Determinismo do skip em merge/diamante (F2).

Um nó de merge com um pai VIVO (fora do ramo) e um pai SKIPADO (no ramo não
tomado) era skipado ou não conforme a ORDEM em que o batch era processado:
`_propagate_skip` zerava `pending_parents_count` e marcava skipped sem checar se
algum pai tinha de fato executado e entregue dado. Se o pai vivo decrementava o
merge primeiro e o skip do ramo irmão zerava por último, o merge — com dado real
na mão — era apagado.

Reproduz o diamante com o executor real e um nó de bifurcação real (Conditional):

    TX (trigger) ─────────────────► D (merge)      pai vivo, independente
    TA (trigger) ──► A (Conditional) ─true─► B      ramo tomado
                                     └false─► C ──► D   ramo skipado → merge

Com 3 feições e `count > 1`, A decide `branch=True`: B roda, C é skipado. D tem
de RODAR (recebeu o dado de TX), nunca ser skipado.
"""

import asyncio
import geopandas as gpd
from shapely.geometry import Point
from unittest.mock import MagicMock

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


def _trigger(nid):
    # type 'trigger' faz o executor injetar initial_inputs; name 'Merge' é o
    # factory lookup (strategy first devolve o 1º valor real como saída).
    return {"id": nid, "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}}


def _merge(nid, alias=None):
    props = {"strategy": "first"}
    if alias:
        props["alias"] = alias
    return {"id": nid, "type": "control", "name": "Merge", "properties": props}


def _branch(nid):
    return {"id": nid, "type": "control", "name": "Conditional",
            "properties": {"metric": "count", "operator": ">", "compareTo": "1"}}


def _spread(source, target):
    # sem from_key/to_key → espalha o dict do pai (o pai skipado espalha {}).
    return {"source": source, "target": target}


def _cond_edge(source, target, condition):
    return {"source": source, "target": target, "condition": condition}


def _rodar(ordem_nos):
    """Monta o diamante com os nós na ORDEM dada (controla o interleaving do
    batch) e roda. Devolve (final_outputs, node_stats)."""
    node_por_id = {
        "TX": _trigger("TX"),
        "TA": _trigger("TA"),
        "A": _branch("A"),
        "B": _merge("B"),
        "C": _merge("C"),
        "D": _merge("D", alias="Fim"),
    }
    definition = {
        "nodes": [node_por_id[i] for i in ordem_nos],
        "edges": [
            _spread("TX", "D"),               # pai vivo independente → merge
            _spread("TA", "A"),               # alimenta a bifurcação
            _cond_edge("A", "B", True),       # ramo tomado
            _cond_edge("A", "C", False),      # ramo NÃO tomado → skipado
            _spread("C", "D"),                # pai skipado → merge
        ],
    }
    ex = WorkflowExecutor(definition, task_id=f"f2-{'-'.join(ordem_nos)}", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"TX": {"output": _gdf()}, "TA": {"output": _gdf()}}))
    return final, ex.node_stats


def test_merge_roda_quando_pai_vivo_decrementa_antes_do_skip():
    # Ordem que aciona o bug: TX (pai vivo) é processado ANTES de A, então o
    # skip de C zera o pending de D por último. Antes: D skipado. Agora: D roda.
    final, stats = _rodar(["TX", "TA", "A", "B", "C", "D"])
    assert stats["C"]["status"] == "skipped", "C está no ramo não tomado — deve ser skipado"
    assert stats["D"]["status"] != "skipped", "D tem pai vivo (TX) — não pode ser skipado"
    assert "D" in final and final["D"], "D rodou e produziu saída"


def test_merge_roda_independente_da_ordem_do_batch():
    # Ordem inversa (A/TA antes de TX): o skip de C decrementa D primeiro, depois
    # TX o zera. Já funcionava antes; aqui confirma que a correção é simétrica.
    final, stats = _rodar(["TA", "A", "B", "C", "TX", "D"])
    assert stats["C"]["status"] == "skipped"
    assert stats["D"]["status"] != "skipped"
    assert "D" in final and final["D"]


def test_merge_com_todos_os_pais_skipados_continua_skipado():
    # Guarda contra sobre-correção: se D NÃO tem pai vivo (ambos no ramo morto),
    # ele DEVE continuar sendo skipado.
    #   TA → A ─true─► B
    #             └false─► C1 ─► D
    #             └false─► C2 ─► D
    # branch=True, então C1 e C2 (false) são skipados e D (só filhos deles) também.
    definition = {
        "nodes": [_trigger("TA"), _branch("A"), _merge("B"),
                  _merge("C1"), _merge("C2"), _merge("D")],
        "edges": [
            _spread("TA", "A"),
            _cond_edge("A", "B", True),
            _cond_edge("A", "C1", False),
            _cond_edge("A", "C2", False),
            _spread("C1", "D"),
            _spread("C2", "D"),
        ],
    }
    ex = WorkflowExecutor(definition, task_id="f2-all-skip", publisher=_publisher())
    final = asyncio.run(ex.run(initial_inputs={"TA": {"output": _gdf()}}))
    assert ex.node_stats["C1"]["status"] == "skipped"
    assert ex.node_stats["C2"]["status"] == "skipped"
    assert ex.node_stats["D"]["status"] == "skipped", "sem pai vivo, D deve ser skipado"
    assert "D" not in final
