# tests/unit/test_alias_expressions.py
"""Alias de no em expressoes: registro no contexto e sintaxe `$Alias.campo`.

Duas regras precisam concordar, e nao concordavam:

- `_resolve_alias` (flow/executor/core.py) decide sob QUAL nome o no entra no
  contexto. Aceita `str.isidentifier()`, que em Python 3 e Unicode — "Area"
  com acento vale.
- `_ALIAS_PATTERN` (flow/utils/expression_service.py) decide o que conta como
  `$Alias` no texto do parametro. Abria com `[A-Za-z_]`, ASCII puro.

O alias acentuado passava pela primeira e falhava na segunda: o `$` sobrevivia
ao pre-processamento e o Jinja estourava erro de sintaxe. O front tambem sugeria
o alias — o modal de configuracao aceita Unicode desde sempre.
"""
import pytest

from flow.executor.core import _resolve_alias
from flow.utils.expression_service import ExpressionService


@pytest.fixture
def svc():
    return ExpressionService()


# ── Registro no contexto ─────────────────────────────────────────────────────

def test_alias_customizado_valido_e_usado():
    assert _resolve_alias({"alias": "Caixa", "name": "ComputeBoundingBox"}) == "Caixa"


def test_rotulo_do_catalogo_cai_no_name():
    """"Caixa Delimitadora" tem espaco — nao e identificador."""
    node = {"alias": "Caixa Delimitadora", "name": "ComputeBoundingBox"}

    assert _resolve_alias(node) == "ComputeBoundingBox"


def test_alias_reservado_cai_no_name():
    assert _resolve_alias({"alias": "inputs", "name": "DataInput"}) == "DataInput"


def test_alias_acentuado_e_aceito_no_registro():
    assert _resolve_alias({"alias": "Área", "name": "ComputeArea"}) == "Área"


def test_alias_em_properties_so_vale_com_alias_vazio():
    """O `or` do _resolve_alias escolhe por veracidade, nao por validade."""
    preenchido = {"alias": "Caixa Delimitadora",
                  "properties": {"alias": "Caixa"}, "name": "ComputeBoundingBox"}
    vazio = {"alias": "", "properties": {"alias": "Caixa"}, "name": "ComputeBoundingBox"}

    assert _resolve_alias(preenchido) == "ComputeBoundingBox"
    assert _resolve_alias(vazio) == "Caixa"


# ── Sintaxe $Alias no texto ──────────────────────────────────────────────────

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
    """`R$100` e texto comum — nao pode virar variavel."""
    assert svc.find_alias("preço R$100") is None
    assert svc.render("preço R$100", {}) == "preço R$100"


def test_alias_ausente_no_contexto_levanta(svc):
    """StrictUndefined: erro explicito em vez de string vazia silenciosa."""
    with pytest.raises(Exception):
        svc.render("{{$NaoExiste.campo}}", {})


def test_find_alias_captura_o_caminho_completo(svc):
    m = svc.find_alias("{{$Área.sub.campo}}")

    assert m is not None
    assert m.group("alias") == "Área.sub.campo"


def test_alias_registrado_e_renderizavel(svc):
    """As duas regras precisam concordar: o que _resolve_alias registra,
    _ALIAS_PATTERN tem de reconhecer no texto."""
    for custom in ("Caixa", "Área", "Bifurcação", "_interno", "no2"):
        alias = _resolve_alias({"alias": custom, "name": "QualquerNo"})
        assert alias == custom, f"{custom} deveria ser registrado como si mesmo"

        m = svc.find_alias(f"{{{{${alias}.campo}}}}")
        assert m is not None, f"${alias} nao foi reconhecido como alias"
        assert m.group("alias").split(".")[0] == alias


# ── `$Alias` fora de um bloco Jinja ─────────────────────────────────────────
#
# O pré-processamento tirava o `$` do texto inteiro e, se não houvesse nenhum
# `{{`, embrulhava a STRING INTEIRA em `{{ }}`. Isso só funciona quando o
# template é um alias sozinho; nos outros casos dava em três desfechos, e dois
# eram silenciosos.

import json as _json

import pytest as _pytest

from flow.utils.expression_service import ExpressionService as _ES

_CTX = {"Pedido": {"id": 42, "nome": "Centro"}}


def _r(template):
    return _ES().render(template, dict(_CTX))


def test_alias_sozinho_continua_igual():
    assert _r("$Pedido.id") == "42"


def test_alias_no_meio_da_url():
    """Antes: TemplateSyntaxError "expected token 'end of print statement',
    got ':'" — quem escreveu uma URL recebia um erro de parser de template."""
    assert _r("https://api.org/v1/$Pedido.id/dados") == "https://api.org/v1/42/dados"


def test_alias_no_meio_do_texto():
    assert _r("bairro $Pedido.nome fim") == "bairro Centro fim"


def test_corpo_json_continua_json():
    """O pior dos três, e silencioso: a string inteira era avaliada como
    expressão Python, o corpo virava repr de dict (aspas simples, JSON
    inválido) e o alias entre aspas virava TEXTO literal — sem erro nenhum."""
    saida = _r('{"id": $Pedido.id, "n": "$Pedido.nome"}')
    assert _json.loads(saida) == {"id": 42, "n": "Centro"}


def test_alias_dentro_de_bloco_jinja_nao_e_embrulhado_de_novo():
    """Dentro de `{{ }}` já se está numa expressão: virar `{{ {{ x }} }}`
    quebraria tudo."""
    assert _r("{{ $Pedido.id }}") == "42"


def test_misturar_as_duas_sintaxes_funciona():
    """Antes o `$Alias` virava texto literal, também em silêncio."""
    assert _r("https://api.org/{{ Pedido.id }}/b/$Pedido.nome") == "https://api.org/42/b/Centro"


def test_alias_dentro_de_statement():
    assert _r("{% if $Pedido.id > 10 %}alto{% else %}baixo{% endif %}") == "alto"


def test_alias_repetido_no_mesmo_texto():
    assert _r("$Pedido.nome-$Pedido.id-$Pedido.nome") == "Centro-42-Centro"


def test_alias_desconhecido_falha_alto():
    """StrictUndefined: melhor que o erro de parser que vinha antes."""
    with _pytest.raises(Exception):
        _r("https://api.org/$Outro.id/x")


def test_tipo_nativo_sobrevive_ao_novo_preprocessamento():
    """`render_native` compartilha o mesmo pré-processamento — um alias sozinho
    tem de continuar devolvendo o valor, não o texto."""
    assert _ES().render_native("$Pedido.id", dict(_CTX)) == 42
    assert _ES().render_native("id-$Pedido.id", dict(_CTX)) == "id-42"
