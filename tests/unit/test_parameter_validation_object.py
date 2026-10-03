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

def test_dict_serialized_by_the_ui_is_accepted():
    out = validate_node_parameters(
        {"inputsMapping": '{"geometry": "camada_wfs"}'}, _prop(),
    )
    assert out["inputsMapping"] == {"geometry": "camada_wfs"}


def test_serialized_list_is_accepted():
    """`ports` declara type "object" mas o valor legitimo e lista."""
    out = validate_node_parameters(
        {"ports": '["geometry", "buffer_m"]'}, _prop("ports", default=[]),
    )
    assert out["ports"] == ["geometry", "buffer_m"]


def test_empty_string_becomes_empty_object():
    """A field cleared in the UI must not bring down the run."""
    out = validate_node_parameters({"inputsMapping": ""}, _prop())
    assert out["inputsMapping"] == {}


# ── Comportamento preservado ─────────────────────────────────────────────────

def test_native_dict_still_passes():
    out = validate_node_parameters({"inputsMapping": {"a": "b"}}, _prop())
    assert out["inputsMapping"] == {"a": "b"}


def test_native_list_still_passes():
    out = validate_node_parameters({"ports": ["a"]}, _prop("ports", default=[]))
    assert out["ports"] == ["a"]


# ── Invalid input is still rejected ──────────────────────────────────────────

def test_malformed_json_fails_citing_the_value():
    with pytest.raises(ValueError, match="JSON válido"):
        validate_node_parameters({"inputsMapping": "{isto nao e json"}, _prop())


def test_scalar_json_is_rejected():
    """'123' decodes, but it is not a structure — it cannot become an object parameter."""
    with pytest.raises(ValueError, match="objeto"):
        validate_node_parameters({"inputsMapping": "123"}, _prop())


def test_incompatible_type_is_rejected():
    with pytest.raises(ValueError, match="Tipo recebido: int"):
        validate_node_parameters({"inputsMapping": 42}, _prop())
