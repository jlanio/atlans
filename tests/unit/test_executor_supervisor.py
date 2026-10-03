# tests/unit/test_executor_supervisor.py
"""
Watchdog for the supervisor process (anti-orphan).

The scenario it exists to prevent: the user kills the desktop app through the
Task Manager; Electron dies without terminating the child; the executor stays
alive, with no window and no tray, holding the WebSocket connection under the
same EXECUTOR_ID. The next time the app starts, the server sees two connections
from the same executor.

The subtlest case covered here is **PID reuse**: the operating system reuses
process numbers, and a watchdog that only compares the PID would conclude that
the supervisor is alive when in fact another program inherited the number.
"""
import asyncio

import pytest

from executor import supervisor


# ── Reading the variable ─────────────────────────────────────────────────────

def test_sem_variavel_nao_ha_o_que_vigiar(monkeypatch):
    """Running `python -m executor` by hand does not set the variable — the
    watchdog simply does not start."""
    monkeypatch.delenv(supervisor.VAR_PID, raising=False)
    assert supervisor.pid_configurado() is None


@pytest.mark.parametrize("valor", ["", "   ", "abc", "0", "-5", "12.5"])
def test_valor_invalido_desativa_em_vez_de_derrubar(monkeypatch, valor):
    """A malformed variable must not prevent the executor from starting."""
    monkeypatch.setenv(supervisor.VAR_PID, valor)
    assert supervisor.pid_configurado() is None


def test_valor_valido_e_lido(monkeypatch):
    monkeypatch.setenv(supervisor.VAR_PID, " 4321 ")
    assert supervisor.pid_configurado() == 4321


# ── Process identity ─────────────────────────────────────────────────────────

class _ProcFalso:
    def __init__(self, *, rodando=True, criado=1000.0, status="running"):
        self._rodando, self._criado, self._status = rodando, criado, status

    def is_running(self): return self._rodando
    def create_time(self): return self._criado
    def status(self): return self._status


def _monitor(proc, criado=1000.0):
    m = supervisor.MonitorSupervisor(4321, intervalo=0.01)
    m._proc, m._criado_em = proc, criado
    return m


def test_supervisor_vivo():
    assert _monitor(_ProcFalso()).vivo() is True


def test_supervisor_encerrado():
    assert _monitor(_ProcFalso(rodando=False)).vivo() is False


def test_pid_reciclado_por_outro_processo_conta_como_morto():
    """The core of the test: same PID, different `create_time` — it is another
    program that inherited the number, not the supervisor. Comparing only the
    PID would keep the orphan alive forever."""
    assert _monitor(_ProcFalso(criado=2000.0), criado=1000.0).vivo() is False


def test_zumbi_nao_conta_como_vivo():
    """A zombie process still answers True to `is_running()`, but supervises
    nobody."""
    import psutil
    assert _monitor(_ProcFalso(status=psutil.STATUS_ZOMBIE)).vivo() is False


def test_excecao_do_psutil_conta_como_morto():
    """NoSuchProcess, AccessDenied on a process that changed owner — all of them
    mean 'the supervisor I knew is gone'."""
    class _Explode:
        def is_running(self): raise RuntimeError("sumiu")

    assert _monitor(_Explode()).vivo() is False


def test_sem_vincular_conta_como_morto():
    assert supervisor.MonitorSupervisor(4321).vivo() is False


# ── Vinculo ──────────────────────────────────────────────────────────────────

def test_vincular_no_proprio_processo_funciona():
    import os
    m = supervisor.MonitorSupervisor(os.getpid())
    assert m.vincular() is True
    assert m.vivo() is True


def test_vincular_em_pid_inexistente_falha_sem_levantar():
    # Absurd PID: above the limit of any system in use.
    m = supervisor.MonitorSupervisor(2 ** 31 - 1)
    assert m.vincular() is False


# ── Loop ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vigiar_dispara_o_shutdown_quando_o_supervisor_some():
    disparos = []
    m = _monitor(_ProcFalso(rodando=False))
    await asyncio.wait_for(m.vigiar(lambda: disparos.append(True)), timeout=2.0)
    assert disparos == [True]


@pytest.mark.asyncio
async def test_vigiar_nao_dispara_enquanto_vivo():
    disparos = []
    m = _monitor(_ProcFalso())
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(m.vigiar(lambda: disparos.append(True)), timeout=0.1)
    assert disparos == []


@pytest.mark.asyncio
async def test_handler_que_levanta_nao_deixa_a_task_estourar():
    """The task is watched by `_observar_task`; an error here would become an ERROR
    in the log on every boot."""
    m = _monitor(_ProcFalso(rodando=False))
    await asyncio.wait_for(
        m.vigiar(lambda: (_ for _ in ()).throw(RuntimeError("boom"))), timeout=2.0)


@pytest.mark.asyncio
async def test_criar_task_sem_variavel_devolve_none(monkeypatch):
    monkeypatch.delenv(supervisor.VAR_PID, raising=False)
    assert supervisor.criar_task(lambda: None) is None


@pytest.mark.asyncio
async def test_supervisor_ja_morto_no_start_encerra_na_hora(monkeypatch):
    """If the supervisor died between the spawn and the boot, shutting down right
    away is correct: nobody will consume the NDJSON channel or stop this process later."""
    monkeypatch.setenv(supervisor.VAR_PID, str(2 ** 31 - 1))
    disparos = []
    assert supervisor.criar_task(lambda: disparos.append(True)) is None
    assert disparos == [True]


@pytest.mark.asyncio
async def test_criar_task_com_supervisor_vivo_sobe_a_task(monkeypatch):
    import os
    monkeypatch.setenv(supervisor.VAR_PID, str(os.getpid()))
    task = supervisor.criar_task(lambda: None, intervalo=0.01)
    assert task is not None
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
