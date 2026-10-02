"""
Parametros de tipo "object" chegando serializados do canvas.

Regressao real: ao configurar um SubWorkflow, a execucao falhava com

    O parametro 'inputsMapping' deve ser um objeto (dict).

O editor de nodes so grava primitivos — `setNodeField` tem assinatura
(field, value: string | number | boolean) — entao os helpers da UI serializam
estruturas com JSON.stringify. O valor chegava como str e a checagem
`isinstance(value, dict)` rejeitava algo que a UI tinha gravado corretamente.

`ports` (SubWorkflowInput/Output) expoe a mesma armadilha por outro lado:
declara type "object" mas o valor legitimo e uma LISTA.
"""
import pytest

from flow.utils.parameter_validation import validate_node_parameters


def _prop(name="inputsMapping", default=None):
    return [{"name": name, "type": "object", "default": default if default is not None else {}}]


# ── O caso que quebrava ──────────────────────────────────────────────────────

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
    """Campo limpo na UI nao pode derrubar a execucao."""
    out = validate_node_parameters({"inputsMapping": ""}, _prop())
    assert out["inputsMapping"] == {}


# ── Comportamento preservado ─────────────────────────────────────────────────

def test_dict_nativo_continua_passando():
    out = validate_node_parameters({"inputsMapping": {"a": "b"}}, _prop())
    assert out["inputsMapping"] == {"a": "b"}


def test_lista_nativa_continua_passando():
    out = validate_node_parameters({"ports": ["a"]}, _prop("ports", default=[]))
    assert out["ports"] == ["a"]


# ── Entrada invalida ainda e recusada ────────────────────────────────────────

def test_json_malformado_falha_citando_o_valor():
    with pytest.raises(ValueError, match="JSON válido"):
        validate_node_parameters({"inputsMapping": "{isto nao e json"}, _prop())


def test_json_escalar_e_recusado():
    """'123' decodifica, mas nao e estrutura — nao pode virar parametro object."""
    with pytest.raises(ValueError, match="objeto"):
        validate_node_parameters({"inputsMapping": "123"}, _prop())


def test_tipo_incompativel_e_recusado():
    with pytest.raises(ValueError, match="Tipo recebido: int"):
        validate_node_parameters({"inputsMapping": 42}, _prop())
