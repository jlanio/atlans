"""`:placeholder` só conta em posição de código.

O regex varria o texto cru da query, então `:nome` dentro de literal ou
comentário era tratado como parâmetro. Dois desfechos, ambos silenciosos para
quem escreveu a consulta:

  WHERE obs = 'urgente:revisar'   -> "Parâmetro SQL 'revisar' não fornecido":
                                     uma query válida era recusada.
  WHERE tag = 'nota:importante'   -> virava `'nota$1'` se existisse um parâmetro
                                     chamado `importante` — o conteúdo do
                                     literal trocado por um bind, e a consulta
                                     passando a filtrar outra coisa.
"""
import pytest

from flow.utils.query_param_formatter import prepare_query


# ── O que deve ser substituído ──────────────────────────────────────────────

def test_placeholder_simples():
    q, v = prepare_query("SELECT * FROM t WHERE b = :bairro", {"bairro": "Centro"})
    assert q == "SELECT * FROM t WHERE b = $1"
    assert v == ["Centro"]


def test_placeholder_repetido_reusa_o_indice():
    q, v = prepare_query(
        "SELECT * FROM t WHERE a = :id OR b = :id AND c = :outro",
        {"id": 5, "outro": "x"},
    )
    assert q == "SELECT * FROM t WHERE a = $1 OR b = $1 AND c = $2"
    assert v == [5, "x"]


def test_cast_com_dois_pontos_nao_e_placeholder():
    q, v = prepare_query("SELECT id::text FROM t WHERE b = :b", {"b": 1})
    assert q == "SELECT id::text FROM t WHERE b = $1"


def test_parametro_ausente_falha_alto():
    with pytest.raises(ValueError, match="'bairro' não fornecido"):
        prepare_query("SELECT * FROM t WHERE b = :bairro", {})


# ── O que NÃO deve ser tocado ───────────────────────────────────────────────

def test_dois_pontos_dentro_de_string_nao_vira_parametro():
    q, v = prepare_query("SELECT * FROM notas WHERE obs = 'urgente:revisar'", {})
    assert q == "SELECT * FROM notas WHERE obs = 'urgente:revisar'"
    assert v == []


def test_string_nao_e_corrompida_quando_o_nome_existe_nos_params():
    """O caso pior: o texto do literal era trocado por um bind, e a consulta
    passava a comparar outra coisa — sem erro nenhum."""
    q, v = prepare_query(
        "SELECT * FROM t WHERE tag = 'nota:importante' AND id = :id",
        {"importante": "IGNORAR", "id": 7},
    )
    assert "'nota:importante'" in q
    assert q.endswith("id = $1")
    assert v == [7]


def test_comentario_de_linha_e_ignorado():
    q, v = prepare_query("SELECT 1 -- filtrar por :bairro depois\nFROM t", {})
    assert ":bairro" in q and v == []


def test_comentario_de_bloco_e_ignorado():
    q, v = prepare_query("SELECT /* usar :bairro aqui */ 1 FROM t", {})
    assert v == []


def test_identificador_entre_aspas_e_ignorado():
    q, v = prepare_query('SELECT t."col:esquisita" FROM t WHERE a = :a', {"a": 1})
    assert '"col:esquisita"' in q
    assert v == [1]


def test_dollar_quoting_e_ignorado():
    q, v = prepare_query("SELECT $$texto com :nome dentro$$ FROM t", {})
    assert v == []


def test_hora_dentro_de_literal_nao_confunde():
    q, v = prepare_query("SELECT * FROM t WHERE h = '08:30' AND b = :b", {"b": 1})
    assert "'08:30'" in q
    assert v == [1]


# ── Origem dos parâmetros: aresta ou formulário ─────────────────────────────
#
# A forma anterior era `inputs.get('queryParams') or parameters.get(...)`, e o
# `or` tratava `{}` como ausência. Mas um dicionário vazio vindo de uma aresta é
# uma RESPOSTA — "não há filtro nenhum" —, não um silêncio: a consulta que
# deveria rodar sem filtro rodava com os filtros antigos gravados no formulário,
# e o resultado voltava plausível, só que errado.

from flow.utils.query_param_formatter import resolver_query_params


def test_valor_da_aresta_vence_o_do_formulario():
    assert resolver_query_params(
        {"queryParams": {"bairro": "Centro"}},
        {"queryParams": {"bairro": "Antigo"}},
    ) == {"bairro": "Centro"}


def test_dicionario_vazio_da_aresta_e_uma_resposta_e_nao_ausencia():
    """O defeito em uma linha: `{}` caía no valor estático por causa do `or`."""
    assert resolver_query_params(
        {"queryParams": {}},
        {"queryParams": {"bairro": "Antigo"}},
    ) == {}


def test_sem_aresta_usa_o_formulario():
    assert resolver_query_params(
        {"outraCoisa": 1},
        {"queryParams": {"bairro": "Centro"}},
    ) == {"bairro": "Centro"}


def test_sem_aresta_e_sem_formulario_e_vazio():
    assert resolver_query_params({}, {}) == {}


def test_none_na_aresta_vira_vazio():
    """Aresta ligada a uma saída que não trouxe nada — vazio, não erro."""
    assert resolver_query_params({"queryParams": None}, {"queryParams": {"a": 1}}) == {}


@pytest.mark.parametrize("valor", ["texto", 42, ["a"]])
def test_tipo_errado_falha_dizendo_a_origem(valor):
    """As duas origens pedem ações opostas: mexer na aresta ou no formulário."""
    with pytest.raises(ValueError, match="recebido do nó anterior"):
        resolver_query_params({"queryParams": valor}, {})

    with pytest.raises(ValueError, match="Parâmetros da consulta"):
        resolver_query_params({}, {"queryParams": valor})
