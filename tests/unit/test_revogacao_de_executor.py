"""Revoking an executor actually takes effect.

Two loopholes:

- A cert renewal in progress undid a cert-only revocation. The renewal
  authenticates at the start of the request, waits for step-ca to sign and
  writes the new serial unconditionally: a revocation that came in during that
  window (`cert_serial=None`) was overwritten by a new, valid cert.
- mTLS is only checked on connect. If the revocation's close notice got lost
  (Redis restarting, listener reconnecting), the revoked session stayed alive —
  receiving jobs — until it reconnected.
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

from ._mcp_harness import executors_db

_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
_SEEN = datetime(2026, 9, 26, 8, 0)          # UTC column without time zone


def _cert(serial: str = "S2") -> dict:
    return {"serial": serial, "fingerprint": f"fp-{serial}", "issued_at": _NOW,
            "expires_at": _NOW + timedelta(days=90)}


async def _executor(SessionMaker, **campos):
    dados = {"id_hash": "ex-1", "name": "ex-1", "status": "active", "cert_serial": "S1", "last_seen_at": _SEEN}
    async with SessionMaker() as db:
        db.add(Executor(**{**dados, **campos}))
        await db.commit()


async def _row(SessionMaker):
    async with SessionMaker() as db:
        return (await db.execute(
            select(Executor.status, Executor.cert_serial, Executor.cert_fingerprint_sha256, Executor.last_seen_at)
            .where(Executor.id_hash == "ex-1")
        )).one()


# ── Renewal does not undo the revocation ─────────────────────────────────────

@pytest.mark.asyncio
async def test_renewal_writes_the_new_cert_without_touching_status_or_last_seen():
    async with executors_db() as SessionMaker:
        await _executor(SessionMaker)

        async with SessionMaker() as db:
            assert await E.renovar_cert_do_executor(db, "ex-1", "S1", _cert()) is True

        assert tuple(await _row(SessionMaker)) == ("active", "S2", "fp-S2", _SEEN)


@pytest.mark.asyncio
@pytest.mark.parametrize("revogacao", [
    {"cert_serial": None},                          # only the cert (admin_revoke_cert)
    {"cert_serial": None, "status": "revoked"},     # o executor inteiro (revoke_executor)
])
async def test_revocation_during_renewal_prevails(revogacao):
    """The race, in the order it happens in production: the renewal loads the
    executor in mTLS, the admin revokes while step-ca signs, and only then does
    the renewal write."""
    async with executors_db() as SessionMaker:
        await _executor(SessionMaker)
        renovacao = SessionMaker()
        apresentado = (await renovacao.execute(select(Executor).where(Executor.id_hash == "ex-1"))).scalar_one()
        async with SessionMaker() as admin:
            alvo = (await admin.execute(select(Executor).where(Executor.id_hash == "ex-1"))).scalar_one()
            for campo, valor in revogacao.items():
                setattr(alvo, campo, valor)
            await admin.commit()

        renovou = await E.renovar_cert_do_executor(renovacao, "ex-1", apresentado.cert_serial, _cert())
        await renovacao.close()

        assert renovou is False
        status, serial, _, _ = await _row(SessionMaker)
        assert serial is None                       # before: "S2", a new, valid cert
        assert status == revogacao.get("status", "active")


@pytest.mark.asyncio
async def test_two_parallel_renewals_only_one_wins():
    async with executors_db() as SessionMaker:
        await _executor(SessionMaker)

        async with SessionMaker() as db:
            primeira = await E.renovar_cert_do_executor(db, "ex-1", "S1", _cert("S2"))
        async with SessionMaker() as db:
            segunda = await E.renovar_cert_do_executor(db, "ex-1", "S1", _cert("S3"))

        assert (primeira, segunda) == (True, False)
        assert (await _row(SessionMaker))[1] == "S2"


@pytest.mark.asyncio
async def test_without_presented_serial_does_not_renew():
    async with executors_db() as SessionMaker:
        await _executor(SessionMaker, cert_serial=None)

        async with SessionMaker() as db:
            assert await E.renovar_cert_do_executor(db, "ex-1", None, _cert()) is False

        assert (await _row(SessionMaker))[1] is None


def _renewal_route(monkeypatch, *, renovou: bool):
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
async def test_route_renews_via_compare_and_swap(monkeypatch):
    executor, revoga, renova = _renewal_route(monkeypatch, renovou=True)
    db = MagicMock()

    resposta = await R.agent_renew_cert(request=None, payload=SimpleNamespace(csr_pem="csr"), db=db, executor=executor)

    assert resposta.serial == "S2"
    assert renova.await_args.args[:3] == (db, "ex-1", "S1")
    assert [c.args[0] for c in revoga.await_args_list] == ["S1"]     # only the old one goes to the blacklist


@pytest.mark.asyncio
async def test_route_discards_the_new_cert_if_the_executor_changed(monkeypatch):
    executor, revoga, _ = _renewal_route(monkeypatch, renovou=False)

    with pytest.raises(HTTPException) as erro:
        await R.agent_renew_cert(request=None, payload=SimpleNamespace(csr_pem="csr"), db=MagicMock(), executor=executor)

    assert erro.value.status_code == 409
    # The old one and also the freshly issued one: mTLS would already reject the
    # new one (its serial is not in the database); the blacklist is belt and braces.
    assert [c.args[0] for c in revoga.await_args_list] == ["S1", "S2"]


def test_renewal_has_per_executor_limit():
    from app.core.rate_limiter import limiter

    limites = limiter._route_limits["app.api.routers.executores_router.agent_renew_cert"]
    assert sorted(str(limite.limit) for limite in limites) == ["30 per 1 day", "6 per 1 hour"]
    assert all(limite.key_func is R._executor_key_from_mtls for limite in limites)


def test_limit_key_is_the_cert_cn():
    with_cert = SimpleNamespace(
        headers={"x-forwarded-tls-client-cert-info": 'Subject="CN=executor-ex-1";SerialNumber="123"'},
        client=SimpleNamespace(host="10.0.0.9"),
    )
    without_cert = SimpleNamespace(headers={}, client=SimpleNamespace(host="10.0.0.9"))

    assert R._executor_key_from_mtls(with_cert) == "cert:executor-ex-1"
    assert R._executor_key_from_mtls(without_cert) == "10.0.0.9"


# ── The open session of a revoked executor is dropped ────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("campos, motivo", [
    ({}, None),
    ({"cert_serial": "S2"}, None),                            # renewed: the session that renewed carries on
    ({"cert_serial": None}, "Cert revogado."),
    ({"status": "revoked", "cert_serial": None}, "Executor revogado."),
    ({"deleted_at": datetime(2026, 9, 27, 9, 0)}, "Executor removido."),
])
async def test_revocation_reason(campos, motivo):
    async with executors_db() as SessionMaker:
        await _executor(SessionMaker, **campos)

        async with SessionMaker() as db:
            assert await motivo_da_revogacao(db, "ex-1") == motivo


@pytest.mark.asyncio
async def test_missing_executor_has_no_valid_session():
    async with executors_db() as SessionMaker:
        async with SessionMaker() as db:
            assert await motivo_da_revogacao(db, "ex-sumiu") == "Executor removido."


class _Socket:
    def __init__(self):
        self.fechado = None

    async def close(self, code=1000, reason=""):
        self.fechado = (code, reason)


def _watcher_without_wait(monkeypatch, motivos):
    """The real watcher, without the interval and without a database: `motivos` is
    what the check returns on each round (an exception simulates the database being down)."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _session():
        yield None

    monkeypatch.setattr(WS, "_REVOGACAO_INTERVALO", 0)
    monkeypatch.setattr(WS, "get_session_async", _session)
    conferencia = AsyncMock(side_effect=motivos)
    monkeypatch.setattr(WS, "motivo_da_revogacao", conferencia)
    return conferencia


