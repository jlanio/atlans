# tests/unit/test_mcp_resumo_das_arestas.py
"""
The edges in `get_workflow`'s summary say what the run does with them.

`source_handle` was left out as "canvas drawing", but it routes a branch edge
written without `condition` and names the SubWorkflow port an edge leaves from:
an agent that rewrote a workflow from the summary lost both. And an edge saved
from port `r2` with the envelope as key reads as `r2` in the run, so that is
the key the summary shows.
"""
from app.mcp.saida import definition_summary


def _resumo(*arestas):
    return definition_summary({"nodes": [{"id": "a"}, {"id": "b"}], "edges": list(arestas)})["edges"]


def test_handle_de_ramo_aparece():
    assert _resumo({"source": "a", "target": "b", "source_handle": "true"}) == [
        {"source": "a", "target": "b", "source_handle": "true"},
    ]


def test_porta_do_subfluxo_aparece_com_a_chave_que_o_run_entrega():
    assert _resumo({"source": "a", "target": "b", "source_handle": "r2", "from_key": "subWorkflowResult"}) == [
        {"source": "a", "target": "b", "from_key": "r2", "source_handle": "r2"},
    ]


def test_aresta_sem_handle_nao_ganha_chaves_vazias():
    assert _resumo({"source": "a", "target": "b", "from_key": "output", "source_handle": None, "to_key": ""}) == [
        {"source": "a", "target": "b", "from_key": "output"},
    ]
