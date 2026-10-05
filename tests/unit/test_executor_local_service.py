"""The executor that `make up-dev` brings up on its own: each pass compares the
database with the two files the executor container shares, and does the least
it can. Real database (SQLite): what matters is what stays stored — the
executor, its type, the OTPs — and what lands in the shared folder.
"""
from __future__ import annotations

import json
import os
import stat
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import JSON, MetaData, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.executor import Executor
from app.models.executor_enrollment_otp import ExecutorEnrollmentOTP
from app.services import executor_local_service as local


@pytest.fixture
async def fabrica(monkeypatch):
    """SQLite with the executors and the OTPs. `executors` uses JSONB, which SQLite
    does not compile: a copy of the table with JSON."""
    executores = Executor.__table__.to_metadata(MetaData())
    for coluna in executores.columns:
        if isinstance(coluna.type, JSONB):
            coluna.type = JSON()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(executores.create)
        await conn.run_sync(Base.metadata.create_all, tables=[ExecutorEnrollmentOTP.__table__])
    fab = async_sessionmaker(engine, expire_on_commit=False)

    # Like app.core.db.get_session_async: it rolls back on the way out, which
    # expires every instance the pass still holds.
    @asynccontextmanager
    async def _sessao():
        async with fab() as s:
            try:
                yield s
            finally:
                await s.rollback()

    monkeypatch.setattr("app.core.db.get_session_async", _sessao)
    with patch("app.services.executor_enrollment_service.OTP_PEPPER", "pepper-de-teste-256-bits-base64xxxx"):
        yield fab
    await engine.dispose()


async def _executores(fab) -> list[Executor]:
    async with fab() as s:
        return list((await s.execute(select(Executor).order_by(Executor.id))).scalars())


async def _otps(fab) -> int:
    async with fab() as s:
        return (await s.execute(select(func.count()).select_from(ExecutorEnrollmentOTP))).scalar_one()


def _pedido(pasta) -> dict:
    return json.loads((pasta / local.PEDIDO).read_text())


async def _marcar(fab, executor_id: str, **campos) -> None:
    async with fab() as s:
        ex = (await s.execute(select(Executor).where(Executor.id_hash == executor_id))).scalar_one()
        for nome, valor in campos.items():
            setattr(ex, nome, valor)
        await s.commit()


async def test_banco_vazio_cria_o_executor_no_pool_padrao_e_grava_o_pedido(fabrica, tmp_path):
    assert await local.provisionar(tmp_path) == "pedido"

    [ex] = await _executores(fabrica)
    assert ex.name == local.NOME
    assert ex.executor_type == "default" and ex.is_default is True  # every workspace routes to it
    assert ex.status == "pending"
    pedido = _pedido(tmp_path)
    assert pedido["executor_id"] == ex.id_hash
    assert len(pedido["otp"]) >= 40
    # The OTP is a credential: the file is born 600.
    assert stat.S_IMODE(os.stat(tmp_path / local.PEDIDO).st_mode) == 0o600


async def test_pedido_ainda_valido_nao_gera_outro_otp(fabrica, tmp_path):
    await local.provisionar(tmp_path)
    primeiro = _pedido(tmp_path)["otp"]

    # Another OTP would invalidate the one the executor may be using right now.
    assert await local.provisionar(tmp_path) == "aguardando"
    assert _pedido(tmp_path)["otp"] == primeiro
    assert await _otps(fabrica) == 1
    assert len(await _executores(fabrica)) == 1


async def test_ativo_e_cadastrado_nao_faz_nada(fabrica, tmp_path):
    await local.provisionar(tmp_path)
    executor_id = _pedido(tmp_path)["executor_id"]
    # What the executor's entrypoint does after enrolling.
    (tmp_path / local.CADASTRADO).write_text(json.dumps({"executor_id": executor_id}))
    (tmp_path / local.PEDIDO).unlink()
    await _marcar(fabrica, executor_id, status="active")

    assert await local.provisionar(tmp_path) == "pronto"
    assert not (tmp_path / local.PEDIDO).exists()
    assert await _otps(fabrica) == 1


