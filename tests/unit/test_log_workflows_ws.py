"""Invariants of the run panel's events WebSocket.

The subscribe → LRANGE → dedup → pub/sub loop now lives in
`app/services/run_events_service.py` (`iter_run_events`); the
`websocket_workflow` handler is a client of it. These tests pin what the BROWSER
observes, so they exercise the whole handler (handshake + real generator with fake
Redis and pub/sub) and keep covering the audit's regressions:

  A10 — replay paginated by absolute index lost events when the publisher's
        LTRIM shifted the list between pages;
  A11 — single `{"type":"events",...}` envelope (the `{"type":"live"}` marker
        no longer exists and live can no longer claim to be "replay");
  A36 — events published between SUBSCRIBE and LRANGE arrived twice;
  A37 — a real Redis failure was logged as "encerrado pelo cliente" (closed by the
        client) and the socket closed with 1000, which the client ignores;
  A56 — database session stuck "idle in transaction" during the poll's sleeps.

The socket's lifetime ceiling (`_WS_MAX_S`), which exists for the orphaned subscriber
of a run whose marker never comes, is also observed from here: when it is exceeded,
a normal close and no invented frame.
"""
import asyncio
import json
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocketState

from app.api.routers import log_workflows_router as mod
from app.core.constants import WORKFLOW_COMPLETE_NODE
from app.services import run_events_service as svc


# ── Test doubles ──────────────────────────────────────────────────────────────


class FakeWS:
    def __init__(self, *, fechar_apos_frames: int | None = None):
        self.sent: list[str] = []
        self.closes: list[tuple[int, str]] = []
        self.client_state = WebSocketState.CONNECTED
        self.application_state = WebSocketState.CONNECTED
        self._disconnect = asyncio.Event()
        # Simulates the tab closing after N frames received.
        self._fechar_apos_frames = fechar_apos_frames

    async def send_text(self, text: str) -> None:
        self.sent.append(text)
        if self._fechar_apos_frames is not None and len(self.sent) >= self._fechar_apos_frames:
            self._disconnect.set()

    async def receive(self) -> dict:
        await self._disconnect.wait()
        return {"type": "websocket.disconnect"}

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closes.append((code, reason))
        self.client_state = WebSocketState.DISCONNECTED
        self.application_state = WebSocketState.DISCONNECTED

    def frames(self) -> list[dict]:
        return [json.loads(raw) for raw in self.sent]

    def eventos(self) -> list[dict]:
        return [ev for frame in self.frames() for ev in frame["events"]]


class FakePubSub:
    """`segurar=True` simulates a run still alive: `listen()` never ends."""

    def __init__(self, mensagens: list[str], *, segurar: bool = False):
        self._mensagens = mensagens
        self._segurar = segurar
        self.canais: list[str] = []

    async def subscribe(self, canal: str) -> None:
        self.canais.append(canal)

    async def listen(self):
        for raw in self._mensagens:
            yield {"type": "message", "data": raw}
        if self._segurar:
            await asyncio.Event().wait()


class _PubSubCtx:
    def __init__(self, pubsub):
        self._pubsub = pubsub

    async def __aenter__(self):
        return self._pubsub

    async def __aexit__(self, *_):
        return False


class FakeSubClient:
    def __init__(self, pubsub):
        self._pubsub = pubsub
        self.fechado = False

    def pubsub(self):
        return _PubSubCtx(self._pubsub)

    async def aclose(self):
        self.fechado = True


def evento(node: str, texto: str = "") -> str:
    return json.dumps({"node": node, "kind": "stdout", "msg": texto})


COMPLETE = json.dumps({"node": WORKFLOW_COMPLETE_NODE, "status": "success"})


class _FakeDB:
    def __init__(self):
        self.eventos: list[str] = []

    async def execute(self, *_a, **_kw):  # pragma: no cover - _authorize_run is mocked
        self.eventos.append("execute")
        return MagicMock()

    async def rollback(self):
        self.eventos.append("rollback")


def _patches_de_handshake(stack, autorizado=(True, True), db=None):
    import app.core.db as core_db

    usuario = MagicMock()
    usuario.id_hash = "usr-1"
    sessao = db if db is not None else _FakeDB()

    class _SessCtx:
        async def __aenter__(self_):
            return sessao

        async def __aexit__(self_, *_):
            return False

    stack.enter_context(patch.object(mod, "ws_authenticate", AsyncMock(return_value=usuario)))
    stack.enter_context(patch.object(mod, "check_ws_rate_limit", AsyncMock(return_value=True)))
    stack.enter_context(patch.object(core_db, "get_session_async", lambda: _SessCtx()))
    stack.enter_context(
        patch.object(mod, "_authorize_run", AsyncMock(return_value=autorizado))
    )
    return sessao


