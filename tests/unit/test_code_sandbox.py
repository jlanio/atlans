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


def _block_message(code: str) -> str:
    """Runs the validator; returns the block message or fails the test."""
    with pytest.raises(UnsafeCodeError) as exc:
        validate_code_ast(code)
    return str(exc.value)


# ── Decisao 1: operator/string fora da allowlist ────────────────────────────

def test_operator_and_string_outside_the_allowlist():
    """Mutation: re-add 'operator'/'string' to ALLOWED_MODULES.

    They were the two direct vectors: attrgetter/methodcaller fetch an attribute
    by string, Formatter.get_field reaches a function's globals.
    """
    assert "operator" not in ALLOWED_MODULES
    assert "string" not in ALLOWED_MODULES


def test_import_of_operator_blocked():
    _block_message("import operator")


def test_import_of_string_blocked():
    _block_message("import string")


def test_operator_attrgetter_escape_blocked():
    _block_message(
        "import operator\n"
        "x = operator.attrgetter('__bases__')(().__class__)"
    )


def test_string_formatter_get_field_escape_blocked():
    _block_message(
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
def test_dunder_in_attribute_blocked(code):
    """Mutation: replace _e_dunder with the old fixed _BLOCKED_ATTRS list.

    The old list lacked __getattribute__/__reduce__ — the demonstrated escape
    used exactly __getattribute__.
    """
    msg = _block_message(code)
    assert "dunder" in msg


# ── Decision 3: frame/code/traceback attributes (non-dunder) ────────────────

@pytest.mark.parametrize("code", [
    "x = (i for i in []).gi_frame.f_back.f_globals",
    "x = (i for i in []).gi_frame",
    "x = e.__traceback__.tb_frame",  # tb_frame bloqueado (o __traceback__ tb)
    "x = frame.f_builtins",
    "x = frame.f_locals",
])
def test_introspection_attribute_blocked(code):
    """Mutation: remove _BLOCKED_ATTR_NAMES.

    gi_frame/f_back/f_globals/f_builtins are NOT dunders and would escape the
    predicate; they lead to the real globals and the true __builtins__.
    """
    _block_message(code)


# ── Decisao 4: format/format_map/get_field bloqueados como metodo ───────────

@pytest.mark.parametrize("code", [
    "x = '{0.__class__}'.format(())",
    "x = '{}'.format(v)",
    "x = '{k}'.format_map(d)",
    "x = fmt.get_field('0', a, k)",
    # concatenation to dodge the string-literal check — blocked at .format
    "fmt = '{0.__' + 'class__}'\nx = fmt.format(())",
])
def test_format_method_blocked(code):
    """Mutation: remove 'format'/'format_map'/'get_field' from _BLOCKED_METHODS.

    str.format resolves `{0.__class__}` through the format-field machinery,
    without an ast.Attribute the check can see; concatenation would dodge even
    the string-literal check.
    """
    _block_message(code)


# ── Decisao 5: dunder contrabandeado em string literal ──────────────────────

@pytest.mark.parametrize("code", [
    "x = ().__getattribute__('__class__')",
    "g = '{0.__init__.__globals__}'",
    "x = d['__builtins__']",
    "x = algo['__globals__']",
])
def test_dunder_in_string_blocked(code):
    """Mutation: remove the ast.Constant check.

    Covers subscript (`d['__builtins__']`), call argument and format string
    all at once — ast.walk visits every ast.Constant.
    """
    _block_message(code)


# ── typing outside the allowlist ────────────────────────────────────────────

def test_typing_outside_the_allowlist():
    """Mutation: re-add 'typing' to ALLOWED_MODULES.

    `typing.ForwardRef(s)._evaluate({}, ...)` and `typing.get_type_hints(obj,
    globalns={})` eval a string with the real builtins — arbitrary execution
    in the executor process, with the string built at runtime so it is not a
    literal containing a dunder.
    """
    assert "typing" not in ALLOWED_MODULES
    _block_message("import typing")
    _block_message("from typing import ForwardRef")


def test_typing_forwardref_escape_blocked():
    """The path demonstrated in the review: it passed the AST check."""
    _block_message(
        "import typing\n"
        "d = '_' + '_'\n"
        "out = []\n"
        "typing.ForwardRef('out.append(' + d + 'import' + d + '(\"os\").getpid())')"
        "._evaluate({}, {'out': out}, frozenset())"
    )


def test_type_annotation_without_typing_passes():
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
def test_legitimate_code_passes(code):
    """Mutation: any rule that is too broad (e.g. blocking EVERY string with '__',
    or every `.format`-like call) breaks one of these."""
    validate_code_ast(code)  # does not raise


# ── Builtins perigosos removidos + __import__ trocado ───────────────────────

def test_build_safe_builtins_removes_dangerous_and_replaces_import():
    """Mutation: empty BLOCKED_BUILTINS, or do not replace __import__."""
    safe = build_safe_builtins()
    for nome in ("getattr", "setattr", "delattr", "type", "eval", "exec",
                 "open", "compile", "globals", "vars"):
        assert nome not in safe, f"{nome} deveria estar bloqueado"
    assert safe["__import__"].__name__ == "safe_import"
    # sanidade: builtins uteis continuam
    for nome in ("len", "range", "enumerate", "print", "sorted", "dict"):
        assert nome in safe


def test_safe_import_blocks_module_outside_the_allowlist():
    """Mutacao: safe_import deixar de checar a allowlist."""
    safe = build_safe_builtins()
    with pytest.raises(ImportError):
        safe["__import__"]("os")
    # modulo permitido passa
    assert safe["__import__"]("math") is not None


def test_import_with_syntax_error_propagates_syntaxerror():
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
def test_blocks_dangerous_module_handle(codigo):
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
def test_allows_legitimate_data_manipulation(codigo):
    validate_code_ast(codigo)  # must not raise


# ── I/O of the allowlisted libraries (review of 2026-10-31) ─────────────────
# pandas/geopandas/numpy read and write files and URLs by themselves: none of
# these has a dunder or an import for the older checks to see.

@pytest.mark.parametrize("code", [
    "import pandas as pd\nresult = pd.read_pickle('/tmp/x.pkl')",
    "import pandas as pd\nresult = pd.read_csv('/etc/passwd')",
    "import pandas as pd\nresult = pd.read_csv('http://169.254.169.254/latest/meta-data/')",
    "import pandas as pd\nresult = pd.read_parquet('http://169.254.169.254/x')",
    "import geopandas as gpd\nresult = gpd.read_file('/etc/passwd')",
    "import pyogrio\nresult = pyogrio.read_dataframe('/etc/passwd')",
    "result = minha.to_pickle('/tmp/evil.pkl')",
    "minha.to_file('/tmp/x.gpkg')",
    "import numpy as np\nresult = np.DataSource('/tmp').open('/etc/passwd')",
    "import numpy as np\nresult = np.load('/tmp/x.npy')",
    "import numpy as np\nnp.save('/tmp/x.npy', np.array([1]))",
    "result = minha.query('a > 1', engine='python')",
    "result = minha.eval('a + b')",
    "import pandas as pd\nresult = pd.io.common.urlopen('http://x')",
    "import pyproj\npyproj.network.set_network_enabled(True)",
])
def test_library_io_is_refused(code):
    with pytest.raises(UnsafeCodeError):
        validate_code_ast(code)


@pytest.mark.parametrize("code", [
    "result = minha.to_csv('/tmp/evil.txt')",
    "result = minha.to_csv(path_or_buf='/tmp/evil.txt')",
    "result = minha.to_json(buf)",
    "result = minha.to_csv(**{'path_or_buf': '/tmp/x'})",
    "f = minha.to_csv\nresult = f('/tmp/x')",       # the bound method under another name
    "result = list(map(minha.to_csv, ['/tmp/x']))",
])
def test_writers_with_a_destination_are_refused(code):
    with pytest.raises(UnsafeCodeError):
        validate_code_ast(code)


@pytest.mark.parametrize("code", [
    "result = gdf.to_json()",
    "result = df.to_csv(index=False, sep=';')",
    "result = df.to_string(max_rows=10)",
    "result = df.to_html(index=False)",
    "result = gdf.to_crs(3857)",
    "result = df.to_dict(orient='records')",
    "import json\nresult = json.loads('{\"a\": 1}')",
    "result = df[df['pop'] > 1000]",
])
def test_transformations_without_io_still_pass(code):
    validate_code_ast(code)


# ── Round-2 review: import forms, class patterns and legitimate privates ─────

@pytest.mark.parametrize("code", [
    "from pyogrio.raw import read",
    "import pyogrio.raw as r",
    "from pyogrio import vsi_listtree",
    "from geopandas.io.file import _read_file",
    "from pandas.io.common import os",
    "from pandas.core.arrays.arrow.array import pa",
    "from datetime import sys",
    "from numpy import *",
    "import geopandas.io.file as f",
    "match 1:\n    case object(__class__=c):\n        pass",
    "match x:\n    case object(OSFile=f):\n        pass",
    "from . import algo",
])
def test_import_forms_and_class_patterns_go_through_the_same_rules(code):
    """Only attribute access was checked: imported names, submodules of an
    import and the keywords of a class pattern read attributes with no
    ast.Attribute — the GDAL/Arrow I/O and /vsicurl/ came back through them."""
    with pytest.raises(UnsafeCodeError):
        validate_code_ast(code)


def test_pyogrio_left_the_allowlist():
    with pytest.raises(UnsafeCodeError):
        validate_code_ast("import pyogrio")


@pytest.mark.parametrize("code", [
    "for row in df.itertuples():\n    d = row._asdict()\n    v = row._1",
    "from collections import namedtuple\nP = namedtuple('P', 'a b')\np = P(1, 2)._replace(a=3)\nf = P._fields",
    "class C:\n    def __init__(self):\n        self._x = 1\n    def v(self):\n        return self._x",
    "result = df._get_numeric_data()",
    "nome = gdf._geometry_column_name",
    "result = df.raw + df.fs",
    "from shapely.geometry import Point, shape\nfrom shapely.ops import unary_union",
    "from datetime import datetime, timedelta",
    "import numpy.random as npr",
    "match row:\n    case {'a': 1}:\n        pass",
])
def test_ordinary_code_with_underscores_and_imports_still_passes(code):
    """A general ban on `_x` refused namedtuples, itertuples rows, user classes
    and pandas' own helpers (round-2 review): only the I/O internals are out."""
    validate_code_ast(code)


@pytest.mark.parametrize("nome", ["_read_file", "_to_file", "_datasource", "_get_handle", "vsi_unlink"])
def test_the_private_io_internals_stay_out(nome):
    with pytest.raises(UnsafeCodeError):
        validate_code_ast(f"x = obj.{nome}")