async def test_ativo_sem_cadastro_no_volume_pede_de_novo(fabrica, tmp_path):
    """The executor's volume was removed (`down -v`): the database still says
    active, but nobody holds the certificate. A new OTP for the SAME executor."""
    await local.provisionar(tmp_path)
    executor_id = _pedido(tmp_path)["executor_id"]
    (tmp_path / local.PEDIDO).unlink()
    await _marcar(fabrica, executor_id, status="active")

    assert await local.provisionar(tmp_path) == "pedido"
    assert _pedido(tmp_path)["executor_id"] == executor_id
    assert len(await _executores(fabrica)) == 1


async def test_revogado_vira_um_executor_novo(fabrica, tmp_path):
    await local.provisionar(tmp_path)
    antigo = _pedido(tmp_path)["executor_id"]
    (tmp_path / local.CADASTRADO).write_text(json.dumps({"executor_id": antigo}))
    await _marcar(fabrica, antigo, status="revoked")

    assert await local.provisionar(tmp_path) == "pedido"
    novo = _pedido(tmp_path)["executor_id"]
    assert novo != antigo
    assert [e.status for e in await _executores(fabrica)] == ["revoked", "pending"]


async def test_removido_na_tela_volta_sozinho(fabrica, tmp_path):
    await local.provisionar(tmp_path)
    antigo = _pedido(tmp_path)["executor_id"]
    (tmp_path / local.CADASTRADO).write_text(json.dumps({"executor_id": antigo}))
    await _marcar(fabrica, antigo, deleted_at=datetime.now(timezone.utc).replace(tzinfo=None))

    assert await local.provisionar(tmp_path) == "pedido"
    assert _pedido(tmp_path)["executor_id"] != antigo


async def test_o_id_cadastrado_vale_mais_que_o_nome(fabrica, tmp_path):
    """Renamed in the UI: still the same executor, found by the id it holds a certificate for."""
    await local.provisionar(tmp_path)
    executor_id = _pedido(tmp_path)["executor_id"]
    (tmp_path / local.CADASTRADO).write_text(json.dumps({"executor_id": executor_id}))
    await _marcar(fabrica, executor_id, status="active", name="Meu executor de testes")

    assert await local.provisionar(tmp_path) == "pronto"
    assert len(await _executores(fabrica)) == 1


async def test_pedido_vencido_ou_de_outro_executor_e_trocado(fabrica, tmp_path):
    await local.provisionar(tmp_path)
    executor_id = _pedido(tmp_path)["executor_id"]

    vencido = {"executor_id": executor_id, "otp": "x" * 43,
               "expira_em": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()}
    (tmp_path / local.PEDIDO).write_text(json.dumps(vencido))
    assert await local.provisionar(tmp_path) == "pedido"
    assert _pedido(tmp_path)["otp"] != vencido["otp"]

    alheio = {**_pedido(tmp_path), "executor_id": "outro"}
    (tmp_path / local.PEDIDO).write_text(json.dumps(alheio))
    assert await local.provisionar(tmp_path) == "pedido"
    assert _pedido(tmp_path)["executor_id"] == executor_id


async def test_arquivo_ilegivel_conta_como_ausente(fabrica, tmp_path):
    (tmp_path / local.PEDIDO).write_text("{meio arquivo")
    (tmp_path / local.CADASTRADO).write_text("[]")
    assert await local.provisionar(tmp_path) == "pedido"
    assert _pedido(tmp_path)["executor_id"]


def test_schema_ausente_diz_o_comando_da_migracao():
    erro = Exception('(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) '
                     '<class \'asyncpg.exceptions.UndefinedTableError\'>: relation "executors" does not exist')
    assert "alembic upgrade head" in local.explicar_erro(erro)


def test_outro_erro_nao_finge_ser_o_schema():
    assert "alembic" not in local.explicar_erro(ConnectionRefusedError("connection refused"))
