"""Regression for the PythonScript timeout (audit: high).

`asyncio.to_thread`/the executor do NOT cancel the thread: a script in `while True`
blew the node's timeout but left the THREAD alive, stuck in a worker of the
DEFAULT pool — shared with all CPU-bound nodes. A few of those hung the whole
executor.

The fix has two parts, one tested by reading the code and the other by execution:
 - a DEDICATED, bounded pool (_SCRIPT_POOL), isolating the damage; and never
   asyncio.wait_for on the executor's future (which WOULD WAIT for the thread to
   finish, defeating the timeout);
 - best-effort interruption of the thread on timeout, which returns the worker to
   the pool in the common case of a pure-Python loop.

Each test fails WITHOUT the fix; the docstring names the mutation that breaks ONLY it.
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
    _ScriptInterrupted,
    _interromper_thread,
)


def _no(code: str, timeout: int = 30, saida: str = "result") -> PythonScript:
    n = PythonScript("n", {"code": code, "output_vars": saida, "timeout": timeout})
    n._publisher = MagicMock()
    n._task_id = "t"
    return n


# ── Pool dedicado e limitado ────────────────────────────────────────────────

def test_dedicated_pool_is_bounded():
    """Mutation: go back to using asyncio.to_thread (default pool).

    The default pool is the same one used by the other nodes and the heartbeat;
    a thread stuck there hangs everything. The dedicated one contains the damage.
    """
    assert isinstance(_SCRIPT_POOL, ThreadPoolExecutor)
    assert _SCRIPT_POOL._thread_name_prefix == "pythonscript"
    assert 1 <= _MAX_PYTHONSCRIPT_WORKERS <= 8


def test_execute_uses_the_pool_and_not_wait_for_on_the_future():
    """Mutation: `asyncio.wait_for(future, ...)` instead of `asyncio.wait`.

    wait_for tries to CANCEL the executor's future; since the thread cannot be
    cancelled, it WAITS for the thread to finish — which in a `while True` never
    happens, defeating the timeout itself. `asyncio.wait` only observes.
    """
    codigo = inspect.getsource(PythonScript.execute)
    assert "_SCRIPT_POOL" in codigo
    assert "asyncio.wait(" in codigo
    assert "asyncio.wait_for(future" not in codigo
    assert "asyncio.to_thread(" not in codigo
    # Mutation: replace the _interromper_thread call with `released = False`.
    # Without interrupting, a `while True` holds the worker forever. The
    # behavioral proof that the interruption returns the worker is in
    # test_interrupt_ends_loop_and_reclaims_the_worker; here we ensure the node
    # actually INVOKES it in the timeout branch.
    assert "_interromper_thread(" in codigo


def test_run_script_does_not_use_to_thread():
    """Mutacao: reintroduzir asyncio.to_thread em qualquer ponto do modulo."""
    codigo = inspect.getsource(ps)
    assert "asyncio.to_thread(" not in codigo


# ── Thread interruption ─────────────────────────────────────────────────────

class _FakeFuture:
    def __init__(self, done: bool):
        self._done = done

    def done(self) -> bool:
        return self._done


def test_interrupt_ignores_null_ident():
    assert _interromper_thread(_FakeFuture(False), None) is False


def test_interrupt_ignores_already_done_future():
    """Mutation: remove the `future.done()` guard.

    Without it, the interruption could land on a NEXT task in the pool after the
    thread had finished ours — killing the wrong script.
    """
    assert _interromper_thread(_FakeFuture(True), threading.get_ident()) is False


def test_interrupt_ends_loop_and_reclaims_the_worker():
    """Mutation: do not call _interromper_thread in the timeout branch.

    Proves the injection ends a pure-Python `while True` and returns the worker:
    after interrupting, a 2nd task runs in the SAME 1-worker pool.
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
    assert segunda.result(timeout=5) == 42  # worker was returned
    pool.shutdown(wait=False)


# ── End-to-end behavior through the node ────────────────────────────────────

async def test_timeout_ends_and_reclaims_via_the_node():
    """Mutation: any regression that makes the timeout hang (wait_for) or not
    release the worker.

    The outer `asyncio.wait_for` turns a possible hang into a test FAILURE
    (it never leaves the suite hanging).
    """
    t0 = time.monotonic()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(_no("while True:\n    x = 1", timeout=1).execute({}), timeout=8)
    assert time.monotonic() - t0 < 6  # timed out around 1s, did not hang

    # the previous loop's worker was returned: a new script runs right away
    r = await asyncio.wait_for(_no("result = 'vivo'").execute({}), timeout=5)
    assert r == {"result": "vivo"}


async def test_normal_script_works():
    r = await _no("result = 1 + 2").execute({})
    assert r == {"result": 3}


async def test_script_error_becomes_runtimeerror():
    with pytest.raises(RuntimeError) as exc:
        await _no("result = 1 / 0").execute({})
    assert "division by zero" in str(exc.value)


async def test_escape_blocked_by_the_node_before_running():
    """AST validation runs BEFORE compiling/executing: an escape becomes ValueError."""
    with pytest.raises(ValueError) as exc:
        await _no("result = ().__class__").execute({})
    assert "seguran" in str(exc.value).lower()


def test_interrupted_script_is_baseexception():
    """Mutation: _ScriptInterrupted becoming a subclass of Exception.

    It must be a BaseException to survive an `except Exception` in the user's
    code and actually end the loop.
    """
    assert issubclass(_ScriptInterrupted, BaseException)
    assert not issubclass(_ScriptInterrupted, Exception)
