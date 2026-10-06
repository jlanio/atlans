"""`python -m app.cli status`, which scripts/up.sh reads: the schema, the
admins and who of the executors is online, from a real database (SQLite) with a
session that expires its objects on the way out, like app.core.db does.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import JSON, MetaData, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.executor import Executor
from app.models.user import User
from app.services import situacao_instalacao


def _sem_jsonb(tabela):
    copia = tabela.to_metadata(MetaData())
    for coluna in copia.columns:
        if isinstance(coluna.type, JSONB):
            coluna.type = JSON()
    return copia


@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(_sem_jsonb(Executor.__table__).create)
        await conn.run_sync(_sem_jsonb(User.__table__).create)
    fab = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _sessao():
        async with fab() as s:
            try:
                yield s
            finally:
                await s.rollback()

    monkeypatch.setattr("app.core.db.get_session_async", _sessao)
    yield engine, fab
    await engine.dispose()


async def _migrar(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        await conn.execute(text("INSERT INTO alembic_version VALUES ('9ed006ca1660')"))


async def test_sem_schema_diz_que_falta_migrar(banco):
    assert await situacao_instalacao.situacao() == {
        "schema": False, "revisao": None, "admins": 0, "executores": [],
    }


async def test_conta_so_admins_ativos_e_cruza_os_executores_com_a_presenca(banco, monkeypatch):
    engine, fab = banco
    await _migrar(engine)
    async with fab() as s:
        s.add_all([
            User(username="ana", email="ana@x.org", hashed_password="h", role="admin", status="active"),
            User(username="bia", email="bia@x.org", hashed_password="h", role="admin", status="inactive"),
            User(username="caio", email="caio@x.org", hashed_password="h", role="user", status="active"),
            Executor(id_hash="e1", name="Executor local (dev)", status="active"),
            Executor(id_hash="e2", name="Servidor", status="pending"),
        ])
        await s.commit()

    async def presenca(ids):
        assert sorted(ids) == ["e1", "e2"]
        return {"e1": True}
    monkeypatch.setattr(situacao_instalacao, "_presenca", presenca)

    r = await situacao_instalacao.situacao()
    assert r["schema"] is True and r["revisao"] == "9ed006ca1660" and r["admins"] == 1
    assert {e["id"]: (e["nome"], e["status"], e["online"]) for e in r["executores"]} == {
        "e1": ("Executor local (dev)", "active", True),
        "e2": ("Servidor", "pending", False),
    }


async def test_a_linha_json_e_a_que_o_up_sh_le(banco, monkeypatch, capsys):
    """up.sh greps `"schema": true` and the executor entry in this order and format."""
    engine, fab = banco
    await _migrar(engine)
    async with fab() as s:
        s.add(Executor(id_hash="e1", name="Executor local (dev)", status="active"))
        await s.commit()

    async def presenca(ids):
        return {"e1": True}
    monkeypatch.setattr(situacao_instalacao, "_presenca", presenca)
    linha = json.dumps(await situacao_instalacao.situacao(), ensure_ascii=False)
    assert '"schema": true' in linha
    assert '"nome": "Executor local (dev)", "status": "active", "online": true' in linha


async def test_sem_redis_ninguem_esta_online(monkeypatch):
    async def quebra(ids):
        raise ConnectionError("redis fora")
    monkeypatch.setattr(
        "app.core.executor_connections.executor_registry.read_presence_and_capacities", quebra,
    )
    assert await situacao_instalacao._presenca(["e1"]) == {}


def test_create_admin_le_a_senha_da_entrada(monkeypatch):
    """--password-stdin: the password of scripts/up.sh never goes on a command line."""
    from app import cli

    visto = {}

    async def falso(email, password, username):
        visto.update(email=email, password=password)
        return 0
    monkeypatch.setattr(cli, "_create_admin", falso)
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("senha-forte-12345\n"))  # pragma: allowlist secret
    assert cli.main(["create-admin", "--email", "a@x.org", "--password-stdin"]) == 0
    assert visto == {"email": "a@x.org", "password": "senha-forte-12345"}  # pragma: allowlist secret
