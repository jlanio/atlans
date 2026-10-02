"""Revogar um executor vale de verdade.

Duas brechas:

- Uma renovação de cert em andamento desfazia a revogação só do cert. A
  renovação autentica no início do request, espera o step-ca assinar e grava o
  serial novo sem condição: a revogação que entrasse nessa janela
  (`cert_serial=None`) era sobrescrita por um cert novo e válido.
- O mTLS só é conferido ao conectar. Se o aviso de fechamento da revogação se
  perdesse (Redis reiniciando, listener reconectando), a sessão revogada seguia
  viva — recebendo jobs — até reconectar.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.routers import executor_ws_router as WS
from app.api.routers import executores_router as R
from app.models.executor import Executor
from app.services import executor_enrollment_service as E
from app.services.executor_service import motivo_da_revogacao

from ._mcp_harness import banco_de_executores

_AGORA = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
_VISTO = datetime(2026, 9, 26, 8, 0)          # coluna em UTC sem fuso


def _cert(serial: str = "S2") -> dict:
    return {"serial": serial, "fingerprint": f"fp-{serial}", "issued_at": _AGORA,
            "expires_at": _AGORA + timedelta(days=90)}


async def _executor(Sessao, **campos):
    dados = {"id_hash": "ex-1", "name": "ex-1", "status": "active", "cert_serial": "S1", "last_seen_at": _VISTO}
    async with Sessao() as db:
        db.add(Executor(**{**dados, **campos}))
        await db.commit()


async def _linha(Sessao):
    async with Sessao() as db:
        return (await db.execute(
            select(Executor.status, Executor.cert_serial, Executor.cert_fingerprint_sha256, Executor.last_seen_at)
            .where(Executor.id_hash == "ex-1")
        )).one()


# ── A renovação não desfaz a revogação ───────────────────────────────────────

@pytest.mark.asyncio
async def test_renovacao_grava_o_cert_novo_sem_mexer_em_status_nem_last_seen():
    async with banco_de_executores() as Sessao:
        await _executor(Sessao)

        async with Sessao() as db:
            assert await E.renovar_cert_do_executor(db, "ex-1", "S1", _cert()) is True

        assert tuple(await _linha(Sessao)) == ("active", "S2", "fp-S2", _VISTO)


@pytest.mark.asyncio
@pytest.mark.parametrize("revogacao", [
    {"cert_serial": None},                          # só o cert (admin_revoke_cert)
    {"cert_serial": None, "status": "revoked"},     # o executor inteiro (revoke_executor)
])
async def test_revogacao_durante_a_renovacao_prevalece(revogacao):
    """A corrida, na ordem em que acontece em produção: a renovação carrega o
    executor no mTLS, o admin revoga enquanto o step-ca assina, e só então a
    renovação grava."""
    async with banco_de_executores() as Sessao:
        await _executor(Sessao)
        renovacao = Sessao()
        apresentado = (await renovacao.execute(select(Executor).where(Executor.id_hash == "ex-1"))).scalar_one()
        async with Sessao() as admin:
            alvo = (await admin.execute(select(Executor).where(Executor.id_hash == "ex-1"))).scalar_one()
            for campo, valor in revogacao.items():
                setattr(alvo, campo, valor)
            await admin.commit()

        renovou = await E.renovar_cert_do_executor(renovacao, "ex-1", apresentado.cert_serial, _cert())
        await renovacao.close()

        assert renovou is False
        status, serial, _, _ = await _linha(Sessao)
        assert serial is None                       # antes: "S2", um cert novo e válido
        assert status == revogacao.get("status", "active")


@pytest.mark.asyncio
async def test_duas_renovacoes_em_paralelo_so_uma_vale():
    async with banco_de_executores() as Sessao:
        await _executor(Sessao)

        async with Sessao() as db:
            primeira = await E.renovar_cert_do_executor(db, "ex-1", "S1", _cert("S2"))
        async with Sessao() as db:
            segunda = await E.renovar_cert_do_executor(db, "ex-1", "S1", _cert("S3"))

        assert (primeira, segunda) == (True, False)
        assert (await _linha(Sessao))[1] == "S2"


@pytest.mark.asyncio
async def test_sem_serial_apresentado_nao_renova():
    async with banco_de_executores() as Sessao:
        await _executor(Sessao, cert_serial=None)

        async with Sessao() as db:
            assert await E.renovar_cert_do_executor(db, "ex-1", None, _cert()) is False

        assert (await _linha(Sessao))[1] is None


def _rota_de_renovacao(monkeypatch, *, renovou: bool):
    from app.core.rate_limiter import limiter

    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(R.executor_enrollment_service, "parse_and_validate_csr", MagicMock())
    cert = {**_cert(), "cert_pem": "c", "chain_pem": "ch", "ca_pem": "ca"}
    monkeypatch.setattr(R.executor_enrollment_service, "sign_csr_via_stepca", AsyncMock(return_value=cert))
    revoga = AsyncMock()
    monkeypatch.setattr(R.executor_enrollment_service, "revoke_cert", revoga)
    renova = AsyncMock(return_value=renovou)
    monkeypatch.setattr(R.executor_enrollment_service, "renovar_cert_do_executor", renova)
    monkeypatch.setattr(R, "get_server_signing_public_key_b64", lambda: "chave")
    executor = SimpleNamespace(id_hash="ex-1", cert_serial="S1", cert_expires_at=None)
    return executor, revoga, renova


@pytest.mark.asyncio
async def test_rota_renova_pelo_compare_and_swap(monkeypatch):
    executor, revoga, renova = _rota_de_renovacao(monkeypatch, renovou=True)
    db = MagicMock()

    resposta = await R.agent_renew_cert(request=None, payload=SimpleNamespace(csr_pem="csr"), db=db, executor=executor)

    assert resposta.serial == "S2"
    assert renova.await_args.args[:3] == (db, "ex-1", "S1")
    assert [c.args[0] for c in revoga.await_args_list] == ["S1"]     # só o antigo vai para a blacklist


@pytest.mark.asyncio
async def test_rota_descarta_o_cert_novo_se_o_executor_mudou(monkeypatch):
    executor, revoga, _ = _rota_de_renovacao(monkeypatch, renovou=False)

    with pytest.raises(HTTPException) as erro:
        await R.agent_renew_cert(request=None, payload=SimpleNamespace(csr_pem="csr"), db=MagicMock(), executor=executor)

    assert erro.value.status_code == 409
    # O antigo e também o recém-emitido: o mTLS já recusaria o novo (o serial
    # dele não está no banco), a blacklist é o cinto duplo.
    assert [c.args[0] for c in revoga.await_args_list] == ["S1", "S2"]


def test_renovacao_tem_limite_por_executor():
    from app.core.rate_limiter import limiter

    limites = limiter._route_limits["app.api.routers.executores_router.agent_renew_cert"]
    assert sorted(str(limite.limit) for limite in limites) == ["30 per 1 day", "6 per 1 hour"]
    assert all(limite.key_func is R._chave_do_executor_no_mtls for limite in limites)


def test_chave_do_limite_e_o_cn_do_cert():
    com_cert = SimpleNamespace(
        headers={"x-forwarded-tls-client-cert-info": 'Subject="CN=executor-ex-1";SerialNumber="123"'},
        client=SimpleNamespace(host="10.0.0.9"),
    )
    sem_cert = SimpleNamespace(headers={}, client=SimpleNamespace(host="10.0.0.9"))

    assert R._chave_do_executor_no_mtls(com_cert) == "cert:executor-ex-1"
    assert R._chave_do_executor_no_mtls(sem_cert) == "10.0.0.9"


# ── A sessão aberta de um executor revogado cai ──────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("campos, motivo", [
    ({}, None),
    ({"cert_serial": "S2"}, None),                            # renovado: a sessão que renovou segue
    ({"cert_serial": None}, "Cert revogado."),
    ({"status": "revoked", "cert_serial": None}, "Executor revogado."),
    ({"deleted_at": datetime(2026, 9, 27, 9, 0)}, "Executor removido."),
])
async def test_motivo_da_revogacao(campos, motivo):
    async with banco_de_executores() as Sessao:
        await _executor(Sessao, **campos)

        async with Sessao() as db:
            assert await motivo_da_revogacao(db, "ex-1") == motivo


@pytest.mark.asyncio
async def test_executor_inexistente_nao_tem_sessao_valida():
    async with banco_de_executores() as Sessao:
        async with Sessao() as db:
            assert await motivo_da_revogacao(db, "ex-sumiu") == "Executor removido."


class _Socket:
    def __init__(self):
        self.fechado = None

    async def close(self, code=1000, reason=""):
        self.fechado = (code, reason)


def _vigia_sem_espera(monkeypatch, motivos):
    """A vigia de verdade, sem o intervalo e sem banco: `motivos` é o que a
    conferência devolve a cada volta (uma exceção simula o banco fora)."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _sessao():
        yield None

    monkeypatch.setattr(WS, "_REVOGACAO_INTERVALO", 0)
    monkeypatch.setattr(WS, "get_session_async", _sessao)
    conferencia = AsyncMock(side_effect=motivos)
    monkeypatch.setattr(WS, "motivo_da_revogacao", conferencia)
    return conferencia


