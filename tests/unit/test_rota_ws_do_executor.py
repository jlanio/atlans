# tests/unit/test_rota_ws_do_executor.py
"""The executor's WebSocket route reaches the real handler.

A helper inserted between `@router.websocket(...)` and `agent_websocket` stole
the route: FastAPI started validating the handshake against the helper's
signature (required `corpo`), closed every connection with 1008 before the accept
and the executor — which treats HTTP statuses as non-terminal on purpose —
reconnected forever. No test went through the route; this one does.
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.routers import executor_ws_router as R
from app.core import executor_connections as ec

from ._rotas import effective_routes


def test_the_route_points_to_the_executor_handler():
    [rota] = [r for r in R.router.routes if getattr(r, "path", "") == "/ws/executores/{executor_id}"]
    assert rota.endpoint is R.agent_websocket


def test_handshake_reaches_the_handler_authentication(monkeypatch):
    """Without the Traefik cert the handler accepts and closes with 44xx (the
    authoritative deny). With the stolen route, it closed with 1008 before getting here."""
    from app.api import dependencies

    chamou = []

    async def _deny(**kwargs):
        chamou.append(kwargs["expected_executor_id"])
        raise dependencies.ExecutorMtlsError("missing_cert", "sem certificado")

    @asynccontextmanager
    async def _session():
        yield None

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _deny)
    monkeypatch.setattr(R, "get_session_async", _session)
    fim = AsyncMock()
    monkeypatch.setattr(R, "registrar_fim_da_sessao", fim)
    app = FastAPI()
    app.include_router(R.router)
    outboxes_before = len(ec._outboxes)

    with TestClient(app) as cliente:
        with pytest.raises(WebSocketDisconnect) as fechou:
            with cliente.websocket_connect("/ws/executores/ex-1") as ws:
                ws.receive_text()

    assert chamou == ["ex-1"]
    assert fechou.value.code == 4401
    fim.assert_not_awaited()                     # rejected is not a session: no "visto há" (seen ago)
    # The close creates the socket's (closing) outbox; the deny does not have the
    # handler's `finally`, so it removes it from the map itself — it holds the ws,
    # and the WeakKeyDictionary alone would never release it.
    assert len(ec._outboxes) == outboxes_before


def test_no_app_route_points_to_a_private_function():
    """The whole class of the bug: a helper `_x` written between the decorator and
    the handler becomes the endpoint, and nothing breaks until someone calls the route."""
    from app.main import app

    privadas = [
        (getattr(rota, "path", "?"), rota.endpoint.__name__)
        for rota in effective_routes(app)
        if getattr(getattr(rota, "endpoint", None), "__name__", "").startswith("_")
    ]
    assert privadas == []


class _Registro:
    """The minimum of the registry that the handler uses — without Redis."""

    def __init__(self):
        self.conexoes = {}
        self.eventos = []

    async def register(self, executor_id, ws, executor_version=None, **_k):
        self.conexoes[executor_id] = SimpleNamespace(
            handshake_received=False, websocket=ws, executor_version=executor_version,
            last_seen_at=datetime.now(timezone.utc),
        )
        self.eventos.append("register")
        self.ws = ws

    def get(self, executor_id):
        return self.conexoes.get(executor_id)

    async def update_last_seen(self, executor_id):
        self.eventos.append("vivo")
        if executor_id in self.conexoes:
            self.conexoes[executor_id].last_seen_at = datetime.now(timezone.utc)

    async def update_capacity(self, executor_id, capacidade):
        self.eventos.append("capacity")

    async def unregister(self, executor_id, expected_ws=None):
        self.eventos.append("unregister")
        self.conexoes.pop(executor_id, None)


def test_executor_session_passes_ack_and_inventory_through_the_drainer(monkeypatch):
    """A whole session through the real handler: handshake, ack, inventory and
    disconnect. The ack and the inventory (new in this protocol) reach their
    processors through the connection's drainer."""
    from app.api import dependencies
    from app.api.routers.executor_ws import inbox as IB

    registro = _Registro()
    processed = []

    async def _authenticate(**_k):
        return SimpleNamespace(executor_version="1.0", max_concurrent_jobs=4, max_queue_size=10)

    # The handshake writes the version to the database (see the tests at the end of the file).
    _, banco = _executor_db()

    @asynccontextmanager
    async def _session():
        yield banco

    async def _ack(executor_id, job_id, status):
        processed.append(("ack", executor_id, job_id))

    async def _inventory(executor_id, msg):
        processed.append(("inventario", executor_id, tuple(msg["ativos"])))

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _authenticate)
    monkeypatch.setattr(R, "get_session_async", _session)
    monkeypatch.setattr(R, "update_agent_last_seen", AsyncMock())
    monkeypatch.setattr(R, "executor_registry", registro)
    monkeypatch.setattr(R, "_fail_orphan_runs_if_gone", AsyncMock())
    monkeypatch.setattr("app.core.artifact_cleanup.purgar_pendentes_do_executor", AsyncMock(return_value=0))
    monkeypatch.setattr(IB, "_record_job_ack", _ack)
    monkeypatch.setattr(IB, "_reconciliar_inventario", _inventory)
    # While the teardown drains the queue (up to 10 s), the connection stays
    # registered and the relay listener alive: the socket outbox must already be closing.
    closing_during_drain = []
    drenagem = R._encerrar_drenagem

    async def _drain(*args):
        saida = ec._outboxes.get(registro.ws)
        closing_during_drain.append(saida is not None and saida.fechando)
        return await drenagem(*args)

    monkeypatch.setattr(R, "_encerrar_drenagem", _drain)
    app = FastAPI()
    app.include_router(R.router)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            ws.send_json({"type": "ack", "job_id": "j1", "status": "enqueued"})
            ws.send_json({"type": "inventario", "ativos": ["j1"], "resultados": [], "truncado": False})
            ws.send_json({"type": "heartbeat"})
            _wait_for(lambda: len(processed) == 2)
            # The executor disconnects. Wait for the handler's teardown IN HERE: on
            # leaving the context the TestClient cancels the app's task right away,
            # and the teardown could be cut in the middle (the test failed under load).
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)

    assert processed == [("ack", "ex-1", "j1"), ("inventario", "ex-1", ("j1",))]
    assert registro.eventos[0] == "register" and registro.eventos[-1] == "unregister"
    assert closing_during_drain == [True]
    assert registro.ws not in ec._outboxes          # and leaves the map at the end of the handler


