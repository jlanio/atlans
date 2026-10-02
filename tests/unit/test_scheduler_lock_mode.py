# tests/unit/test_scheduler_lock_mode.py
"""
Regressão de um AUTO-DEADLOCK invisível ao Postgres.

`_process_schedule` abre uma transação e a mantém aberta enquanto
`_fire_workflow` roda EM OUTRA conexão. Esse disparo insere um `WorkflowRun`
com FK para `schedules.id` (schedule_id) — e todo INSERT com FK pede um
`FOR KEY SHARE` na linha referenciada. `FOR UPDATE` conflita com `FOR KEY
SHARE`: a conexão do disparo bloqueia esperando a linha que a transação de
fora segura, mas essa transação está `await`-ando o disparo terminar. Trava
mútua — e como a conexão de fora fica idle-in-transaction (sem esperar lock
nenhum no nível do banco), o detector de deadlock do PG nunca a vê.

`FOR NO KEY UPDATE` NÃO conflita com `FOR KEY SHARE` e mantém a exclusividade
de "um worker por schedule". O bug não aparecia no CI (SQLite ignora o clause),
então este teste trava o MODO no SQL compilado para o dialeto Postgres.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql


def _sessao(db):
    @asynccontextmanager
    async def _ctx():
        yield db
    return _ctx


@pytest.mark.asyncio
async def test_process_schedule_trava_com_for_no_key_update_skip_locked():
    from app.core.async_scheduler import AsyncScheduler

    capturado: dict = {}

    resultado = MagicMock()
    resultado.scalar_one_or_none = MagicMock(return_value=None)  # sai cedo, sem disparo

    db = MagicMock()

    async def _execute(stmt):
        capturado["stmt"] = stmt
        return resultado

    db.execute = _execute
    db.commit = AsyncMock()

    sched = MagicMock()
    sched.id = 1
    sched.job_id = "job-1"

    with patch("app.core.async_scheduler.AsyncSessionLocal", _sessao(db)):
        await AsyncScheduler()._process_schedule(sched, datetime(2026, 1, 1))

    sql = str(capturado["stmt"].compile(dialect=postgresql.dialect()))
    assert "FOR NO KEY UPDATE" in sql, sql
    assert "SKIP LOCKED" in sql, sql
    # O modo antigo — o que conflitava com o FOR KEY SHARE do INSERT do run.
    # ("FOR NO KEY UPDATE" não contém a substring "FOR UPDATE".)
    assert "FOR UPDATE" not in sql, sql
    db.commit.assert_not_awaited()  # scalar_one_or_none None → nenhum commit/disparo
