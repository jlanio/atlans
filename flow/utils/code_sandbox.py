# flow/utils/code_sandbox.py
# Validacao de seguranca para codigo Python executado pelo PythonScript node.
# Duas camadas: analise AST pre-execucao + __import__ customizado.
#
# ATENCAO — o que este modulo NAO garante. A checagem de AST e uma ALLOWLIST
# defensiva, nao um isolamento. Ela fecha as fugas CONHECIDAS (cadeia de
# classes, introspeccao de frame, atributo-por-string), mas o codigo do usuario
# ainda roda NO MESMO PROCESSO dos outros nos. A defesa correta e um subprocesso
# com seccomp/rlimits, registrada como follow-up; ate la, trate esta camada como
# "eleva a barra", nao "impede tudo". Por isso ela e conservadora: na duvida,
# bloqueia.

import ast
import builtins
import re

# ── Modulos permitidos ───────────────────────────────────────────────────────
# Apenas modulos seguros para manipulacao de dados geoespaciais.
# Qualquer import fora desta lista sera bloqueado.
ALLOWED_MODULES = {
    # Dados e GIS
    # `fiona` saiu da lista junto com a dependencia: geopandas 1.x le e escreve
    # via pyogrio, e manter as duas empacotava duas copias de GDAL no mesmo
    # processo (~99 MB, com GDAL_DATA/PROJ_LIB globais disputados entre elas).
    "pandas", "geopandas", "numpy", "shapely", "pyproj", "pyogrio",
    # Stdlib seguros
    # `operator` e `string` SAIRAM da lista: eram vetores de fuga do sandbox.
    # `operator.attrgetter('__bases__')(cls)` e `operator.methodcaller(...)`
    # buscam atributos por STRING, driblando a checagem de ast.Attribute abaixo;
    # `string.Formatter().get_field('0.__init__.__globals__', ...)` alcanca
    # globals de funcao pelo maquinario de format-field. Sem eles na allowlist,
    # os dois caminhos ficam indisponiveis. Substituto do usuario: lambdas no
    # lugar de attrgetter/itemgetter, f-strings no lugar de Formatter.
    #
    # `typing` tambem SAIU: `typing.ForwardRef(texto)._evaluate({}, ...)` e
    # `typing.get_type_hints(obj, globalns={})` fazem `eval` de uma string com os
    # builtins VERDADEIROS (um globals sem `__builtins__` ganha os reais) — e a
    # string montada em runtime (`'_' + '_' + 'import' ...`) nao e literal que a
    # checagem de dunder veja. Anotacao de tipo nao precisa dele: `list[int]`,
    # `dict[str, float]` e `X | None` sao embutidos desde o 3.10.
    "math", "json", "re", "datetime", "collections", "itertools",
    "functools", "statistics", "decimal", "fractions",
    "copy", "enum", "dataclasses", "textwrap",
    "hashlib", "base64", "uuid", "random",
}

# ── Builtins perigosos ───────────────────────────────────────────────────────
# Bloqueados para impedir acesso ao filesystem, execucao de codigo e
# introspeccao de objetos internos do runtime.
BLOCKED_BUILTINS = {
    # Execucao de codigo
    "open", "exec", "eval", "__import__", "compile", "breakpoint",
    "input", "memoryview", "reload",
    # Introspeccao perigosa — permite acessar namespace interno,
    # atributos privados e construir classes arbitrarias
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "type",
}

