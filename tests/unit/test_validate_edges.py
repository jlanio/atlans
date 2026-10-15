# tests/unit/test_validate_edges.py
"""
Static edge diagnostics in /validate (PR-E) and the empty-schema guard in the
simulation (F11).

The strict run OMITS the port of a missing from_key (it does not bring down the
workflow because of an optional/dynamic output). The "stale from_key is an
error" enforcement lives here, in static validation, which has the
hand-declared schema.
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

def test_stale_from_key_becomes_error():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "nope"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    diag = ex.validate_edges()
    assert len(diag) == 1
    assert diag[0]["severity"] == "error" and diag[0]["from_key"] == "nope"
    assert diag[0]["source"] == "a" and diag[0]["target"] == "b"


def test_valid_from_key_produces_no_diagnostic():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "output"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output", "meta")}}
    assert ex.validate_edges() == []


def test_porta_do_filho_saindo_de_subworkflow_nao_vira_erro():
    # SubWorkflow returns `{subWorkflowResult, **child ports}`; the ports come from
    # the child's contract, which the simulation does not read. The editor writes
    # the port name as from_key, and that edge is the one that works at run.
    ex = _executor([_n("a", name="SubWorkflow", ntype="control"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "faixa_de_risco"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("subWorkflowResult")}}
    assert ex.validate_edges() == []


def test_from_key_errado_de_outro_no_continua_erro():
    ex = _executor([_n("a", name="Merge", ntype="control"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "faixa_de_risco"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert [d["severity"] for d in ex.validate_edges()] == ["error"]


def test_so_to_key_de_origem_com_varias_saidas_vira_aviso():
    # The run renames the FIRST value of the output (edge_resolver): an HTTP
    # Request's status_code, not the body the edge was meant to carry.
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "to_key": "entrada"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("status_code", "headers", "body")}}
    diag = ex.validate_edges()
    assert [(d["severity"], d.get("code")) for d in diag] == [("warning", "edge_to_key_only")]
    assert "primeiro valor" in diag[0]["message"]


def test_so_to_key_de_origem_com_uma_saida_e_renomear():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "to_key": "entrada"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert ex.validate_edges() == []


def test_to_key_fora_das_entradas_declaradas_vira_aviso():
    # SpatialJoin reads `layerA`/`layerB` by name: `left` is never read.
    ex = _executor([_n("a", ntype="action"), {"id": "j", "type": "spatial", "name": "SpatialJoin", "properties": {}}],
                   [{"source": "a", "target": "j", "from_key": "output", "to_key": "left"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    diag = ex.validate_edges()
    assert [(d["severity"], d.get("code")) for d in diag] == [("warning", "edge_to_key_unknown")]
    assert "layerA" in diag[0]["message"]


def test_to_key_declarado_nao_avisa():
    ex = _executor([_n("a", ntype="action"), {"id": "j", "type": "spatial", "name": "SpatialJoin", "properties": {}}],
                   [{"source": "a", "target": "j", "from_key": "output", "to_key": "layerA"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert ex.validate_edges() == []


def test_to_key_fora_das_portas_do_subworkflowoutput_vira_aviso():
    saida = {"id": "s", "type": "output", "name": "SubWorkflowOutput", "properties": {"ports": ["faixa"]}}
    ex = _executor([_n("a", ntype="action"), saida],
                   [{"source": "a", "target": "s", "from_key": "output", "to_key": "faixas"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert [d.get("code") for d in ex.validate_edges()] == ["edge_to_key_unknown"]


def test_spread_from_multi_output_source_becomes_warning():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b"}])  # no from_key/to_key
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("x", "y")}}
    diag = ex.validate_edges()
    assert len(diag) == 1 and diag[0]["severity"] == "warning"


def test_spread_from_single_output_source_does_not_warn():
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert ex.validate_edges() == []


def test_branch_edge_is_not_ambiguous():
    # bool condition → it is a branch edge, not an ambiguous spread.
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "condition": True}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("x", "y")}}
    assert ex.validate_edges() == []


def test_source_without_known_schema_is_not_diagnosed():
    # No declared outputs (a dynamic one that did not simulate) → cannot flag a typo.
    ex = _executor([_n("a", ntype="action"), _n("b")],
                   [{"source": "a", "target": "b", "from_key": "qualquer"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": []}}
    assert ex.validate_edges() == []


# ── F11: schema == [] does not cascade an error in the preview ───────────────

class _ParentWithoutOutput(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "PaiSemSaida", "type": "action", "properties": [], "outputs": []}

    async def execute(self, inputs):
        return {}


class _DynamicChild(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "FilhoDinamico", "type": "action", "properties": [], "dynamic_output": True}

    @classmethod
    async def simulate(cls, params, inputs):
        return [{"fields": [{"name": "ok", "type": "any"}]}]

    async def execute(self, inputs):
        return {}


@pytest.fixture
def _register_nodes():
    from flow.registry import NODE_REGISTRY
    NODE_REGISTRY["PaiSemSaida"] = _ParentWithoutOutput
    NODE_REGISTRY["FilhoDinamico"] = _DynamicChild
    try:
        yield
    finally:
        NODE_REGISTRY.pop("PaiSemSaida", None)
        NODE_REGISTRY.pop("FilhoDinamico", None)


def test_empty_parent_schema_does_not_cascade_error(_register_nodes):
    # Parent with outputs=[] (like SubWorkflowInput/Output). Before:
    # schema[0] on [] → IndexError → child marked 'error' and a cascade. Now ok.
    ex = _executor(
        [{"id": "p", "type": "action", "name": "PaiSemSaida", "properties": {}},
         {"id": "c", "type": "action", "name": "FilhoDinamico", "properties": {}}],
        [{"source": "p", "target": "c", "from_key": "x"}],
    )
    asyncio.run(ex.simulate_runner())
    assert ex.simulated_outputs["c"]["status"] == "ok", ex.simulated_outputs["c"]


# ── Target-side checks run whatever the source ────────────────────────────────

def _merge_com_portas(nid="m", portas=("a", "b")):
    return {"id": nid, "type": "control", "name": "Merge", "properties": {"strategy": "all", "ports": list(portas)}}


def test_aresta_de_subworkflow_sem_to_key_num_merge_com_portas_avisa():
    # The child port is not in the simulated schema: the source check skips it,
    # but the target check (no port on the Merge) used to be skipped along.
    ex = _executor([_n("s", name="SubWorkflow", ntype="control"), _merge_com_portas()],
                   [{"source": "s", "target": "m", "from_key": "porta_do_filho"}])
    ex.simulated_outputs = {"s": {"status": "ok", "schema": _schema("subWorkflowResult")}}
    assert [d.get("code") for d in ex.validate_edges()] == ["edge_to_key_missing"]


def test_origem_sem_esquema_conhecido_ainda_tem_o_destino_conferido():
    ex = _executor([_n("a", ntype="action"), _merge_com_portas()],
                   [{"source": "a", "target": "m", "from_key": "qualquer"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": []}}
    assert [d.get("code") for d in ex.validate_edges()] == ["edge_to_key_missing"]
    ex.simulated_outputs = {"a": {"status": "error", "error": "falhou"}}
    assert [d.get("code") for d in ex.validate_edges()] == ["edge_to_key_missing"]


def test_to_key_fora_das_camadas_da_carta_vira_aviso():
    carta = {"id": "c", "type": "output", "name": "CartaImagem", "properties": {"ports": ["lotes", "quadras"]}}
    ex = _executor([_n("a", ntype="action"), carta],
                   [{"source": "a", "target": "c", "from_key": "output", "to_key": "lote"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert [d.get("code") for d in ex.validate_edges()] == ["edge_to_key_unknown"]


@pytest.mark.parametrize("alvo", [
    # One declared input: the node takes whatever arrives (get_first_gdf).
    {"id": "h", "type": "spatial", "name": "ConvexHullNode", "properties": {}},
    # A Carta with a single layer takes the layer that arrives.
    {"id": "h", "type": "output", "name": "CartaImagem", "properties": {"ports": ["lotes"]}},
])
def test_to_key_com_outro_nome_onde_qualquer_chave_serve_nao_avisa(alvo):
    ex = _executor([_n("a", ntype="action"), alvo],
                   [{"source": "a", "target": "h", "from_key": "output", "to_key": "pontos"}])
    ex.simulated_outputs = {"a": {"status": "ok", "schema": _schema("output")}}
    assert ex.validate_edges() == []
