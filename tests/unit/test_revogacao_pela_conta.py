"""Suspender ou excluir a conta derruba os executores dela — sem mexer nos
níveis da política dos workspaces.

A revogação de um executor estava escrita em quatro lugares, e a da conta fazia
só o UPDATE do status e a blacklist do cert: a sessão aberta ficava até a vigia
de revogação passar. Agora a conta usa a mesma revogação do DELETE do executor
(status, cert, blacklist, `control: revoked` e close 4403 depois do commit).

O que a conta NÃO faz é tirar o executor dos níveis: ele pode estar no nível
principal de workspaces de outros donos, e esvaziá-lo à força apagava a reserva
e o terminal — o workspace Isolado virava pool compartilhado e a configuração do
dono se perdia, mesmo com a conta reativada depois. Fica no nível, como manda a
spec (executor-isolation-routing §4.4), e o despacho o pula. Tirar dos níveis é
do DELETE do executor e do "revogar todos" do operador.

Banco de verdade (SQLite): o que importa é o que sobra gravado — o nível, o
status, a auditoria.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import JSON, MetaData, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.api_token import ApiToken
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.executor import Executor
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_executor import WorkspaceExecutor
from app.services import admin_user_service, execution_alert_service, executor_enrollment_service
from app.services import executor_service


@asynccontextmanager
async def _banco():
    """SQLite com o que a revogação toca. `executors` usa JSONB, que o SQLite
    não compila: vai uma cópia da tabela com JSON (ver `banco_de_executores`)."""
    executores = Executor.__table__.to_metadata(MetaData())
    for coluna in executores.columns:
        if isinstance(coluna.type, JSONB):
            coluna.type = JSON()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(executores.create)
        await conn.run_sync(Base.metadata.create_all, tables=[
            User.__table__, ApiToken.__table__, Workspace.__table__,
            WorkspaceExecutor.__table__, AuditEvent.__table__,
        ])
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def _semear(Sessao):
    """A conta da ana tem a máquina dela, que é o ÚNICO executor do nível
    principal de ws-1 (da bia) e divide o de ws-2 com outro executor."""
    async with Sessao() as db:
        db.add_all([
            User(id_hash="u-ana", username="ana", email="ana@x.test", hashed_password="x"),
            User(id_hash="u-bia", username="bia", email="bia@x.test", hashed_password="x"),
            Executor(id_hash="ex-ana", name="maquina-da-ana", status="active", cert_serial="S1",
                     public_key="pem", created_by="u-ana"),
            Executor(id_hash="ex-outro", name="outro", status="active", cert_serial="S9",
                     public_key="pem", created_by="u-bia"),
            Workspace(id_hash="ws-1", name="Bacia", owner_id="u-bia"),
            Workspace(id_hash="ws-2", name="Cadastro", owner_id="u-bia"),
            WorkspaceExecutor(workspace_id="ws-1", executor_id="ex-ana", tier=1),
            WorkspaceExecutor(workspace_id="ws-2", executor_id="ex-ana", tier=1),
            WorkspaceExecutor(workspace_id="ws-2", executor_id="ex-outro", tier=1),
        ])
        await db.commit()


@pytest.fixture
def efeitos(monkeypatch):
    """O que sai do banco: blacklist, e-mail aos donos e o WebSocket."""
    registro = MagicMock()
    registro.send_json = AsyncMock(return_value=True)
    registro.disconnect_executor = AsyncMock(return_value=True)
    monkeypatch.setattr(executor_service, "executor_registry", registro, raising=False)
    blacklist = AsyncMock()
    monkeypatch.setattr(executor_enrollment_service, "revoke_cert", blacklist)
    aviso = MagicMock()
    monkeypatch.setattr(execution_alert_service, "notify_primary_emptied_background", aviso)
    return {"registro": registro, "blacklist": blacklist, "aviso": aviso}


async def _suspender(db, ana):
    await admin_user_service.suspend_user(db, ana, motivo="teste", por="adm")


async def _excluir(db, ana):
    await admin_user_service.soft_delete_user(db, ana)


async def _suspender_em_lote(db, ana):
    await admin_user_service.bulk_suspend(db, [ana], motivo="teste", por="adm")


async def _excluir_em_lote(db, ana):
    await admin_user_service.bulk_soft_delete(db, [ana])


ACOES = [
    pytest.param(_suspender, "user_suspended", id="suspender"),
    pytest.param(_excluir, "user_deleted", id="excluir"),
    pytest.param(_suspender_em_lote, "user_suspended", id="suspender-em-lote"),
    pytest.param(_excluir_em_lote, "user_deleted", id="excluir-em-lote"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("acao, motivo", ACOES)
async def test_a_conta_revogada_derruba_o_executor_e_mantem_os_niveis(efeitos, acao, motivo):
    async with _banco() as Sessao:
        await _semear(Sessao)
        async with Sessao() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            await acao(db, ana)

        async with Sessao() as db:
            status, serial = (await db.execute(
                select(Executor.status, Executor.cert_serial).where(Executor.id_hash == "ex-ana")
            )).one()
            niveis = (await db.execute(
                select(WorkspaceExecutor.workspace_id).where(WorkspaceExecutor.executor_id == "ex-ana")
            )).scalars().all()
            auditoria = (await db.execute(
                select(AuditEvent.workspace_id)
                .where(AuditEvent.action == "workspace.executor_policy.member_detached")
            )).all()

    assert (status, serial) == ("revoked", None)
    # Os níveis de ws-1 e ws-2 (da bia) ficam: o despacho pula o executor
    # revogado e segue a cadeia; nada de detach nem de aviso de nível esvaziado.
    assert sorted(niveis) == ["ws-1", "ws-2"]
    assert auditoria == []
    assert all(c.args[0] == [] for c in efeitos["aviso"].call_args_list)

    # A sessão aberta cai na hora, como no DELETE do executor.
    registro = efeitos["registro"]
    registro.send_json.assert_awaited_once()
    destino, mensagem = registro.send_json.await_args.args
    assert destino == "ex-ana"
    assert (mensagem["type"], mensagem["action"]) == ("control", "revoked")
    registro.disconnect_executor.assert_awaited_once_with("ex-ana", code=4403, reason="Operador revogado.")
    efeitos["blacklist"].assert_awaited_once()
    assert efeitos["blacklist"].await_args.args == ("S1",)


@pytest.mark.asyncio
@pytest.mark.parametrize("acao, motivo", ACOES)
async def test_suspender_a_conta_nao_rebaixa_o_workspace_isolado_de_outro_dono(efeitos, acao, motivo):
    """ws-1 (da bia) é Isolado: principal [ex-ana], reserva [ex-outro], terminal
    `fail`. Com o detach forçado da conta, o principal esvaziava, a reserva e o
    terminal eram apagados e o workspace passava a mandar jobs ao pool
    compartilhado."""
    from app.services import workspace_executor_service as politica

    async with _banco() as Sessao:
        await _semear(Sessao)
        async with Sessao() as db:
            db.add(WorkspaceExecutor(workspace_id="ws-1", executor_id="ex-outro", tier=2))
            await db.commit()
        async with Sessao() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            await acao(db, ana)

        async with Sessao() as db:
            niveis = sorted((await db.execute(
                select(WorkspaceExecutor.executor_id, WorkspaceExecutor.tier)
                .where(WorkspaceExecutor.workspace_id == "ws-1")
            )).all())
            politica_ws1 = await politica.load_policy_by_id(db, "ws-1")

    assert niveis == [("ex-ana", 1), ("ex-outro", 2)]
    assert politica_ws1.mode == politica.MODE_ISOLATED


@pytest.mark.asyncio
async def test_revogar_todos_do_operador_tira_dos_niveis_e_avisa_os_donos(efeitos, monkeypatch):
    """O "revogar todos" é ação explícita sobre os executores: como o DELETE
    forçado, sai dos níveis e o dono do nível principal esvaziado é avisado."""
    from types import SimpleNamespace

    from app.api.routers import admin_users_router as R
    from app.core.rate_limiter import limiter

    monkeypatch.setattr(limiter, "enabled", False)
    admin = SimpleNamespace(role="admin", id_hash="u-adm", username="adm")
    async with _banco() as Sessao:
        await _semear(Sessao)
        async with Sessao() as db:
            await R.revoke_all_user_agents(request=None, id_hash="u-ana", db=db, current_user=admin)

        async with Sessao() as db:
            niveis = (await db.execute(
                select(WorkspaceExecutor.workspace_id).where(WorkspaceExecutor.executor_id == "ex-ana")
            )).scalars().all()

    assert niveis == []
    [chamada] = efeitos["aviso"].call_args_list
    assert [d["workspace_id"] for d in chamada.args[0] if d["would_empty_primary"]] == ["ws-1"]
    efeitos["registro"].disconnect_executor.assert_awaited_once_with("ex-ana", code=4403, reason="Operador revogado.")


@pytest.mark.asyncio
async def test_nada_sai_do_banco_se_o_commit_falha(efeitos):
    """Blacklist, e-mail e o close 4403 (terminal para o executor) só depois do
    commit: um rollback não pode deixar o executor derrubado e ativo no banco."""
    async with _banco() as Sessao:
        await _semear(Sessao)
        async with Sessao() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            db.commit = AsyncMock(side_effect=RuntimeError("banco fora"))
            with pytest.raises(RuntimeError):
                await _suspender(db, ana)

    efeitos["registro"].send_json.assert_not_awaited()
    efeitos["registro"].disconnect_executor.assert_not_awaited()
    efeitos["blacklist"].assert_not_awaited()
    efeitos["aviso"].assert_not_called()


# ── O DELETE do executor passa pela mesma revogação ──────────────────────────

async def _revogar_pela_rota(Sessao, *, force):
    from types import SimpleNamespace

    from app.api.routers import executores_router as R

    admin = SimpleNamespace(role="admin", id_hash="u-adm", username="adm")
    async with Sessao() as db:
        ag = (await db.execute(select(Executor).where(Executor.id_hash == "ex-ana"))).scalar_one()
        await R.revoke_executor("ex-ana", force=force, db=db, current_user=admin, ag=ag)


@pytest.mark.asyncio
async def test_delete_do_executor_revoga_como_a_conta(efeitos):
    async with _banco() as Sessao:
        await _semear(Sessao)
        await _revogar_pela_rota(Sessao, force=True)

        async with Sessao() as db:
            status, serial = (await db.execute(
                select(Executor.status, Executor.cert_serial).where(Executor.id_hash == "ex-ana")
            )).one()
            niveis = (await db.execute(
                select(WorkspaceExecutor.workspace_id).where(WorkspaceExecutor.executor_id == "ex-ana")
            )).scalars().all()

    assert (status, serial, niveis) == ("revoked", None, [])
    [chamada] = efeitos["aviso"].call_args_list
    assert chamada.kwargs["executor_name"] == "maquina-da-ana"
    efeitos["registro"].disconnect_executor.assert_awaited_once_with(
        "ex-ana", code=4403, reason="Executor revogado.",
    )
    assert efeitos["registro"].send_json.await_args.args[1]["reason"] == "Executor revogado pelo administrador."


@pytest.mark.asyncio
async def test_delete_sem_force_nao_esvazia_o_nivel_principal(efeitos):
    from app.core.exceptions import WorkspacePolicyConflictError

    async with _banco() as Sessao:
        await _semear(Sessao)
        with pytest.raises(WorkspacePolicyConflictError):
            await _revogar_pela_rota(Sessao, force=False)

        async with Sessao() as db:
            status = (await db.execute(
                select(Executor.status).where(Executor.id_hash == "ex-ana")
            )).scalar_one()

    assert status == "active"
    efeitos["registro"].disconnect_executor.assert_not_awaited()


@pytest.mark.asyncio
async def test_executor_de_outra_conta_nao_e_tocado(efeitos):
    async with _banco() as Sessao:
        await _semear(Sessao)
        async with Sessao() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            await _suspender(db, ana)

        async with Sessao() as db:
            outro = (await db.execute(select(Executor).where(Executor.id_hash == "ex-outro"))).scalar_one()
            nivel = (await db.execute(
                select(WorkspaceExecutor.tier).where(WorkspaceExecutor.executor_id == "ex-outro")
            )).scalars().all()

    assert (outro.status, outro.cert_serial) == ("active", "S9")
    assert nivel == [1]
    assert [c.args[0] for c in efeitos["registro"].disconnect_executor.await_args_list] == ["ex-ana"]
