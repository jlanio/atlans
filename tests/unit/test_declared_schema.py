# tests/unit/test_declared_schema.py
"""A node with `dynamic_output` and no `simulate()` no longer vanishes from /validate.

Eight catalog nodes (PythonScript, Switch, ReadGeoJSON, WFS, DataInput...)
fell into a silent `continue`: no schema in the panel and no edge diagnostics.
The outputs are written in the definition itself (`output_vars`, `rules`/
`fallback_output`, `ports`) or in the catalog's `outputs`; now simulate_runner
returns them with `schema_source` saying where they came from — and `unknown`
when there is nothing to assert, instead of omitting the node.

Real registry + WorkflowExecutor, modeled on test_simulate_runner.py.
"""
from __future__ import annotations

import pytest

from flow.executor.core import WorkflowExecutor
from flow.executor.declared_schema import schema_declarado, schema_do_catalogo
from flow.nodes.base import BaseNode
from flow.registry import NODE_REGISTRY


class NoDinamicoTeste(BaseNode):
    """dynamic_output=True COM simulate(): o caminho simulado continua o mesmo."""

    @classmethod
    def description(cls):
        return {
            "name": "NoDinamicoTeste",
            "type": "datasource",
            "dynamic_output": True,
            "properties": [{"name": "query", "type": "string", "default": ""}],
        }

    @classmethod
    async def simulate(cls, parameters: dict, simulated_inputs: dict = None) -> list:
        return [{"fields": [{"name": "col", "type": "string"}]}]

    async def execute(self, inputs):  # pragma: no cover - simulation does not execute
        return {}


class NoDinamicoSemSchema(BaseNode):
    """dynamic_output=True, no simulate() and no outputs: nothing to assert."""

    @classmethod
    def description(cls):
        return {
            "name": "NoDinamicoSemSchema",
            "type": "datasource",
            "dynamic_output": True,
            "properties": [],
        }

    async def execute(self, inputs):  # pragma: no cover
        return {}


@pytest.fixture(autouse=True)
def _registra_nos_de_teste():
    NODE_REGISTRY["NoDinamicoTeste"] = NoDinamicoTeste
    NODE_REGISTRY["NoDinamicoSemSchema"] = NoDinamicoSemSchema
    yield
    NODE_REGISTRY.pop("NoDinamicoTeste", None)
    NODE_REGISTRY.pop("NoDinamicoSemSchema", None)


def _executor(*nodes, edges=()) -> WorkflowExecutor:
    return WorkflowExecutor({"nodes": list(nodes), "edges": list(edges)})


def _nomes(saida: dict) -> list:
    return [f["name"] for f in saida["schema"][0]["fields"]]


def _merge(nid: str = "m") -> dict:
    return {"id": nid, "name": "Merge", "type": "control", "parameters": {"strategy": "first"}}


# ── Outputs declared in the definition ───────────────────────────────────────

async def test_python_script_declara_as_saidas_por_output_vars():
    ex = _executor({"id": "ps", "name": "PythonScript", "type": "action",
                    "parameters": {"code": "a = 1\nb = 2", "output_vars": "a, b"}})

    out = await ex.simulate_runner()

    assert out["ps"]["status"] == "ok"
    assert out["ps"]["schema_source"] == "declared"
    assert _nomes(out["ps"]) == ["a", "b"]


async def test_python_script_sem_output_vars_usa_o_default_result():
    ex = _executor({"id": "ps", "name": "PythonScript", "type": "action", "parameters": {}})

    out = await ex.simulate_runner()

    assert _nomes(out["ps"]) == ["result"]


async def test_output_vars_vazio_vira_erro_com_a_frase_do_run(caplog):
    """Before: schema `[{"fields": []}]` with `ok` — and with no known outputs the
    edge diagnostics switched off. The run rejects with this sentence."""
    ex = _executor({"id": "ps", "name": "PythonScript", "type": "action",
                    "parameters": {"code": "x = 1", "output_vars": " , "}})

    with caplog.at_level("WARNING", logger="flow.executor.core"):
        out = await ex.simulate_runner()

    assert out["ps"] == {
        "status": "error", "error": "'output_vars' deve conter ao menos um nome de variável.",
    }
    avisos = [r for r in caplog.records if r.levelname == "WARNING" and "ps" in r.message]
    assert avisos and "output_vars" in avisos[0].message and "PythonScript" in avisos[0].message


