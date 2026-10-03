# tests/unit/test_alias_expressions.py
"""Node alias in expressions: registration in the context and `$Alias.campo` syntax.

Two rules need to agree, and they did not:

- `_resolve_alias` (flow/executor/core.py) decides under WHICH name the node
  enters the context. It accepts `str.isidentifier()`, which in Python 3 is
  Unicode — "Area" with an accent is valid.
- `_ALIAS_PATTERN` (flow/utils/expression_service.py) decides what counts as
  `$Alias` in the parameter text. It started with `[A-Za-z_]`, pure ASCII.

The accented alias passed the first and failed the second: the `$` survived
the preprocessing and Jinja blew up with a syntax error. The frontend also
suggested the alias — the configuration modal has always accepted Unicode.
"""
import pytest

from flow.executor.core import _resolve_alias
from flow.utils.expression_service import ExpressionService


@pytest.fixture
def svc():
    return ExpressionService()


# ── Registration in the context ──────────────────────────────────────────────

def test_alias_customizado_valido_e_usado():
    assert _resolve_alias({"alias": "Caixa", "name": "ComputeBoundingBox"}) == "Caixa"


def test_rotulo_do_catalogo_cai_no_name():
    """"Caixa Delimitadora" has a space — it is not an identifier."""
    node = {"alias": "Caixa Delimitadora", "name": "ComputeBoundingBox"}

    assert _resolve_alias(node) == "ComputeBoundingBox"


def test_alias_reservado_cai_no_name():
    assert _resolve_alias({"alias": "inputs", "name": "DataInput"}) == "DataInput"


def test_alias_acentuado_e_aceito_no_registro():
    assert _resolve_alias({"alias": "Área", "name": "ComputeArea"}) == "Área"


def test_alias_em_properties_so_vale_com_alias_vazio():
    """_resolve_alias's `or` picks by truthiness, not by validity."""
    preenchido = {"alias": "Caixa Delimitadora",
                  "properties": {"alias": "Caixa"}, "name": "ComputeBoundingBox"}
    vazio = {"alias": "", "properties": {"alias": "Caixa"}, "name": "ComputeBoundingBox"}

    assert _resolve_alias(preenchido) == "ComputeBoundingBox"
    assert _resolve_alias(vazio) == "Caixa"


# ── $Alias syntax in the text ────────────────────────────────────────────────

def test_renderiza_alias_ascii(svc):
    ctx = {"ComputeBoundingBox": {"bbox_string": "-63,-13,-60,-10"}}

    assert svc.render("{{$ComputeBoundingBox.bbox_string}}", ctx) == "-63,-13,-60,-10"


def test_renderiza_alias_comecado_por_letra_acentuada(svc):
    """Regressao: `[A-Za-z_]` recusava o primeiro caractere e o `$` vazava."""
    ctx = {"Área": {"total": 42}}

    assert svc.render("{{$Área.total}}", ctx) == "42"


def test_renderiza_campo_com_acento(svc):
    """Coluna de shapefile costuma vir acentuada."""
    ctx = {"Municipios": {"população": 1500}}

    assert svc.render("{{$Municipios.população}}", ctx) == "1500"


def test_alias_acentuado_no_meio_ja_funcionava(svc):
    ctx = {"Bifurcação": {"branch": True}}

    assert svc.render("{{$Bifurcação.branch}}", ctx) == "True"


def test_alias_sem_chaves_e_envolvido_em_jinja(svc):
    ctx = {"Área": {"total": 7}}

    assert svc.render("$Área.total", ctx) == "7"


def test_alias_interpolado_no_meio_do_texto(svc):
    ctx = {"Área": {"total": 7}}

    assert svc.render("total={{$Área.total}}ha", ctx) == "total=7ha"


def test_cifrao_seguido_de_digito_nao_e_alias(svc):
    """`R$100` is ordinary text — it must not become a variable."""
    assert svc.find_alias("preço R$100") is None
    assert svc.render("preço R$100", {}) == "preço R$100"


