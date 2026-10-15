# tests/unit/test_aresta_malformada.py
"""
An edge that does not connect two nodes.

The definition is a free dict: an edge with no `source` or `target` (or a
`null` in the list) was saved through REST as written. The canvas cannot draw
it, and the executor raised a bare KeyError on it, taking down the whole run
before any node. Now REST refuses it (422), the executor skips it as an orphan
and the validation reports it.
"""
import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.routers import workflows_router as WR
from flow.executor.core import WorkflowExecutor
from flow.utils.definition_lint import lint_definition


def _definicao(*arestas):
    return {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "Merge", "properties": {"strategy": "first"}},
            {"id": "m", "type": "control", "name": "Merge", "properties": {"strategy": "first"}},
        ],
        "edges": [{"source": "t", "target": "m"}, *arestas],
    }


@pytest.mark.parametrize("aresta", [{"source": "t"}, {"target": "m"}, {"source": "", "target": "m"}, None, "t->m"])
def test_rest_recusa_aresta_sem_as_duas_pontas(aresta):
    with pytest.raises(HTTPException) as exc:
        WR._recusar_arestas_malformadas(_definicao(aresta))
    assert exc.value.status_code == 422
    assert "posição 1" in exc.value.detail


def test_rest_recusa_edges_que_nao_e_lista():
    with pytest.raises(HTTPException) as exc:
        WR._recusar_arestas_malformadas({"nodes": [], "edges": {"source": "t", "target": "m"}})
    assert exc.value.status_code == 422


@pytest.mark.parametrize("definicao", [_definicao(), {"nodes": []}, {"nodes": [], "edges": None}, None])
def test_rest_aceita_o_que_liga_nos(definicao):
    WR._recusar_arestas_malformadas(definicao)


def test_run_segue_sem_a_aresta_malformada():
    ex = WorkflowExecutor(_definicao({"source": "t"}, None), task_id="malformada", publisher=MagicMock())
    final = asyncio.run(ex.run(initial_inputs={"t": {"output": 1}}))
    assert final["m"]["output"] == 1


def test_validacao_aponta_a_aresta_como_orfa():
    # The MCP route's Pydantic refuses it before the lint; the lint itself, which
    # also serves other callers, must not crash on it.
    relatorio = lint_definition(
        _definicao({"source": "t", "target": None})["nodes"],
        _definicao({"source": "t", "target": None})["edges"],
        registry_names={"Merge"},
    )
    assert [d.code for d in relatorio.warnings if d.code == "orphan_edge"] == ["orphan_edge"]
