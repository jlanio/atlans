# tests/unit/test_contrato_isolamento_de_pacotes.py
"""
Isolation of `flow/` and `executor/` from `app/`.

The engine (`flow/`) and the executor run on the CUSTOMER's machine, where
`app/` does not exist and neither do the server's environment variables. Two
invariants hold that up, and neither had an automated guard:

  EXECUTOR   never imports `app.*`, at any level.

  FLOW       may import `app.*`, but ONLY inside a function. Moving one of
             those imports to the top of the file takes down the whole fleet
             at boot: `app.core.utils.encryption` imports `app.core.config`,
             which raises ValueError when APP_SECRET is not set — and on the
             executor it never is.

Today both invariants hold only because someone remembered to write
`from app...` indented. An IDE "organize imports" silently reverts that, and
no test would fail: the suite runs with the server's variables present, so the
import works here and breaks there.
"""
from __future__ import annotations

import ast
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]


def _files(pacote: str) -> list[Path]:
    return sorted((RAIZ / pacote).rglob("*.py"))


def _imports_de_app(caminho: Path) -> list[tuple[int, str, bool]]:
    """(line, target, is_module_level) for each import of `app.*` in the file."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))

    # Nodes that are inside some function => deferred import.
    inside_function: set[int] = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for filho in ast.walk(no):
                inside_function.add(id(filho))

    achados = []
    for no in ast.walk(arvore):
        alvo = None
        if isinstance(no, ast.ImportFrom) and (no.module or "").startswith("app"):
            alvo = no.module
        elif isinstance(no, ast.Import):
            for nome in no.names:
                if nome.name.startswith("app.") or nome.name == "app":
                    alvo = nome.name
        if alvo:
            achados.append((no.lineno, alvo, id(no) not in inside_function))
    return achados


# ── EXECUTOR ─────────────────────────────────────────────────────────────────

def test_executor_never_imports_app():
    """The deploy boundary: the executor is distributed without the `app` package."""
    violacoes = [
        f"{caminho.relative_to(RAIZ)}:{linha} importa {alvo}"
        for caminho in _files("executor")
        for linha, alvo, _ in _imports_de_app(caminho)
    ]
    assert not violacoes, (
        "executor/ passou a importar app/ — o executor roda on-premise e nao "
        "tem esse pacote:\n  " + "\n  ".join(violacoes)
    )


# ── FLOW ─────────────────────────────────────────────────────────────────────

def test_flow_only_imports_app_inside_functions():
    """An import of `app.*` at the top of a flow/ module takes down every executor."""
    violacoes = [
        f"{caminho.relative_to(RAIZ)}:{linha} importa {alvo} no topo do modulo"
        for caminho in _files("flow")
        for linha, alvo, module_level in _imports_de_app(caminho)
        if module_level
    ]
    assert not violacoes, (
        "import de app/ no nivel de modulo em flow/ — o executor quebra no boot "
        "(app.core.config levanta ValueError sem APP_SECRET):\n  "
        + "\n  ".join(violacoes)
    )


def test_the_late_flow_import_still_exists_where_expected():
    """Anchors the premise: if the deferred imports disappear, the test above becomes vacuous.

    Without this, deleting `workflow_contract.py` entirely would leave the suite
    green and give the impression that the invariant is still being checked.
    """
    late_imports = [
        (caminho.relative_to(RAIZ), linha, alvo)
        for caminho in _files("flow")
        for linha, alvo, module_level in _imports_de_app(caminho)
        if not module_level
    ]
    assert late_imports, (
        "nenhum import tardio de app/ em flow/ — ou o acoplamento acabou (otimo, "
        "remova este teste) ou os arquivos que o tinham sumiram"
    )


def test_importing_flow_does_not_require_server_env_vars(monkeypatch):
    """The empirical proof of the invariant, not just the structural one.

    Simulates the customer's machine: without APP_SECRET/FERNET_KEY, importing
    the engine and the node registry has to work.
    """
    import subprocess
    import sys

    ambiente = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONPATH": str(RAIZ),
        "EXECUTOR_ID": "exec-teste",
    }
    # Imports EVERY module in flow/, not just the entry points: a stray import
    # in a file the entrypoints do not reach would slip through, and that was
    # exactly the case of `flow/utils/workflow_contract.py`.
    programa = (
        "import importlib, pkgutil, sys\n"
        "import flow\n"
        "falhas = []\n"
        "for m in pkgutil.walk_packages(flow.__path__, prefix='flow.'):\n"
        "    try: importlib.import_module(m.name)\n"
        "    except Exception as e: falhas.append(f'{m.name}: {e!r}')\n"
        "if falhas:\n"
        "    print('\\n'.join(falhas), file=sys.stderr); sys.exit(1)\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", programa],
        capture_output=True, text=True, env=ambiente, cwd=str(RAIZ), timeout=180,
    )
    assert resultado.returncode == 0, (
        "importar flow/ sem as variaveis do servidor falhou — o executor nao "
        f"conseguiria subir:\n{resultado.stderr[-2000:]}"
    )
