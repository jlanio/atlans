"""Regressao do timeout do PythonScript (auditoria: alta).

`asyncio.to_thread`/o executor NAO cancelam a thread: um script em `while True`
estourava o timeout do no mas deixava a THREAD viva, presa num worker do pool
DEFAULT — compartilhado com todos os nos CPU-bound. Poucas assim travavam o
executor inteiro.

O fix tem duas partes, uma testada por leitura de codigo e outra por execucao:
 - pool DEDICADO e limitado (_SCRIPT_POOL), isolando o dano; e nunca
   asyncio.wait_for sobre o future do executor (que ESPERARIA a thread terminar,
   anulando o timeout);
 - interrupcao best-effort da thread no timeout, que devolve o worker ao pool no
   caso comum de laco puro-Python.

Cada teste falha SEM o fix; a docstring nomeia a mutacao que derruba SO ele.
"""
import asyncio
import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from flow.nodes.action import python_script as ps
from flow.nodes.action.python_script import (
    PythonScript,
    _MAX_PYTHONSCRIPT_WORKERS,
    _SCRIPT_POOL,
    _ScriptInterrompido,
    _interromper_thread,
)


def _no(code: str, timeout: int = 30, saida: str = "result") -> PythonScript:
    n = PythonScript("n", {"code": code, "output_vars": saida, "timeout": timeout})
    n._publisher = MagicMock()
    n._task_id = "t"
    return n


# ── Pool dedicado e limitado ────────────────────────────────────────────────

def test_pool_dedicado_e_limitado():
    """Mutacao: voltar a usar asyncio.to_thread (pool default).

    O pool default e o mesmo dos demais nos e do heartbeat; uma thread presa la
    trava tudo. O dedicado contem o dano.
    """
    assert isinstance(_SCRIPT_POOL, ThreadPoolExecutor)
    assert _SCRIPT_POOL._thread_name_prefix == "pythonscript"
    assert 1 <= _MAX_PYTHONSCRIPT_WORKERS <= 8


def test_execute_usa_o_pool_e_nao_wait_for_do_future():
    """Mutacao: `asyncio.wait_for(future, ...)` no lugar de `asyncio.wait`.

    wait_for tenta CANCELAR o future do executor; como a thread nao e cancelavel,
    ele ESPERA a thread terminar — que num `while True` nunca ocorre, anulando o
    proprio timeout. `asyncio.wait` apenas observa.
    """
    codigo = inspect.getsource(PythonScript.execute)
    assert "_SCRIPT_POOL" in codigo
    assert "asyncio.wait(" in codigo
    assert "asyncio.wait_for(future" not in codigo
    assert "asyncio.to_thread(" not in codigo
    # Mutacao: trocar a chamada de _interromper_thread por `liberou = False`.
    # Sem interromper, um `while True` prende o worker para sempre. A prova
    # comportamental de que a interrupcao devolve o worker esta em
    # test_interromper_encerra_laco_e_reclama_o_worker; aqui garantimos que o no
    # de fato a INVOCA no ramo de timeout.
    assert "_interromper_thread(" in codigo


def test_run_script_nao_usa_to_thread():
    """Mutacao: reintroduzir asyncio.to_thread em qualquer ponto do modulo."""
    codigo = inspect.getsource(ps)
    assert "asyncio.to_thread(" not in codigo


# ── Interrupcao da thread ───────────────────────────────────────────────────

class _FutureFalso:
    def __init__(self, done: bool):
        self._done = done

    def done(self) -> bool:
        return self._done


def test_interromper_ignora_ident_nulo():
    assert _interromper_thread(_FutureFalso(False), None) is False


def test_interromper_ignora_future_ja_concluido():
    """Mutacao: remover a guarda `future.done()`.

    Sem ela, a interrupcao poderia cair numa PROXIMA tarefa do pool depois de a
    thread ter terminado a nossa — matando o script errado.
    """
    assert _interromper_thread(_FutureFalso(True), threading.get_ident()) is False


def test_interromper_encerra_laco_e_reclama_o_worker():
    """Mutacao: nao chamar _interromper_thread no ramo de timeout.

    Prova que a injecao encerra um `while True` puro-Python e devolve o worker:
    apos interromper, uma 2a tarefa roda no MESMO pool de 1 worker.
    """
    pool = ThreadPoolExecutor(max_workers=1)
    ident: dict = {}

    def laco():
        ident["v"] = threading.get_ident()
        while True:
            pass

    fut = pool.submit(laco)
    fut.add_done_callback(lambda f: (not f.cancelled()) and f.exception())
    # espera a thread registrar o ident e entrar no laco
    for _ in range(200):
        if "v" in ident:
            break
        time.sleep(0.01)
    assert "v" in ident and not fut.done()

    assert _interromper_thread(fut, ident["v"]) is True

    segunda = pool.submit(lambda: 42)
    assert segunda.result(timeout=5) == 42  # worker foi devolvido
    pool.shutdown(wait=False)


# ── Comportamento ponta a ponta pelo no ─────────────────────────────────────

async def test_timeout_encerra_e_reclama_pelo_no():
    """Mutacao: qualquer regressao que faca o timeout pendurar (wait_for) ou nao
    liberar o worker.

    O `asyncio.wait_for` externo converte um eventual travamento em FALHA de
    teste (nunca deixa a suite pendurada).
    """
    t0 = time.monotonic()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(_no("while True:\n    x = 1", timeout=1).execute({}), timeout=8)
    assert time.monotonic() - t0 < 6  # estourou perto de 1s, nao pendurou

    # o worker do laco anterior foi devolvido: um script novo roda logo
    r = await asyncio.wait_for(_no("result = 'vivo'").execute({}), timeout=5)
    assert r == {"result": "vivo"}


async def test_script_normal_funciona():
    r = await _no("result = 1 + 2").execute({})
    assert r == {"result": 3}


async def test_erro_do_script_vira_runtimeerror():
    with pytest.raises(RuntimeError) as exc:
        await _no("result = 1 / 0").execute({})
    assert "division by zero" in str(exc.value)


async def test_fuga_bloqueada_pelo_no_antes_de_executar():
    """A validacao AST roda ANTES de compilar/executar: fuga vira ValueError."""
    with pytest.raises(ValueError) as exc:
        await _no("result = ().__class__").execute({})
    assert "seguran" in str(exc.value).lower()


def test_script_interrompido_e_baseexception():
    """Mutacao: _ScriptInterrompido virar subclasse de Exception.

    Precisa ser BaseException para sobreviver a um `except Exception` no codigo
    do usuario e realmente encerrar o laco.
    """
    assert issubclass(_ScriptInterrompido, BaseException)
    assert not issubclass(_ScriptInterrompido, Exception)
