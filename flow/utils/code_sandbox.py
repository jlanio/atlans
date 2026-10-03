# flow/utils/code_sandbox.py
# Security validation for Python code executed by the PythonScript node.
# Two layers: pre-execution AST analysis + a custom __import__.
#
# WARNING — what this module does NOT guarantee. The AST check is a defensive
# ALLOWLIST, not isolation. It closes the KNOWN escapes (class chain, frame
# introspection, attribute-by-string), but the user's code still runs IN THE
# SAME PROCESS as the other nodes. The proper defense is a subprocess with
# seccomp/rlimits, logged as a follow-up; until then, treat this layer as
# "raises the bar", not "prevents everything". That is why it is conservative:
# when in doubt, it blocks.

import ast
import builtins
import re

# ── Allowed modules ──────────────────────────────────────────────────────────
# Only modules that are safe for geospatial data manipulation.
# Any import outside this list will be blocked.
ALLOWED_MODULES = {
    # Data and GIS
    # `fiona` left the list together with the dependency: geopandas 1.x reads and
    # writes via pyogrio, and keeping both packaged two copies of GDAL in the same
    # process (~99 MB, with global GDAL_DATA/PROJ_LIB contended between them).
    "pandas", "geopandas", "numpy", "shapely", "pyproj", "pyogrio",
    # Safe stdlib
    # `operator` and `string` LEFT the list: they were sandbox escape vectors.
    # `operator.attrgetter('__bases__')(cls)` and `operator.methodcaller(...)`
    # look up attributes by STRING, sidestepping the ast.Attribute check below;
    # `string.Formatter().get_field('0.__init__.__globals__', ...)` reaches
    # function globals through the format-field machinery. Without them in the
    # allowlist, both paths are unavailable. User substitute: lambdas instead of
    # attrgetter/itemgetter, f-strings instead of Formatter.
    #
    # `typing` also LEFT: `typing.ForwardRef(texto)._evaluate({}, ...)` and
    # `typing.get_type_hints(obj, globalns={})` `eval` a string with the REAL
    # builtins (a globals without `__builtins__` gets the real ones) — and a
    # string assembled at runtime (`'_' + '_' + 'import' ...`) is not a literal the
    # dunder check can see. Type annotations do not need it: `list[int]`,
    # `dict[str, float]` and `X | None` are built in since 3.10.
    "math", "json", "re", "datetime", "collections", "itertools",
    "functools", "statistics", "decimal", "fractions",
    "copy", "enum", "dataclasses", "textwrap",
    "hashlib", "base64", "uuid", "random",
}

# ── Dangerous builtins ───────────────────────────────────────────────────────
# Blocked to prevent filesystem access, code execution and introspection
# of the runtime's internal objects.
BLOCKED_BUILTINS = {
    # Code execution
    "open", "exec", "eval", "__import__", "compile", "breakpoint",
    "input", "memoryview", "reload",
    # Introspeccao perigosa — permite acessar namespace interno,
    # atributos privados e construir classes arbitrarias
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "type",
}

# ── NON-dunder attributes that expose interpreter internals ──────────────────
# The _e_dunder predicate below covers __class__/__globals__/__subclasses__/etc.
# These have NO underscores at the ends and would escape the predicate, but give
# access to frames, code objects and tracebacks — from which the real globals
# and the true __builtins__ can be reached (e.g. `(x for x in []).gi_frame.f_back.f_globals`).
#
# Besides frame internals, this list closes the MODULE HANDLE escape: an
# allowlisted module re-exports dangerous stdlib as a plain attribute, with no
# dunder or `import` for the check to see — `uuid.os`, `random._os`,
# `dataclasses.sys`, `datetime.sys`, `collections._sys`, `enum.sys`. From
# `os`/`sys` one gets to `os.system`/`os.popen`/`os.environ`, to
# `sys.modules['subprocess']` and to `importlib.import_module` (which bypasses
# safe_import). Since the only possible `import` already goes through the
# allowlist, blocking the NAME of these attributes cuts the last hop to stdlib
# outside the allowlist. The definitive defense is still the isolated
# subprocess (follow-up); this closes the known vectors.
_MODULOS_PERIGOSOS = {
    "os", "sys", "subprocess", "importlib", "imp", "pkgutil", "runpy",
    "socket", "ssl", "ctypes", "cffi", "platform", "posix", "nt", "pty",
    "shutil", "tempfile", "pathlib", "glob", "pickle", "marshal", "shelve",
    "sqlite3", "multiprocessing", "threading", "asyncio", "concurrent",
    "signal", "resource", "mmap", "fcntl", "webbrowser",
    "urllib", "http", "ftplib", "smtplib", "requests", "httpx", "aiohttp",
    "gc", "inspect", "traceback", "codeop", "pdb", "bdb", "atexit",
    # `select`/`selectors`/`code` WERE removed: they collide with legitimate data
    # APIs (numpy.select, a DataFrame with a "code" column) and are not an escape
    # vector — none of them reaches os/subprocess by attribute; a direct import is
    # already blocked by the allowlist.
    "site", "sysconfig", "distutils", "setuptools", "pip", "venv", "modulefinder",
    "commands", "popen2", "_thread", "_io", "_pickle",
    # aliases sublinhados comuns (random._os, collections._sys, etc.)
    "_os", "_sys", "_socket", "_ssl", "_subprocess", "_posixsubprocess",
    "_ctypes", "_frozen_importlib", "_frozen_importlib_external", "_bootstrap",
    "_bootstrap_external", "_imp", "_warnings",
}
# Dangerous callables reachable even without naming the module (`x.system(...)`,
# `x.import_module(...)`). Complements the blocking of the handles above.
_CHAMAVEIS_PERIGOSOS = {
    "system", "popen", "popen2", "popen3", "popen4", "startfile",
    "spawn", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve",
    "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp",
    "exec", "execl", "execle", "execlp", "execlpe", "execv", "execve",
    "execvp", "execvpe", "fork", "forkpty", "putenv", "unsetenv",
    "import_module", "load_module", "exec_module", "create_module",
    "find_module", "find_spec", "module_from_spec", "reload", "import_",
    "check_output", "check_call", "getoutput", "getstatusoutput", "Popen",
    "call", "run", "getattr", "setattr", "delattr", "vars", "globals", "locals",
    "environ",
}
_BLOCKED_ATTR_NAMES = {
    "gi_frame", "gi_code", "cr_frame", "cr_code", "ag_frame", "ag_code",
    "f_globals", "f_builtins", "f_locals", "f_back", "f_code", "f_trace",
    "tb_frame", "tb_next", "func_globals", "func_code",
    "modules", "builtins",  # sys.modules / *.builtins → recuperam a stdlib inteira
} | _MODULOS_PERIGOSOS | _CHAMAVEIS_PERIGOSOS

