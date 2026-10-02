# tests/unit/test_validate_edges.py
"""
Diagnósticos estáticos de aresta no /validate (PR-E) e o guard de schema vazio
na simulação (F11).

O run strict OMITE a porta de um from_key ausente (não derruba o fluxo por causa
de saída opcional/dinâmica). O enforcement "from_key defasado é erro" mora aqui,
na validação estática, que tem o schema declarado à mão.
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

def test_from_key_defasado_vira_erro():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "nope"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    diag = ex.validate_edges()
    assert len(diag) == 1
    assert diag[0]["severity"] == "error" and diag[0]["from_key"] == "nope"
    assert diag[0]["source"] == "a" and diag[0]["target"] == "b"


def test_from_key_valido_nao_gera_diagnostico():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "output"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output", "meta")}}
    assert ex.validate_edges() == []


def test_spread_de_origem_multi_saida_vira_aviso():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b"}])  # sem from_key/to_key
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("x", "y")}}
    diag = ex.validate_edges()
    assert len(diag) == 1 and diag[0]["severity"] == "warning"


def test_spread_de_origem_unica_saida_nao_avisa():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert ex.validate_edges() == []


def test_aresta_de_ramo_nao_e_ambigua():
    # condition bool → é aresta de ramo, não spread ambíguo.
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "condition": True}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("x", "y")}}
    assert ex.validate_edges() == []


def test_origem_sem_schema_conhecido_nao_diagnostica():
    # Sem saídas declaradas (dynamic que não simulou) → não dá para acusar typo.
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "qualquer"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": []}}
    assert ex.validate_edges() == []


# ── F11: schema == [] não cascateia erro no preview ──────────────────────────

class _PaiSemSaida(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "PaiSemSaida", "type": "action", "properties": [], "outputs": []}

    async def execute(self, inputs):
        return {}


class _FilhoDinamico(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "FilhoDinamico", "type": "action", "properties": [], "dynamic_output": True}

    @classmethod
    async def simulate(cls, params, inputs):
        return [{"fields": [{"name": "ok", "type": "any"}]}]

    async def execute(self, inputs):
        return {}


@pytest.fixture
def _registra_nos():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["PaiSemSaida"] = _PaiSemSaida
    NODE_REGISTRY["FilhoDinamico"] = _FilhoDinamico
    try:
        yield
    finally:
        NODE_REGISTRY.pop("PaiSemSaida", None)
        NODE_REGISTRY.pop("FilhoDinamico", None)


def test_schema_vazio_do_pai_nao_cascateia_erro(_registra_nos):
    # Pai com outputs=[] (como SubWorkflowInput/Output). Antes:
    # schema[0] em [] → IndexError → filho marcado 'error' e cascata. Agora ok.
    ex = _executor(
        [{"id": "p", "type": "action", "name": "PaiSemSaida", "properties": {}},
         {"id": "c", "type": "action", "name": "FilhoDinamico", "properties": {}}],
        [{"source": "p", "target": "c", "from_key": "x"}],
    )
    asyncio.run(ex.simulate_runner())
    assert ex.simulated_outputs["c"]["status"] == "ok", ex.simulated_outputs["c"]