def _patches_de_redis(stack, historico, pubsub: FakePubSub) -> tuple[MagicMock, FakeSubClient]:
    """Fake Redis in the SERVICE's namespace — that is where the generator looks it up."""
    rc = MagicMock()
    rc.lrange = AsyncMock(
        side_effect=historico if callable(historico) else None,
        return_value=None if callable(historico) else list(historico),
    )
    sub_client = FakeSubClient(pubsub)
    stack.enter_context(patch.object(svc, "new_pubsub_client", lambda: sub_client))
    stack.enter_context(patch.object(svc, "get_redis_pool", return_value=rc))
    return rc, sub_client


async def _rodar(ws: FakeWS, run_id: str = "run-1", timeout: float = 3.0) -> None:
    """The handler has to end on its own; a test that hangs is a regression."""
    await asyncio.wait_for(mod.websocket_workflow(ws, run_id), timeout=timeout)


# ── A11: single envelope ──────────────────────────────────────────────────────


def test_batch_frame_usa_envelope_events_com_dropped_sempre():
    frame = json.loads(mod._batch_frame([evento("n1")]))
    assert frame["type"] == "events"
    assert frame["dropped"] == 0
    assert len(frame["events"]) == 1

    frame = json.loads(mod._batch_frame([evento("n1")], 7))
    assert frame["type"] == "events"
    assert frame["dropped"] == 7


# ── A10: stable replay under concurrent LTRIM ─────────────────────────────────


@pytest.mark.asyncio
async def test_replay_le_o_historico_em_uma_unica_chamada():
    """A single read: paginating by absolute index loses events under LTRIM."""
    historico = [evento(f"n{i}") for i in range(1200)]
    ws = FakeWS()

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        rc, sub_client = _patches_de_redis(stack, historico, FakePubSub([COMPLETE]))
        await _rodar(ws)

    rc.lrange.assert_awaited_once_with("workflow:run-1:history", 0, -1)
    assert sub_client._pubsub.canais == ["workflow:run-1:events"]
    # SENDING is still paginated — the gain of fewer WS frames still stands:
    # 500 + 500 + 200 from the replay and the live complete.
    assert [len(frame["events"]) for frame in ws.frames()] == [500, 500, 200, 1]
    assert [ev["node"] for ev in ws.eventos()] == (
        [f"n{i}" for i in range(1200)] + [WORKFLOW_COMPLETE_NODE]
    )
    assert sub_client.fechado is True
    assert ws.closes[-1][0] == 1000


@pytest.mark.asyncio
async def test_replay_nao_perde_eventos_quando_a_lista_desliza():
    """Simulates the publisher's LTRIM on each read: nothing may be skipped."""
    historico = [evento(f"n{i}") for i in range(1500)]
    estado = {"lista": list(historico)}

    async def lrange(_key, inicio, fim):
        pagina = estado["lista"][inicio:] if fim == -1 else estado["lista"][inicio:fim + 1]
        # Each round-trip "costs" one publisher batch: 300 come in at the end and 300
        # leave from the start. This is what made pagination by absolute index
        # skip events permanently.
        estado["lista"] = estado["lista"][300:] + [evento(f"novo{i}") for i in range(300)]
        return pagina

    ws = FakeWS()
    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _patches_de_redis(stack, lrange, FakePubSub([COMPLETE]))
        await _rodar(ws)

    nodes = [ev["node"] for ev in ws.eventos()]
    assert nodes == [f"n{i}" for i in range(1500)] + [WORKFLOW_COMPLETE_NODE]


@pytest.mark.asyncio
async def test_replay_corta_no_marcador_de_conclusao_e_nao_vai_ao_vivo():
    ws = FakeWS()
    # If the handler went live it would get stuck here and `_rodar` would time out.
    pubsub = FakePubSub([evento("n-fantasma")], segurar=True)

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _, sub_client = _patches_de_redis(stack, [evento("n1"), COMPLETE, evento("n2")], pubsub)
        await _rodar(ws)

    assert [ev["node"] for ev in ws.eventos()] == ["n1", WORKFLOW_COMPLETE_NODE]
    assert sub_client.fechado is True
    assert ws.closes[-1][0] == 1000


