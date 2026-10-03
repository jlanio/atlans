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
from flow.executor.declared_schema import schema_declarado, catalog_schema
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
def _register_test_nodes():
    NODE_REGISTRY["NoDinamicoTeste"] = NoDinamicoTeste
    NODE_REGISTRY["NoDinamicoSemSchema"] = NoDinamicoSemSchema
    yield
    NODE_REGISTRY.pop("NoDinamicoTeste", None)
    NODE_REGISTRY.pop("NoDinamicoSemSchema", None)


def _executor(*nodes, edges=()) -> WorkflowExecutor:
    return WorkflowExecutor({"nodes": list(nodes), "edges": list(edges)})


def _names(saida: dict) -> list:
    return [f["name"] for f in saida["schema"][0]["fields"]]


def _merge(nid: str = "m") -> dict:
    return {"id": nid, "name": "Merge", "type": "control", "parameters": {"strategy": "first"}}


# ── Outputs declared in the definition ───────────────────────────────────────

async def test_python_script_declares_outputs_via_output_vars():
    ex = _executor({"id": "ps", "name": "PythonScript", "type": "action",
                    "parameters": {"code": "a = 1\nb = 2", "output_vars": "a, b"}})

    out = await ex.simulate_runner()

    assert out["ps"]["status"] == "ok"
    assert out["ps"]["schema_source"] == "declared"
    assert _names(out["ps"]) == ["a", "b"]


async def test_python_script_without_output_vars_uses_default_result():
    ex = _executor({"id": "ps", "name": "PythonScript", "type": "action", "parameters": {}})

    out = await ex.simulate_runner()

    assert _names(out["ps"]) == ["result"]


async def test_empty_output_vars_becomes_error_with_the_run_message(caplog):
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


async def test_non_string_output_vars_becomes_error():
    ex = _executor({"id": "ps", "name": "PythonScript", "type": "action",
                    "parameters": {"code": "x = 1", "output_vars": ["a", "b"]}})

    out = await ex.simulate_runner()

    assert out["ps"] == {"status": "error", "error": "O parâmetro 'output_vars' deve ser uma string."}


async def test_error_in_declared_output_does_not_cascade_to_the_child():
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


async def test_switch_declares_fallback_and_rule_outputs():
    """`rules` chega como JSON string (o editor grava via JSON.stringify)."""
    ex = _executor({"id": "sw", "name": "Switch", "type": "control", "parameters": {
        "rules": '[{"field": "x", "operator": "==", "value": 1, "output": "output_1"}]',
        "fallback_output": "resto",
    }})

    out = await ex.simulate_runner()

    assert out["sw"]["schema_source"] == "declared"
    assert _names(out["sw"]) == ["resto", "output_1"]


async def test_switch_without_fallback_output_uses_output_0():
    ex = _executor({"id": "sw", "name": "Switch", "type": "control", "parameters": {"rules": []}})

    out = await ex.simulate_runner()

    assert _names(out["sw"]) == ["output_0"]


async def test_switch_empty_fallback_output_emits_the_empty_port():
    """Mirrors the run: `parameters.get("fallback_output", "output_0")` only falls
    back to the default when the key is ABSENT; present and empty, the emitted
    port is ''."""
    ex = _executor({"id": "sw", "name": "Switch", "type": "control",
                    "parameters": {"rules": [], "fallback_output": ""}})

    out = await ex.simulate_runner()

    assert out["sw"]["status"] == "ok"
    assert _names(out["sw"]) == [""]


async def test_sub_workflow_input_declares_the_ports():
    ex = _executor({"id": "in", "name": "SubWorkflowInput", "type": "trigger",
                    "parameters": {"ports": ["geometry"]}})

    out = await ex.simulate_runner()

    assert out["in"]["schema_source"] == "declared"
    assert _names(out["in"]) == ["geometry"]


async def test_sub_workflow_input_without_ports_has_empty_schema():
    ex = _executor({"id": "in", "name": "SubWorkflowInput", "type": "trigger", "parameters": {}})

    out = await ex.simulate_runner()

    assert out["in"] == {"status": "ok", "schema": [{"fields": []}], "schema_source": "declared"}


async def test_dynamic_without_simulate_falls_back_to_catalog_outputs():
    ex = _executor({"id": "gj", "name": "ReadGeoJSON", "type": "datasource",
                    "parameters": {"driveFileId": "x"}})

    out = await ex.simulate_runner()

    assert out["gj"]["schema_source"] == "declared"
    assert _names(out["gj"]) == ["output"]


async def test_dynamic_without_simulate_or_outputs_stays_unknown():
    """Nothing to assert is no reason to vanish: the node stays in the response
    and the source says the schema is unknown."""
    ex = _executor({"id": "n1", "name": "NoDinamicoSemSchema", "type": "datasource",
                    "parameters": {}})

    out = await ex.simulate_runner()

    assert out["n1"] == {"status": "ok", "schema": [], "schema_source": "unknown"}


