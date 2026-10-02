"""Regressao do endurecimento do sandbox do PythonScript (auditoria: critica).

O validate_code_ast e a UNICA barreira entre o codigo do usuario e o host do
executor: o script roda no MESMO processo dos outros nos. A auditoria demonstrou
que a checagem so olhava ast.Attribute POR NOME, deixando passar dunders
contrabandeados como string (`obj.__getattribute__('__class__')`),
`str.format('{0.__class__}')`, e `operator.attrgetter`/`string.Formatter` — todos
caminhos ate `object.__subclasses__()` e, dali, execucao arbitraria + leitura das
credenciais mTLS do executor.

Cada teste falha SEM o fix correspondente; a docstring nomeia a mutacao que
derruba SO aquele teste.
"""
import pytest

from flow.utils.code_sandbox import (
    ALLOWED_MODULES,
    UnsafeCodeError,
    build_safe_builtins,
    validate_code_ast,
)


def _bloqueia(code: str) -> str:
    """Roda o validador; devolve a mensagem de bloqueio ou falha o teste."""
    with pytest.raises(UnsafeCodeError) as exc:
        validate_code_ast(code)
    return str(exc.value)


# ── Decisao 1: operator/string fora da allowlist ────────────────────────────

def test_operator_e_string_fora_da_allowlist():
    """Mutacao: readicionar 'operator'/'string' a ALLOWED_MODULES.

    Eram os dois vetores diretos: attrgetter/methodcaller buscam atributo por
    string, Formatter.get_field alcanca globals de funcao.
    """
    assert "operator" not in ALLOWED_MODULES
    assert "string" not in ALLOWED_MODULES


def test_import_de_operator_bloqueado():
    _bloqueia("import operator")


def test_import_de_string_bloqueado():
    _bloqueia("import string")


def test_fuga_operator_attrgetter_bloqueada():
    _bloqueia(
        "import operator\n"
        "x = operator.attrgetter('__bases__')(().__class__)"
    )


def test_fuga_string_formatter_get_field_bloqueada():
    _bloqueia(
        "import string\n"
        "string.Formatter().get_field('0.__init__.__globals__', [()], {})"
    )


# ── Decisao 2: QUALQUER dunder em ast.Attribute ─────────────────────────────

@pytest.mark.parametrize("code", [
    "x = ().__class__",
    "x = ().__class__.__bases__[0]",
    "x = obj.__subclasses__()",
    "x = ().__getattribute__('__class__')",   # __getattribute__ nao estava na lista velha
    "x = obj.__reduce__()",
    "x = obj.__reduce_ex__(2)",
    "x = f'{obj.__class__.__mro__}'",          # dentro de f-string tambem e ast.Attribute
    "x = obj.__globals__",
])
def test_dunder_em_atributo_bloqueado(code):
    """Mutacao: trocar _e_dunder pela lista fixa _BLOCKED_ATTRS antiga.

    A lista antiga nao tinha __getattribute__/__reduce__ — a fuga demonstrada
    usava exatamente __getattribute__.
    """
    msg = _bloqueia(code)
    assert "dunder" in msg


# ── Decisao 3: atributos de frame/codigo/traceback (nao-dunder) ─────────────

@pytest.mark.parametrize("code", [
    "x = (i for i in []).gi_frame.f_back.f_globals",
    "x = (i for i in []).gi_frame",
    "x = e.__traceback__.tb_frame",  # tb_frame bloqueado (o __traceback__ tb)
    "x = frame.f_builtins",
    "x = frame.f_locals",
])
def test_atributo_de_introspeccao_bloqueado(code):
    """Mutacao: remover _BLOCKED_ATTR_NAMES.

    gi_frame/f_back/f_globals/f_builtins NAO sao dunders e escapariam do
    predicado; levam aos globals reais e ao __builtins__ verdadeiro.
    """
    _bloqueia(code)


# ── Decisao 4: format/format_map/get_field bloqueados como metodo ───────────

@pytest.mark.parametrize("code", [
    "x = '{0.__class__}'.format(())",
    "x = '{}'.format(v)",
    "x = '{k}'.format_map(d)",
    "x = fmt.get_field('0', a, k)",
    # concatenacao para driblar a checagem de string literal — barrada no .format
    "fmt = '{0.__' + 'class__}'\nx = fmt.format(())",
])
def test_metodo_de_format_bloqueado(code):
    """Mutacao: remover 'format'/'format_map'/'get_field' de _BLOCKED_METHODS.

    str.format resolve `{0.__class__}` pelo maquinario de format-field, sem um
    ast.Attribute que a checagem veja; a concatenacao driblaria ate a checagem
    de string literal.
    """
    _bloqueia(code)


# ── Decisao 5: dunder contrabandeado em string literal ──────────────────────

@pytest.mark.parametrize("code", [
    "x = ().__getattribute__('__class__')",
    "g = '{0.__init__.__globals__}'",
    "x = d['__builtins__']",
    "x = algo['__globals__']",
])
def test_dunder_em_string_bloqueado(code):
    """Mutacao: remover a checagem de ast.Constant.

    Cobre subscript (`d['__builtins__']`), argumento de chamada e format string
    de uma so vez — ast.walk visita todo ast.Constant.
    """
    _bloqueia(code)


# ── typing fora da allowlist ────────────────────────────────────────────────

