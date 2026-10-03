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

def test_without_variable_there_is_nothing_to_watch(monkeypatch):
    """Running `python -m executor` by hand does not set the variable — the
    watchdog simply does not start."""
    monkeypatch.delenv(supervisor.VAR_PID, raising=False)
    assert supervisor.configured_pid() is None


@pytest.mark.parametrize("valor", ["", "   ", "abc", "0", "-5", "12.5"])
def test_invalid_value_disables_instead_of_crashing(monkeypatch, valor):
    """A malformed variable must not prevent the executor from starting."""
    monkeypatch.setenv(supervisor.VAR_PID, valor)
    assert supervisor.configured_pid() is None


def test_valid_value_is_read(monkeypatch):
    monkeypatch.setenv(supervisor.VAR_PID, " 4321 ")
    assert supervisor.configured_pid() == 4321


# ── Process identity ─────────────────────────────────────────────────────────

class _FakeProc:
    def __init__(self, *, rodando=True, criado=1000.0, status="running"):
        self._running, self._created, self._status = rodando, criado, status

    def is_running(self): return self._running
    def create_time(self): return self._created
    def status(self): return self._status


def _monitor(proc, criado=1000.0):
    m = supervisor.MonitorSupervisor(4321, intervalo=0.01)
    m._proc, m._created_at = proc, criado
    return m


def test_supervisor_alive():
    assert _monitor(_FakeProc()).vivo() is True


def test_supervisor_ended():
    assert _monitor(_FakeProc(rodando=False)).vivo() is False


def test_pid_recycled_by_another_process_counts_as_dead():
    """The core of the test: same PID, different `create_time` — it is another
    program that inherited the number, not the supervisor. Comparing only the
    PID would keep the orphan alive forever."""
    assert _monitor(_FakeProc(criado=2000.0), criado=1000.0).vivo() is False


def test_zombie_does_not_count_as_alive():
    """A zombie process still answers True to `is_running()`, but supervises
    nobody."""
    import psutil
    assert _monitor(_FakeProc(status=psutil.STATUS_ZOMBIE)).vivo() is False


def test_psutil_exception_counts_as_dead():
    """NoSuchProcess, AccessDenied on a process that changed owner — all of them
    mean 'the supervisor I knew is gone'."""
    class _Explode:
        def is_running(self): raise RuntimeError("sumiu")

    assert _monitor(_Explode()).vivo() is False


def test_without_binding_counts_as_dead():
    assert supervisor.MonitorSupervisor(4321).vivo() is False


# ── Vinculo ──────────────────────────────────────────────────────────────────

def test_binding_to_own_process_works():
    import os
    m = supervisor.MonitorSupervisor(os.getpid())
    assert m.vincular() is True
    assert m.vivo() is True


def test_binding_to_nonexistent_pid_fails_without_raising():
    # Absurd PID: above the limit of any system in use.
    m = supervisor.MonitorSupervisor(2 ** 31 - 1)
    assert m.vincular() is False


# ── Loop ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_watch_triggers_the_shutdown_when_the_supervisor_disappears():
    firings = []
    m = _monitor(_FakeProc(rodando=False))
    await asyncio.wait_for(m.watch(lambda: firings.append(True)), timeout=2.0)
    assert firings == [True]


@pytest.mark.asyncio
async def test_watch_does_not_trigger_while_alive():
    firings = []
    m = _monitor(_FakeProc())
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(m.watch(lambda: firings.append(True)), timeout=0.1)
    assert firings == []


@pytest.mark.asyncio
async def test_handler_that_raises_does_not_let_the_task_blow_up():
    """The task is watched by `_watch_task`; an error here would become an ERROR
    in the log on every boot."""
    m = _monitor(_FakeProc(rodando=False))
    await asyncio.wait_for(
        m.watch(lambda: (_ for _ in ()).throw(RuntimeError("boom"))), timeout=2.0)


@pytest.mark.asyncio
async def test_create_task_without_variable_returns_none(monkeypatch):
    monkeypatch.delenv(supervisor.VAR_PID, raising=False)
    assert supervisor.criar_task(lambda: None) is None


@pytest.mark.asyncio
async def test_supervisor_already_dead_on_start_ends_immediately(monkeypatch):
    """If the supervisor died between the spawn and the boot, shutting down right
    away is correct: nobody will consume the NDJSON channel or stop this process later."""
    monkeypatch.setenv(supervisor.VAR_PID, str(2 ** 31 - 1))
    firings = []
    assert supervisor.criar_task(lambda: firings.append(True)) is None
    assert firings == [True]


@pytest.mark.asyncio
async def test_create_task_with_live_supervisor_starts_the_task(monkeypatch):
    import os
    monkeypatch.setenv(supervisor.VAR_PID, str(os.getpid()))
    task = supervisor.criar_task(lambda: None, intervalo=0.01)
    assert task is not None
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
