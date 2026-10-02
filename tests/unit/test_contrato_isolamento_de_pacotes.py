# tests/unit/test_contrato_isolamento_de_pacotes.py
"""
Isolamento de `flow/` e `executor/` em relacao a `app/`.

O motor (`flow/`) e o executor rodam na maquina do CLIENTE, onde `app/` nao
existe e as variaveis de ambiente do servidor tambem nao. Dois invariantes
sustentam isso, e nenhum tinha guarda automatica:

  EXECUTOR   nunca importa `app.*`, em nivel nenhum.

  FLOW       pode importar `app.*`, mas SOMENTE dentro de funcao. Subir um
             desses imports para o topo do arquivo derruba a frota inteira no
             boot: `app.core.utils.encryption` importa `app.core.config`, que
             levanta ValueError quando APP_SECRET nao esta definida — e no
             executor ela nunca esta.

Hoje os dois invariantes valem apenas porque alguem lembrou de escrever
`from app...` indentado. Um "organizar imports" de IDE reverte isso em silencio,
e o teste que falharia seria nenhum: a suite roda com as variaveis do servidor
presentes, entao o import funciona aqui e quebra la.
"""
from __future__ import annotations

import ast
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]


def _arquivos(pacote: str) -> list[Path]:
    return sorted((RAIZ / pacote).rglob("*.py"))


def _imports_de_app(caminho: Path) -> list[tuple[int, str, bool]]:
    """(linha, alvo, e_nivel_de_modulo) para cada import de `app.*` no arquivo."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))

    # Nos que estao dentro de alguma funcao => import tardio.
    dentro_de_funcao: set[int] = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for filho in ast.walk(no):
                dentro_de_funcao.add(id(filho))

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
            achados.append((no.lineno, alvo, id(no) not in dentro_de_funcao))
    return achados


# ── EXECUTOR ─────────────────────────────────────────────────────────────────

def test_executor_nunca_importa_app():
    """A fronteira de deploy: o executor e distribuido sem o pacote `app`."""
    violacoes = [
        f"{caminho.relative_to(RAIZ)}:{linha} importa {alvo}"
        for caminho in _arquivos("executor")
        for linha, alvo, _ in _imports_de_app(caminho)
    ]
    assert not violacoes, (
        "executor/ passou a importar app/ — o executor roda on-premise e nao "
        "tem esse pacote:\n  " + "\n  ".join(violacoes)
    )


# ── FLOW ─────────────────────────────────────────────────────────────────────

def test_flow_so_importa_app_dentro_de_funcao():
    """Import de `app.*` no topo de um modulo de flow/ derruba todo executor."""
    violacoes = [
        f"{caminho.relative_to(RAIZ)}:{linha} importa {alvo} no topo do modulo"
        for caminho in _arquivos("flow")
        for linha, alvo, nivel_modulo in _imports_de_app(caminho)
        if nivel_modulo
    ]
    assert not violacoes, (
        "import de app/ no nivel de modulo em flow/ — o executor quebra no boot "
        "(app.core.config levanta ValueError sem APP_SECRET):\n  "
        + "\n  ".join(violacoes)
    )


def test_o_import_tardio_de_flow_ainda_existe_onde_e_esperado():
    """Ancora a premissa: se os imports tardios sumirem, o teste acima vira vacuo.

    Sem isto, apagar `workflow_contract.py` inteiro deixaria a suite verde e
    daria a impressao de que o invariante continua sendo verificado.
    """
    tardios = [
        (caminho.relative_to(RAIZ), linha, alvo)
        for caminho in _arquivos("flow")
        for linha, alvo, nivel_modulo in _imports_de_app(caminho)
        if not nivel_modulo
    ]
    assert tardios, (
        "nenhum import tardio de app/ em flow/ — ou o acoplamento acabou (otimo, "
        "remova este teste) ou os arquivos que o tinham sumiram"
    )


def test_importar_flow_nao_exige_variavel_de_ambiente_do_servidor(monkeypatch):
    """A prova empirica do invariante, e nao so a estrutural.

    Simula a maquina do cliente: sem APP_SECRET/FERNET_KEY, importar o motor e
    o registry de nos tem de funcionar.
    """
    import subprocess
    import sys

    ambiente = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONPATH": str(RAIZ),
        "EXECUTOR_ID": "exec-teste",
    }
    # Importa TODO modulo de flow/, e nao so os pontos de entrada: um import
    # indevido num arquivo que os entrypoints nao alcancam passaria batido, e
    # foi exatamente o caso de `flow/utils/workflow_contract.py`.
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
