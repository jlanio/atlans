# tests/unit/test_executor_fila_ordem.py
"""
Ordem da fila local do executor (executor/job_queue.py).

O heap da PriorityQueue não é estável, e o servidor não manda prioridade: todo
job empata no 5. Sem desempate, com dez jobs esperando, o segundo a chegar era
o nono a rodar — e ficava "Em andamento" na tela esse tempo todo. O `seq` de
chegada desempata; a prioridade explícita continua valendo.
"""
from __future__ import annotations

import asyncio

import pytest

from executor.job_queue import ExecutorJobQueue


def _job(job_id, **envelope):
    return {"envelope": {"job_id": job_id, **envelope}}


async def _ordem_de_execucao(mensagens):
    """Enfileira tudo ANTES de ligar o único worker — a ordem de saída é a da
    fila, sem corrida entre o enqueue e o consumo."""
    ordem: list[str] = []

    async def _executar(msg):
        ordem.append(msg["envelope"]["job_id"])

    fila = ExecutorJobQueue(on_execute=_executar, max_concurrent=1, max_queue_size=100)
    for m in mensagens:
        assert await fila.enqueue(m)
    await fila.start(n_workers=1)
    try:
        for _ in range(500):
            if len(ordem) == len(mensagens):
                break
            await asyncio.sleep(0.01)
    finally:
        await fila.shutdown(timeout=5)
    return ordem


@pytest.mark.asyncio
async def test_prioridade_igual_roda_na_ordem_de_chegada():
    ids = [f"job{i}" for i in range(1, 21)]
    assert await _ordem_de_execucao([_job(i) for i in ids]) == ids


@pytest.mark.asyncio
async def test_prioridade_explicita_continua_passando_na_frente():
    mensagens = [
        _job("a"), _job("b"), _job("urgente", priority=1), _job("c"), _job("depois", priority=9),
    ]
    assert await _ordem_de_execucao(mensagens) == ["urgente", "a", "b", "c", "depois"]
