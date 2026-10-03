"""Jinja in parameters that are not top-level strings.

`render_node_parameters` stopped at the first line — `if not isinstance(raw, str):
continue` — and only rendered top-level string parameters. What was left out were
precisely the fields meant to receive dynamic values: `queryParams` of the
database nodes (the values of the `:placeholders`) and `headers`/`params` of HttpRequest.

And the failure mode was worse than "doesn't work": the dictionary went through
raw, the template went as TEXT to the database (`WHERE bairro = '{{ ... }}'`), the
query ran, came back empty and the workflow went on. No error anywhere.
"""
import pytest

from flow.executor.rendering import render_node_parameters


class FakeNode:
    def __init__(self, parameters):
        self.parameters = parameters


def _render(parameters, named=None):
    """Runs the renderer with the same context shape as the executor."""
    named = named if named is not None else {
        "Filtro": {"bairro": "Centro", "limite": 50, "ativo": True,
                   "taxa": 1.5, "nada": None},
    }
    context = {"inputs": {}, "nodes": {}, "named": named,
               "now": None, "uuid": None, "env": {}}
    return render_node_parameters(FakeNode(parameters), "n1", named, context)


# ── The case from the request: queryParams ──────────────────────────────────

def test_expression_in_queryparams_value_is_resolved():
    saida = _render({
        "query": "SELECT * FROM imoveis WHERE bairro = :bairro",
        "queryParams": {"bairro": "{{ $Filtro.bairro }}"},
    })
    assert saida["queryParams"] == {"bairro": "Centro"}


def test_alias_without_braces_also_works_in_queryparams():
    saida = _render({"queryParams": {"b": "$Filtro.bairro"}})
    assert saida["queryParams"] == {"b": "Centro"}


def test_top_level_string_still_works():
    """The regression I would fear most: the old path had to stay the same."""
    saida = _render({"query": "SELECT * FROM t LIMIT {{ $Filtro.limite }}"})
    assert saida["query"] == "SELECT * FROM t LIMIT 50"


# ── Value type ──────────────────────────────────────────────────────────────
#
# The value of `queryParams` becomes a SQL bind (`$1`), and the type decides how
# Postgres compares it with the column. Jinja's `Template.render()` always
# returns text — `{{ x }}` with 50 becomes `'50'` and with None the string `'None'`.

@pytest.mark.parametrize("expressao,esperado,tipo", [
    ("{{ $Filtro.limite }}", 50,       int),
    ("{{ $Filtro.taxa }}",   1.5,      float),
    ("{{ $Filtro.ativo }}",  True,     bool),
    ("{{ $Filtro.nada }}",   None,     type(None)),
    ("{{ $Filtro.bairro }}", "Centro", str),
])
def test_type_is_preserved_when_the_value_is_the_whole_expression(expressao, esperado, tipo):
    saida = _render({"queryParams": {"v": expressao}})
    assert saida["queryParams"]["v"] == esperado
    assert isinstance(saida["queryParams"]["v"], tipo)


def test_mixed_template_stays_text():
    """`ano-{{ x }}` asks for concatenation — text is the right result."""
    saida = _render({"queryParams": {"v": "ano-{{ $Filtro.limite }}"}})
    assert saida["queryParams"]["v"] == "ano-50"


def test_top_level_does_not_change_type():
    """At the top level the old behavior is preserved on purpose: some nodes
    call `.strip()` on the parameter, and changing the type there would mix a fix
    with breakage."""
    saida = _render({"timeout": "{{ $Filtro.limite }}"})
    assert saida["timeout"] == "50"


# ── Estrutura ───────────────────────────────────────────────────────────────

def test_descends_into_nested_list_and_dictionary():
    saida = _render({"conf": {"filtros": [{"campo": "{{ $Filtro.bairro }}"}]}})
    assert saida["conf"]["filtros"][0]["campo"] == "Centro"


def test_dictionary_key_is_not_rendered():
    """The key is the name of the `:placeholder` and must match the SQL."""
    saida = _render({"queryParams": {"{{ $Filtro.bairro }}": "x"}})
    assert list(saida["queryParams"]) == ["{{ $Filtro.bairro }}"]


def test_value_without_expression_passes_intact():
    saida = _render({"queryParams": {"a": "texto", "b": 7, "c": None}})
    assert saida["queryParams"] == {"a": "texto", "b": 7, "c": None}


def test_error_points_to_the_path_inside_the_structure():
    with pytest.raises(ValueError) as exc:
        _render({"queryParams": {"bairro": "{{ $Filtro.inexistente }}"}})
    # Without the path, the message would say only "queryParams" and the user would
    # have to guess which of the keys broke.
    assert "queryParams.bairro" in str(exc.value)


# ── What the server injects from the credential is not a template ────────────

@pytest.mark.parametrize("senha", ["p@ss{{w0rd}}", "abc{%x%}def", "x$Filtro.bairro"])
def test_the_injected_credential_passes_intact_and_without_error(senha):
    # Rendered, the password would change silently — or the rendering failure would
    # repeat it in the error message, which goes to the screen, the database and the log.
    parametros = {
        "http_auth": {"type": "wfs", "username": "leitor", "password": senha},
        "connectionString": f"postgresql://u:{senha}@h/db",
        "query": "SELECT {{ $Filtro.limite }}",
    }
    saida = _render(parametros)
    assert saida["http_auth"] == parametros["http_auth"]
    assert saida["connectionString"] == parametros["connectionString"]
    assert saida["query"] == "SELECT 50"  # o resto segue renderizado