def _wait_for(condicao, timeout_s: float = 5.0) -> None:
    fim = time.monotonic() + timeout_s
    while not condicao():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        time.sleep(0.01)


# ── The end of the session is recorded ───────────────────────────────────────
# `last_seen_at` stopped at the handshake: the screen showed an executor that
# was up for three days and dropped ten minutes ago as "visto há 3 dias" (seen 3 days ago).

def _app_with_session(monkeypatch, visto, banco=None, fim=None):
    """The real handler with fake registry and database: `visto` plays the role of
    `update_agent_last_seen` (session start), `fim` that of
    `registrar_fim_da_sessao` and `banco` is what the session delivers."""
    from app.api import dependencies

    registro = _Registro()

    async def _authenticate(**_k):
        return SimpleNamespace(executor_version="1.0", max_concurrent_jobs=4, max_queue_size=10)

    @asynccontextmanager
    async def _session():
        yield banco

    orfaos = AsyncMock()
    monkeypatch.setattr(dependencies, "validate_executor_mtls", _authenticate)
    monkeypatch.setattr(R, "get_session_async", _session)
    monkeypatch.setattr(R, "update_agent_last_seen", visto)
    monkeypatch.setattr(R, "registrar_fim_da_sessao", fim or AsyncMock())
    monkeypatch.setattr(R, "executor_registry", registro)
    monkeypatch.setattr(R, "_fail_orphan_runs_if_gone", orfaos)
    monkeypatch.setattr("app.core.artifact_cleanup.purgar_pendentes_do_executor", AsyncMock(return_value=0))
    app = FastAPI()
    app.include_router(R.router)
    return app, registro, orfaos