def test_alias_ausente_no_contexto_levanta(svc):
    """StrictUndefined: an explicit error instead of a silent empty string."""
    with pytest.raises(Exception):
        svc.render("{{$NaoExiste.campo}}", {})


def test_find_alias_captura_o_caminho_completo(svc):
    m = svc.find_alias("{{$Área.sub.campo}}")

    assert m is not None
    assert m.group("alias") == "Área.sub.campo"


def test_alias_registrado_e_renderizavel(svc):
    """The two rules need to agree: what _resolve_alias registers,
    _ALIAS_PATTERN has to recognize in the text."""
    for custom in ("Caixa", "Área", "Bifurcação", "_interno", "no2"):
        alias = _resolve_alias({"alias": custom, "name": "QualquerNo"})
        assert alias == custom, f"{custom} deveria ser registrado como si mesmo"

        m = svc.find_alias(f"{{{{${alias}.campo}}}}")
        assert m is not None, f"${alias} nao foi reconhecido como alias"
        assert m.group("alias").split(".")[0] == alias


# ── `$Alias` outside a Jinja block ──────────────────────────────────────────
#
# The preprocessing stripped the `$` from the whole text and, if there was no
# `{{`, wrapped the WHOLE STRING in `{{ }}`. That only works when the template
# is a lone alias; in the other cases it led to three outcomes, and two of them
# were silent.

import json as _json

import pytest as _pytest

from flow.utils.expression_service import ExpressionService as _ES

_CTX = {"Pedido": {"id": 42, "nome": "Centro"}}


def _r(template):
    return _ES().render(template, dict(_CTX))


def test_alias_sozinho_continua_igual():
    assert _r("$Pedido.id") == "42"


def test_alias_no_meio_da_url():
    """Before: TemplateSyntaxError "expected token 'end of print statement',
    got ':'" — whoever wrote a URL got a template parser error."""
    assert _r("https://api.org/v1/$Pedido.id/dados") == "https://api.org/v1/42/dados"


def test_alias_no_meio_do_texto():
    assert _r("bairro $Pedido.nome fim") == "bairro Centro fim"


def test_corpo_json_continua_json():
    """The worst of the three, and silent: the whole string was evaluated as a
    Python expression, the body became a dict repr (single quotes, invalid
    JSON) and the quoted alias became literal TEXT — with no error at all."""
    saida = _r('{"id": $Pedido.id, "n": "$Pedido.nome"}')
    assert _json.loads(saida) == {"id": 42, "n": "Centro"}


def test_alias_dentro_de_bloco_jinja_nao_e_embrulhado_de_novo():
    """Inside `{{ }}` you are already in an expression: turning it into
    `{{ {{ x }} }}` would break everything."""
    assert _r("{{ $Pedido.id }}") == "42"


def test_misturar_as_duas_sintaxes_funciona():
    """Before, the `$Alias` became literal text, also silently."""
    assert _r("https://api.org/{{ Pedido.id }}/b/$Pedido.nome") == "https://api.org/42/b/Centro"


def test_alias_dentro_de_statement():
    assert _r("{% if $Pedido.id > 10 %}alto{% else %}baixo{% endif %}") == "alto"


def test_alias_repetido_no_mesmo_texto():
    assert _r("$Pedido.nome-$Pedido.id-$Pedido.nome") == "Centro-42-Centro"


def test_alias_desconhecido_falha_alto():
    """StrictUndefined: better than the parser error that came before."""
    with _pytest.raises(Exception):
        _r("https://api.org/$Outro.id/x")


def test_tipo_nativo_sobrevive_ao_novo_preprocessamento():
    """`render_native` shares the same preprocessing — a lone alias must keep
    returning the value, not the text."""
    assert _ES().render_native("$Pedido.id", dict(_CTX)) == 42
    assert _ES().render_native("id-$Pedido.id", dict(_CTX)) == "id-42"