async def test_unknown_source_produces_no_edge_diagnostic():
    ex = _executor(
        {"id": "n1", "name": "NoDinamicoSemSchema", "type": "datasource", "parameters": {}},
        _merge(),
        edges=[{"source": "n1", "target": "m", "from_key": "qualquer"}],
    )
    await ex.simulate_runner()

    assert ex.validate_edges() == []


async def test_node_with_simulate_stays_simulated():
    ex = _executor({"id": "n1", "name": "NoDinamicoTeste", "type": "datasource",
                    "parameters": {}})

    out = await ex.simulate_runner()

    assert out["n1"]["schema_source"] == "simulated"
    assert _names(out["n1"]) == ["col"]


async def test_static_node_gets_schema_source_static():
    ex = _executor(_merge())

    out = await ex.simulate_runner()

    assert out["m"]["schema_source"] == "static"
    assert _names(out["m"]) == ["output"]


# ── validate_edges sees the declared output ──────────────────────────────────

async def test_from_key_outside_output_vars_is_edge_error():
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


async def test_from_key_inside_output_vars_passes():
    ex = _executor(
        {"id": "ps", "name": "PythonScript", "type": "action",
         "parameters": {"code": "a = 1", "output_vars": "a"}},
        _merge(),
        edges=[{"source": "ps", "target": "m", "from_key": "a"}],
    )
    await ex.simulate_runner()

    assert ex.validate_edges() == []


# ── Catalog fields in the simulation ─────────────────────────────────────────

async def test_catalog_fields_enter_the_simulation():
    """ChangeDetector declares its fields in `outputs` (and routes by `branches`):
    all fields appear in the simulated schema."""
    ex = _executor({"id": "cd", "name": "ChangeDetector", "type": "control", "parameters": {}})

    out = await ex.simulate_runner()

    assert out["cd"]["schema_source"] == "static"
    assert {"output", "branch", "previous_hash", "current_hash", "reason"} <= set(_names(out["cd"]))


async def test_internal_protocol_keys_do_not_become_outputs():
    """Response only declares `__response__` in `outputs`; the executor removes it."""
    ex = _executor({"id": "r", "name": "Response", "type": "output", "parameters": {}})

    out = await ex.simulate_runner()

    assert out["r"]["schema"] == [{"fields": []}]


# ── catalog_schema / schema_declarado (puros) ────────────────────────────

def test_catalog_schema_groups_the_flat_fields():
    desc = {"outputs": [{"name": "output", "type": "object"}]}

    assert catalog_schema(desc) == [{"fields": [{"name": "output", "type": "object"}]}]


def test_catalog_schema_filters_internal_names():
    desc = {"outputs": [{"name": "output", "type": "object"},
                        {"name": "__response__", "type": "object"}]}

    assert catalog_schema(desc) == [{"fields": [{"name": "output", "type": "object"}]}]


def test_catalog_schema_without_outputs_has_no_fields():
    assert catalog_schema({}) == [{"fields": []}]
    assert catalog_schema({"outputs": None}) == [{"fields": []}]


def test_declared_schema_with_nothing_to_assert_returns_none():
    assert schema_declarado({"parameters": {}}, {"properties": []}) is None


def test_declared_schema_output_vars_with_spaces_and_blanks():
    desc = {"properties": [{"name": "output_vars"}]}

    assert schema_declarado({"parameters": {"output_vars": " a , b ,, "}}, desc) == \
        [{"fields": [{"name": "a", "type": "any"}, {"name": "b", "type": "any"}]}]


def test_declared_schema_invalid_output_vars_raises_the_run_message():
    desc = {"properties": [{"name": "output_vars"}]}

    with pytest.raises(ValueError, match="deve ser uma string"):
        schema_declarado({"parameters": {"output_vars": ["a"]}}, desc)
    with pytest.raises(ValueError, match="ao menos um nome de variável"):
        schema_declarado({"parameters": {"output_vars": ""}}, desc)


def test_declared_schema_invalid_rules_leave_only_the_fallback():
    desc = {"properties": [{"name": "rules"}, {"name": "fallback_output"}]}

    assert schema_declarado({"properties": {"rules": "{nao e json"}}, desc) == \
        [{"fields": [{"name": "output_0", "type": "any"}]}]


def test_declared_schema_non_string_fallback_output_raises():
    desc = {"properties": [{"name": "rules"}, {"name": "fallback_output"}]}

    with pytest.raises(ValueError, match="fallback_output"):
        schema_declarado({"parameters": {"fallback_output": None}}, desc)
