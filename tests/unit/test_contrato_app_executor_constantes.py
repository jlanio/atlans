# tests/unit/test_contrato_app_executor_constantes.py
"""
Constantes espelhadas entre `app/` e `executor/`.

O executor nao importa `app.*` em nenhum arquivo — e essa fronteira e
deliberada: ele roda on-premise, na maquina do cliente, e um import do servidor
seria acoplamento de deploy. O preco e que algumas constantes existem duas
vezes, cada uma com um comentario mandando manter a outra em sincronia.

Comentario nao e guarda. Estas constantes tinham ZERO teste comparando os dois
lados, ou eram testadas cada uma contra o proprio valor — o que passa verde
mesmo depois de uma divergir. As consequencias de cada divergencia estao
descritas em cada teste; nenhuma delas apareceria como erro obvio em producao.

O que ja saiu da duplicacao mora em `flow/` (que vai nas duas imagens) e os dois
lados importam de la. Para essas regras o teste confere que cada lado usa a
peca unica: se um deles voltar a ter a sua copia, quebra aqui.
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
    """Divergir aqui vira comando silenciosamente descartado.

    Um tipo que o executor exige assinado mas o servidor envia cru e recusado
    sem erro visivel no servidor: `revoked`, `shutdown` ou `purge_artifacts`
    simplesmente nao acontecem. O caminho inverso e pior — um tipo que o
    servidor assina e o executor NAO exige assinado aceita comando forjado por
    quem vencer a conexao.
    """
    from app.core.control_crypto import SIGNED_MESSAGE_TYPES
    from executor.connection import _SIGNED_SERVER_MESSAGES

    assert SIGNED_MESSAGE_TYPES == _SIGNED_SERVER_MESSAGES, (
        "SIGNED_MESSAGE_TYPES (app/core/control_crypto.py) divergiu de "
        "_SIGNED_SERVER_MESSAGES (executor/connection.py)"
    )


def test_reducao_de_node_event_e_a_mesma_nos_dois_lados():
    """Teto e reducao de node_event: uma regra so, em flow/utils/publisher.

    Eram duas copias. Com o teto do executor MAIOR que o do servidor, a
    mensagem chegava grande e o servidor a reduzia de novo (acima do frame, ele
    fecha com 1009 e derruba a sessao). Com o mesmo teto e regras diferentes, o
    executor entregava o evento ja reduzido e a regra do servidor — a que
    preservava `output_columns` — nunca rodava.
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
    """O canal de remocao de dado pessoal tem de existir dos dois lados.

    `_ordenar_remocao_local` manda `action: purge_artifacts` num `control`. Se o
    executor deixar de reconhecer essa acao, a ordem e entregue (o send_json
    devolve True), o servidor apaga a linha do banco e o arquivo fica orfao no
    disco do usuario — exatamente o desfecho que aquele codigo existe para
    evitar, so que agora invisivel.
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
    """Versao, tipos, chaves de stats e campos de system_info: uma copia so.

    Cada lado declarava o seu: "1.0" literal no handshake do executor contra o
    PROTOCOL_VERSION do servidor; as chaves de controle de `stats` e a
    truncagem escritas duas vezes ("espelha a do executor"); a allowlist de
    system_info longe de quem produz os campos; e o `error` que o servidor
    responde fora da allowlist do executor.
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
    """A resposta de erro REAL do servidor passa pelo recebimento REAL do executor.

    O servidor responde `error` a toda mensagem que recusa ("evita loop onde
    ele aguarda ACK"). O executor a descartava como "Mensagem desconhecida", em
    DEBUG: a recusa so existia no log do servidor, que o operador do executor
    nao ve.
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
    """O handshake REAL do executor passa pela validacao REAL do servidor.

    Versao fora de SUPPORTED_PROTOCOL_VERSIONS fecha a sessao com 4426. Campo de
    system_info fora da allowlist e descartado com um WARNING a cada conexao —
    e a tela de executores mostra o hardware incompleto.
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
            raise StopAsyncIteration  # o servidor fecha logo depois do handshake

    class _Connect:
        def __init__(self, ws):
            self._ws = ws

        async def __aenter__(self):
            return self._ws

        async def __aexit__(self, *_exc):
            return False

    ws = _WS()
    # ws:// local => sem contexto mTLS.
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
    """Tipo que um lado manda e o outro nao trata some em silencio.

    Foi o que aconteceu com `error` na direcao servidor → executor. Na outra
    direcao, o servidor so registra em DEBUG um tipo fora do seu despacho.
    """
    from app.api.routers import executor_ws_router as rota
    from app.api.routers.executor_ws import protocolo
    from executor import connection
    from executor.sync import events as eventos_de_sync

    # O despacho é a tabela `{tipo: tratador}` do loop de recebimento.
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
    """Sem `__response__` o BRPOP do webhook sincrono fica preso ate o timeout.

    A truncagem de `stats` era escrita duas vezes, cada lado com a sua lista de
    chaves de controle: a que sumisse de uma delas chegaria so por um lado.
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
