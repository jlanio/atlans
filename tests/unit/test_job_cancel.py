"""
Cancelamento de job no executor (ExecutorJobQueue.cancel).

Até então um workflow disparado só terminava sozinho ou por timeout — não havia
como interromper um job caro ou travado. O ponto delicado é o aviso de volta:
a task interrompida nunca produz resultado, então sem `on_cancelled` o run
ficaria "running" para sempre no servidor.
"""
import asyncio

import pytest

from executor.job_queue import ExecutorJobQueue


def _job(job_id: str, priority: int = 5) -> dict:
    return {"envelope": {"job_id": job_id, "priority": priority}}


async def _drain(queue: ExecutorJobQueue, timeout: float = 2.0):
    """Espera a fila esvaziar sem depender de sleeps fixos."""
    async def _wait():
        while queue.get_capacity()["queued"] > 0 or queue.get_capacity()["running"] > 0:
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_wait(), timeout=timeout)


async def _eventually(pred, timeout: float = 2.0):
    """Aguarda uma condição virar verdadeira.

    `_drain` sozinho não serve para observar o descarte: ele só olha fila e
    contador de execução, e um job cancelado já saiu da fila enquanto o worker
    ainda processa o aviso.
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
        await asyncio.sleep(30)  # job longo — seria impossível parar antes

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
    """Cancelar um job não pode derrubar o worker que o executava."""
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
    """Não dá para remover do meio de uma PriorityQueue: o worker descarta."""
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

        assert executados == ["bloqueia"]  # o cancelado nunca executou
    finally:
        await queue.shutdown(timeout=2)


@pytest.mark.asyncio
async def test_cancelamento_durante_espera_pelo_semaforo_nao_se_perde():
    """Executor saturado: o job já saiu da fila mas ainda espera vaga.

    Nessa janela `cancel()` não acha task ativa e marca para descarte; sem a
    re-checagem depois do semáforo o worker já teria passado da primeira e o job
    rodaria até o fim enquanto a UI dizia "cancelamento solicitado".
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

    # 1 slot de concorrência e 2 workers: o segundo worker tira "alvo" da fila e
    # fica preso no semáforo enquanto "ocupa" segura a única vaga.
    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1,
                             max_queue_size=10, on_cancelled=on_cancelled)
    await queue.start(n_workers=2)
    try:
        await queue.enqueue(_job("ocupa", priority=1))
        await asyncio.wait_for(ocupando.wait(), timeout=2.0)

        await queue.enqueue(_job("alvo", priority=1))
        await asyncio.sleep(0.05)   # o 2º worker pega "alvo" e trava no semáforo

        assert queue.cancel("alvo") == "queued"
        liberar.set()
        await _eventually(lambda: cancelled == ["alvo"])

        assert executados == ["ocupa"], "job cancelado não podia ter executado"
    finally:
        await queue.shutdown(timeout=2)


@pytest.mark.asyncio
async def test_shutdown_nao_deixa_job_orfao_rodando():
    """Cancelar `await task` não cancela a task — o job vazaria após o shutdown."""
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

    # timeout=0 força o caminho de abandono: cancela os workers com job em curso.
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
