"""`:placeholder` only counts in code position.

The regex scanned the raw query text, so `:nome` inside a literal or a comment
was treated as a parameter. Two outcomes, both silent for whoever wrote the
query:

  WHERE obs = 'urgente:revisar'   -> "Parâmetro SQL 'revisar' não fornecido":
                                     a valid query was rejected.
  WHERE tag = 'nota:importante'   -> became `'nota$1'` if there was a parameter
                                     called `importante` — the literal's content
                                     replaced by a bind, and the query starting
                                     to filter on something else.
"""
import pytest

from flow.utils.query_param_formatter import prepare_query


# ── What must be replaced ───────────────────────────────────────────────────

def test_simple_placeholder():
    q, v = prepare_query("SELECT * FROM t WHERE b = :bairro", {"bairro": "Centro"})
    assert q == "SELECT * FROM t WHERE b = $1"
    assert v == ["Centro"]


def test_repeated_placeholder_reuses_the_index():
    q, v = prepare_query(
        "SELECT * FROM t WHERE a = :id OR b = :id AND c = :outro",
        {"id": 5, "outro": "x"},
    )
    assert q == "SELECT * FROM t WHERE a = $1 OR b = $1 AND c = $2"
    assert v == [5, "x"]


def test_double_colon_cast_is_not_placeholder():
    q, v = prepare_query("SELECT id::text FROM t WHERE b = :b", {"b": 1})
    assert q == "SELECT id::text FROM t WHERE b = $1"


def test_missing_parameter_fails_loudly():
    with pytest.raises(ValueError, match="'bairro' não fornecido"):
        prepare_query("SELECT * FROM t WHERE b = :bairro", {})


# ── What must NOT be touched ────────────────────────────────────────────────

def test_colon_inside_string_does_not_become_parameter():
    q, v = prepare_query("SELECT * FROM notas WHERE obs = 'urgente:revisar'", {})
    assert q == "SELECT * FROM notas WHERE obs = 'urgente:revisar'"
    assert v == []


def test_string_is_not_corrupted_when_the_name_exists_in_params():
    """The worst case: the literal's text was replaced by a bind, and the query
    started comparing something else — with no error at all."""
    q, v = prepare_query(
        "SELECT * FROM t WHERE tag = 'nota:importante' AND id = :id",
        {"importante": "IGNORAR", "id": 7},
    )
    assert "'nota:importante'" in q
    assert q.endswith("id = $1")
    assert v == [7]


def test_line_comment_is_ignored():
    q, v = prepare_query("SELECT 1 -- filtrar por :bairro depois\nFROM t", {})
    assert ":bairro" in q and v == []


def test_block_comment_is_ignored():
    q, v = prepare_query("SELECT /* usar :bairro aqui */ 1 FROM t", {})
    assert v == []


def test_quoted_identifier_is_ignored():
    q, v = prepare_query('SELECT t."col:esquisita" FROM t WHERE a = :a', {"a": 1})
    assert '"col:esquisita"' in q
    assert v == [1]


def test_dollar_quoting_is_ignored():
    q, v = prepare_query("SELECT $$texto com :nome dentro$$ FROM t", {})
    assert v == []


def test_time_inside_literal_does_not_confuse():
    q, v = prepare_query("SELECT * FROM t WHERE h = '08:30' AND b = :b", {"b": 1})
    assert "'08:30'" in q
    assert v == [1]


# ── Source of the parameters: edge or form ──────────────────────────────────
#
# The previous form was `inputs.get('queryParams') or parameters.get(...)`, and
# the `or` treated `{}` as absence. But an empty dictionary coming from an edge
# is an ANSWER — "there is no filter at all" —, not silence: the query that
# should run with no filter ran with the old filters stored in the form, and the
# result came back plausible, just wrong.

from flow.utils.query_param_formatter import resolver_query_params


def test_edge_value_wins_over_the_form_value():
    assert resolver_query_params(
        {"queryParams": {"bairro": "Centro"}},
        {"queryParams": {"bairro": "Antigo"}},
    ) == {"bairro": "Centro"}


def test_empty_edge_dict_is_an_answer_not_absence():
    """The defect in one line: `{}` fell through to the static value because of the `or`."""
    assert resolver_query_params(
        {"queryParams": {}},
        {"queryParams": {"bairro": "Antigo"}},
    ) == {}


def test_without_edge_uses_the_form():
    assert resolver_query_params(
        {"outraCoisa": 1},
        {"queryParams": {"bairro": "Centro"}},
    ) == {"bairro": "Centro"}


def test_without_edge_and_without_form_is_empty():
    assert resolver_query_params({}, {}) == {}


def test_none_on_the_edge_becomes_empty():
    """Edge connected to an output that brought nothing — empty, not an error."""
    assert resolver_query_params({"queryParams": None}, {"queryParams": {"a": 1}}) == {}


@pytest.mark.parametrize("valor", ["texto", 42, ["a"]])
def test_wrong_type_fails_stating_the_source(valor):
    """The two sources call for opposite actions: change the edge or the form."""
    with pytest.raises(ValueError, match="recebido do nó anterior"):
        resolver_query_params({"queryParams": valor}, {})

    with pytest.raises(ValueError, match="Parâmetros da consulta"):
        resolver_query_params({}, {"queryParams": valor})
