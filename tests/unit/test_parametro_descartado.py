"""Parameter present in the definition but missing from the node's schema.

`validate_node_parameters` builds the return value from `props`, so every
undeclared key is dropped. That protects the node from garbage in the definition,
but it made an outdated executor indistinguishable from a logic bug:

  server publishes the catalog -> UI shows the new field and stores the value
  -> executor with an old `flow/` does not declare the property -> value dropped
  -> no error, no log, unchanged behavior

That is how DataOutput's "Sobrescrever se ja existir" (overwrite if it already
exists) option had no effect. The warning exists so the next occurrence fits in
one log line.
"""
import logging

import pytest

from flow.utils.parameter_validation import validate_node_parameters


PROPS = [
    {"name": "label", "type": "string", "default": ""},
    {"name": "context", "type": "string", "default": "artifacts"},
]


def test_parametro_nao_declarado_e_descartado():
    saida = validate_node_parameters({"label": "x", "overwrite": True}, PROPS)

    assert "overwrite" not in saida
    assert saida["label"] == "x"


def test_descarte_gera_aviso_com_nome_do_no(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "overwrite": True}, PROPS, node_name="DataOutput")

    assert "DataOutput" in caplog.text
    assert "overwrite" in caplog.text
    # O aviso precisa apontar a causa provavel, senao vira ruido sem acao.
    assert "executor" in caplog.text.lower()


def test_aviso_lista_o_que_o_no_conhece(caplog):
    """Without the declared ones, whoever reads the log does not know what to compare against."""
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "overwrite": True}, PROPS)

    assert "'context'" in caplog.text and "'label'" in caplog.text


def test_sem_descarte_nao_avisa(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "context": "drive"}, PROPS)

    assert caplog.text == ""


@pytest.mark.parametrize("chave", ["alias", "retry_count", "retry_delay_s"])
def test_chaves_de_plataforma_nao_avisam(caplog, chave):
    """They live in `properties` without being node parameters.

    `alias` is the label stored by the modal; retry_count/retry_delay_s the
    executor reads directly from `parameters` before execute (core.py::get_retry_params).
    Warning about them would turn the log into noise on every run.
    """
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", chave: "v"}, PROPS)

    assert caplog.text == ""


@pytest.mark.parametrize("chave", ["outputKey", "outputKeyA", "inputKey", "inputKeyB"])
def test_mapeamentos_legados_agora_avisam(caplog, chave):
    """auto_map_edges was retired (see node_manager / spec §5): these prefixes
    no longer have any effect and MUST show up as dropped, so the owner fixes
    the legacy workflow by hand instead of the param vanishing silently."""
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", chave: "output"}, PROPS)

    assert chave in caplog.text


def test_aviso_e_deterministico_com_varios_descartes(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "zeta": 1, "alfa": 2}, PROPS)

    assert "['alfa', 'zeta']" in caplog.text


def test_no_real_avisa_quando_o_schema_nao_tem_a_opcao(caplog):
    """Reproduces the outdated-executor scenario, with the real node."""
    from flow.nodes.outputs.data_output import DataOutput

    node = DataOutput("n1", {"label": "r", "context": "drive", "opcao_do_futuro": True})

    with caplog.at_level(logging.WARNING):
        node.validate()

    assert "DataOutput" in caplog.text
    assert "opcao_do_futuro" in caplog.text
    assert "opcao_do_futuro" not in node.parameters


def test_no_real_nao_avisa_por_alias(caplog):
    """The modal stores the alias in properties — it must not become a warning on every run."""
    from flow.nodes.outputs.data_output import DataOutput

    node = DataOutput("n1", {"label": "r", "context": "drive", "alias": "Minha Saida"})

    with caplog.at_level(logging.WARNING):
        node.validate()

    assert caplog.text == ""


# ── Campo numerico opcional limpo na UI ──────────────────────────────────────

def test_campo_numerico_vazio_cai_no_default():
    """Clearing an optional integer field stores "" (the text input does not remove
    the key). That means 'not filled in', not a value: without the detour, the run
    failed with "deve ser inteiro. Recebido: ''"."""
    props = [{"name": "ttl_hours", "type": "integer", "default": 168}]
    assert validate_node_parameters({"ttl_hours": ""}, props)["ttl_hours"] == 168
    assert validate_node_parameters({"ttl_hours": None}, props)["ttl_hours"] == 168
    # Valor preenchido continua valendo.
    assert validate_node_parameters({"ttl_hours": "24"}, props)["ttl_hours"] == 24


def test_campo_vazio_sem_default_continua_obrigatorio():
    """The detour applies only to a param with a declared default — a cleared
    required one is still an error, not a silent None."""
    props = [{"name": "max_items", "type": "integer"}]
    with pytest.raises(ValueError):
        validate_node_parameters({"max_items": ""}, props)