# ── A36: dedup at the replay ↔ live boundary ──────────────────────────────────


@pytest.mark.asyncio
async def test_stream_live_descarta_eventos_ja_enviados_no_replay():
    duplicados = [evento("n8", "linha"), evento("n8", "linha"), evento("n9")]
    novos = [evento("n10"), evento("n8", "linha")]
    ws = FakeWS()

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _patches_de_redis(stack, duplicados, FakePubSub([*duplicados, *novos, COMPLETE]))
        await _rodar(ws)

    replay, ao_vivo = ws.frames()[0], ws.frames()[1:]
    assert [ev["node"] for ev in replay["events"]] == ["n8", "n8", "n9"]
    recebidos = [ev for frame in ao_vivo for ev in frame["events"]]
    assert [ev["node"] for ev in recebidos] == [
        "n10", "n8", WORKFLOW_COMPLETE_NODE,
    ]
    # The `n8` repeated AFTER the boundary is legitimate and has to pass.
    assert recebidos[1]["msg"] == "linha"


@pytest.mark.asyncio
async def test_stream_live_sem_dedup_entrega_tudo():
    ws = FakeWS()

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _patches_de_redis(stack, [], FakePubSub([evento("n1"), evento("n2"), COMPLETE]))
        await _rodar(ws)

    assert [ev["node"] for ev in ws.eventos()] == [
        "n1", "n2", WORKFLOW_COMPLETE_NODE,
    ]
    # Every live frame uses the SAME envelope as the replay (A11).
    assert all(frame["type"] == "events" for frame in ws.frames())
    assert all("dropped" in frame for frame in ws.frames())


# ── Coalescing, descarte e heartbeat ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_frames_coalescidos_carregam_o_dropped_do_buffer():
    """Browser lento: stdout cai primeiro, o ciclo de vida chega e `dropped` conta."""
    lifecycle = lambda n: json.dumps({"node": n, "kind": "lifecycle", "status": "completed"})
    mensagens = [evento("s1"), evento("s2"), lifecycle("n1"), lifecycle("n2"), COMPLETE]
    ws = FakeWS()

    # The fake pub/sub delivers everything without yielding the loop: the producer fills
    # the buffer before the consumer drains it.
    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _patches_de_redis(stack, [], FakePubSub(mensagens))
        stack.enter_context(patch.object(svc, "_QUEUE_MAXSIZE", 3))
        await _rodar(ws)

    assert len(ws.frames()) == 1
    assert ws.frames()[0]["dropped"] == 2
    assert [ev["node"] for ev in ws.eventos()] == ["n1", "n2", WORKFLOW_COMPLETE_NODE]


@pytest.mark.asyncio
async def test_canal_quieto_manda_lote_vazio_de_heartbeat():
    # Closes the tab after two heartbeats — it is `watch_close` that ends it.
    ws = FakeWS(fechar_apos_frames=2)
    real = svc.iter_run_events

    def com_heartbeat_curto(run_id, **kw):
        return real(run_id, heartbeat_s=0.01, **kw)

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _, sub_client = _patches_de_redis(stack, [], FakePubSub([], segurar=True))
        stack.enter_context(patch.object(mod, "iter_run_events", com_heartbeat_curto))
        await _rodar(ws)

    assert len(ws.frames()) >= 2
    assert all(frame == {"type": "events", "dropped": 0, "events": []} for frame in ws.frames())
    assert sub_client.fechado is True


@pytest.mark.asyncio
async def test_watch_close_encerra_o_laco_quando_a_aba_fecha():
    """Live and silent run: without the socket reader the handler would be stuck until the end."""
    ws = FakeWS()

    async def fechar_aba():
        await asyncio.sleep(0.02)
        ws._disconnect.set()

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _, sub_client = _patches_de_redis(stack, [evento("n1")], FakePubSub([], segurar=True))
        fechamento = asyncio.create_task(fechar_aba())
        await _rodar(ws)
        await fechamento

    assert [ev["node"] for ev in ws.eventos()] == ["n1"]
    assert sub_client.fechado is True
    assert ws.closes[-1][0] == 1000