# ── Methods blocked by name ──────────────────────────────────────────────────
# `str.format`/`format_map` resolve fields like `{0.__class__}` through the
# format-field machinery, reaching attributes WITHOUT an ast.Attribute the check
# can see — and a `'{0.__' + 'class__}'.format(x)` built by concatenation would
# even sidestep the string-literal check below. `get_field`/`get_value` are the
# methods of `string.Formatter` (the module left the allowlist, but blocking the
# name closes any other path). Same for `attrgetter`/`methodcaller`, in case
# `operator` comes back some day. User alternative: f-strings (`f"{x}"`), whose
# expressions become real ast.Attribute nodes and fall under the dunder predicate.
_BLOCKED_METHODS = {
    "format", "format_map", "get_field", "get_value",
    "attrgetter", "methodcaller",
}

# Dunder token (`__algo__`) — used to catch dunders SMUGGLED in as a
# string literal (`obj.__getattribute__('__class__')`, `'{0.__init__.__globals__}'`,
# `d['__builtins__']`). Requires at least one character between the underscore pairs.
_DUNDER_EM_STRING = re.compile(r"__\w+__")


class UnsafeCodeError(Exception):
    """Codigo Python contem construtos nao permitidos."""
    pass


def _e_dunder(nome: str) -> bool:
    """True for identifiers in dunder format (`__algo__`)."""
    return len(nome) > 4 and nome.startswith("__") and nome.endswith("__")


def validate_code_ast(code: str) -> None:
    """
    Analyzes the code's AST and rejects disallowed imports, access to
    dangerous attributes and strings that smuggle dunder names.

    Raises:
        UnsafeCodeError: if the code contains blocked constructs.
        SyntaxError: if the code has a syntax error.
    """
    tree = ast.parse(code)
    for node in ast.walk(tree):
        # import xxx
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_module(alias.name)
        # from xxx import yyy
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                _check_module(node.module)
        # obj.__subclasses__, obj.format, obj.gi_frame, etc.
        elif isinstance(node, ast.Attribute):
            _check_attr(node.attr)
        # '__class__', '{0.__init__.__globals__}', d['__builtins__'] — the dunder
        # travels as text. ast.walk visits EVERY ast.Constant (call argument,
        # subscript key, format spec), so a single loop covers all three.
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str) and _DUNDER_EM_STRING.search(node.value):
                raise UnsafeCodeError(
                    "String contendo atributo dunder "
                    f"('{node.value[:40]}') nao e permitida por seguranca: "
                    "pode ser usada para burlar a checagem de atributos."
                )


def _check_attr(attr: str) -> None:
    """Rejects attributes that open a sandbox escape."""
    if _e_dunder(attr):
        raise UnsafeCodeError(
            f"Acesso ao atributo dunder '{attr}' nao e permitido por seguranca."
        )
    if attr in _BLOCKED_ATTR_NAMES:
        raise UnsafeCodeError(
            f"Acesso ao atributo '{attr}' nao e permitido por seguranca: "
            "expoe modulos ou internals fora da allowlist (ex.: os, sys, "
            "subprocess, importlib, frames)."
        )
    if attr in _BLOCKED_METHODS:
        raise UnsafeCodeError(
            f"Uso do metodo '{attr}' nao e permitido por seguranca; "
            "use f-strings para formatar texto."
        )


def _check_module(module_name: str) -> None:
    """Validates that the module is in the allowlist."""
    top_level = module_name.split(".")[0]
    if top_level not in ALLOWED_MODULES:
        raise UnsafeCodeError(
            f"Importacao do modulo '{module_name}' nao e permitida. "
            f"Modulos disponiveis: {sorted(ALLOWED_MODULES)}"
        )


# ── __import__ customizado ───────────────────────────────────────────────────
_original_import = builtins.__import__


def safe_import(name, *args, **kwargs):
    """
    Replacement for __import__ that validates against the allowlist.
    Closes the gap where blocking __import__ in the builtins does not prevent
    the 'import' statement — because internally it calls __builtins__.__import__.
    """
    top = name.split(".")[0]
    if top not in ALLOWED_MODULES:
        raise ImportError(
            f"Modulo '{name}' nao e permitido no PythonScript. "
            f"Modulos disponiveis: {sorted(ALLOWED_MODULES)}"
        )
    return _original_import(name, *args, **kwargs)


def build_safe_builtins() -> dict:
    """Builds a dict of safe builtins with a custom __import__."""
    safe = {
        k: v for k, v in vars(builtins).items()
        if k not in BLOCKED_BUILTINS
    }
    safe["__import__"] = safe_import
    return safe
