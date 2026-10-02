"""Parametro presente na definicao mas ausente do schema do no.

`validate_node_parameters` monta o retorno a partir de `props`, entao toda chave
nao declarada e descartada. Isso protege o no de lixo na definition, mas tornava
um executor defasado indistinguivel de um bug de logica:

  servidor publica o catalogo -> UI mostra o campo novo e grava o valor
  -> executor com `flow/` antigo nao declara a propriedade -> valor descartado
  -> nenhum erro, nenhum log, comportamento inalterado

Foi assim que a opcao "Sobrescrever se ja existir" do DataOutput nao surtiu
efeito. O aviso existe para que a proxima ocorrencia caiba numa linha de log.
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
    """Sem os declarados, quem le o log nao sabe contra o que comparar."""
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "overwrite": True}, PROPS)

    assert "'context'" in caplog.text and "'label'" in caplog.text


def test_sem_descarte_nao_avisa(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "context": "drive"}, PROPS)

    assert caplog.text == ""


@pytest.mark.parametrize("chave", ["alias", "retry_count", "retry_delay_s"])
def test_chaves_de_plataforma_nao_avisam(caplog, chave):
    """Vivem em `properties` sem serem parametros do no.

    `alias` e o rotulo gravado pelo modal; retry_count/retry_delay_s o executor
    le direto de `parameters` antes do execute (core.py::get_retry_params).
    Avisar sobre elas transformaria o log em ruido em todo run.
    """
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", chave: "v"}, PROPS)

    assert caplog.text == ""


@pytest.mark.parametrize("chave", ["outputKey", "outputKeyA", "inputKey", "inputKeyB"])
def test_mapeamentos_legados_agora_avisam(caplog, chave):
    """auto_map_edges foi aposentado (ver node_manager / spec §5): esses prefixos
    não têm mais efeito e DEVEM aparecer como descartados, para o dono corrigir
    à mão o workflow legado em vez de o param sumir em silêncio."""
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", chave: "output"}, PROPS)

    assert chave in caplog.text


def test_aviso_e_deterministico_com_varios_descartes(caplog):
    with caplog.at_level(logging.WARNING):
        validate_node_parameters({"label": "x", "zeta": 1, "alfa": 2}, PROPS)

    assert "['alfa', 'zeta']" in caplog.text


def test_no_real_avisa_quando_o_schema_nao_tem_a_opcao(caplog):
    """Reproduz o cenario do executor defasado, com o no de verdade."""
    from flow.nodes.outputs.data_output import DataOutput

    node = DataOutput("n1", {"label": "r", "context": "drive", "opcao_do_futuro": True})

    with caplog.at_level(logging.WARNING):
        node.validate()

    assert "DataOutput" in caplog.text
    assert "opcao_do_futuro" in caplog.text
    assert "opcao_do_futuro" not in node.parameters


def test_no_real_nao_avisa_por_alias(caplog):
    """O modal grava o alias em properties — nao pode virar aviso em todo run."""
    from flow.nodes.outputs.data_output import DataOutput

    node = DataOutput("n1", {"label": "r", "context": "drive", "alias": "Minha Saida"})

    with caplog.at_level(logging.WARNING):
        node.validate()

    assert caplog.text == ""


# ── Campo numerico opcional limpo na UI ──────────────────────────────────────

def test_campo_numerico_vazio_cai_no_default():
    """Limpar um campo inteiro opcional grava "" (o input de texto nao remove a
    chave). Isso e 'nao preenchido', nao um valor: sem o desvio, a run caia com
    "deve ser inteiro. Recebido: ''"."""
    props = [{"name": "ttl_hours", "type": "integer", "default": 168}]
    assert validate_node_parameters({"ttl_hours": ""}, props)["ttl_hours"] == 168
    assert validate_node_parameters({"ttl_hours": None}, props)["ttl_hours"] == 168
    # Valor preenchido continua valendo.
    assert validate_node_parameters({"ttl_hours": "24"}, props)["ttl_hours"] == 24


def test_campo_vazio_sem_default_continua_obrigatorio():
    """O desvio vale so para param com default declarado — um obrigatorio limpo
    continua sendo erro, nao um None silencioso."""
    props = [{"name": "max_items", "type": "integer"}]
    with pytest.raises(ValueError):
        validate_node_parameters({"max_items": ""}, props)
