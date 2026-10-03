# tests/unit/test_contrato_do_no.py
"""A node's description() is validated AT IMPORT (A14).

The `type` field piled up three roles (node category, output field type,
property widget) and none was checked: a typo slipped silently through the
registry and became a visual defect far from its cause — a node without an
icon, a field without an editor, a port without a type. Now `register_node`
calls `validar_description` and the malformed node dies in CI with the exact
cause.
"""
import pytest

from flow.nodes.base import BaseNode
from flow.nodes.contrato import (
    CATEGORIAS,
    CHAVES_DO_DESCRIPTION,
    TIPOS_DE_CAMPO,
    TIPOS_DE_PROPRIEDADE,
    validar_description,
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


# ── validar_description (puro) ───────────────────────────────────────────────

def test_description_valido_passa():
    validar_description(_desc())


def test_categoria_fora_do_vocabulario_e_recusada():
    with pytest.raises(ValueError, match="categoria.*'transform'"):
        validar_description(_desc(type="transform"))


def test_chave_desconhecida_no_topo_e_recusada():
    # The classic typo: 'output' (singular) instead of 'outputs' — before, the
    # field simply ceased to exist for the editor.
    with pytest.raises(ValueError, match="chaves desconhecidas.*output"):
        d = _desc()
        d["output"] = d.pop("outputs")
        validar_description(d)


def test_tipo_de_propriedade_invalido_e_recusado():
    with pytest.raises(ValueError, match="propriedade 'campo' com type inválido: 'texto'"):
        validar_description(_desc(properties=[{"name": "campo", "type": "texto"}]))


def test_select_sem_options_e_recusado():
    with pytest.raises(ValueError, match="select sem 'options'"):
        validar_description(_desc(properties=[{"name": "modo", "type": "select"}]))


def test_credential_sem_tipos_e_recusado():
    with pytest.raises(ValueError, match="credential sem 'credential_types'"):
        validar_description(_desc(properties=[{"name": "cred", "type": "credential"}]))


def test_campo_de_saida_sem_type_e_recusado():
    # The rule that A13 establishes: an output field WITHOUT a type is no longer accepted.
    with pytest.raises(ValueError, match="campo de saída 'output' com type inválido: None"):
        validar_description(_desc(outputs=[{"name": "output"}]))


def test_campo_de_saida_com_chave_estranha_e_recusado():
    with pytest.raises(ValueError, match="campo de saída 'output' com chaves desconhecidas"):
        validar_description(_desc(outputs=[
            {"name": "output", "type": "any", "porta": True},
        ]))


def test_flag_que_nao_e_bool_e_recusada():
    with pytest.raises(ValueError, match="'branches' deve ser bool"):
        validar_description(_desc(branches="true"))


def test_nome_com_espaco_e_recusado():
    with pytest.raises(ValueError, match="sem espaços"):
        validar_description(_desc(name="No De Teste"))


# ── register_node applies the validation at import ──────────────────────────

def test_register_node_recusa_no_malformado():
    class NoTorto(BaseNode):
        @classmethod
        def description(cls):
            return _desc(name="NoTorto", type="transform")

        async def execute(self, inputs):  # pragma: no cover
            return {}

    with pytest.raises(ValueError, match="NoTorto.*categoria"):
        register_node(NoTorto)
    assert "NoTorto" not in NODE_REGISTRY


def test_register_node_registra_no_valido():
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

def test_os_63_nos_do_catalogo_passam_no_contrato():
    assert len(NODE_REGISTRY) >= 63
    for nome, cls in NODE_REGISTRY.items():
        validar_description(cls.description())


def test_vocabularios_sao_fechados_e_documentados():
    """The three roles of the old 'type', now each with its own vocabulary."""
    assert CATEGORIAS == {"trigger", "action", "spatial", "datasource", "output", "control"}
    assert "geodataframe" in TIPOS_DE_CAMPO and "select" not in TIPOS_DE_CAMPO
    assert "select" in TIPOS_DE_PROPRIEDADE and "geodataframe" not in TIPOS_DE_PROPRIEDADE
    assert "outputs" in CHAVES_DO_DESCRIPTION and "static_output" not in CHAVES_DO_DESCRIPTION
