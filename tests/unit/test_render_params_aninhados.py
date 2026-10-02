"""Jinja nos parâmetros que não são string de topo.

`render_node_parameters` parava na primeira linha — `if not isinstance(raw, str):
continue` — e só renderizava parâmetro string de topo. Quem ficava de fora eram
justamente os campos feitos para receber valor dinâmico: `queryParams` dos nós
de banco (os valores dos `:placeholders`) e `headers`/`params` do HttpRequest.

E o modo de falha era pior que "não funciona": o dicionário seguia cru, o
template ia como TEXTO para o banco (`WHERE bairro = '{{ ... }}'`), a consulta
rodava, voltava vazia e o fluxo continuava. Nenhum erro em lugar nenhum.
"""
import pytest

from flow.executor.rendering import render_node_parameters


class NoFalso:
    def __init__(self, parameters):
        self.parameters = parameters


def _render(parameters, named=None):
    """Roda o renderizador com o mesmo formato de contexto do executor."""
    named = named if named is not None else {
        "Filtro": {"bairro": "Centro", "limite": 50, "ativo": True,
                   "taxa": 1.5, "nada": None},
    }
    context = {"inputs": {}, "nodes": {}, "named": named,
               "now": None, "uuid": None, "env": {}}
    return render_node_parameters(NoFalso(parameters), "n1", named, context)


# ── O caso do pedido: queryParams ───────────────────────────────────────────

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
    """A regressão que eu mais temeria: o caminho antigo tinha de ficar igual."""
    saida = _render({"query": "SELECT * FROM t LIMIT {{ $Filtro.limite }}"})
    assert saida["query"] == "SELECT * FROM t LIMIT 50"


# ── Tipo do valor ───────────────────────────────────────────────────────────
#
# O valor de `queryParams` vira bind de SQL (`$1`), e o tipo decide como o
# Postgres compara com a coluna. `Template.render()` do Jinja devolve texto
# sempre — `{{ x }}` com 50 vira `'50'` e com None vira a string `'None'`.

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
    """`ano-{{ x }}` pede concatenação — texto é o resultado certo."""
    saida = _render({"queryParams": {"v": "ano-{{ $Filtro.limite }}"}})
    assert saida["queryParams"]["v"] == "ano-50"


def test_topo_nao_muda_de_tipo():
    """No topo o comportamento antigo é preservado de propósito: há nós que
    fazem `.strip()` no parâmetro, e trocar o tipo lá misturaria correção com
    quebra."""
    saida = _render({"timeout": "{{ $Filtro.limite }}"})
    assert saida["timeout"] == "50"


# ── Estrutura ───────────────────────────────────────────────────────────────

def test_desce_por_lista_e_dicionario_aninhados():
    saida = _render({"conf": {"filtros": [{"campo": "{{ $Filtro.bairro }}"}]}})
    assert saida["conf"]["filtros"][0]["campo"] == "Centro"


def test_chave_do_dicionario_nao_e_renderizada():
    """A chave é o nome do `:placeholder` e precisa casar com o SQL."""
    saida = _render({"queryParams": {"{{ $Filtro.bairro }}": "x"}})
    assert list(saida["queryParams"]) == ["{{ $Filtro.bairro }}"]


def test_valor_sem_expressao_passa_intacto():
    saida = _render({"queryParams": {"a": "texto", "b": 7, "c": None}})
    assert saida["queryParams"] == {"a": "texto", "b": 7, "c": None}


def test_erro_aponta_o_caminho_dentro_da_estrutura():
    with pytest.raises(ValueError) as exc:
        _render({"queryParams": {"bairro": "{{ $Filtro.inexistente }}"}})
    # Sem o caminho, a mensagem diria só "queryParams" e o usuário teria de
    # adivinhar qual das chaves quebrou.
    assert "queryParams.bairro" in str(exc.value)


# ── O que o servidor injeta da credencial não é template ─────────────────────

@pytest.mark.parametrize("senha", ["p@ss{{w0rd}}", "abc{%x%}def", "x$Filtro.bairro"])
def test_a_credencial_injetada_passa_intacta_e_sem_erro(senha):
    # Renderizada, a senha mudaria em silêncio — ou a falha de renderização a
    # repetiria na mensagem de erro, que vai à tela, ao banco e ao log.
    parametros = {
        "http_auth": {"type": "wfs", "username": "leitor", "password": senha},
        "connectionString": f"postgresql://u:{senha}@h/db",
        "query": "SELECT {{ $Filtro.limite }}",
    }
    saida = _render(parametros)
    assert saida["http_auth"] == parametros["http_auth"]
    assert saida["connectionString"] == parametros["connectionString"]
    assert saida["query"] == "SELECT 50"  # o resto segue renderizado
