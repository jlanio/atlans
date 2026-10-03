# tests/unit/test_contrato_app_executor_constantes.py
"""
Constants mirrored between `app/` and `executor/`.

The executor does not import `app.*` in any file — and that boundary is
deliberate: it runs on-premise, on the customer's machine, and an import from
the server would be deploy coupling. The price is that some constants exist
twice, each with a comment telling you to keep the other in sync.

A comment is not a guard. These constants had ZERO tests comparing the two
sides, or each was tested against its own value — which stays green even after
one diverges. The consequences of each divergence are described in each test;
none of them would show up as an obvious error in production.

What has already left the duplication lives in `flow/` (which ships in both
images) and both sides import from there. For those rules the test checks that
each side uses the single piece: if one of them gets its own copy back, it
breaks here.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re

import pytest

from flow.utils import protocolo_ws as PW


def test_tipos_de_mensagem_assinada_batem_nos_dois_lados():
    """Diverging here turns into a silently discarded command.

    A type that the executor requires signed but the server sends unsigned is
    rejected with no visible error on the server: `revoked`, `shutdown` or
    `purge_artifacts` simply do not happen. The reverse is worse — a type that
    the server signs and the executor does NOT require signed accepts a command
    forged by whoever wins the connection.
    """
    from app.core.control_crypto import SIGNED_MESSAGE_TYPES
    from executor.connection import _SIGNED_SERVER_MESSAGES

    assert SIGNED_MESSAGE_TYPES == _SIGNED_SERVER_MESSAGES, (
        "SIGNED_MESSAGE_TYPES (app/core/control_crypto.py) divergiu de "
        "_SIGNED_SERVER_MESSAGES (executor/connection.py)"
    )


def test_reducao_de_node_event_e_a_mesma_nos_dois_lados():
    """node_event ceiling and reduction: a single rule, in flow/utils/publisher.

    There were two copies. With the executor's ceiling HIGHER than the server's,
    the message arrived large and the server reduced it again (above the frame,
    it closes with 1009 and drops the session). With the same ceiling and
    different rules, the executor delivered the event already reduced and the
    server's rule — the one that preserved `output_columns` — never ran.
    """
    from app.api.routers.executor_ws import resultados
    from executor import connection
    from flow.utils.publisher import reducao

    assert connection.reduzir_node_event is reducao.reduzir_node_event, (
        "o executor voltou a ter a sua propria reducao de node_event"
    )
    assert resultados.reduzir_node_event is reducao.reduzir_node_event, (
        "o servidor voltou a ter a sua propria reducao de node_event"
    )
    assert connection.TETO_NODE_EVENT_BYTES is reducao.TETO_NODE_EVENT_BYTES
    assert resultados.TETO_NODE_EVENT_BYTES is reducao.TETO_NODE_EVENT_BYTES


def test_a_acao_de_purga_que_o_servidor_envia_e_aceita_pelo_executor():
    """The personal-data removal channel has to exist on both sides.

    `_ordenar_remocao_local` sends `action: purge_artifacts` in a `control`. If
    the executor stops recognizing that action, the order is delivered (send_json
    returns True), the server deletes the database row and the file is left
    orphaned on the user's disk — exactly the outcome that code exists to
    prevent, only now invisible.
    """
    from app.core import artifact_cleanup
    from executor.connection import _CONTROL_ACTIONS

    fonte = inspect.getsource(artifact_cleanup._ordenar_remocao_local)
    assert '"purge_artifacts"' in fonte, (
        "o servidor deixou de enviar a acao purge_artifacts"
    )
    assert "purge_artifacts" in _CONTROL_ACTIONS, (
        "o executor deixou de aceitar purge_artifacts — a ordem seria contada "
        "como entregue e o arquivo ficaria orfao"
    )


# ── Vocabulario do protocolo WS (flow/utils/protocolo_ws.py) ─────────────────

def test_vocabulario_do_protocolo_vem_do_modulo_unico():
    """Version, types, stats keys and system_info fields: a single copy.

    Each side declared its own: a literal "1.0" in the executor's handshake
    versus the server's PROTOCOL_VERSION; the `stats` control keys and the
    truncation written twice ("espelha a do executor" — mirrors the executor's);
    the system_info allowlist far from whoever produces the fields; and the
    `error` the server replies with outside the executor's allowlist.
    """
    from app.api.routers import executor_ws_router as rota
    from app.api.routers.executor_ws import protocolo
    from executor import connection

    assert connection.PROTOCOL_VERSION is PW.PROTOCOL_VERSION
    assert rota.PROTOCOL_VERSION is PW.PROTOCOL_VERSION
    assert rota.SUPPORTED_PROTOCOL_VERSIONS is PW.SUPPORTED_PROTOCOL_VERSIONS
    assert PW.PROTOCOL_VERSION in PW.SUPPORTED_PROTOCOL_VERSIONS

    assert connection.TIPOS_DO_SERVIDOR is PW.TIPOS_DO_SERVIDOR
    assert connection.TIPO_ERRO is PW.TIPO_ERRO
    assert rota.TIPO_ERRO is PW.TIPO_ERRO
    assert PW.TIPO_ERRO in PW.TIPOS_DO_SERVIDOR

    assert connection.reduzir_stats is PW.reduzir_stats
    assert protocolo.reduzir_stats is PW.reduzir_stats

    assert protocolo.SYSTEM_INFO_TEXTOS is PW.SYSTEM_INFO_TEXTOS
    assert protocolo.SYSTEM_INFO_NUMEROS is PW.SYSTEM_INFO_NUMEROS
    assert protocolo.SYSTEM_INFO_BOOLEANOS is PW.SYSTEM_INFO_BOOLEANOS


async def test_erro_que_o_servidor_responde_chega_ao_operador_do_executor(monkeypatch, caplog):
    """The server's REAL error response goes through the executor's REAL receive path.

    The server replies `error` to every message it rejects ("evita loop onde
    ele aguarda ACK" — avoids a loop where it waits for an ACK). The executor
    discarded it as "Mensagem desconhecida" (unknown message), at DEBUG: the
    rejection only existed in the server's log, which the executor's operator
    does not see.
    """
    from app.api.routers import executor_ws_router as rota
    from executor.connection import ExecutorConnection

    respostas: list[str] = []
    monkeypatch.setattr(
        rota, "enfileirar_ao_executor", lambda _ws, texto, _eid: respostas.append(texto),
    )
    rota._responder_erro(object(), "ex-1", "invalid_capacity", errors=["queued: negativo (-1)"])
    assert json.loads(respostas[0])["type"] in PW.TIPOS_DO_SERVIDOR

    class _WS:
        def __aiter__(self):
            async def _gen():
                for texto in respostas:
                    yield texto
            return _gen()

        async def send(self, _raw):
            raise AssertionError("resposta de erro nao tem resposta")

    conexao = ExecutorConnection(job_queue=None, result_queue=asyncio.Queue())
    with caplog.at_level(logging.DEBUG, logger="executor.connection"):
        await conexao._receive_loop(_WS())

    avisos = [
        r.getMessage() for r in caplog.records
        if r.name == "executor.connection" and r.levelno == logging.WARNING
    ]
    assert any("invalid_capacity" in a and "queued: negativo" in a for a in avisos), (
        "o executor recebeu a recusa do servidor e nao disse nada ao operador"
    )


async def test_handshake_do_executor_e_aceito_inteiro_pelo_servidor(monkeypatch):
    """The executor's REAL handshake goes through the server's REAL validation.

    A version outside SUPPORTED_PROTOCOL_VERSIONS closes the session with 4426.
    A system_info field outside the allowlist is discarded with a WARNING on
    every connection — and the executors screen shows incomplete hardware.
    """
    from app.api.routers import executor_ws_router as rota
    from app.api.routers.executor_ws import protocolo
    from executor import connection

    class _WS:
        def __init__(self):
            self.enviadas: list[dict] = []

        async def send(self, raw):
            self.enviadas.append(json.loads(raw))

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration  # the server closes right after the handshake

    class _Connect:
        def __init__(self, ws):
            self._ws = ws

        async def __aenter__(self):
            return self._ws

        async def __aexit__(self, *_exc):
            return False

    ws = _WS()
    # local ws:// => no mTLS context.
    monkeypatch.setattr(connection.config, "SERVER_URL", "ws://localhost:8000")
    monkeypatch.setattr(connection.websockets, "connect", lambda *a, **k: _Connect(ws))

    await connection.ExecutorConnection(
        job_queue=None, result_queue=asyncio.Queue(),
    )._connect_and_run()

    handshake = next(m for m in ws.enviadas if m.get("type") == "handshake")
    assert handshake["protocol_version"] in rota.SUPPORTED_PROTOCOL_VERSIONS
    enviado = handshake["system_info"]
    assert set(enviado) == set(
        PW.SYSTEM_INFO_TEXTOS + PW.SYSTEM_INFO_NUMEROS + PW.SYSTEM_INFO_BOOLEANOS
    )
    guardado = protocolo._sanitize_system_info("ex-1", enviado) or {}
    assert set(guardado) == set(enviado), "o servidor descartou campo que o executor manda"


def test_tipos_que_o_executor_envia_sao_os_que_o_servidor_trata():
    """A type that one side sends and the other does not handle vanishes silently.

    That is what happened with `error` in the server → executor direction. In
    the other direction, the server only logs at DEBUG a type outside its dispatch.
    """
    from app.api.routers import executor_ws_router as rota
    from app.api.routers.executor_ws import protocolo
    from executor import connection
    from executor.sync import events as eventos_de_sync

    # The dispatch is the `{tipo: tratador}` table of the receive loop.
    tratados = set(rota._TRATADORES)
    assert tratados == PW.TIPOS_DO_EXECUTOR

    enviados: set[str] = set()
    for modulo in (connection, eventos_de_sync):
        enviados |= set(re.findall(r'"type":\s*"(\w+)"', inspect.getsource(modulo)))
    assert enviados and enviados <= PW.TIPOS_DO_EXECUTOR, (
        f"o executor manda tipo que o servidor nao trata: {enviados - PW.TIPOS_DO_EXECUTOR}"
    )
    assert set(protocolo._REQUIRED_FIELDS) <= PW.TIPOS_DO_EXECUTOR


@pytest.mark.parametrize("chave", PW.CHAVES_DE_CONTROLE_STATS)
def test_chave_de_controle_de_stats_sobrevive_a_truncagem_nos_dois_lados(chave, monkeypatch):
    """Without `__response__` the synchronous webhook's BRPOP hangs until the timeout.

    The `stats` truncation was written twice, each side with its own list of
    control keys: one missing from either list would arrive through one side only.
    """
    from app.api.routers.executor_ws import protocolo
    from executor import connection

    controle = {"ok": True}
    monkeypatch.setattr(connection, "_MAX_WS_PAYLOAD", 4_000)
    monkeypatch.setattr(protocolo, "_MAX_JOB_STATS_BYTES", 4_000)
    stats = {chave: controle, "no-1": "x" * 10_000}

    enviado = json.loads(connection._dumps_result({
        "type": "job_result", "job_id": "j1", "status": "ok", "stats": stats,
    }))["stats"]
    recebido, _ = protocolo._cap_job_result("ex-1", {"job_id": "j1", "status": "ok", "stats": stats})

    for lado in (enviado, recebido["stats"]):
        assert lado[chave] == controle
        assert "no-1" not in lado
        assert lado[PW.STATS_TRUNCADO] is True
