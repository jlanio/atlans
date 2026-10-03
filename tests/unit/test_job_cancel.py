"""
Job cancellation on the executor (ExecutorJobQueue.cancel).

Until now a triggered workflow only ended on its own or by timeout — there was
no way to interrupt an expensive or stuck job. The delicate point is the notice
back: the interrupted task never produces a result, so without `on_cancelled` the run
would stay "running" forever on the server.
"""
import asyncio

import pytest

from executor.job_queue import ExecutorJobQueue


def _job(job_id: str, priority: int = 5) -> dict:
    return {"envelope": {"job_id": job_id, "priority": priority}}


async def _drain(queue: ExecutorJobQueue, timeout: float = 2.0):
    """Waits for the queue to drain without relying on fixed sleeps."""
    async def _wait():
        while queue.get_capacity()["queued"] > 0 or queue.get_capacity()["running"] > 0:
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_wait(), timeout=timeout)


async def _eventually(pred, timeout: float = 2.0):
    """Waits for a condition to become true.

    `_drain` alone is not enough to observe the discard: it only looks at the queue
    and the execution counter, and a cancelled job has already left the queue while
    the worker is still processing the notice.
    """
    async def _wait():
        while not pred():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_wait(), timeout=timeout)


@pytest.mark.asyncio
async def test_cancela_job_em_execucao_e_avisa():
    started = asyncio.Event()
    cancelled: list[str] = []

    async def on_execute(message):
        started.set()
        await asyncio.sleep(30)  # long job — it would be impossible to stop beforehand

    async def on_cancelled(message):
        cancelled.append(message["envelope"]["job_id"])

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1,
                             max_queue_size=10, on_cancelled=on_cancelled)
    await queue.start(n_workers=1)
    try:
        await queue.enqueue(_job("job-1"))
        await asyncio.wait_for(started.wait(), timeout=2.0)

        assert queue.cancel("job-1") == "running"
        await _eventually(lambda: cancelled == ["job-1"])
        await _drain(queue)
        # O worker sobrevive ao cancelamento e volta a consumir a fila.
        assert queue.get_capacity()["running"] == 0
    finally:
        await queue.shutdown(timeout=2)


@pytest.mark.asyncio
async def test_worker_continua_vivo_apos_cancelamento():
    """Cancelling a job must not bring down the worker that was executing it."""
    started = asyncio.Event()
    executados: list[str] = []

    async def on_execute(message):
        job_id = message["envelope"]["job_id"]
        if job_id == "lento":
            started.set()
            await asyncio.sleep(30)
        else:
            executados.append(job_id)

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1, max_queue_size=10)
    await queue.start(n_workers=1)
    try:
        await queue.enqueue(_job("lento"))
        await asyncio.wait_for(started.wait(), timeout=2.0)
        queue.cancel("lento")

        await queue.enqueue(_job("seguinte"))
        await _drain(queue)

        assert executados == ["seguinte"]
    finally:
        await queue.shutdown(timeout=2)


@pytest.mark.asyncio
async def test_cancela_job_ainda_na_fila():
    """You cannot remove from the middle of a PriorityQueue: the worker discards it."""
    liberar = asyncio.Event()
    executados: list[str] = []
    cancelled: list[str] = []

    async def on_execute(message):
        job_id = message["envelope"]["job_id"]
        if job_id == "bloqueia":
            await liberar.wait()
        executados.append(job_id)

    async def on_cancelled(message):
        cancelled.append(message["envelope"]["job_id"])

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1,
                             max_queue_size=10, on_cancelled=on_cancelled)
    await queue.start(n_workers=1)
    try:
        await queue.enqueue(_job("bloqueia"))
        await asyncio.sleep(0.05)          # garante que o worker pegou o primeiro
        await queue.enqueue(_job("na-fila"))

        assert queue.cancel("na-fila") == "queued"
        liberar.set()
        await _eventually(lambda: cancelled == ["na-fila"])

        assert executados == ["bloqueia"]  # the cancelled one never executed
    finally:
        await queue.shutdown(timeout=2)


@pytest.mark.asyncio
async def test_cancelamento_durante_espera_pelo_semaforo_nao_se_perde():
    """Saturated executor: the job has already left the queue but is still waiting for a slot.

    In that window `cancel()` finds no active task and marks it for discard; without the
    re-check after the semaphore the worker would already be past the first one and the job
    would run to the end while the UI said "cancelamento solicitado" (cancellation requested).
    """
    ocupando = asyncio.Event()
    liberar = asyncio.Event()
    executados: list[str] = []
    cancelled: list[str] = []

    async def on_execute(message):
        job_id = message["envelope"]["job_id"]
        if job_id == "ocupa":
            ocupando.set()
            await liberar.wait()
        executados.append(job_id)

    async def on_cancelled(message):
        cancelled.append(message["envelope"]["job_id"])

    # 1 concurrency slot and 2 workers: the second worker takes "alvo" off the queue and
    # gets stuck on the semaphore while "ocupa" holds the only slot.
    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1,
                             max_queue_size=10, on_cancelled=on_cancelled)
    await queue.start(n_workers=2)
    try:
        await queue.enqueue(_job("ocupa", priority=1))
        await asyncio.wait_for(ocupando.wait(), timeout=2.0)

        await queue.enqueue(_job("alvo", priority=1))
        await asyncio.sleep(0.05)   # the 2nd worker picks up "alvo" and blocks on the semaphore

        assert queue.cancel("alvo") == "queued"
        liberar.set()
        await _eventually(lambda: cancelled == ["alvo"])

        assert executados == ["ocupa"], "job cancelado não podia ter executado"
    finally:
        await queue.shutdown(timeout=2)


@pytest.mark.asyncio
async def test_shutdown_nao_deixa_job_orfao_rodando():
    """Cancelling `await task` does not cancel the task — the job would leak after shutdown."""
    started = asyncio.Event()
    concluiu = False

    async def on_execute(message):
        nonlocal concluiu
        started.set()
        try:
            await asyncio.sleep(30)
            concluiu = True
        except asyncio.CancelledError:
            raise

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1, max_queue_size=10)
    await queue.start(n_workers=1)
    await queue.enqueue(_job("longo"))
    await asyncio.wait_for(started.wait(), timeout=2.0)

    # timeout=0 forces the abandon path: cancels the workers with a job in progress.
    await queue.shutdown(timeout=0)
    await asyncio.sleep(0.05)

    task = queue._active_tasks.get("longo")
    assert task is None or task.cancelled(), "job seguiu rodando após o shutdown"
    assert concluiu is False


@pytest.mark.asyncio
async def test_falha_no_aviso_nao_derruba_o_worker():
    started = asyncio.Event()

    async def on_execute(message):
        started.set()
        await asyncio.sleep(30)

    async def on_cancelled(message):
        raise RuntimeError("servidor fora do ar")

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1,
                             max_queue_size=10, on_cancelled=on_cancelled)
    await queue.start(n_workers=1)
    try:
        await queue.enqueue(_job("job-1"))
        await asyncio.wait_for(started.wait(), timeout=2.0)
        queue.cancel("job-1")
        await _drain(queue)
        assert queue.get_capacity()["running"] == 0
    finally:
        await queue.shutdown(timeout=2)
