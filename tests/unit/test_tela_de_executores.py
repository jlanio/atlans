"""The executors screen says the same thing on any API worker.

Regression: with `--workers 4`, each executor's WebSocket lives on ONE worker,
and the screen read the capacity and the "connected since" from the LOCAL
registry. 3 out of 4 refreshes (the list re-runs the query every 15 s) showed a
fully loaded executor as idle ("0/4") and one connected for days as "visto há
2 dias" (seen 2 days ago). Cert and operator revocations had the same defect:
they only closed the WebSocket when the admin landed on the worker holding it.

The tests set up two real registries over the same fake Redis — the one of the
worker holding the WebSocket and the one of any other worker — and request the
same route from both. The response has to be identical: the WebSocket's worker
also reads from Redis and the database, not from its own memory.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.routers import executores_router as R
from app.core import executor_connections as ec

from ._mcp_harness import RedisFalso, banco_de_executores
from ._rotas import rotas_efetivas

_AGORA = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
_CONECTOU = _AGORA - timedelta(days=3)


# ── Factories ─────────────────────────────────────────────────────────────────

@pytest.fixture
def redis(monkeypatch):
    rc = RedisFalso()

    async def _get_redis():
        return rc

    monkeypatch.setattr(ec, "_get_redis", _get_redis)
    return rc


def _executor(id_hash: str, *, last_seen_at: datetime | None = None, system_info=None):
    """Database row. `last_seen_at` without a time zone, as the column stores it."""
    return SimpleNamespace(
        id_hash=id_hash, name=id_hash, description=None, status="active",
        executor_type="default", is_default=True, capabilities=[],
        max_concurrent_jobs=4, max_queue_size=50, executor_version="2.0",
        system_info=system_info,
        last_seen_at=last_seen_at.replace(tzinfo=None) if last_seen_at else None,
        created_at=_AGORA.replace(tzinfo=None) - timedelta(days=30), created_by="usr-1",
    )


def _capacidade(running: int, queued: int = 0, **extra) -> dict:
    return {"queued": queued, "running": running, "max_concurrent": 4, "max_queue": 50, **extra}


async def _no_ar(redis, executor_id: str, capacidade: dict, *, conectou_em=_CONECTOU) -> ec.ExecutorConnection:
    """What the WebSocket's worker leaves in Redis — presence and capacity — and
    the connection that only it has."""
    redis.dados[ec._presence_key(executor_id)] = "1"
    await ec._redis_store_capacity(executor_id, capacidade)
    conn = ec.ExecutorConnection(executor_id=executor_id, websocket=MagicMock(), connected_at=conectou_em)
    conn.capacity = dict(capacidade)
    return conn


def _worker(*conexoes: ec.ExecutorConnection) -> ec.ExecutorConnectionRegistry:
    reg = ec.ExecutorConnectionRegistry()
    for conn in conexoes:
        reg._connections[conn.executor_id] = conn
    return reg


async def _listar(monkeypatch, worker, executores) -> dict[str, dict]:
    monkeypatch.setattr(R, "executor_registry", worker)
    monkeypatch.setattr(R.executor_service, "list_agents", AsyncMock(return_value=executores))
    resposta = await R.list_agents(executor_type=None, db=MagicMock(), _=None)
    return {item["id_hash"]: item for item in resposta}


# ── The regression: the same response on any worker ─────────────────────────

@pytest.mark.asyncio
async def test_lista_e_a_mesma_no_worker_do_websocket_e_nos_outros(redis, monkeypatch):
    lotado = _capacidade(4, queued=2, disk_free_gb=120.5, ram_available_gb=7.25)
    # The connection is created a few ms before the handshake stamp in the
    # database: if the WebSocket's worker used its `connected_at`, the responses
    # differed and the row re-rendered on every refresh that landed on a
    # different worker.
    conn = await _no_ar(redis, "ex-1", lotado, conectou_em=_CONECTOU - timedelta(milliseconds=300))
    conn.system_info = {"hostname": "so-na-memoria"}
    executores = [_executor("ex-1", last_seen_at=_CONECTOU,
                            system_info={"hostname": "maq-1", "disk_total_gb": 500})]

    no_worker_do_ws = await _listar(monkeypatch, _worker(conn), executores)
    em_outro_worker = await _listar(monkeypatch, _worker(), executores)

    assert em_outro_worker == no_worker_do_ws
    item = em_outro_worker["ex-1"]
    assert item["online"] is True
    # Before: capacity None outside the WS worker — the gauge showed "0/4".
    assert item["capacity"]["running"] == 4 and item["capacity"]["queued"] == 2
    # Before: connected_at None — the cell fell back to "visto há 3 dias".
    assert datetime.fromisoformat(item["connected_at"]) == _CONECTOU
    # Free disk and RAM also come from the published capacity.
    assert item["system_info"] == {
        "hostname": "maq-1", "disk_total_gb": 500, "disk_free_gb": 120.5, "ram_available_gb": 7.25,
    }


@pytest.mark.asyncio
async def test_offline_nao_mostra_capacidade_que_sobrou_no_redis(redis, monkeypatch):
    """The copy of the capacity in Redis can outlive the presence (the removal on
    unregister failed; the keys expire at different moments): it must not
    show up as the current load of someone who has already left."""
    await ec._redis_store_capacity("ex-caiu", _capacidade(4))   # no presence
    executores = [_executor("ex-caiu", last_seen_at=_CONECTOU)]

    item = (await _listar(monkeypatch, _worker(), executores))["ex-caiu"]

    assert item["online"] is False
    assert item["capacity"] is None
    assert item["connected_at"] is None


@pytest.mark.asyncio
async def test_presenca_e_capacidade_numa_ida_so_ao_redis(redis, monkeypatch):
    """One MGET with both keys of each executor — not one EXISTS and one GET per
    executor —, including the one whose WebSocket is on this worker."""
    local = await _no_ar(redis, "ex-local", _capacidade(1))
    await _no_ar(redis, "ex-a", _capacidade(2))
    await _no_ar(redis, "ex-b", _capacidade(3))
    redis.chamadas.clear()
    ids = ("ex-local", "ex-a", "ex-b")
    executores = [_executor(i, last_seen_at=_CONECTOU) for i in ids]

    itens = await _listar(monkeypatch, _worker(local), executores)

    assert {i: itens[i]["capacity"]["running"] for i in itens} == {"ex-local": 1, "ex-a": 2, "ex-b": 3}
    leituras = [c for c in redis.chamadas if c[0] in ("get", "mget", "exists")]
    chaves = tuple(k for i in ids for k in (ec._presence_key(i), ec._capacity_key(i)))
    assert leituras == [("mget", chaves)]


@pytest.mark.asyncio
async def test_cache_de_presenca_do_worker_nao_vale_para_a_tela(redis, monkeypatch):
    """`is_online` caches "online" for 5 s on a worker: right after the drop,
    that worker showed the executor as up ("no ar há 1 s", "0/4") and the others
    did not. The screen reads presence from Redis, the same for everyone."""
    import time

    await ec._redis_store_capacity("ex-1", _capacidade(2))   # left over; the presence is already gone
    worker = _worker()
    worker._presence_cache["ex-1"] = (True, time.monotonic())
    executores = [_executor("ex-1", last_seen_at=_CONECTOU)]

    item = (await _listar(monkeypatch, worker, executores))["ex-1"]

    assert (item["online"], item["capacity"], item["connected_at"]) == (False, None, None)


@pytest.mark.asyncio
async def test_redis_fora_todos_offline(monkeypatch):
    async def _redis_fora():
        raise ConnectionError("redis fora")

    monkeypatch.setattr(ec, "_get_redis", _redis_fora)
    monkeypatch.setattr(ec, "_reset_redis_singleton", AsyncMock())
    executores = [_executor(i, last_seen_at=_CONECTOU) for i in ("ex-1", "ex-2")]

    itens = await _listar(monkeypatch, _worker(), executores)

    assert {i: (itens[i]["online"], itens[i]["capacity"]) for i in itens} == {
        "ex-1": (False, None), "ex-2": (False, None),
    }


@pytest.mark.asyncio
async def test_sessao_substituida_nao_publica_capacidade_por_cima_da_nova(redis, monkeypatch):
    """The presence renewal discovers that another session is the owner and drops
    this one; publishing the capacity right afterwards overwrote the new
    session's capacity in Redis — on the screen and in dispatch — until it
    rewrote it (30 s)."""
    import json

    antiga = ec.ExecutorConnection(executor_id="ex-1", websocket=MagicMock())
    worker_antigo = _worker(antiga)

    async def _perdeu_a_posse(conn):
        worker_antigo._connections.pop(conn.executor_id, None)   # what unregister does

    worker_antigo._renew_presence_or_drop = _perdeu_a_posse
    await ec._redis_store_capacity("ex-1", _capacidade(1))       # the new session's one

    await worker_antigo.update_capacity("ex-1", _capacidade(3, queued=5))

    assert json.loads(redis.dados[ec._capacity_key("ex-1")])["running"] == 1


@pytest.mark.asyncio
async def test_disco_e_ram_iguais_em_todos_os_workers(redis, monkeypatch):
    """The copy in Redis is only rewritten when the load changes (or every 30 s):
    with the load idle and RAM dropping, the WebSocket's worker read 3.2 GB from
    memory and the others 7.9 GB from Redis — the number changed on every list
    refresh."""
    conn = await _no_ar(redis, "ex-1", _capacidade(2, ram_available_gb=7.9, disk_free_gb=100.0))
    dono = _worker(conn)
    dono._renew_presence_or_drop = AsyncMock()
    for ram in (6.1, 3.2):                          # two reports, same load
        await dono.update_capacity("ex-1", _capacidade(2, ram_available_gb=ram, disk_free_gb=100.0))
    executores = [_executor("ex-1", last_seen_at=_CONECTOU, system_info={"ram_total_gb": 16})]

    no_worker_do_ws = await _listar(monkeypatch, dono, executores)
    em_outro_worker = await _listar(monkeypatch, _worker(), executores)

    assert em_outro_worker == no_worker_do_ws


@pytest.mark.asyncio
async def test_copia_do_redis_e_revalidada_antes_de_ir_para_a_tela(redis, monkeypatch):
    """Redis is not trusted territory: a field outside the contract does not get
    through, an invalid measurement becomes None and an invalid counter discards
    the capacity."""
    import json

    redis.dados[ec._presence_key("ex-1")] = "1"
    redis.dados[ec._presence_key("ex-2")] = "1"
    redis.dados[ec._capacity_key("ex-1")] = json.dumps(
        {**_capacidade(2), "ram_available_gb": "muito", "disk_free_gb": -1, "html": "<b>x</b>"})
    redis.dados[ec._capacity_key("ex-2")] = json.dumps({**_capacidade(2), "running": "dois"})
    executores = [_executor(i, last_seen_at=_CONECTOU, system_info={"hostname": "maq"}) for i in ("ex-1", "ex-2")]

    itens = await _listar(monkeypatch, _worker(), executores)

    assert itens["ex-1"]["capacity"] == {"queued": 0, "running": 2, "max_concurrent": 4, "max_queue": 50,
                                         "disk_free_gb": None, "ram_available_gb": None}
    assert itens["ex-1"]["system_info"] == {"hostname": "maq"}
    assert itens["ex-2"]["capacity"] is None


@pytest.mark.asyncio
async def test_meus_executores_le_de_qualquer_worker(redis, monkeypatch):
    """The non-admin route builds dicts (last_seen_at already in ISO, no time zone)."""
    await _no_ar(redis, "ex-1", _capacidade(2))
    monkeypatch.setattr(R, "executor_registry", _worker())
    monkeypatch.setattr(R.user_executor_service, "get_user_accessible_agents", AsyncMock(return_value=[
        {"id_hash": "ex-1", "last_seen_at": _CONECTOU.replace(tzinfo=None).isoformat()},
        {"id_hash": "ex-2", "last_seen_at": None},
    ]))

    itens = {i["id_hash"]: i for i in await R.my_agents(db=MagicMock(), current_user=SimpleNamespace(id_hash="usr-1"))}

    assert itens["ex-1"]["online"] is True
    assert itens["ex-1"]["capacity"]["running"] == 2
    assert datetime.fromisoformat(itens["ex-1"]["connected_at"]) == _CONECTOU
    assert itens["ex-2"] == {"id_hash": "ex-2", "last_seen_at": None,
                             "online": False, "capacity": None, "connected_at": None}


# ── "Conectado desde" ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("last_seen_at", [
    _CONECTOU.replace(tzinfo=None),                 # database column: UTC without time zone
    _CONECTOU.replace(tzinfo=None).isoformat(),     # dict from `my_agents`
    _CONECTOU,                                      # already with time zone
])
def test_conectado_desde_e_o_last_seen_em_utc(last_seen_at):
    desde = R._conectado_desde(True, last_seen_at)
    assert desde.endswith("+00:00")                 # the front end reads no-time-zone as UTC; with a time zone there is no doubt
    assert datetime.fromisoformat(desde) == _CONECTOU


def test_offline_nao_tem_sessao():
    assert R._conectado_desde(False, _CONECTOU) is None
    assert R._conectado_desde(True, None) is None


@pytest.mark.asyncio
async def test_fim_de_sessao_so_avanca_o_last_seen():
    """The end of a replaced session arrives after the new one's handshake;
    written unconditionally, it erased the new one's "no ar desde" (up since) on
    the other workers."""
    from sqlalchemy import select

    from app.models.executor import Executor
    from app.services.executor_service import registrar_fim_da_sessao

    inicio_da_nova = _CONECTOU.replace(tzinfo=None)
    async with banco_de_executores() as Sessao:
        async with Sessao() as db:
            db.add(Executor(id_hash="ex-1", name="ex-1", last_seen_at=inicio_da_nova))
            await db.commit()

        async def _gravado():
            async with Sessao() as db:
                return (await db.execute(select(Executor.last_seen_at).where(Executor.id_hash == "ex-1"))).scalar_one()

        # The old session ends now, but its last contact is earlier.
        async with Sessao() as db:
            await registrar_fim_da_sessao(db, "ex-1", inicio_da_nova - timedelta(seconds=40))
        assert await _gravado() == inicio_da_nova
        # The end of the current session moves forward.
        async with Sessao() as db:
            await registrar_fim_da_sessao(db, "ex-1", inicio_da_nova + timedelta(hours=5))
        assert await _gravado() == inicio_da_nova + timedelta(hours=5)


# ── Revocations close the WebSocket from any worker ──────────────────────────

def _registro_sem_o_ws():
    """A worker that does NOT hold the WebSocket: `get` does not find the connection."""
    reg = MagicMock()
    reg.get = MagicMock(return_value=None)
    reg.send_json = AsyncMock(return_value=True)
    reg.disconnect_executor = AsyncMock(return_value=True)
    return reg


@pytest.mark.asyncio
async def test_revogar_cert_fecha_o_websocket_em_outro_worker(monkeypatch):
    reg = _registro_sem_o_ws()
    # The notice and the close are those of every revocation (`concluir_revogacoes`).
    monkeypatch.setattr(R.executor_service, "executor_registry", reg)
    monkeypatch.setattr(R.executor_enrollment_service, "revoke_cert", AsyncMock())
    ag = SimpleNamespace(id_hash="ex-1", name="ex-1", cert_serial="abc", cert_expires_at=None)
    db = MagicMock(commit=AsyncMock())

    await R.admin_revoke_cert("ex-1", db=db, current_user=SimpleNamespace(username="adm"), ag=ag)

    assert ag.cert_serial is None
    reg.send_json.assert_awaited_once()
    assert reg.send_json.await_args.args[1]["action"] == "revoked"
    reg.disconnect_executor.assert_awaited_once_with("ex-1", code=4403, reason="Cert revogado.")


@pytest.mark.asyncio
async def test_revogar_cert_fecha_mesmo_se_o_aviso_falhar(monkeypatch):
    reg = _registro_sem_o_ws()
    reg.send_json = AsyncMock(side_effect=RuntimeError("relay fora"))
    monkeypatch.setattr(R.executor_service, "executor_registry", reg)
    monkeypatch.setattr(R.executor_enrollment_service, "revoke_cert", AsyncMock())
    ag = SimpleNamespace(id_hash="ex-1", name="ex-1", cert_serial="abc", cert_expires_at=None)

    await R.admin_revoke_cert("ex-1", db=MagicMock(commit=AsyncMock()),
                              current_user=SimpleNamespace(username="adm"), ag=ag)

    reg.disconnect_executor.assert_awaited_once()


class _RedisDoRelay:
    """What the relay uses from Redis: presence (only that exists) and PUBLISH."""

    def __init__(self):
        self.publicados: list[tuple[str, str]] = []

    async def exists(self, chave):
        return 1 if chave.startswith("executor:presence:") else 0

    async def publish(self, canal, mensagem):
        self.publicados.append((canal, mensagem))
        return 1                                    # the listener of the WebSocket's worker


class _SocketDoExecutor:
    def __init__(self):
        self.escritos: list[str] = []
        self.fechado = None

    async def send_text(self, texto):
        self.escritos.append(texto)

    async def close(self, code=1000, reason=""):
        self.fechado = (code, reason)


@pytest.mark.asyncio
async def test_revogacao_fecha_de_verdade_o_websocket_de_outro_worker(monkeypatch):
    """No fake registry: the route runs on the admin's worker, which does not have
    the WebSocket; what it publishes on the relay reaches the listener of the
    worker that does, and that worker closes the socket with 4403 and removes
    the connection from the registry."""
    rc = _RedisDoRelay()

    async def _get_redis():
        return rc

    monkeypatch.setattr(ec, "_get_redis", _get_redis)
    monkeypatch.setattr(R.executor_enrollment_service, "revoke_cert", AsyncMock())
    ws = _SocketDoExecutor()
    worker_do_ws = _worker(ec.ExecutorConnection(executor_id="ex-1", websocket=ws))
    worker_do_ws.unregister = AsyncMock()
    monkeypatch.setattr(R.executor_service, "executor_registry", _worker())   # the admin's
    monkeypatch.setattr(ec, "executor_registry", worker_do_ws)                # the listener's
    ag = SimpleNamespace(id_hash="ex-1", name="ex-1", cert_serial="abc", cert_expires_at=None)

    try:
        await R.admin_revoke_cert("ex-1", db=MagicMock(commit=AsyncMock()),
                                  current_user=SimpleNamespace(username="adm"), ag=ag)
        assert rc.publicados and {canal for canal, _ in rc.publicados} == {ec._relay_channel("ex-1")}

        for _, envelope in rc.publicados:                            # the listener, in order
            continua = await ec._handle_relay_message("ex-1", ws, "dono", envelope)

        assert continua is False                                     # o marcador de close encerra o listener
        assert ws.fechado == (4403, "Cert revogado.")
        worker_do_ws.unregister.assert_awaited_once_with("ex-1", expected_ws=ws)
    finally:
        ec.encerrar_saida(ws)


@pytest.mark.asyncio
async def test_revogar_operador_fecha_os_websockets_em_outros_workers(monkeypatch):
    from app.api.routers import admin_users_router as A
    from app.core.rate_limiter import limiter
    from app.services import execution_alert_service
    from app.services import workspace_executor_service as politica

    monkeypatch.setattr(limiter, "enabled", False)
    reg = _registro_sem_o_ws()
    reg.send_json = AsyncMock(side_effect=[RuntimeError("relay fora"), True])
    monkeypatch.setattr(R.executor_service, "executor_registry", reg)
    monkeypatch.setattr(R.executor_enrollment_service, "revoke_cert", AsyncMock())
    monkeypatch.setattr(A, "_ensure_admin_can_modify_target", AsyncMock())
    monkeypatch.setattr(A.svc, "get_user", AsyncMock(return_value=SimpleNamespace(id_hash="usr-1", username="ana")))
    monkeypatch.setattr(politica, "workspace_ids_for_executor", AsyncMock(return_value=set()))
    monkeypatch.setattr(politica, "detach_executor", AsyncMock(return_value=[]))
    monkeypatch.setattr(execution_alert_service, "notify_primary_emptied_background", MagicMock())
    executores = [
        SimpleNamespace(id_hash=e, name=e, status="active", cert_serial=f"s-{e}", cert_expires_at=None)
        for e in ("ex-1", "ex-2")
    ]
    linhas = MagicMock()
    linhas.scalars.return_value.all.return_value = executores
    db = MagicMock(execute=AsyncMock(return_value=linhas), commit=AsyncMock())

    resposta = await A.revoke_all_user_agents(
        request=None, id_hash="usr-1", db=db, current_user=SimpleNamespace(username="adm", id_hash="adm-1"),
    )

    assert resposta.agent_ids == ["ex-1", "ex-2"]
    assert [e.status for e in executores] == ["revoked", "revoked"]
    db.commit.assert_awaited_once()
    # The notice to the first one failed; both are closed anyway.
    assert [c.args[0] for c in reg.disconnect_executor.await_args_list] == ["ex-1", "ex-2"]
    assert all(c.kwargs == {"code": 4403, "reason": "Operador revogado."}
               for c in reg.disconnect_executor.await_args_list)


# ── last_seen_at: enrollment writes it; renewal does not (see test_revogacao_de_executor) ──

@pytest.mark.asyncio
async def test_enrollment_grava_last_seen(monkeypatch):
    from app.core import redis as redis_mod
    from app.services import executor_enrollment_service as E

    monkeypatch.setattr(redis_mod, "get_redis_pool", lambda: MagicMock(delete=AsyncMock()))
    antes = _CONECTOU.replace(tzinfo=None)
    ag = SimpleNamespace(id_hash="ex-1", last_seen_at=antes)
    resultado = MagicMock()
    resultado.scalar_one_or_none.return_value = ag
    db = MagicMock(execute=AsyncMock(return_value=resultado), commit=AsyncMock(), refresh=AsyncMock())
    cert = {"serial": "s2", "fingerprint": "f2", "issued_at": _AGORA, "expires_at": _AGORA + timedelta(days=90)}

    await E.attach_cert_to_agent(db, "ex-1", cert)

    assert (ag.cert_serial, ag.status) == ("s2", "active")
    assert ag.last_seen_at > antes


# ── The version declared in the handshake ────────────────────────────────────

@pytest.mark.parametrize("bruta, esperada", [
    ("2.3.1", "2.3.1"),
    ("  2.3.1\n", "2.3.1"),
    ("1.0.0-beta.123456789", "1.0.0-beta.123456789"),   # 20: the column size
    ("1.0.0-beta.1234567890", None),                    # 21: discarded, not truncated
    ("", None),
    ("   ", None),
    ("2.3\x00.1", None),
    (231, None),
    ({"v": "2.3.1"}, None),
    (None, None),
])
def test_versao_do_handshake(bruta, esperada):
    from app.api.routers.executor_ws.protocolo import _sanitize_executor_version

    assert _sanitize_executor_version("ex-1", bruta) == esperada


# ── No partial snapshot of the fleet ─────────────────────────────────────────

def test_rotas_que_so_viam_o_proprio_worker_nao_existem():
    """`GET /executores/connections` and `/ws/executores-status` listed only the
    connections of the worker that served the request: a different slice of the
    fleet on each call. Nothing used them; a dashboard built on top of them
    would lie."""
    from app.main import app

    caminhos = {getattr(rota, "path", None) for rota in rotas_efetivas(app)}
    assert "/executores/connections" not in caminhos
    assert "/ws/executores-status" not in caminhos
    assert not hasattr(ec.executor_registry, "status_summary")
    # The real screen is still there.
    assert {"/executores", "/executores/my", "/executores/{executor_id}"} <= caminhos