# ── Endpoint: fechamentos, A37 e A56 ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_handshake_libera_a_conexao_do_pool_antes_de_dormir():
    """A56: without the rollback the session stays `idle in transaction` during the sleep."""
    db = _FakeDB()
    ws = FakeWS()
    dormidas: list[float] = []

    async def fake_sleep(segundos):
        dormidas.append(segundos)
        db.eventos.append("sleep")

    with ExitStack() as stack:
        _patches_de_handshake(stack, autorizado=(False, False), db=db)
        stack.enter_context(patch.object(asyncio, "sleep", fake_sleep))
        await mod.websocket_workflow(ws, "run-1")

    assert len(dormidas) == mod._WS_POLL_ATTEMPTS - 1
    # Every sleep is immediately preceded by a rollback.
    for indice, marca in enumerate(db.eventos):
        if marca == "sleep":
            assert db.eventos[indice - 1] == "rollback"
    assert ws.closes[-1][0] == 4404


@pytest.mark.asyncio
async def test_run_de_outro_workspace_fecha_com_4403():
    ws = FakeWS()
    with ExitStack() as stack:
        _patches_de_handshake(stack, autorizado=(True, False))
        chamado = stack.enter_context(patch.object(mod, "iter_run_events"))
        await _rodar(ws)

    assert ws.closes[-1][0] == 4403
    assert ws.sent == []
    chamado.assert_not_called()


@pytest.mark.asyncio
async def test_erro_na_verificacao_de_acesso_fecha_com_4500():
    ws = FakeWS()
    with ExitStack() as stack:
        _patches_de_handshake(stack)
        stack.enter_context(
            patch.object(mod, "_authorize_run", AsyncMock(side_effect=RuntimeError("db fora")))
        )
        await _rodar(ws)

    assert ws.closes[-1] == (4500, "Erro interno na verificação de acesso.")


@pytest.mark.asyncio
async def test_falha_de_redis_nao_e_confundida_com_aba_fechada(caplog):
    """A37: a missing pool with a live socket is a server error, not a close."""
    ws = FakeWS()
    sub_client = FakeSubClient(FakePubSub([]))

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        stack.enter_context(patch.object(svc, "new_pubsub_client", lambda: sub_client))
        stack.enter_context(
            patch.object(
                svc, "get_redis_pool",
                MagicMock(side_effect=RuntimeError("Redis pool não inicializado.")),
            )
        )
        with caplog.at_level("ERROR"):
            await _rodar(ws)

    assert sub_client.fechado is True
    # 1000 is ignored by the client: the panel would stay "Executando" (running) forever.
    assert ws.closes[-1][0] == 4500
    assert any("Erro no WebSocket do workflow" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_aba_fechada_durante_o_envio_e_encerramento_normal(caplog):
    """Starlette's RuntimeError with an already-dead socket does NOT become 4500."""
    from starlette.websockets import WebSocketDisconnect

    ws = FakeWS()

    async def send_text(_texto):
        ws.client_state = WebSocketState.DISCONNECTED
        raise WebSocketDisconnect(1001)

    ws.send_text = send_text
    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _, sub_client = _patches_de_redis(stack, [evento("n1")], FakePubSub([], segurar=True))
        with caplog.at_level("ERROR"):
            await _rodar(ws)

    assert sub_client.fechado is True
    assert ws.closes == []
    assert not any("Erro no WebSocket" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_endpoint_nao_emite_mais_o_marcador_live():
    """A11: o marcador `{"type":"live"}` deixou de existir."""
    ws = FakeWS()

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _patches_de_redis(stack, [evento("n1"), COMPLETE], FakePubSub([]))
        await _rodar(ws)

    assert all(frame["type"] == "events" for frame in ws.frames())
    assert '"live"' not in "".join(ws.sent)
    assert ws.closes[-1][0] == 1000


@pytest.mark.asyncio
async def test_teto_de_vida_do_socket_fecha_normal_e_sem_frames_extras():
    """`_WS_MAX_S`: orphaned subscriber of a run that never publishes the marker.

    The old loop had no ceiling — the socket lived until `__workflow_complete__`
    or until the tab closed, and a dead consumer left it stuck forever. When the
    ceiling is exceeded the handler ends with a NORMAL close (1000, which the UI
    handles by reopening) and without inventing any frame: nothing was published,
    nothing is sent — not even a heartbeat, which only goes out while the deadline still allows.
    """
    ws = FakeWS()

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _, sub_client = _patches_de_redis(stack, [], FakePubSub([], segurar=True))
        stack.enter_context(patch.object(mod, "_WS_MAX_S", 0.05))
        await _rodar(ws)

    assert ws.sent == []
    assert ws.closes[-1] == (1000, "")
    assert sub_client.fechado is True