async def test_output_vars_que_nao_e_string_vira_erro():
    ex = _executor({"id": "ps", "name": "PythonScript", "type": "action",
                    "parameters": {"code": "x = 1", "output_vars": ["a", "b"]}})

    out = await ex.simulate_runner()

    assert out["ps"] == {"status": "error", "error": "O parâmetro 'output_vars' deve ser uma string."}


async def test_erro_na_saida_declarada_nao_cascateia_para_o_filho():
    ex = _executor(
        {"id": "ps", "name": "PythonScript", "type": "action",
         "parameters": {"code": "x = 1", "output_vars": ""}},
        _merge(),
        edges=[{"source": "ps", "target": "m", "from_key": "a"}],
    )

    out = await ex.simulate_runner()

    assert out["ps"]["status"] == "error"
    assert out["m"]["status"] == "ok"
    assert ex.validate_edges() == []  # origem em erro: nada a afirmar sobre a aresta


async def test_switch_declara_fallback_e_saidas_das_regras():
    """`rules` chega como JSON string (o editor grava via JSON.stringify)."""
    ex = _executor({"id": "sw", "name": "Switch", "type": "control", "parameters": {
        "rules": '[{"field": "x", "operator": "==", "value": 1, "output": "output_1"}]',
        "fallback_output": "resto",
    }})

    out = await ex.simulate_runner()

    assert out["sw"]["schema_source"] == "declared"
    assert _nomes(out["sw"]) == ["resto", "output_1"]


async def test_switch_sem_fallback_output_usa_output_0():
    ex = _executor({"id": "sw", "name": "Switch", "type": "control", "parameters": {"rules": []}})

    out = await ex.simulate_runner()

    assert _nomes(out["sw"]) == ["output_0"]


async def test_switch_fallback_output_vazio_emite_a_porta_vazia():
    """Mirrors the run: `parameters.get("fallback_output", "output_0")` only falls
    back to the default when the key is ABSENT; present and empty, the emitted
    port is ''."""
    ex = _executor({"id": "sw", "name": "Switch", "type": "control",
                    "parameters": {"rules": [], "fallback_output": ""}})

    out = await ex.simulate_runner()

    assert out["sw"]["status"] == "ok"
    assert _nomes(out["sw"]) == [""]


async def test_sub_workflow_input_declara_as_ports():
    ex = _executor({"id": "in", "name": "SubWorkflowInput", "type": "trigger",
                    "parameters": {"ports": ["geometry"]}})

    out = await ex.simulate_runner()

    assert out["in"]["schema_source"] == "declared"
    assert _nomes(out["in"]) == ["geometry"]


async def test_sub_workflow_input_sem_ports_tem_schema_vazio():
    ex = _executor({"id": "in", "name": "SubWorkflowInput", "type": "trigger", "parameters": {}})

    out = await ex.simulate_runner()

    assert out["in"] == {"status": "ok", "schema": [{"fields": []}], "schema_source": "declared"}


async def test_dinamico_sem_simulate_cai_nos_outputs_do_catalogo():
    ex = _executor({"id": "gj", "name": "ReadGeoJSON", "type": "datasource",
                    "parameters": {"driveFileId": "x"}})

    out = await ex.simulate_runner()

    assert out["gj"]["schema_source"] == "declared"
    assert _nomes(out["gj"]) == ["output"]


async def test_dinamico_sem_simulate_e_sem_outputs_fica_como_unknown():
    """Nothing to assert is no reason to vanish: the node stays in the response
    and the source says the schema is unknown."""
    ex = _executor({"id": "n1", "name": "NoDinamicoSemSchema", "type": "datasource",
                    "parameters": {}})

    out = await ex.simulate_runner()

    assert out["n1"] == {"status": "ok", "schema": [], "schema_source": "unknown"}


async def test_origem_unknown_nao_gera_diagnostico_de_aresta():
    ex = _executor(
        {"id": "n1", "name": "NoDinamicoSemSchema", "type": "datasource", "parameters": {}},
        _merge(),
        edges=[{"source": "n1", "target": "m", "from_key": "qualquer"}],
    )
    await ex.simulate_runner()

    assert ex.validate_edges() == []


async def test_no_com_simulate_continua_simulado():
    ex = _executor({"id": "n1", "name": "NoDinamicoTeste", "type": "datasource",
                    "parameters": {}})

    out = await ex.simulate_runner()

    assert out["n1"]["schema_source"] == "simulated"
    assert _nomes(out["n1"]) == ["col"]