def test_session_end_writes_the_last_contact_after_unregister(monkeypatch):
    eventos = []

    async def _seen(db, executor_id):
        eventos.append(("inicio", executor_id))

    async def _on_done(db, executor_id, seen_at):
        eventos.append(("fim", executor_id, seen_at))

    _, banco = _executor_db()
    app, registro, orfaos = _app_with_session(monkeypatch, _seen, banco=banco, fim=_on_done)
    registro.eventos = eventos      # a single timeline
    erros = []
    monkeypatch.setattr(R.logger, "error", lambda msg, *args: erros.append(msg % args))

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            _wait_for(lambda: "vivo" in eventos)       # the handshake was processed
            conn = registro.conexoes["ex-1"]
            last_contact = conn.last_seen_at
            conn.last_seen_at = last_contact - timedelta(minutes=2)   # the sign of life precedes the teardown
            ws.close()
            _wait_for(lambda: eventos and eventos[-1][0] == "fim")

    # Session start, and the end after the presence is removed. The session ended
    # through the executor's close, not through an error midway.
    assert eventos[0] == "register" and eventos[1] == ("inicio", "ex-1")
    assert eventos[-2] == "unregister"
    _, executor_id, seen_at = eventos[-1]
    assert executor_id == "ex-1"
    # The session's last contact, in the UTC column without time zone — not the teardown instant.
    assert seen_at == (last_contact - timedelta(minutes=2)).replace(tzinfo=None)
    assert erros == []
    orfaos.assert_called_once_with("ex-1")


@pytest.mark.parametrize("falha", ["erro", "demora"])
def test_session_end_without_db_does_not_hold_the_teardown(monkeypatch, falha):
    """Database down: the stamp gives up (with a deadline) and the orphan check was
    already scheduled before it."""
    async def _on_done(db, executor_id, seen_at):
        if falha == "erro":
            raise RuntimeError("banco fora")
        await asyncio.sleep(60)

    monkeypatch.setattr(R, "_FIM_DA_SESSAO_TIMEOUT", 0.05)
    avisos = []
    monkeypatch.setattr(R.logger, "warning", lambda msg, *args: avisos.append(msg % args))
    app, registro, orfaos = _app_with_session(monkeypatch, AsyncMock(), fim=_on_done)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.close()
            _wait_for(lambda: any("fim da sessão não gravado" in a for a in avisos))

    assert "unregister" in registro.eventos
    orfaos.assert_called_once_with("ex-1")


# ── Version and system_info go to the database on the handshake ──────────────
# The screen reads both from the database. The version stayed only in the
# connection (memory of the WebSocket worker), and the "versão" column showed "—"
# for every executor.

def _executor_db():
    ag = SimpleNamespace(system_info=None, executor_version=None)
    resultado = SimpleNamespace(scalar_one_or_none=lambda: ag)
    return ag, SimpleNamespace(execute=AsyncMock(return_value=resultado), commit=AsyncMock())


def test_handshake_writes_version_and_system_info_to_the_db(monkeypatch):
    ag, banco = _executor_db()
    app, registro, _ = _app_with_session(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": " 2.3.1 ", "protocol_version": "1.0",
                          "system_info": {"hostname": "maq-1", "cpu_cores": 8}})
            _wait_for(lambda: ag.executor_version is not None)
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)

    assert ag.executor_version == "2.3.1"
    assert ag.system_info == {"hostname": "maq-1", "cpu_cores": 8.0}
    assert registro.conexoes == {} and banco.commit.await_count >= 1


def test_invalid_version_neither_goes_to_the_db_nor_drops_the_connection(monkeypatch):
    """Larger than the column, it would blow up the UPDATE in the middle of the
    receive loop — and the error closed the connection."""
    ag, banco = _executor_db()
    app, registro, _ = _app_with_session(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "9" * 40, "protocol_version": "1.0"})
            ws.send_json({"type": "heartbeat"})
            _wait_for(lambda: registro.eventos.count("vivo") == 2)   # handshake e heartbeat: seguiu viva
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)

    assert ag.executor_version is None
    banco.execute.assert_not_awaited()                        # nada a gravar


