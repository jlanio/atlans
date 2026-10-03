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


def test_undeclared_parameter_is_discarded():
    saida = validate_node_parameters({"label": "x", "overwrite": True}, PROPS)

    assert "overwrite" not in saida
    assert saida["label"] == "x"


def test_discard_emits_warning_with_node_name(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "overwrite": True}, PROPS, node_name="DataOutput")

    assert "DataOutput" in caplog.text
    assert "overwrite" in caplog.text
    # O aviso precisa apontar a causa provavel, senao vira ruido sem acao.
    assert "executor" in caplog.text.lower()


def test_warning_lists_what_the_node_knows(caplog):
    """Without the declared ones, whoever reads the log does not know what to compare against."""
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "overwrite": True}, PROPS)

    assert "'context'" in caplog.text and "'label'" in caplog.text


def test_no_discard_no_warning(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "context": "drive"}, PROPS)

    assert caplog.text == ""


@pytest.mark.parametrize("chave", ["alias", "retry_count", "retry_delay_s"])
def test_platform_keys_do_not_warn(caplog, chave):
    """They live in `properties` without being node parameters.

    `alias` is the label stored by the modal; retry_count/retry_delay_s the
    executor reads directly from `parameters` before execute (core.py::get_retry_params).
    Warning about them would turn the log into noise on every run.
    """
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", chave: "v"}, PROPS)

    assert caplog.text == ""


@pytest.mark.parametrize("chave", ["outputKey", "outputKeyA", "inputKey", "inputKeyB"])
def test_legacy_mappings_now_warn(caplog, chave):
    """auto_map_edges was retired (see node_manager / spec §5): these prefixes
    no longer have any effect and MUST show up as dropped, so the owner fixes
    the legacy workflow by hand instead of the param vanishing silently."""
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", chave: "output"}, PROPS)

    assert chave in caplog.text


def test_warning_is_deterministic_with_several_discards(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "zeta": 1, "alfa": 2}, PROPS)

    assert "['alfa', 'zeta']" in caplog.text


def test_real_node_warns_when_the_schema_lacks_the_option(caplog):
    """Reproduces the outdated-executor scenario, with the real node."""
    from flow.nodes.outputs.data_output import DataOutput

    node = DataOutput("n1", {"label": "r", "context": "drive", "opcao_do_futuro": True})

    with caplog.at_level(logging.WARNING):
        node.validate()

    assert "DataOutput" in caplog.text
    assert "opcao_do_futuro" in caplog.text
    assert "opcao_do_futuro" not in node.parameters


def test_real_node_does_not_warn_for_alias(caplog):
    """The modal stores the alias in properties — it must not become a warning on every run."""
    from flow.nodes.outputs.data_output import DataOutput

    node = DataOutput("n1", {"label": "r", "context": "drive", "alias": "Minha Saida"})

    with caplog.at_level(logging.WARNING):
        node.validate()

    assert caplog.text == ""


# ── Campo numerico opcional limpo na UI ──────────────────────────────────────

def test_empty_numeric_field_falls_back_to_default():
    """Clearing an optional integer field stores "" (the text input does not remove
    the key). That means 'not filled in', not a value: without the detour, the run
    failed with "deve ser inteiro. Recebido: ''"."""
    props = [{"name": "ttl_hours", "type": "integer", "default": 168}]
    assert validate_node_parameters({"ttl_hours": ""}, props)["ttl_hours"] == 168
    assert validate_node_parameters({"ttl_hours": None}, props)["ttl_hours"] == 168
    # Valor preenchido continua valendo.
    assert validate_node_parameters({"ttl_hours": "24"}, props)["ttl_hours"] == 24


def test_empty_field_without_default_stays_required():
    """The detour applies only to a param with a declared default — a cleared
    required one is still an error, not a silent None."""
    props = [{"name": "max_items", "type": "integer"}]
    with pytest.raises(ValueError):
        validate_node_parameters({"max_items": ""}, props)