@pytest.mark.asyncio
async def test_vigia_fecha_com_4403_quando_revogam():
    import app.core.executor_connections as ec

    ws = _Socket()
    with pytest.MonkeyPatch.context() as monkeypatch:
        conferencia = _vigia_sem_espera(monkeypatch, [None, None, "Cert revogado."])
        try:
            await WS._vigiar_revogacao("ex-1", ws)
        finally:
            ec.encerrar_saida(ws)

    assert ws.fechado == (4403, "Cert revogado.")
    assert conferencia.await_count == 3


@pytest.mark.asyncio
async def test_vigia_nao_derruba_a_sessao_com_o_banco_fora():
    """Um blip do banco derrubaria as sessões vivas da frota inteira: fica para
    a próxima volta."""
    import app.core.executor_connections as ec

    ws = _Socket()
    avisos = []
    with pytest.MonkeyPatch.context() as monkeypatch:
        _vigia_sem_espera(monkeypatch, [ConnectionError("banco fora"), None, "Executor revogado."])
        monkeypatch.setattr(WS.logger, "warning", lambda msg, *args: avisos.append(msg % args))
        try:
            await WS._vigiar_revogacao("ex-1", ws)
        finally:
            ec.encerrar_saida(ws)

    assert any("conferência de revogação falhou" in a for a in avisos)
    assert ws.fechado == (4403, "Executor revogado.")