def test_invalid_version_does_not_block_the_system_info(monkeypatch):
    """The bad version is discarded and the database keeps the last good one; the
    rest of the handshake is written normally."""
    ag, banco = _executor_db()
    ag.executor_version = "2.3.0"
    app, registro, _ = _app_with_session(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": {"v": 2}, "protocol_version": "1.0",
                          "system_info": {"hostname": "maq-1"}})
            _wait_for(lambda: ag.system_info is not None)
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)

    assert (ag.executor_version, ag.system_info) == ("2.3.0", {"hostname": "maq-1"})


def test_register_does_not_receive_the_previous_session_version(monkeypatch):
    """The database now stores the version: passed to register, it went to the
    connection log and to the connections status until the handshake — the one
    from the previous session, which may predate an update."""
    from app.api import dependencies

    app, registro, _ = _app_with_session(monkeypatch, AsyncMock(), banco=_executor_db()[1])

    async def _authenticate(**_k):
        return SimpleNamespace(executor_version="1.9.0", max_concurrent_jobs=4, max_queue_size=10)

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _authenticate)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            _wait_for(lambda: "register" in registro.eventos)
            version_at_register = registro.conexoes["ex-1"].executor_version
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)

    assert version_at_register is None



def test_only_the_first_handshake_writes_to_the_db(monkeypatch):
    """A repeated handshake was a SELECT + UPDATE on every message, unbounded,
    and could change the system_info only in this worker's memory."""
    ag, banco = _executor_db()
    app, registro, _ = _app_with_session(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.3.1", "protocol_version": "1.0",
                          "system_info": {"hostname": "maq-1"}})
            for i in range(3):
                ws.send_json({"type": "handshake", "executor_version": f"9.9.{i}", "protocol_version": "1.0",
                              "system_info": {"hostname": f"outra-{i}"}})
            ws.send_json({"type": "heartbeat"})
            _wait_for(lambda: registro.eventos.count("vivo") >= 5)   # 4 handshakes + 1 heartbeat
            conn = registro.conexoes["ex-1"]
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)

    assert banco.execute.await_count == 1
    assert (ag.executor_version, ag.system_info) == ("2.3.1", {"hostname": "maq-1"})
    assert (conn.executor_version, conn.system_info) == ("2.3.1", {"hostname": "maq-1"})


# ── Revoked with the session open ────────────────────────────────────────────

def test_revoked_executor_session_drops_with_4403(monkeypatch):
    """The watcher in the real handler: revoked with the session open — and the
    relay notice lost —, the executor receives close 4403 (terminal for it) and
    the teardown runs. Before, the session stayed alive until it reconnected."""
    app, registro, orfaos = _app_with_session(monkeypatch, AsyncMock(), banco=_executor_db()[1])
    monkeypatch.setattr(R, "_REVOGACAO_INTERVALO", 0.01)
    conferencia = AsyncMock(side_effect=[None, "Cert revogado."])
    monkeypatch.setattr(R, "motivo_da_revogacao", conferencia)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            with pytest.raises(WebSocketDisconnect) as fechou:
                ws.receive_text()
            # The executor answers the close. In the TestClient that is what delivers the
            # disconnect to the app's pending receive (in uvicorn the server's close
            # already ends it); leaving the context earlier would cancel the app's
            # task in the middle of the teardown.
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)

    assert fechou.value.code == 4403
    assert conferencia.await_count == 2
    orfaos.assert_called_once_with("ex-1")


def test_valid_session_is_not_dropped_by_the_watcher(monkeypatch):
    app, registro, _ = _app_with_session(monkeypatch, AsyncMock(), banco=_executor_db()[1])
    monkeypatch.setattr(R, "_REVOGACAO_INTERVALO", 0.01)
    conferencia = AsyncMock(return_value=None)
    monkeypatch.setattr(R, "motivo_da_revogacao", conferencia)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            _wait_for(lambda: conferencia.await_count >= 3)
            ws.send_json({"type": "heartbeat"})
            _wait_for(lambda: registro.eventos.count("vivo") == 2)   # seguiu viva
            ws.close()
            _wait_for(lambda: "unregister" in registro.eventos)