# ── Atributos NAO-dunder que expoem internals do interpretador ───────────────
# O predicado _e_dunder abaixo cobre __class__/__globals__/__subclasses__/etc.
# Estes NAO tem sublinhados na ponta e escapariam do predicado, mas dao acesso
# a frames, objetos de codigo e tracebacks — de onde se alcanca os globals reais
# e o __builtins__ verdadeiro (ex.: `(x for x in []).gi_frame.f_back.f_globals`).
#
# Alem dos internals de frame, esta lista fecha a fuga por HANDLE DE MODULO: um
# modulo da allowlist reexporta stdlib perigosa como atributo comum, sem dunder
# nem `import` que a checagem veja — `uuid.os`, `random._os`, `dataclasses.sys`,
# `datetime.sys`, `collections._sys`, `enum.sys`. A partir de `os`/`sys` chega-se
# a `os.system`/`os.popen`/`os.environ`, a `sys.modules['subprocess']` e a
# `importlib.import_module` (que ignora o safe_import). Como o unico `import`
# possivel ja passa pela allowlist, barrar o NOME desses atributos corta o
# ultimo salto ate a stdlib fora da allowlist. A defesa definitiva continua
# sendo o subprocesso isolado (follow-up); isto fecha os vetores conhecidos.
_MODULOS_PERIGOSOS = {
    "os", "sys", "subprocess", "importlib", "imp", "pkgutil", "runpy",
    "socket", "ssl", "ctypes", "cffi", "platform", "posix", "nt", "pty",
    "shutil", "tempfile", "pathlib", "glob", "pickle", "marshal", "shelve",
    "sqlite3", "multiprocessing", "threading", "asyncio", "concurrent",
    "signal", "resource", "mmap", "fcntl", "webbrowser",
    "urllib", "http", "ftplib", "smtplib", "requests", "httpx", "aiohttp",
    "gc", "inspect", "traceback", "codeop", "pdb", "bdb", "atexit",
    # `select`/`selectors`/`code` FORAM removidos: colidem com APIs de dados
    # legítimas (numpy.select, DataFrame com coluna "code") e não são vetor de
    # fuga — nenhum deles alcança os/subprocess por atributo; o import direto já
    # é barrado pela allowlist.
    "site", "sysconfig", "distutils", "setuptools", "pip", "venv", "modulefinder",
    "commands", "popen2", "_thread", "_io", "_pickle",
    # aliases sublinhados comuns (random._os, collections._sys, etc.)
    "_os", "_sys", "_socket", "_ssl", "_subprocess", "_posixsubprocess",
    "_ctypes", "_frozen_importlib", "_frozen_importlib_external", "_bootstrap",
    "_bootstrap_external", "_imp", "_warnings",
}
# Chamaveis perigosos alcancaveis mesmo sem nomear o modulo (`x.system(...)`,
# `x.import_module(...)`). Complementa o bloqueio dos handles acima.
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

# ── Metodos bloqueados por nome ──────────────────────────────────────────────
# `str.format`/`format_map` resolvem campos como `{0.__class__}` pelo maquinario
# de format-field, alcancando atributos SEM um ast.Attribute que a checagem veja
# — e um `'{0.__' + 'class__}'.format(x)` montado por concatenacao driblaria ate
# a checagem de string literal abaixo. `get_field`/`get_value` sao os metodos de
# `string.Formatter` (o modulo saiu da allowlist, mas bloquear o nome fecha
# qualquer outro caminho). `attrgetter`/`methodcaller` idem, caso `operator`
# volte um dia. Alternativa do usuario: f-strings (`f"{x}"`), cujas expressoes
# viram ast.Attribute de verdade e caem no predicado de dunder.
_BLOCKED_METHODS = {
    "format", "format_map", "get_field", "get_value",
    "attrgetter", "methodcaller",
}

# Token dunder (`__algo__`) — usado para pegar dunders CONTRABANDEADOS como
# string literal (`obj.__getattribute__('__class__')`, `'{0.__init__.__globals__}'`,
# `d['__builtins__']`). Exige ao menos um caractere entre os pares de sublinhado.
_DUNDER_EM_STRING = re.compile(r"__\w+__")


class UnsafeCodeError(Exception):
    """Codigo Python contem construtos nao permitidos."""
    pass


def _e_dunder(nome: str) -> bool:
    """True para identificadores no formato dunder (`__algo__`)."""
    return len(nome) > 4 and nome.startswith("__") and nome.endswith("__")


def validate_code_ast(code: str) -> None:
    """
    Analisa o AST do codigo e rejeita imports nao permitidos, acessos a
    atributos perigosos e strings que contrabandeiam nomes dunder.

    Raises:
        UnsafeCodeError: se o codigo contem construtos bloqueados.
        SyntaxError: se o codigo tem erro de sintaxe.
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
        # '__class__', '{0.__init__.__globals__}', d['__builtins__'] — o dunder
        # viaja como texto. ast.walk visita TODO ast.Constant (arg de chamada,
        # chave de subscript, spec de format), entao um unico laco cobre os tres.
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str) and _DUNDER_EM_STRING.search(node.value):
                raise UnsafeCodeError(
                    "String contendo atributo dunder "
                    f"('{node.value[:40]}') nao e permitida por seguranca: "
                    "pode ser usada para burlar a checagem de atributos."
                )


def _check_attr(attr: str) -> None:
    """Rejeita atributos que abrem fuga do sandbox."""
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
    """Valida se o modulo esta na allowlist."""
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
    Substituto de __import__ que valida contra a allowlist.
    Fecha a brecha de que bloquear __import__ nos builtins nao impede
    o statement 'import' — porque internamente ele chama __builtins__.__import__.
    """
    top = name.split(".")[0]
    if top not in ALLOWED_MODULES:
        raise ImportError(
            f"Modulo '{name}' nao e permitido no PythonScript. "
            f"Modulos disponiveis: {sorted(ALLOWED_MODULES)}"
        )
    return _original_import(name, *args, **kwargs)


def build_safe_builtins() -> dict:
    """Constroi dict de builtins seguros com __import__ customizado."""
    safe = {
        k: v for k, v in vars(builtins).items()
        if k not in BLOCKED_BUILTINS
    }
    safe["__import__"] = safe_import
    return safe
