# tests/unit/test_fronteira_das_extensoes.py
"""
The core runs without the extensions (app/extensoes), and the free distribution does
not ship them. Two ways to break that, and one test for each:

  IMPORT     a core module (or one of its tests) imports an extension by
             name, or cites it in a patch target;
  STARTUP    the API, with ATLANS_SEM_EXTENSOES=1, loads an extension's code
             anyway, or ends up with one of its routes, tables or tasks.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# The core: everything the free distribution ships.
_CORE_FOLDERS = ("app", "flow", "executor", "scripts", "alembic", "tests")
# The registry API, which the core may use.
_API_DO_REGISTRO = {"registro", "importar_modelos", "desligadas", "esquemas", "Registro"}
# A name after the registry, in a string: `app.extensoes.planos` cites an
# extension; `app.extensoes.registro` is the API. The prefix alone
# (`app.extensoes.`) is generic and allowed.
_NAME_IN_TEXT = re.compile(r"app\.extensoes\.([A-Za-z_]\w*)")
_REGISTRO = "app.extensoes"


def _is_extension_file(caminho: Path) -> bool:
    relativo = caminho.relative_to(RAIZ).parts
    return (
        relativo[:2] == ("app", "extensoes") and len(relativo) > 3
    ) or relativo[:2] == ("tests", "extensoes")


def _core_files():
    for pasta in _CORE_FOLDERS:
        for caminho in (RAIZ / pasta).rglob("*.py"):
            if "__pycache__" in caminho.parts or _is_extension_file(caminho):
                continue
            yield caminho


def _docstrings(arvore: ast.AST) -> set[int]:
    ids = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if no.body and isinstance(no.body[0], ast.Expr) and isinstance(no.body[0].value, ast.Constant):
                ids.add(id(no.body[0].value))
    return ids


def _package(relativo: str) -> str:
    """A file's package, to resolve its relative imports:
    `app/services/x.py` is in `app.services`, and `app/extensoes/__init__.py`
    is `app.extensoes` itself."""
    return ".".join(Path(relativo).with_suffix("").parts[:-1])


def _dotted(no: ast.AST) -> str | None:
    """`app.extensoes.planos.config` from an attribute chain, or None."""
    partes = []
    while isinstance(no, ast.Attribute):
        partes.append(no.attr)
        no = no.value
    if not isinstance(no, ast.Name):
        return None
    partes.append(no.id)
    return ".".join(reversed(partes))


def _outside_the_api(resto: str) -> bool:
    """Does `planos.config` (what comes after the registry) cite an extension?"""
    primeiro = resto.split(".")[0]
    return not (primeiro in _API_DO_REGISTRO or primeiro.startswith("__"))


def citations(arvore: ast.AST, relativo: str) -> list[str]:
    """The citations of an extension by name in a core module.

    Three paths: an import (absolute or relative, resolved against the file's
    package), an attribute chain starting from the registry
    (`app.extensoes.planos...`, or an alias of it, `extensoes.planos...`) and a
    string that names the extension (a patch target, an `import_module`)."""
    docstrings = _docstrings(arvore)
    pacote = _package(relativo)
    aliases = {_REGISTRO}  # names that point to the registry package
    found: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for a in no.names:
                if a.name.startswith(_REGISTRO + ".") and _outside_the_api(a.name[len(_REGISTRO) + 1:]):
                    found.append(f"import {a.name}")
                elif a.name == _REGISTRO and a.asname:
                    aliases.add(a.asname)
        elif isinstance(no, ast.ImportFrom):
            modulo = no.module or ""
            if no.level:
                try:
                    modulo = importlib.util.resolve_name("." * no.level + modulo, pacote)
                except (ImportError, ValueError):
                    continue
            if modulo.startswith(_REGISTRO + ".") and _outside_the_api(modulo[len(_REGISTRO) + 1:]):
                found.append(f"from {modulo} import …")
            elif modulo == _REGISTRO:
                found += [f"from {_REGISTRO} import {a.name}" for a in no.names if _outside_the_api(a.name)]
            elif modulo == "app":
                aliases.update(a.asname or a.name for a in no.names if a.name == "extensoes")
        elif (
            isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docstrings
            and any(_outside_the_api(nome) for nome in _NAME_IN_TEXT.findall(no.value))
        ):
            found.append(f"texto {no.value[:60]!r}")
    # Aliases apply to the whole file, so the chains come in a second pass.
    # Each chain is recorded up to the extension name (`app.extensoes.ouro`), only
    # once: `ast.walk` goes through every piece of `a.b.c.d`.
    chains = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Attribute) and (nome := _dotted(no)):
            for apelido in aliases:
                if nome.startswith(apelido + ".") and _outside_the_api(resto := nome[len(apelido) + 1:]):
                    chains.add(f"{apelido}.{resto.split('.')[0]}")
    found += sorted(f"atributo {c}" for c in chains)
    return found


def test_the_detector_sees_the_ways_to_cite_an_extension():
    """The ways the detector must see — and the ones the core may use."""
    def ve(codigo: str, arquivo: str = "app/services/x.py") -> list[str]:
        return citations(ast.parse(codigo), arquivo)

    ouro = "ouro"  # a fake extension; the real name must not be here
    assert ve(f"from ..extensoes.{ouro} import config")
    assert ve(f"from . import {ouro}", "app/extensoes/__init__.py")
    assert ve(f"import app.extensoes\napp.extensoes.{ouro}.config.X")
    assert ve(f"from app import extensoes\nextensoes.{ouro}.config")
    assert ve(f"from app import extensoes as ext\next.{ouro}.config")
    assert ve(f"import app.extensoes as ext\next.{ouro}")
    assert ve(f"from app.extensoes.{ouro} import config")
    assert ve(f"from app.extensoes import {ouro}")
    assert ve(f"monkeypatch.setattr('app.extensoes.{ouro}.config.X', 1)")

    assert ve("from app.extensoes import registro, esquemas\nregistro()") == []
    assert ve("import app.extensoes\napp.extensoes.registro()") == []
    assert ve("from app import extensoes\nextensoes.__name__, extensoes.desligadas()") == []
    assert ve("from .x import y", "tests/unit/test_y.py") == []


def test_the_core_does_not_import_extension_by_name():
    erros = {}
    for caminho in _core_files():
        relativo = caminho.relative_to(RAIZ).as_posix()
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
        if found := citations(arvore, relativo):
            erros[relativo] = found
    assert not erros, (
        "O núcleo não pode citar uma extensão pelo nome (use o registro de app/extensoes, "
        f"e ponha os testes dela em tests/extensoes/): {erros}"
    )


_PROBE = """
import json, sys
import app.main
from app.extensoes import registro
from app.main import _tarefas_de_fundo, app
from app.models.base import Base

