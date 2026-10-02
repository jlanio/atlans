# tests/unit/test_simulate_runner.py
"""simulate_runner precisa realmente chamar o simulate() dos nos dinamicos.

Regressao: a chamada era `validate_node_parameters(node_def, node_cls)`, mas a
assinatura e (parametros, lista_de_propriedades). Passar a CLASSE fazia
`for prop in props` levantar TypeError, que o `except Exception` do laco
convertia em {"status": "error"} — entao `simulate()` nunca rodava e
POST /workflows/validate devolvia erro para todo no com dynamic_output.
"""
import pytest

from flow.executor.core import WorkflowExecutor
from flow.nodes.base import BaseNode
from flow.registry import NODE_REGISTRY

_RECEBIDO: dict = {}


class NoDinamicoTeste(BaseNode):
    """dynamic_output=True — o único tipo que chega a simulate()."""

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

    async def execute(self, inputs):  # pragma: no cover - simulação não executa
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
    """A factory resolve pelo NODE_REGISTRY global — registra e limpa depois."""
    _RECEBIDO.clear()
    NODE_REGISTRY["NoDinamicoTeste"] = NoDinamicoTeste
    NODE_REGISTRY["NoEstaticoTeste"] = NoEstaticoTeste
    yield
    NODE_REGISTRY.pop("NoDinamicoTeste", None)
    NODE_REGISTRY.pop("NoEstaticoTeste", None)


def _executor(node: dict) -> WorkflowExecutor:
    return WorkflowExecutor({"nodes": [node], "edges": []})


async def test_simulate_e_chamado_com_os_parametros_do_no():
    """Formato `parameters` — o que a validação (`validate_service`) envia."""
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
    """A definition persistida usa `properties`, não `parameters`."""
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
    """Um nó com problema não pode derrubar a validação inteira."""
    ex = _executor({
        "id": "n1", "name": "NoDinamicoTeste", "type": "datasource",
        "parameters": {"query": "__boom__"},
    })

    out = await ex.simulate_runner()

    assert out["n1"]["status"] == "error"
    assert "credencial ausente" in out["n1"]["error"]


async def test_erro_no_simulate_e_logado_e_os_demais_nos_seguem(caplog):
    """A exceção era engolida sem rastro: um simulate() quebrado aparecia como
    "nó sem schema" e ninguém descobria o porquê. O warning identifica o nó e a
    causa — e a simulação dos demais nós continua."""
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
