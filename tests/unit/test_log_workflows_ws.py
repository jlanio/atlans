"""Invariantes do WebSocket de eventos do painel de execução.

O laço subscribe → LRANGE → dedup → pub/sub agora vive em
`app/services/run_events_service.py` (`iter_run_events`); o handler
`websocket_workflow` é um cliente dele. Estes testes fixam o que o BROWSER
observa, então exercitam o handler inteiro (handshake + gerador real com Redis
e pub/sub falsos) e continuam cobrindo as regressões da auditoria:

  A10 — replay paginado por índice absoluto perdia eventos quando o LTRIM do
        publicador deslocava a lista entre as páginas;
  A11 — envelope único `{"type":"events",...}` (o marcador `{"type":"live"}`
        deixou de existir e o ao vivo não pode mais se dizer "replay");
  A36 — eventos publicados entre o SUBSCRIBE e o LRANGE chegavam duas vezes;
  A37 — falha real de Redis era logada como "encerrado pelo cliente" e o socket
        fechava com 1000, que o cliente ignora;
  A56 — sessão de banco presa "idle in transaction" durante os sleeps do poll.

O teto de vida do socket (`_WS_MAX_S`), que existe para o assinante órfão de um
run cujo marcador nunca vem, também é observado daqui: ao estourar, fechamento
normal e nenhum frame inventado.
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


# ── Dublês ────────────────────────────────────────────────────────────────────


class FakeWS:
    def __init__(self, *, fechar_apos_frames: int | None = None):
        self.sent: list[str] = []
        self.closes: list[tuple[int, str]] = []
        self.client_state = WebSocketState.CONNECTED
        self.application_state = WebSocketState.CONNECTED
        self._disconnect = asyncio.Event()
        # Simula a aba fechando depois de N frames recebidos.
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
    """`segurar=True` simula um run ainda vivo: o `listen()` nunca termina."""

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

    async def execute(self, *_a, **_kw):  # pragma: no cover - _authorize_run é mockado
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
    """Redis falso no namespace do SERVICE — é lá que o gerador o procura."""
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
    """O handler tem que terminar sozinho; um teste que trava é uma regressão."""
    await asyncio.wait_for(mod.websocket_workflow(ws, run_id), timeout=timeout)


# ── A11: envelope único ───────────────────────────────────────────────────────


def test_batch_frame_usa_envelope_events_com_dropped_sempre():
    frame = json.loads(mod._batch_frame([evento("n1")]))
    assert frame["type"] == "events"
    assert frame["dropped"] == 0
    assert len(frame["events"]) == 1

    frame = json.loads(mod._batch_frame([evento("n1")], 7))
    assert frame["type"] == "events"
    assert frame["dropped"] == 7


# ── A10: replay estável sob LTRIM concorrente ─────────────────────────────────


@pytest.mark.asyncio
async def test_replay_le_o_historico_em_uma_unica_chamada():
    """Uma leitura só: paginar por índice absoluto perde eventos sob LTRIM."""
    historico = [evento(f"n{i}") for i in range(1200)]
    ws = FakeWS()

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        rc, sub_client = _patches_de_redis(stack, historico, FakePubSub([COMPLETE]))
        await _rodar(ws)

    rc.lrange.assert_awaited_once_with("workflow:run-1:history", 0, -1)
    assert sub_client._pubsub.canais == ["workflow:run-1:events"]
    # O ENVIO continua paginado — o ganho de menos frames WS segue de pé:
    # 500 + 500 + 200 do replay e o complete ao vivo.
    assert [len(frame["events"]) for frame in ws.frames()] == [500, 500, 200, 1]
    assert [ev["node"] for ev in ws.eventos()] == (
        [f"n{i}" for i in range(1200)] + [WORKFLOW_COMPLETE_NODE]
    )
    assert sub_client.fechado is True
    assert ws.closes[-1][0] == 1000


@pytest.mark.asyncio
async def test_replay_nao_perde_eventos_quando_a_lista_desliza():
    """Simula o LTRIM do publicador a cada leitura: nada pode ser pulado."""
    historico = [evento(f"n{i}") for i in range(1500)]
    estado = {"lista": list(historico)}

    async def lrange(_key, inicio, fim):
        pagina = estado["lista"][inicio:] if fim == -1 else estado["lista"][inicio:fim + 1]
        # Cada round-trip "custa" um lote do publicador: 300 entram no fim e 300
        # saem do início. Era isto que fazia a paginação por índice absoluto
        # pular eventos em definitivo.
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
    # Se o handler fosse ao vivo ficaria preso aqui e o `_rodar` estouraria.
    pubsub = FakePubSub([evento("n-fantasma")], segurar=True)

    with ExitStack() as stack:
        _patches_de_handshake(stack)
        _, sub_client = _patches_de_redis(stack, [evento("n1"), COMPLETE, evento("n2")], pubsub)
        await _rodar(ws)

    assert [ev["node"] for ev in ws.eventos()] == ["n1", WORKFLOW_COMPLETE_NODE]
    assert sub_client.fechado is True
    assert ws.closes[-1][0] == 1000


# ── A36: dedup da fronteira replay ↔ ao vivo ──────────────────────────────────


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
    # A `n8` repetida DEPOIS da fronteira é legítima e tem que passar.
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
    # Todo frame ao vivo usa o MESMO envelope do replay (A11).
    assert all(frame["type"] == "events" for frame in ws.frames())
    assert all("dropped" in frame for frame in ws.frames())


# ── Coalescing, descarte e heartbeat ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_frames_coalescidos_carregam_o_dropped_do_buffer():
    """Browser lento: stdout cai primeiro, o ciclo de vida chega e `dropped` conta."""
    lifecycle = lambda n: json.dumps({"node": n, "kind": "lifecycle", "status": "completed"})
    mensagens = [evento("s1"), evento("s2"), lifecycle("n1"), lifecycle("n2"), COMPLETE]
    ws = FakeWS()

    # O pub/sub falso entrega tudo sem ceder o laço: o produtor enche o buffer
    # antes de o consumidor drenar.
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
    # Fecha a aba depois de dois heartbeats — é o `watch_close` que encerra.
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
    """Run vivo e mudo: sem o leitor do socket o handler ficaria preso até o fim."""
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
    """A56: sem o rollback a sessão fica `idle in transaction` durante o sleep."""
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
    # Todo sleep é precedido imediatamente por um rollback.
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
    """A37: pool ausente com socket vivo é erro do servidor, não close."""
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
    # 1000 é ignorado pelo cliente: o painel ficaria "Executando" para sempre.
    assert ws.closes[-1][0] == 4500
    assert any("Erro no WebSocket do workflow" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_aba_fechada_durante_o_envio_e_encerramento_normal(caplog):
    """RuntimeError do Starlette com socket já morto NÃO vira 4500."""
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
    """`_WS_MAX_S`: assinante órfão de um run que nunca publica o marcador.

    O laço antigo não tinha teto — o socket vivia até o `__workflow_complete__`
    ou até a aba fechar, e um consumer morto o deixava preso para sempre. Ao
    estourar o teto o handler encerra como encerramento NORMAL (1000, que a UI
    trata reabrindo) e sem inventar frame nenhum: nada foi publicado, nada é
    enviado — nem um heartbeat, que só sai quando o prazo ainda permite.
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
