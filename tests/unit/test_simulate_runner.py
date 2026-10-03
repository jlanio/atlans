# tests/unit/test_simulate_runner.py
"""simulate_runner must actually call the simulate() of dynamic nodes.

Regression: the call was `validate_node_parameters(node_def, node_cls)`, but the
signature is (parametros, lista_de_propriedades). Passing the CLASS made
`for prop in props` raise TypeError, which the loop's `except Exception`
turned into {"status": "error"} — so `simulate()` never ran and
POST /workflows/validate returned an error for every node with dynamic_output.
"""
import pytest

from flow.executor.core import WorkflowExecutor
from flow.nodes.base import BaseNode
from flow.registry import NODE_REGISTRY

_RECEBIDO: dict = {}


class NoDinamicoTeste(BaseNode):
    """dynamic_output=True — the only type that reaches simulate()."""

    @classmethod
    def description(cls):
        return {
            "name": "NoDinamicoTeste",
            "type": "datasource",
            "dynamic_output": True,
            "properties": [
                {"name": "query", "type": "string", "default": ""},
                {"name": "limite", "type": "integer", "default": 10},
            ],
        }

    @classmethod
    async def simulate(cls, parameters: dict, simulated_inputs: dict = None) -> list:
        _RECEBIDO["params"] = parameters
        if parameters.get("query") == "__boom__":
            raise ValueError("credencial ausente")
        return [{"fields": [{"name": "col", "type": "string"}]}]

    async def execute(self, inputs):  # pragma: no cover - simulation does not execute
        return {}


class NoEstaticoTeste(BaseNode):
    @classmethod
    def description(cls):
        return {
            "name": "NoEstaticoTeste",
            "type": "datasource",
            "properties": [],
            "outputs": [{"name": "output", "type": "object"}],
        }

    async def execute(self, inputs):  # pragma: no cover
        return {}


@pytest.fixture(autouse=True)
def _registra_nos_de_teste():
    """The factory resolves through the global NODE_REGISTRY — registers and cleans up afterwards."""
    _RECEBIDO.clear()
    NODE_REGISTRY["NoDinamicoTeste"] = NoDinamicoTeste
    NODE_REGISTRY["NoEstaticoTeste"] = NoEstaticoTeste
    yield
    NODE_REGISTRY.pop("NoDinamicoTeste", None)
    NODE_REGISTRY.pop("NoEstaticoTeste", None)


def _executor(node: dict) -> WorkflowExecutor:
    return WorkflowExecutor({"nodes": [node], "edges": []})


async def test_simulate_e_chamado_com_os_parametros_do_no():
    """`parameters` format — what the validation (`validate_service`) sends."""
    ex = _executor({
        "id": "n1", "name": "NoDinamicoTeste", "type": "datasource",
        "parameters": {"query": "SELECT 1", "limite": 5},
    })

    out = await ex.simulate_runner()

    assert out["n1"]["status"] == "ok", out["n1"]
    assert out["n1"]["schema"][0]["fields"][0]["name"] == "col"
    assert _RECEBIDO["params"]["query"] == "SELECT 1"
    assert _RECEBIDO["params"]["limite"] == 5


async def test_aceita_o_formato_properties_da_definition_salva():
    """The persisted definition uses `properties`, not `parameters`."""
    ex = _executor({
        "id": "n1", "name": "NoDinamicoTeste", "type": "datasource",
        "properties": {"query": "SELECT 2", "limite": 7},
    })

    out = await ex.simulate_runner()

    assert out["n1"]["status"] == "ok", out["n1"]
    assert _RECEBIDO["params"]["query"] == "SELECT 2"


async def test_defaults_das_propriedades_sao_aplicados():
    ex = _executor({
        "id": "n1", "name": "NoDinamicoTeste", "type": "datasource", "parameters": {},
    })

    await ex.simulate_runner()

    assert _RECEBIDO["params"]["limite"] == 10


async def test_erro_no_simulate_vira_status_error():
    """One node with a problem must not bring down the whole validation."""
    ex = _executor({
        "id": "n1", "name": "NoDinamicoTeste", "type": "datasource",
        "parameters": {"query": "__boom__"},
    })

    out = await ex.simulate_runner()

    assert out["n1"]["status"] == "error"
    assert "credencial ausente" in out["n1"]["error"]


async def test_erro_no_simulate_e_logado_e_os_demais_nos_seguem(caplog):
    """The exception was swallowed without a trace: a broken simulate() showed up as
    "node without schema" and nobody found out why. The warning identifies the node
    and the cause — and the simulation of the other nodes goes on."""
    ex = WorkflowExecutor({"nodes": [
        {"id": "n1", "name": "NoDinamicoTeste", "type": "datasource",
         "parameters": {"query": "__boom__"}},
        {"id": "n2", "name": "NoEstaticoTeste", "type": "datasource",
         "parameters": {}},
    ], "edges": []})

    with caplog.at_level("WARNING", logger="flow.executor.core"):
        out = await ex.simulate_runner()

    registros = [r for r in caplog.records
                 if r.levelname == "WARNING" and "simulate()" in r.message]
    assert registros, "a falha do simulate tinha que virar warning"
    assert "n1" in registros[0].message
    assert "NoDinamicoTeste" in registros[0].message
    assert "credencial ausente" in registros[0].message
    assert out["n1"]["status"] == "error"
    assert out["n2"]["status"] == "ok", "a falha de um nó não pode parar a simulação"


async def test_no_estatico_usa_o_schema_declarado():
    ex = _executor({
        "id": "n1", "name": "NoEstaticoTeste", "type": "datasource", "parameters": {},
    })

    out = await ex.simulate_runner()

    assert out["n1"]["status"] == "ok"
    assert out["n1"]["schema"][0]["fields"][0]["name"] == "output"
