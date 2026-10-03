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


class NoFalso:
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
    return render_node_parameters(NoFalso(parameters), "n1", named, context)


# ── The case from the request: queryParams ──────────────────────────────────

def test_expressao_no_valor_do_queryparams_e_resolvida():
    saida = _render({
        "query": "SELECT * FROM imoveis WHERE bairro = :bairro",
        "queryParams": {"bairro": "{{ $Filtro.bairro }}"},
    })
    assert saida["queryParams"] == {"bairro": "Centro"}


def test_alias_sem_chaves_tambem_vale_no_queryparams():
    saida = _render({"queryParams": {"b": "$Filtro.bairro"}})
    assert saida["queryParams"] == {"b": "Centro"}


def test_string_de_topo_continua_funcionando():
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
def test_tipo_e_preservado_quando_o_valor_e_a_expressao_inteira(expressao, esperado, tipo):
    saida = _render({"queryParams": {"v": expressao}})
    assert saida["queryParams"]["v"] == esperado
    assert isinstance(saida["queryParams"]["v"], tipo)


def test_template_misto_continua_texto():
    """`ano-{{ x }}` asks for concatenation — text is the right result."""
    saida = _render({"queryParams": {"v": "ano-{{ $Filtro.limite }}"}})
    assert saida["queryParams"]["v"] == "ano-50"


def test_topo_nao_muda_de_tipo():
    """At the top level the old behavior is preserved on purpose: some nodes
    call `.strip()` on the parameter, and changing the type there would mix a fix
    with breakage."""
    saida = _render({"timeout": "{{ $Filtro.limite }}"})
    assert saida["timeout"] == "50"


# ── Estrutura ───────────────────────────────────────────────────────────────

def test_desce_por_lista_e_dicionario_aninhados():
    saida = _render({"conf": {"filtros": [{"campo": "{{ $Filtro.bairro }}"}]}})
    assert saida["conf"]["filtros"][0]["campo"] == "Centro"


def test_chave_do_dicionario_nao_e_renderizada():
    """The key is the name of the `:placeholder` and must match the SQL."""
    saida = _render({"queryParams": {"{{ $Filtro.bairro }}": "x"}})
    assert list(saida["queryParams"]) == ["{{ $Filtro.bairro }}"]


def test_valor_sem_expressao_passa_intacto():
    saida = _render({"queryParams": {"a": "texto", "b": 7, "c": None}})
    assert saida["queryParams"] == {"a": "texto", "b": 7, "c": None}


def test_erro_aponta_o_caminho_dentro_da_estrutura():
    with pytest.raises(ValueError) as exc:
        _render({"queryParams": {"bairro": "{{ $Filtro.inexistente }}"}})
    # Without the path, the message would say only "queryParams" and the user would
    # have to guess which of the keys broke.
    assert "queryParams.bairro" in str(exc.value)


# ── What the server injects from the credential is not a template ────────────

@pytest.mark.parametrize("senha", ["p@ss{{w0rd}}", "abc{%x%}def", "x$Filtro.bairro"])
def test_a_credencial_injetada_passa_intacta_e_sem_erro(senha):
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
