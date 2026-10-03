"""
Parameters of type "object" arriving serialized from the canvas.

Real regression: when configuring a SubWorkflow, the run failed with

    O parametro 'inputsMapping' deve ser um objeto (dict).

The node editor only stores primitives — `setNodeField` has the signature
(field, value: string | number | boolean) — so the UI helpers serialize
structures with JSON.stringify. The value arrived as a str and the check
`isinstance(value, dict)` rejected something the UI had stored correctly.

`ports` (SubWorkflowInput/Output) exposes the same pitfall from another side:
it declares type "object" but the legitimate value is a LIST.
"""
import pytest

from flow.utils.parameter_validation import validate_node_parameters


def _prop(name="inputsMapping", default=None):
    return [{"name": name, "type": "object", "default": default if default is not None else {}}]


# ── The case that used to break ──────────────────────────────────────────────

def test_dict_serializado_pela_ui_e_aceito():
    out = validate_node_parameters(
        {"inputsMapping": '{"geometry": "camada_wfs"}'}, _prop(),
    )
    assert out["inputsMapping"] == {"geometry": "camada_wfs"}


def test_lista_serializada_e_aceita():
    """`ports` declara type "object" mas o valor legitimo e lista."""
    out = validate_node_parameters(
        {"ports": '["geometry", "buffer_m"]'}, _prop("ports", default=[]),
    )
    assert out["ports"] == ["geometry", "buffer_m"]


def test_string_vazia_vira_objeto_vazio():
    """A field cleared in the UI must not bring down the run."""
    out = validate_node_parameters({"inputsMapping": ""}, _prop())
    assert out["inputsMapping"] == {}


# ── Comportamento preservado ─────────────────────────────────────────────────

def test_dict_nativo_continua_passando():
    out = validate_node_parameters({"inputsMapping": {"a": "b"}}, _prop())
    assert out["inputsMapping"] == {"a": "b"}


def test_lista_nativa_continua_passando():
    out = validate_node_parameters({"ports": ["a"]}, _prop("ports", default=[]))
    assert out["ports"] == ["a"]


# ── Invalid input is still rejected ──────────────────────────────────────────

def test_json_malformado_falha_citando_o_valor():
    with pytest.raises(ValueError, match="JSON válido"):
        validate_node_parameters({"inputsMapping": "{isto nao e json"}, _prop())


def test_json_escalar_e_recusado():
    """'123' decodes, but it is not a structure — it cannot become an object parameter."""
    with pytest.raises(ValueError, match="objeto"):
        validate_node_parameters({"inputsMapping": "123"}, _prop())


def test_tipo_incompativel_e_recusado():
    with pytest.raises(ValueError, match="Tipo recebido: int"):
        validate_node_parameters({"inputsMapping": 42}, _prop())
