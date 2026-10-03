"""Regression test for the PythonScript sandbox hardening (audit: critical).

validate_code_ast is the ONLY barrier between the user's code and the
executor host: the script runs in the SAME process as the other nodes. The
audit showed that the check only looked at ast.Attribute BY NAME, letting
through dunders smuggled in as strings (`obj.__getattribute__('__class__')`),
`str.format('{0.__class__}')`, and `operator.attrgetter`/`string.Formatter` — all
paths to `object.__subclasses__()` and, from there, arbitrary execution + reading
the executor's mTLS credentials.

Each test fails WITHOUT the corresponding fix; the docstring names the mutation
that breaks ONLY that test.
"""
import pytest

from flow.utils.code_sandbox import (
    ALLOWED_MODULES,
    UnsafeCodeError,
    build_safe_builtins,
    validate_code_ast,
)


def _bloqueia(code: str) -> str:
    """Runs the validator; returns the block message or fails the test."""
    with pytest.raises(UnsafeCodeError) as exc:
        validate_code_ast(code)
    return str(exc.value)


# ── Decisao 1: operator/string fora da allowlist ────────────────────────────

def test_operator_e_string_fora_da_allowlist():
    """Mutation: re-add 'operator'/'string' to ALLOWED_MODULES.

    They were the two direct vectors: attrgetter/methodcaller fetch an attribute
    by string, Formatter.get_field reaches a function's globals.
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
    "x = ().__getattribute__('__class__')",   # __getattribute__ was not in the old list
    "x = obj.__reduce__()",
    "x = obj.__reduce_ex__(2)",
    "x = f'{obj.__class__.__mro__}'",          # inside an f-string it is also an ast.Attribute
    "x = obj.__globals__",
])
def test_dunder_em_atributo_bloqueado(code):
    """Mutation: replace _e_dunder with the old fixed _BLOCKED_ATTRS list.

    The old list lacked __getattribute__/__reduce__ — the demonstrated escape
    used exactly __getattribute__.
    """
    msg = _bloqueia(code)
    assert "dunder" in msg


# ── Decision 3: frame/code/traceback attributes (non-dunder) ────────────────

@pytest.mark.parametrize("code", [
    "x = (i for i in []).gi_frame.f_back.f_globals",
    "x = (i for i in []).gi_frame",
    "x = e.__traceback__.tb_frame",  # tb_frame bloqueado (o __traceback__ tb)
    "x = frame.f_builtins",
    "x = frame.f_locals",
])
def test_atributo_de_introspeccao_bloqueado(code):
    """Mutation: remove _BLOCKED_ATTR_NAMES.

    gi_frame/f_back/f_globals/f_builtins are NOT dunders and would escape the
    predicate; they lead to the real globals and the true __builtins__.
    """
    _bloqueia(code)


# ── Decisao 4: format/format_map/get_field bloqueados como metodo ───────────

@pytest.mark.parametrize("code", [
    "x = '{0.__class__}'.format(())",
    "x = '{}'.format(v)",
    "x = '{k}'.format_map(d)",
    "x = fmt.get_field('0', a, k)",
    # concatenation to dodge the string-literal check — blocked at .format
    "fmt = '{0.__' + 'class__}'\nx = fmt.format(())",
])
def test_metodo_de_format_bloqueado(code):
    """Mutation: remove 'format'/'format_map'/'get_field' from _BLOCKED_METHODS.

    str.format resolves `{0.__class__}` through the format-field machinery,
    without an ast.Attribute the check can see; concatenation would dodge even
    the string-literal check.
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
    """Mutation: remove the ast.Constant check.

    Covers subscript (`d['__builtins__']`), call argument and format string
    all at once — ast.walk visits every ast.Constant.
    """
    _bloqueia(code)


# ── typing outside the allowlist ────────────────────────────────────────────

def test_typing_fora_da_allowlist():
    """Mutation: re-add 'typing' to ALLOWED_MODULES.

    `typing.ForwardRef(s)._evaluate({}, ...)` and `typing.get_type_hints(obj,
    globalns={})` eval a string with the real builtins — arbitrary execution
    in the executor process, with the string built at runtime so it is not a
    literal containing a dunder.
    """
    assert "typing" not in ALLOWED_MODULES
    _bloqueia("import typing")
    _bloqueia("from typing import ForwardRef")


def test_fuga_typing_forwardref_bloqueada():
    """The path demonstrated in the review: it passed the AST check."""
    _bloqueia(
        "import typing\n"
        "d = '_' + '_'\n"
        "out = []\n"
        "typing.ForwardRef('out.append(' + d + 'import' + d + '(\"os\").getpid())')"
        "._evaluate({}, {'out': out}, frozenset())"
    )


def test_anotacao_de_tipo_sem_typing_passa():
    """Whoever annotated types loses nothing: the built-in generics are enough."""
    validate_code_ast(
        "def contar(xs: list[int]) -> dict[str, int | None]:\n"
        "    return {str(x): x for x in xs}\n"
        "result = contar([1, 2])"
    )


# ── Legitimate code still passes (must not become a useless sandbox) ────────

@pytest.mark.parametrize("code", [
    "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2]})",
    "gdf['area_ha'] = gdf.geometry.area / 10_000\nresult = gdf",
    "result = gdf.to_json()",
    "n = len(gdf)\nmsg = f'total: {n} feicoes'",       # f-string without an attribute
    "s = 'valor: %d' % 42",                             # %-formatting continua
    "import math, json, re, collections, itertools, functools",
    "items = sorted(dados, key=lambda x: x[0])",
    "df2 = df.rename(columns={'old__mid': 'novo'})",    # __ in the middle is not a dunder
    "cols = [c for c in gdf.columns if c.startswith('geo')]",
    "import numpy as np\narr = np.array([1, 2, 3]).reshape(3, 1)",
    "result = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty]",
])
def test_codigo_legitimo_passa(code):
    """Mutation: any rule that is too broad (e.g. blocking EVERY string with '__',
    or every `.format`-like call) breaks one of these."""
    validate_code_ast(code)  # does not raise


# ── Builtins perigosos removidos + __import__ trocado ───────────────────────

def test_build_safe_builtins_remove_perigosos_e_troca_import():
    """Mutation: empty BLOCKED_BUILTINS, or do not replace __import__."""
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
    """Invalid code is not UnsafeCodeError — let the SyntaxError propagate to the
    node's error path."""
    with pytest.raises(SyntaxError):
        validate_code_ast("def :\n")


# ── Escape through a module handle (audit SEG-02) ────────────────────────────
# The allowlist let through `uuid.os`, `dataclasses.sys`, `collections._sys` and
# `importlib.import_module` — NON-dunder attributes of allowed modules that
# re-export the dangerous stdlib. From `os`/`sys` one reaches
# os.popen/subprocess/importlib. Each case below is a one-liner that opened RCE.
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
    validate_code_ast(codigo)  # must not raise