async def test_no_estatico_ganha_schema_source_static():
    ex = _executor(_merge())

    out = await ex.simulate_runner()

    assert out["m"]["schema_source"] == "static"
    assert _nomes(out["m"]) == ["output"]


# ── validate_edges sees the declared output ──────────────────────────────────

async def test_from_key_fora_de_output_vars_e_erro_de_aresta():
    ex = _executor(
        {"id": "ps", "name": "PythonScript", "type": "action",
         "parameters": {"code": "a = 1", "output_vars": "a"}},
        _merge(),
        edges=[{"source": "ps", "target": "m", "from_key": "c"}],
    )
    await ex.simulate_runner()

    diag = ex.validate_edges()

    assert len(diag) == 1
    assert diag[0]["severity"] == "error" and diag[0]["from_key"] == "c"
    assert diag[0]["source"] == "ps" and diag[0]["target"] == "m"


async def test_from_key_dentro_de_output_vars_passa():
    ex = _executor(
        {"id": "ps", "name": "PythonScript", "type": "action",
         "parameters": {"code": "a = 1", "output_vars": "a"}},
        _merge(),
        edges=[{"source": "ps", "target": "m", "from_key": "a"}],
    )
    await ex.simulate_runner()

    assert ex.validate_edges() == []


# ── Catalog fields in the simulation ─────────────────────────────────────────

async def test_campos_do_catalogo_entram_na_simulacao():
    """ChangeDetector declares its fields in `outputs` (and routes by `branches`):
    all fields appear in the simulated schema."""
    ex = _executor({"id": "cd", "name": "ChangeDetector", "type": "control", "parameters": {}})

    out = await ex.simulate_runner()

    assert out["cd"]["schema_source"] == "static"
    assert {"output", "branch", "previous_hash", "current_hash", "reason"} <= set(_nomes(out["cd"]))


async def test_chaves_internas_do_protocolo_nao_viram_saida():
    """Response only declares `__response__` in `outputs`; the executor removes it."""
    ex = _executor({"id": "r", "name": "Response", "type": "output", "parameters": {}})

    out = await ex.simulate_runner()

    assert out["r"]["schema"] == [{"fields": []}]


# ── schema_do_catalogo / schema_declarado (puros) ────────────────────────────

def test_schema_do_catalogo_agrupa_os_campos_planos():
    desc = {"outputs": [{"name": "output", "type": "object"}]}

    assert schema_do_catalogo(desc) == [{"fields": [{"name": "output", "type": "object"}]}]


def test_schema_do_catalogo_filtra_nomes_internos():
    desc = {"outputs": [{"name": "output", "type": "object"},
                        {"name": "__response__", "type": "object"}]}

    assert schema_do_catalogo(desc) == [{"fields": [{"name": "output", "type": "object"}]}]


def test_schema_do_catalogo_sem_outputs_fica_sem_campos():
    assert schema_do_catalogo({}) == [{"fields": []}]
    assert schema_do_catalogo({"outputs": None}) == [{"fields": []}]


def test_schema_declarado_sem_nada_a_afirmar_devolve_none():
    assert schema_declarado({"parameters": {}}, {"properties": []}) is None


def test_schema_declarado_output_vars_com_espacos_e_vazios():
    desc = {"properties": [{"name": "output_vars"}]}

    assert schema_declarado({"parameters": {"output_vars": " a , b ,, "}}, desc) == \
        [{"fields": [{"name": "a", "type": "any"}, {"name": "b", "type": "any"}]}]


def test_schema_declarado_output_vars_invalido_levanta_a_frase_do_run():
    desc = {"properties": [{"name": "output_vars"}]}

    with pytest.raises(ValueError, match="deve ser uma string"):
        schema_declarado({"parameters": {"output_vars": ["a"]}}, desc)
    with pytest.raises(ValueError, match="ao menos um nome de variável"):
        schema_declarado({"parameters": {"output_vars": ""}}, desc)


def test_schema_declarado_rules_invalidas_deixam_so_o_fallback():
    desc = {"properties": [{"name": "rules"}, {"name": "fallback_output"}]}

    assert schema_declarado({"properties": {"rules": "{nao e json"}}, desc) == \
        [{"fields": [{"name": "output_0", "type": "any"}]}]


def test_schema_declarado_fallback_output_nao_string_levanta():
    desc = {"properties": [{"name": "rules"}, {"name": "fallback_output"}]}

    with pytest.raises(ValueError, match="fallback_output"):
        schema_declarado({"parameters": {"fallback_output": None}}, desc)
