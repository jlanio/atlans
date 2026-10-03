# tests/unit/test_contrato_do_no.py
"""A node's description() is validated AT IMPORT (A14).

The `type` field piled up three roles (node category, output field type,
property widget) and none was checked: a typo slipped silently through the
registry and became a visual defect far from its cause — a node without an
icon, a field without an editor, a port without a type. Now `register_node`
calls `validate_description` and the malformed node dies in CI with the exact
cause.
"""
import pytest

from flow.nodes.base import BaseNode
from flow.nodes.contrato import (
    CATEGORIES,
    DESCRIPTION_KEYS,
    FIELD_TYPES,
    PROPERTY_TYPES,
    validate_description,
)
from flow.registry import NODE_REGISTRY, register_node


def _desc(**mudancas):
    base = {
        "name": "NoDeTeste",
        "alias": "Nó de Teste",
        "description": "Só para o contrato.",
        "type": "action",
        "properties": [
            {"name": "campo", "type": "string", "default": "", "description": "x"},
        ],
        "outputs": [
            {"name": "output", "type": "geodataframe", "description": "resultado"},
        ],
    }
    base.update(mudancas)
    return base


# ── validate_description (puro) ───────────────────────────────────────────────

def test_valid_description_passes():
    validate_description(_desc())


def test_category_outside_the_vocabulary_is_rejected():
    with pytest.raises(ValueError, match="categoria.*'transform'"):
        validate_description(_desc(type="transform"))


def test_unknown_top_level_key_is_rejected():
    # The classic typo: 'output' (singular) instead of 'outputs' — before, the
    # field simply ceased to exist for the editor.
    with pytest.raises(ValueError, match="chaves desconhecidas.*output"):
        d = _desc()
        d["output"] = d.pop("outputs")
        validate_description(d)


def test_invalid_property_type_is_rejected():
    with pytest.raises(ValueError, match="propriedade 'campo' com type inválido: 'texto'"):
        validate_description(_desc(properties=[{"name": "campo", "type": "texto"}]))


def test_select_without_options_is_rejected():
    with pytest.raises(ValueError, match="select sem 'options'"):
        validate_description(_desc(properties=[{"name": "modo", "type": "select"}]))


def test_credential_without_types_is_rejected():
    with pytest.raises(ValueError, match="credential sem 'credential_types'"):
        validate_description(_desc(properties=[{"name": "cred", "type": "credential"}]))


def test_output_field_without_type_is_rejected():
    # The rule that A13 establishes: an output field WITHOUT a type is no longer accepted.
    with pytest.raises(ValueError, match="campo de saída 'output' com type inválido: None"):
        validate_description(_desc(outputs=[{"name": "output"}]))


def test_output_field_with_unknown_key_is_rejected():
    with pytest.raises(ValueError, match="campo de saída 'output' com chaves desconhecidas"):
        validate_description(_desc(outputs=[
            {"name": "output", "type": "any", "porta": True},
        ]))


def test_non_bool_flag_is_rejected():
    with pytest.raises(ValueError, match="'branches' deve ser bool"):
        validate_description(_desc(branches="true"))


def test_name_with_space_is_rejected():
    with pytest.raises(ValueError, match="sem espaços"):
        validate_description(_desc(name="No De Teste"))


# ── register_node applies the validation at import ──────────────────────────

def test_register_node_rejects_malformed_node():
    class NoTorto(BaseNode):
        @classmethod
        def description(cls):
            return _desc(name="NoTorto", type="transform")

        async def execute(self, inputs):  # pragma: no cover
            return {}

    with pytest.raises(ValueError, match="NoTorto.*categoria"):
        register_node(NoTorto)
    assert "NoTorto" not in NODE_REGISTRY


def test_register_node_registers_valid_node():
    class NoReto(BaseNode):
        @classmethod
        def description(cls):
            return _desc(name="NoReto")

        async def execute(self, inputs):  # pragma: no cover
            return {}

    try:
        register_node(NoReto)
        assert NODE_REGISTRY["NoReto"] is NoReto
    finally:
        NODE_REGISTRY.pop("NoReto", None)


# ── The entire real catalog honors the contract ─────────────────────────────

def test_the_63_catalog_nodes_pass_the_contract():
    assert len(NODE_REGISTRY) >= 63
    for nome, cls in NODE_REGISTRY.items():
        validate_description(cls.description())


def test_vocabularies_are_closed_and_documented():
    """The three roles of the old 'type', now each with its own vocabulary."""
    assert CATEGORIES == {"trigger", "action", "spatial", "datasource", "output", "control"}
    assert "geodataframe" in FIELD_TYPES and "select" not in FIELD_TYPES
    assert "select" in PROPERTY_TYPES and "geodataframe" not in PROPERTY_TYPES
    assert "outputs" in DESCRIPTION_KEYS and "static_output" not in DESCRIPTION_KEYS