tabelas_das_extensoes = sorted(
    mapper.local_table.name for mapper in Base.registry.mappers
    if mapper.class_.__module__.startswith("app.extensoes.")
)
print(json.dumps({
    "extensoes": registro().nomes,
    "modulos": sorted(m for m in sys.modules if m.startswith("app.extensoes.")),
    "tabelas": tabelas_das_extensoes,
    "rotas": sorted(app.openapi()["paths"]),
    "tarefas": [nome for nome, _ in _tarefas_de_fundo()],
}))
"""


def test_the_api_starts_without_extensions():
    env = dict(os.environ, ATLANS_SEM_EXTENSOES="1")
    r = subprocess.run([sys.executable, "-c", _PROBE], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    estado = json.loads(r.stdout.strip().splitlines()[-1])

    assert estado["extensoes"] == []
    # No extension code loaded: an import forgotten in the core
    # would pull the module in, and that is what the free distribution would not have.
    assert estado["modulos"] == []
    assert estado["tabelas"] == []
    assert "/admin/assistente/modelo" in estado["rotas"]
    assert "/admin/assistente/cota" not in estado["rotas"]
    assert not [r for r in estado["rotas"] if r.startswith(("/planos", "/webhooks/"))]
    assert "Watchdog de runs órfãos" in estado["tarefas"]