@pytest.mark.asyncio
async def test_watcher_closes_with_4403_when_revoked():
    import app.core.executor_connections as ec

    ws = _Socket()
    with pytest.MonkeyPatch.context() as monkeypatch:
        conferencia = _watcher_without_wait(monkeypatch, [None, None, "Cert revogado."])
        try:
            await WS._watch_revocation("ex-1", ws)
        finally:
            ec.encerrar_saida(ws)

    assert ws.fechado == (4403, "Cert revogado.")
    assert conferencia.await_count == 3


@pytest.mark.asyncio
async def test_watcher_does_not_drop_the_session_with_the_db_down():
    """A database blip would drop the live sessions of the whole fleet: it waits
    for the next round."""
    import app.core.executor_connections as ec

    ws = _Socket()
    avisos = []
    with pytest.MonkeyPatch.context() as monkeypatch:
        _watcher_without_wait(monkeypatch, [ConnectionError("banco fora"), None, "Executor revogado."])
        monkeypatch.setattr(WS.logger, "warning", lambda msg, *args: avisos.append(msg % args))
        try:
            await WS._watch_revocation("ex-1", ws)
        finally:
            ec.encerrar_saida(ws)

    assert any("conferência de revogação falhou" in a for a in avisos)
    assert ws.fechado == (4403, "Executor revogado.")
