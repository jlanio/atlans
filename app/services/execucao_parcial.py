# app/services/execucao_parcial.py
"""Run until a node ("Executar até este nó"): the definition cut down to one
node and its ancestors.

The editor's Entradas/Saídas panels open empty until the workflow runs, and a
whole run to see one node's data was the main friction of the panels
(docs/specs/node-data-panels.md). With `run_until`, the server dispatches only
the target node and every node it depends on, through the same path as a full
run: credentials, disabled-node checks and the envelope only see what runs.

Cut on the server, not in the executor: an executor that predates the option
runs the smaller definition as it would any other.

What runs is what feeds the node, nothing downstream of it. A side-effect node
(email, write to a database) only runs if the target depends on it.
"""
from collections.abc import Mapping
from typing import Any

from app.core.exceptions import WorkflowInputValidationError
from flow.core.graph import ponta


def ate_o_no(definition: Mapping[str, Any], node_id: str) -> dict:
    """`definition` with only `node_id`, its ancestors and the edges among them.

    Every other key of the definition (settings, viewport, metadata) is kept.
    Raises `WorkflowInputValidationError` (422) when the node does not exist.
    """
    nodes = [n for n in (definition.get("nodes") or []) if isinstance(n, Mapping)]
    ids = {n.get("id") for n in nodes}
    if node_id not in ids:
        raise WorkflowInputValidationError(
            f"O nó '{node_id}' não existe neste workflow (salve o canvas e tente de novo)."
        )

    edges = [e for e in (definition.get("edges") or []) if isinstance(e, Mapping)]
    pais: dict = {}
    for e in edges:
        origem, alvo = ponta(e, "source"), ponta(e, "target")
        if origem in ids and alvo in ids:
            pais.setdefault(alvo, set()).add(origem)

    manter = {node_id}
    fila = [node_id]
    while fila:
        atual = fila.pop()
        for pai in pais.get(atual, ()):
            if pai not in manter:
                manter.add(pai)
                fila.append(pai)

    # Same rule as a full run (flow/core/graph.py, filter_trigger_reachable): in
    # a workflow with triggers, a node no trigger leads to never runs. Cut down
    # to it alone, the definition would have no trigger left, the filter would
    # not apply, and it would run here when it never runs for real.
    gatilhos = {n.get("id") for n in nodes if n.get("type") == "trigger"}
    if gatilhos and not (gatilhos & manter):
        raise WorkflowInputValidationError(
            "Este nó não está ligado a nenhum gatilho, então não roda numa execução. "
            "Ligue-o ao fluxo para ver os dados dele."
        )

    podada = dict(definition)
    podada["nodes"] = [n for n in nodes if n.get("id") in manter]
    podada["edges"] = [
        e for e in edges
        if ponta(e, "source") in manter and ponta(e, "target") in manter
    ]
    return podada
