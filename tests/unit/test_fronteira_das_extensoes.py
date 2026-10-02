# tests/unit/test_fronteira_das_extensoes.py
"""
O núcleo anda sem as extensões (app/extensoes), e a distribuição livre não as
traz. Dois jeitos de quebrar isso, e um teste para cada:

  IMPORT     um módulo do núcleo (ou um teste dele) importa uma extensão pelo
             nome, ou a cita num alvo de patch;
  ARRANQUE   a API, com ATLANS_SEM_EXTENSOES=1, carrega o código de uma
             extensão mesmo assim, ou fica com rota, tabela ou tarefa dela.
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

# O núcleo: tudo o que a distribuição livre leva.
_PASTAS_DO_NUCLEO = ("app", "flow", "executor", "scripts", "alembic", "tests")
# A API do registro, que o núcleo pode usar.
_API_DO_REGISTRO = {"registro", "importar_modelos", "desligadas", "esquemas", "Registro"}
# Um nome depois do registro, num texto: `app.extensoes.planos` cita uma
# extensão; `app.extensoes.registro` é a API. O prefixo sozinho
# (`app.extensoes.`) é genérico e pode.
_NOME_NO_TEXTO = re.compile(r"app\.extensoes\.([A-Za-z_]\w*)")
_REGISTRO = "app.extensoes"


def _da_extensao(caminho: Path) -> bool:
    relativo = caminho.relative_to(RAIZ).parts
    return (
        relativo[:2] == ("app", "extensoes") and len(relativo) > 3
    ) or relativo[:2] == ("tests", "extensoes")


def _arquivos_do_nucleo():
    for pasta in _PASTAS_DO_NUCLEO:
        for caminho in (RAIZ / pasta).rglob("*.py"):
            if "__pycache__" in caminho.parts or _da_extensao(caminho):
                continue
            yield caminho


def _docstrings(arvore: ast.AST) -> set[int]:
    ids = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if no.body and isinstance(no.body[0], ast.Expr) and isinstance(no.body[0].value, ast.Constant):
                ids.add(id(no.body[0].value))
    return ids


def _pacote(relativo: str) -> str:
    """O pacote de um arquivo, para resolver os imports relativos dele:
    `app/services/x.py` está em `app.services`, e `app/extensoes/__init__.py`
    é o próprio `app.extensoes`."""
    return ".".join(Path(relativo).with_suffix("").parts[:-1])


def _pontuado(no: ast.AST) -> str | None:
    """`app.extensoes.planos.config` de uma cadeia de atributos, ou None."""
    partes = []
    while isinstance(no, ast.Attribute):
        partes.append(no.attr)
        no = no.value
    if not isinstance(no, ast.Name):
        return None
    partes.append(no.id)
    return ".".join(reversed(partes))


def _fora_da_api(resto: str) -> bool:
    """`planos.config` (o que vem depois do registro) cita uma extensão?"""
    primeiro = resto.split(".")[0]
    return not (primeiro in _API_DO_REGISTRO or primeiro.startswith("__"))


def citacoes(arvore: ast.AST, relativo: str) -> list[str]:
    """As citações de uma extensão pelo nome num módulo do núcleo.

    Três caminhos: um import (absoluto ou relativo, resolvido contra o pacote
    do arquivo), uma cadeia de atributos a partir do registro
    (`app.extensoes.planos...`, ou um apelido dele, `extensoes.planos...`) e um
    texto que nomeia a extensão (um alvo de patch, um `import_module`)."""
    docstrings = _docstrings(arvore)
    pacote = _pacote(relativo)
    apelidos = {_REGISTRO}  # nomes que apontam para o pacote do registro
    achadas: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for a in no.names:
                if a.name.startswith(_REGISTRO + ".") and _fora_da_api(a.name[len(_REGISTRO) + 1:]):
                    achadas.append(f"import {a.name}")
                elif a.name == _REGISTRO and a.asname:
                    apelidos.add(a.asname)
        elif isinstance(no, ast.ImportFrom):
            modulo = no.module or ""
            if no.level:
                try:
                    modulo = importlib.util.resolve_name("." * no.level + modulo, pacote)
                except (ImportError, ValueError):
                    continue
            if modulo.startswith(_REGISTRO + ".") and _fora_da_api(modulo[len(_REGISTRO) + 1:]):
                achadas.append(f"from {modulo} import …")
            elif modulo == _REGISTRO:
                achadas += [f"from {_REGISTRO} import {a.name}" for a in no.names if _fora_da_api(a.name)]
            elif modulo == "app":
                apelidos.update(a.asname or a.name for a in no.names if a.name == "extensoes")
        elif (
            isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docstrings
            and any(_fora_da_api(nome) for nome in _NOME_NO_TEXTO.findall(no.value))
        ):
            achadas.append(f"texto {no.value[:60]!r}")
    # Os apelidos valem no arquivo todo, então as cadeias vêm numa segunda volta.
    # Cada cadeia é anotada até o nome da extensão (`app.extensoes.ouro`), uma
    # vez só: `ast.walk` passa por cada pedaço de `a.b.c.d`.
    cadeias = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Attribute) and (nome := _pontuado(no)):
            for apelido in apelidos:
                if nome.startswith(apelido + ".") and _fora_da_api(resto := nome[len(apelido) + 1:]):
                    cadeias.add(f"{apelido}.{resto.split('.')[0]}")
    achadas += sorted(f"atributo {c}" for c in cadeias)
    return achadas


def test_o_detector_ve_os_jeitos_de_citar_uma_extensao():
    """Os jeitos que o detector tem de ver — e os que o núcleo pode usar."""
    def ve(codigo: str, arquivo: str = "app/services/x.py") -> list[str]:
        return citacoes(ast.parse(codigo), arquivo)

    ouro = "ouro"  # uma extensão de mentira; o nome de verdade não pode estar aqui
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


def test_o_nucleo_nao_importa_extensao_pelo_nome():
    erros = {}
    for caminho in _arquivos_do_nucleo():
        relativo = caminho.relative_to(RAIZ).as_posix()
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
        if achadas := citacoes(arvore, relativo):
            erros[relativo] = achadas
    assert not erros, (
        "O núcleo não pode citar uma extensão pelo nome (use o registro de app/extensoes, "
        f"e ponha os testes dela em tests/extensoes/): {erros}"
    )


_SONDA = """
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


def test_a_api_sobe_sem_extensoes():
    env = dict(os.environ, ATLANS_SEM_EXTENSOES="1")
    r = subprocess.run([sys.executable, "-c", _SONDA], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    estado = json.loads(r.stdout.strip().splitlines()[-1])

    assert estado["extensoes"] == []
    # Nenhum código de extensão carregado: um import esquecido no núcleo
    # puxaria o módulo, e é isso que a distribuição livre não teria.
    assert estado["modulos"] == []
    assert estado["tabelas"] == []
    assert "/admin/assistente/modelo" in estado["rotas"]
    assert "/admin/assistente/cota" not in estado["rotas"]
    assert not [r for r in estado["rotas"] if r.startswith(("/planos", "/webhooks/"))]
    assert "Watchdog de runs órfãos" in estado["tarefas"]
