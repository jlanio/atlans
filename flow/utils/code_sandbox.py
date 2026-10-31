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
import contextlib
import os
import re
import site
import sys
import sysconfig
import threading

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
_DANGEROUS_MODULES = {
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
_DANGEROUS_CALLABLES = {
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
} | _DANGEROUS_MODULES | _DANGEROUS_CALLABLES

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

# ── File, network and deserialization I/O of the allowlisted libraries ───────
# Blocking `open` and `import os` is not enough: pandas, geopandas, numpy and
# pyogrio read and write files and URLs on their own. `pd.read_csv('/etc/...')`
# returned any file of the executor (its mTLS key included),
# `pd.read_csv('http://169.254.169.254/...')` reached internal addresses,
# `df.to_csv('/tmp/x')` wrote anywhere and `pd.read_pickle(...)` executes code
# while deserializing. None of them has a dunder or an import for the checks
# above to see. The Jinja sandbox (flow/utils/jinja_seguro.py) already blocked
# the same methods on the same objects; this layer did not.
#
# Every `read_*` attribute is refused by prefix (read_csv, read_file,
# read_parquet, read_pickle, read_postgis, read_dataframe…): none of them is
# needed to transform data that arrives through the node's inputs.
_IO_READ_PREFIX = "read_"
_IO_BLOCKED_ATTRS = {
    # writers that always take a destination
    "to_file", "to_pickle", "to_parquet", "to_feather", "to_hdf", "to_excel",
    "to_orc", "to_stata", "to_sql", "to_gbq", "to_postgis", "to_clipboard",
    "tofile", "save", "savez", "savez_compressed", "savetxt",
    "write_dataframe", "write_arrow",
    # numpy/pyogrio/pandas loaders and file handles not covered by `read_`
    "load", "loadtxt", "genfromtxt", "fromfile", "fromregex", "memmap",
    "open_memmap", "DataSource", "open_arrow", "list_layers",
    "ctypeslib", "load_library",
    # pandas' own URL/file plumbing and pickle shim
    "urlopen", "get_handle", "pickle_compat",
    # `query`/`eval` evaluate a STRING at runtime: a string assembled by
    # concatenation escapes every check above (`'@g.gi_' + 'frame…'`).
    # Alternative for the user: boolean indexing, `df[df["pop"] > 1000]`.
    "query", "eval",
    # process-wide PROJ settings: they change the behavior of every other node
    # of the executor (and turn on PROJ's network access)
    "set_data_dir", "append_data_dir", "set_network_enabled",
    "set_ca_bundle_path",
}
# Return a string when called WITHOUT a destination (`gdf.to_json()` is common
# and legitimate) and write to a file when given one. Allowed only as the
# function of a call that names no destination: no positional argument, no
# destination keyword and no `**kwargs`. Taking the bound method itself
# (`f = df.to_csv`) is refused, because the call the check sees would be `f(...)`.
_WRITERS_WITH_DESTINATION = {
    "to_csv", "to_json", "to_html", "to_xml", "to_string", "to_markdown",
    "to_latex",
}
_DESTINATION_KWARGS = {
    "path_or_buf", "buf", "path", "fname", "excel_writer",
    "filepath_or_buffer", "filename",
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
    # Parent of each node: `_check_writer` needs to know whether the attribute
    # is the function being called, and with which arguments.
    pais: dict[int, ast.AST] = {}
    for pai in ast.walk(tree):
        for filho in ast.iter_child_nodes(pai):
            pais[id(filho)] = pai
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
            if node.attr in _WRITERS_WITH_DESTINATION:
                _check_writer(node, pais.get(id(node)))
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
    if attr in ("query", "eval"):
        raise UnsafeCodeError(
            f"Uso do metodo '{attr}' nao e permitido por seguranca: ele avalia "
            "texto como codigo. Use indexacao booleana, por exemplo "
            "df[df['coluna'] > 10]."
        )
    if attr.startswith(_IO_READ_PREFIX) or attr in _IO_BLOCKED_ATTRS:
        raise UnsafeCodeError(
            f"Uso de '{attr}' nao e permitido no PythonScript: ler ou gravar "
            "arquivos e URLs fica com os nos de entrada e saida do fluxo. "
            "Conecte os dados como entrada do no."
        )


def _check_writer(node: ast.Attribute, pai: ast.AST | None) -> None:
    """Allows `x.to_json()`-style calls only without a write destination."""
    chamada_direta = isinstance(pai, ast.Call) and pai.func is node
    if chamada_direta and not pai.args and not any(
        kw.arg is None or kw.arg in _DESTINATION_KWARGS for kw in pai.keywords
    ):
        return
    raise UnsafeCodeError(
        f"'{node.attr}' so e permitido sem destino (devolve texto): chame "
        f"'.{node.attr}()' sem caminho, buffer ou argumentos posicionais."
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


# ── Runtime guard (audit hook) ───────────────────────────────────────────────
# The AST check sees names, not objects: a bound method kept under another name,
# or a library path nobody listed, still reaches the file system or the network.
# This second layer watches what the interpreter actually does while the user's
# code runs. A process-wide audit hook (PEP 578) refuses, ONLY on the thread
# running the script, the operations a data transformation never needs:
# sockets, processes, ctypes, unpickling, file writes and file reads outside the
# folders of Python and its packages (imports and time zone data live there; the
# executor's certificates, .env and spill files do not).
#
# What it does not cover: I/O done inside C libraries (GDAL through pyogrio,
# PROJ) raises no audit event — those entry points are refused by name above.
# Audit hooks cannot be removed; outside a script the hook returns on its first
# line, so the other nodes pay one attribute read per audited event.

_estado_do_script = threading.local()

_EVENTOS_BLOQUEADOS = frozenset({
    "os.system", "os.kill", "os.killpg", "os.remove", "os.rename", "os.rmdir",
    "os.mkdir", "os.chmod", "os.chown", "os.chflags", "os.lchflags",
    "os.symlink", "os.link", "os.truncate", "os.utime", "os.putenv",
    "os.unsetenv", "os.chdir", "os.startfile", "os.add_dll_directory",
    # `marshal.loads` stays allowed: the import system uses it to load .pyc
    # files, and a lazy import inside a script is legitimate.
    "pickle.find_class",
    "sys.addaudithook", "sys.settrace", "sys.setprofile",
    "gc.get_objects", "gc.get_referrers", "gc.get_referents",
    "code.__new__",
})
_PREFIXOS_BLOQUEADOS = (
    "socket.", "subprocess.", "os.exec", "os.spawn", "os.posix_spawn",
    "os.fork", "ctypes.", "shutil.", "tempfile.", "sqlite3.", "urllib.",
    "http.client.", "ftplib.", "smtplib.", "poplib.", "imaplib.", "nntplib.",
    "telnetlib.", "webbrowser.", "winreg.", "_winapi.", "msvcrt.",
    "resource.", "signal.", "glob.", "mmap.",
)
_BITS_DE_ESCRITA = (
    getattr(os, "O_WRONLY", 0) | getattr(os, "O_RDWR", 0) | getattr(os, "O_CREAT", 0)
    | getattr(os, "O_TRUNC", 0) | getattr(os, "O_APPEND", 0)
)
_raizes_de_leitura: tuple[str, ...] | None = None
_guarda_instalada = False
_trava_da_guarda = threading.Lock()


def _calcular_raizes_de_leitura() -> tuple[str, ...]:
    """Folders a script may read from: Python itself, its packages, tz data."""
    candidatas: set[str] = set()
    for prefixo in (sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix):
        if prefixo:
            candidatas.add(prefixo)
    for chave in ("stdlib", "platstdlib", "purelib", "platlib"):
        caminho = sysconfig.get_paths().get(chave)
        if caminho:
            candidatas.add(caminho)
    with contextlib.suppress(Exception):
        candidatas.update(site.getsitepackages())
    with contextlib.suppress(Exception):
        candidatas.add(site.getusersitepackages())
    tzpath = sysconfig.get_config_var("TZPATH") or ""
    candidatas.update(p for p in tzpath.split(os.pathsep) if p)
    raizes = set()
    for caminho in candidatas:
        real = os.path.realpath(caminho)
        # A prefix at the file system root would allow everything.
        if real and real != os.path.sep and os.path.dirname(real) != real:
            raizes.add(real)
    return tuple(sorted(raizes))


def _dentro_das_raizes(caminho) -> bool:
    if isinstance(caminho, int):
        return False
    try:
        real = os.path.realpath(os.fsdecode(caminho))
    except Exception:
        return False
    raizes = _raizes_de_leitura or ()
    return any(real == r or real.startswith(r + os.sep) for r in raizes)


def _recusar(evento: str) -> None:
    raise PermissionError(
        f"Operação bloqueada no PythonScript ({evento}): o script não pode "
        "acessar rede, processos ou arquivos fora dos dados recebidos."
    )


def _guarda_de_auditoria(evento: str, args: tuple) -> None:
    if not getattr(_estado_do_script, "ativo", False):
        return
    if evento == "open":
        caminho = args[0] if args else None
        modo = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        escreve = bool(modo and any(c in str(modo) for c in "wax+")) or bool(
            isinstance(flags, int) and flags & _BITS_DE_ESCRITA
        )
        if escreve or not _dentro_das_raizes(caminho):
            _recusar(f"open {caminho!r}")
        return
    if evento in ("os.listdir", "os.scandir"):
        caminho = args[0] if args and args[0] is not None else "."
        if not _dentro_das_raizes(caminho):
            _recusar(evento)
        return
    if evento in _EVENTOS_BLOQUEADOS or evento.startswith(_PREFIXOS_BLOQUEADOS):
        _recusar(evento)


def instalar_guarda_de_execucao() -> None:
    """Installs the audit hook once per process (idempotent)."""
    global _guarda_instalada, _raizes_de_leitura
    with _trava_da_guarda:
        if _guarda_instalada:
            return
        _raizes_de_leitura = _calcular_raizes_de_leitura()
        sys.addaudithook(_guarda_de_auditoria)
        _guarda_instalada = True


@contextlib.contextmanager
def executando_codigo_do_usuario():
    """Marks the CURRENT thread as running user code while the block lasts."""
    instalar_guarda_de_execucao()
    anterior = getattr(_estado_do_script, "ativo", False)
    _estado_do_script.ativo = True
    try:
        yield
    finally:
        _estado_do_script.ativo = anterior


@contextlib.contextmanager
def fora_do_codigo_do_usuario():
    """Suspends the guard for the platform's own work done on the script's
    thread (publishing print() lines, logging), which may legitimately use
    sockets or write log files."""
    anterior = getattr(_estado_do_script, "ativo", False)
    _estado_do_script.ativo = False
    try:
        yield
    finally:
        _estado_do_script.ativo = anterior


def liberar_thread_do_script() -> None:
    """Clears the mark on the current thread (safety net after a timeout)."""
    _estado_do_script.ativo = False
