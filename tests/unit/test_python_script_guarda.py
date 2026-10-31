"""
Runtime guard of the PythonScript (audit hook, flow/utils/code_sandbox.py).

The AST check refuses names; this layer refuses what the interpreter actually
does on the script's thread. The tests call `_run_script` directly, skipping
the AST check on purpose: they prove the second layer holds on its own.
"""
import os
import socket
import threading

import pandas as pd
import pytest

from flow.nodes.action.python_script import _run_script


def _rodar(code: str, **namespace):
    ns = {"pd": pd, **namespace}
    _run_script(code, ns, lambda _m: None, None)
    return ns


def test_reading_a_file_outside_the_python_folders_is_refused(tmp_path):
    segredo = tmp_path / "key.pem"
    segredo.write_text("-----BEGIN PRIVATE KEY-----")
    with pytest.raises(PermissionError, match="bloqueada"):
        _rodar(f"result = pd.read_csv({str(segredo)!r}, header=None)")


def test_writing_a_file_is_refused(tmp_path):
    destino = tmp_path / "x.csv"
    with pytest.raises(PermissionError):
        _rodar(f"pd.DataFrame({{'a': [1]}}).to_csv({str(destino)!r})")
    assert not destino.exists()


def test_the_network_is_refused():
    with pytest.raises(PermissionError):
        _rodar("result = pd.read_csv('http://127.0.0.1:9/x.csv')")


def test_bound_method_under_another_name_is_still_refused(tmp_path):
    # The case the AST layer cannot see: the method reached without its name.
    alvo = tmp_path / "y.txt"
    alvo.write_text("a\n1\n")
    ler = pd.read_csv
    with pytest.raises(PermissionError):
        _rodar(f"result = ler({str(alvo)!r})", ler=ler)


def test_legitimate_work_still_runs():
    ns = _rodar(
        "import json, math\n"
        "import shapely.ops\n"                                    # lazy import from site-packages
        "t = pd.Timestamp('2026-01-01', tz='America/Sao_Paulo')\n"  # tz data read from disk
        "df = pd.DataFrame({'a': [1, 2, 3]})\n"
        "result = (int(df['a'].sum()), json.dumps({'x': 1}), str(t.tz), df.to_csv(index=False))"
    )
    total, texto, fuso, csv = ns["result"]
    assert total == 6 and texto == '{"x": 1}' and fuso == "America/Sao_Paulo"
    assert csv.startswith("a\n")


def test_print_is_still_published_and_logged():
    publicado, logado = [], []
    ns = {"pd": pd}
    _run_script("print('ola')\nresult = 1", ns, logado.append, publicado.extend)
    assert "ola" in publicado and any("ola" in m for m in logado)


def test_the_guard_does_not_leak_to_other_code(tmp_path):
    with pytest.raises(PermissionError):
        _rodar("result = pd.read_csv('/etc/hostname')")
    # Same thread, after the script: back to normal.
    arquivo = tmp_path / "ok.csv"
    pd.DataFrame({"a": [1]}).to_csv(arquivo, index=False)
    assert pd.read_csv(arquivo)["a"].tolist() == [1]
    # Another thread while a script would run: unaffected.
    erros = []

    def _outra():
        try:
            socket.getaddrinfo("localhost", 80)
            os.listdir(tmp_path)
        except Exception as exc:  # pragma: no cover - would be the regression
            erros.append(exc)

    t = threading.Thread(target=_outra)
    t.start()
    t.join()
    assert erros == []


def test_libraries_that_write_on_import_are_warmed_up_outside_the_script(monkeypatch):
    """matplotlib (cache/config folder, font cache) and pyogrio (an environment
    variable) write on their FIRST import; imported inside a script, the guard
    refused it and the script failed for reasons it did not cause (fix review)."""
    import sys

    from flow.nodes.action import python_script as P

    monkeypatch.setattr(P, "_bibliotecas_aquecidas", False)
    P._aquecer_bibliotecas()
    for nome in ("matplotlib", "pyogrio"):
        try:
            __import__(nome)
        except ImportError:
            continue
        assert nome in sys.modules
    # Once per process.
    chamadas = []
    monkeypatch.setattr("builtins.__import__", lambda *a, **k: chamadas.append(a[0]))
    P._aquecer_bibliotecas()
    assert chamadas == []


def test_listing_a_sys_path_folder_is_allowed_reading_outside_is_not(tmp_path, monkeypatch):
    """Python's import machinery lists the sys.path folders; refused, it cached
    an EMPTY listing and later platform imports from that folder failed after
    the script ended (fix review). Only the listing: reading a file there is
    still refused."""
    import sys

    (tmp_path / "segredo.txt").write_text("x")
    monkeypatch.setattr(sys, "path", [*sys.path, str(tmp_path)])
    ns = {"pd": pd, "caminho": str(tmp_path)}
    # The listing happens inside the user's code: the platform's own import
    # search would do the same while the script runs.
    from flow.utils import code_sandbox as C

    C.instalar_guarda_de_execucao()
    with C.executando_codigo_do_usuario():
        assert "segredo.txt" in os.listdir(tmp_path)
        with pytest.raises(PermissionError):
            open(tmp_path / "segredo.txt").read()
        with pytest.raises(PermissionError):
            os.listdir(tmp_path.parent)
    del ns