def test_typing_fora_da_allowlist():
    """Mutacao: readicionar 'typing' a ALLOWED_MODULES.

    `typing.ForwardRef(s)._evaluate({}, ...)` e `typing.get_type_hints(obj,
    globalns={})` fazem eval de string com os builtins reais — execucao
    arbitraria no processo do executor, com a string montada em runtime para
    nao ser um literal com dunder.
    """
    assert "typing" not in ALLOWED_MODULES
    _bloqueia("import typing")
    _bloqueia("from typing import ForwardRef")


def test_fuga_typing_forwardref_bloqueada():
    """O caminho demonstrado na revisao: passava pela checagem de AST."""
    _bloqueia(
        "import typing\n"
        "d = '_' + '_'\n"
        "out = []\n"
        "typing.ForwardRef('out.append(' + d + 'import' + d + '(\"os\").getpid())')"
        "._evaluate({}, {'out': out}, frozenset())"
    )


def test_anotacao_de_tipo_sem_typing_passa():
    """Quem anotava tipos nao perde nada: os genericos embutidos bastam."""
    validate_code_ast(
        "def contar(xs: list[int]) -> dict[str, int | None]:\n"
        "    return {str(x): x for x in xs}\n"
        "result = contar([1, 2])"
    )


# ── Codigo legitimo continua passando (nao pode virar sandbox inutil) ───────

@pytest.mark.parametrize("code", [
    "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2]})",
    "gdf['area_ha'] = gdf.geometry.area / 10_000\nresult = gdf",
    "result = gdf.to_json()",
    "n = len(gdf)\nmsg = f'total: {n} feicoes'",       # f-string sem atributo
    "s = 'valor: %d' % 42",                             # %-formatting continua
    "import math, json, re, collections, itertools, functools",
    "items = sorted(dados, key=lambda x: x[0])",
    "df2 = df.rename(columns={'old__mid': 'novo'})",    # __ no meio nao e dunder
    "cols = [c for c in gdf.columns if c.startswith('geo')]",
    "import numpy as np\narr = np.array([1, 2, 3]).reshape(3, 1)",
    "result = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty]",
])
def test_codigo_legitimo_passa(code):
    """Mutacao: qualquer regra ampla demais (ex.: bloquear TODA string com '__',
    ou todo `.format`-like) derruba um destes."""
    validate_code_ast(code)  # nao levanta


# ── Builtins perigosos removidos + __import__ trocado ───────────────────────

def test_build_safe_builtins_remove_perigosos_e_troca_import():
    """Mutacao: esvaziar BLOCKED_BUILTINS, ou nao substituir __import__."""
    safe = build_safe_builtins()
    for nome in ("getattr", "setattr", "delattr", "type", "eval", "exec",
                 "open", "compile", "globals", "vars"):
        assert nome not in safe, f"{nome} deveria estar bloqueado"
    assert safe["__import__"].__name__ == "safe_import"
    # sanidade: builtins uteis continuam
    for nome in ("len", "range", "enumerate", "print", "sorted", "dict"):
        assert nome in safe


def test_safe_import_barra_modulo_fora_da_allowlist():
    """Mutacao: safe_import deixar de checar a allowlist."""
    safe = build_safe_builtins()
    with pytest.raises(ImportError):
        safe["__import__"]("os")
    # modulo permitido passa
    assert safe["__import__"]("math") is not None


def test_import_com_erro_de_sintaxe_propaga_syntaxerror():
    """Codigo invalido nao e UnsafeCodeError — deixa o SyntaxError subir para o
    caminho de erro do no."""
    with pytest.raises(SyntaxError):
        validate_code_ast("def :\n")


# ── Fuga por handle de modulo (auditoria SEG-02) ─────────────────────────────
# A allowlist deixava passar `uuid.os`, `dataclasses.sys`, `collections._sys` e
# `importlib.import_module` — atributos NAO-dunder de modulos permitidos que
# reexportam a stdlib perigosa. A partir de `os`/`sys` chega-se a
# os.popen/subprocess/importlib. Cada caso abaixo e um one-liner que abria RCE.
import pytest as _pytest


@_pytest.mark.parametrize("codigo", [
    "import uuid\nos = uuid.os\nresult = os.popen('id').read()",
    "import dataclasses\nsub = dataclasses.sys.modules['subprocess']",
    "import collections\nx = collections._sys",
    "import random\nx = random._os.environ",
    "import enum\nx = enum.sys",
    "import datetime\nx = datetime.sys.modules",
    "import pandas as pd\nx = pd.io.common.os.environ",
])
def test_bloqueia_handle_de_modulo_perigoso(codigo):
    with _pytest.raises(UnsafeCodeError):
        validate_code_ast(codigo)


@_pytest.mark.parametrize("codigo", [
    "import pandas as pd\nresult = pd.DataFrame({'a': [1, 2]}).sum()",
    "import geopandas as gpd\nimport shapely\nresult = gpd.GeoDataFrame(geometry=[shapely.Point(0, 0)])",
    "import numpy as np\nresult = np.array([1, 2, 3]).mean()",
    "import re\nresult = re.sub(r'x', 'y', 'xx')",
    "import collections\nresult = dict(collections.Counter([1, 1, 2]))",
    "df = input_data\nresult = df.groupby('c').agg({'v': 'sum'})",
])
def test_permite_manipulacao_de_dados_legitima(codigo):
    validate_code_ast(codigo)  # nao deve levantar
