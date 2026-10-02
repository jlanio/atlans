# tests/unit/test_rota_ws_do_executor.py
"""A rota WebSocket do executor chega ao handler de verdade.

Um helper inserido entre `@router.websocket(...)` e `agent_websocket` roubou a
rota: o FastAPI passou a validar o handshake contra a assinatura do helper
(`corpo` obrigatório), fechava toda conexão com 1008 antes do accept e o
executor — que trata status HTTP como não-terminal de propósito — reconectava
para sempre. Nenhum teste passava pela rota; este passa.
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

from ._rotas import rotas_efetivas


def test_a_rota_aponta_para_o_handler_do_executor():
    [rota] = [r for r in R.router.routes if getattr(r, "path", "") == "/ws/executores/{executor_id}"]
    assert rota.endpoint is R.agent_websocket


def test_handshake_chega_a_autenticacao_do_handler(monkeypatch):
    """Sem o cert do Traefik o handler aceita e fecha com 44xx (o deny
    autoritativo). Com a rota roubada, fechava com 1008 antes de chegar aqui."""
    from app.api import dependencies

    chamou = []

    async def _nega(**kwargs):
        chamou.append(kwargs["expected_executor_id"])
        raise dependencies.ExecutorMtlsError("missing_cert", "sem certificado")

    @asynccontextmanager
    async def _sessao():
        yield None

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _nega)
    monkeypatch.setattr(R, "get_session_async", _sessao)
    fim = AsyncMock()
    monkeypatch.setattr(R, "registrar_fim_da_sessao", fim)
    app = FastAPI()
    app.include_router(R.router)
    saidas_antes = len(ec._saidas)

    with TestClient(app) as cliente:
        with pytest.raises(WebSocketDisconnect) as fechou:
            with cliente.websocket_connect("/ws/executores/ex-1") as ws:
                ws.receive_text()

    assert chamou == ["ex-1"]
    assert fechou.value.code == 4401
    fim.assert_not_awaited()                     # recusado não é sessão: nada de "visto há"
    # O close cria a saída (fechando) do socket; o deny não tem o `finally` do
    # handler, então a tira do mapa ele mesmo — ela segura o ws, e o
    # WeakKeyDictionary sozinho nunca a soltaria.
    assert len(ec._saidas) == saidas_antes


def test_nenhuma_rota_do_app_aponta_para_funcao_privada():
    """A classe inteira do bug: um helper `_x` escrito entre o decorator e o
    handler vira o endpoint, e nada quebra até alguém chamar a rota."""
    from app.main import app

    privadas = [
        (getattr(rota, "path", "?"), rota.endpoint.__name__)
        for rota in rotas_efetivas(app)
        if getattr(getattr(rota, "endpoint", None), "__name__", "").startswith("_")
    ]
    assert privadas == []


class _Registro:
    """O mínimo do registry que o handler usa — sem Redis."""

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


def test_sessao_do_executor_passa_ack_e_inventario_pela_drenadora(monkeypatch):
    """Uma sessão inteira pelo handler de verdade: handshake, ack, inventário e
    desconexão. O ack e o inventário (novos neste protocolo) chegam aos seus
    processadores pela drenadora da conexão."""
    from app.api import dependencies
    from app.api.routers.executor_ws import inbox as IB

    registro = _Registro()
    processados = []

    async def _autentica(**_k):
        return SimpleNamespace(executor_version="1.0", max_concurrent_jobs=4, max_queue_size=10)

    # O handshake grava a versão no banco (ver os testes do fim do arquivo).
    _, banco = _banco_do_executor()

    @asynccontextmanager
    async def _sessao():
        yield banco

    async def _ack(executor_id, job_id, status):
        processados.append(("ack", executor_id, job_id))

    async def _inventario(executor_id, msg):
        processados.append(("inventario", executor_id, tuple(msg["ativos"])))

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _autentica)
    monkeypatch.setattr(R, "get_session_async", _sessao)
    monkeypatch.setattr(R, "update_agent_last_seen", AsyncMock())
    monkeypatch.setattr(R, "executor_registry", registro)
    monkeypatch.setattr(R, "_fail_orphan_runs_if_gone", AsyncMock())
    monkeypatch.setattr("app.core.artifact_cleanup.purgar_pendentes_do_executor", AsyncMock(return_value=0))
    monkeypatch.setattr(IB, "_record_job_ack", _ack)
    monkeypatch.setattr(IB, "_reconciliar_inventario", _inventario)
    # Enquanto o teardown drena a fila (até 10 s), a conexão segue registrada e
    # o listener do relay vivo: a saída do socket já tem de estar fechando.
    fechando_na_drenagem = []
    drenagem = R._encerrar_drenagem

    async def _drenagem(*args):
        saida = ec._saidas.get(registro.ws)
        fechando_na_drenagem.append(saida is not None and saida.fechando)
        return await drenagem(*args)

    monkeypatch.setattr(R, "_encerrar_drenagem", _drenagem)
    app = FastAPI()
    app.include_router(R.router)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            ws.send_json({"type": "ack", "job_id": "j1", "status": "enqueued"})
            ws.send_json({"type": "inventario", "ativos": ["j1"], "resultados": [], "truncado": False})
            ws.send_json({"type": "heartbeat"})
            _esperar(lambda: len(processados) == 2)
            # O executor desconecta. Espera o teardown do handler AQUI dentro: ao
            # sair do contexto o TestClient cancela a task do app na hora, e o
            # teardown podia ser cortado no meio (o teste falhava sob carga).
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)

    assert processados == [("ack", "ex-1", "j1"), ("inventario", "ex-1", ("j1",))]
    assert registro.eventos[0] == "register" and registro.eventos[-1] == "unregister"
    assert fechando_na_drenagem == [True]
    assert registro.ws not in ec._saidas          # e sai do mapa no fim do handler


def _esperar(condicao, prazo_s: float = 5.0) -> None:
    fim = time.monotonic() + prazo_s
    while not condicao():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        time.sleep(0.01)


# ── O fim da sessão fica gravado ─────────────────────────────────────────────
# O `last_seen_at` parava no handshake: a tela mostrava um executor que passou
# três dias no ar e caiu há dez minutos como "visto há 3 dias".

def _app_com_sessao(monkeypatch, visto, banco=None, fim=None):
    """O handler de verdade com registry e banco falsos: `visto` faz o papel de
    `update_agent_last_seen` (início da sessão), `fim` o de
    `registrar_fim_da_sessao` e `banco` é o que a sessão entrega."""
    from app.api import dependencies

    registro = _Registro()

    async def _autentica(**_k):
        return SimpleNamespace(executor_version="1.0", max_concurrent_jobs=4, max_queue_size=10)

    @asynccontextmanager
    async def _sessao():
        yield banco

    orfaos = AsyncMock()
    monkeypatch.setattr(dependencies, "validate_executor_mtls", _autentica)
    monkeypatch.setattr(R, "get_session_async", _sessao)
    monkeypatch.setattr(R, "update_agent_last_seen", visto)
    monkeypatch.setattr(R, "registrar_fim_da_sessao", fim or AsyncMock())
    monkeypatch.setattr(R, "executor_registry", registro)
    monkeypatch.setattr(R, "_fail_orphan_runs_if_gone", orfaos)
    monkeypatch.setattr("app.core.artifact_cleanup.purgar_pendentes_do_executor", AsyncMock(return_value=0))
    app = FastAPI()
    app.include_router(R.router)
    return app, registro, orfaos


def test_fim_da_sessao_grava_o_ultimo_contato_depois_do_unregister(monkeypatch):
    eventos = []

    async def _visto(db, executor_id):
        eventos.append(("inicio", executor_id))

    async def _fim(db, executor_id, visto_em):
        eventos.append(("fim", executor_id, visto_em))

    _, banco = _banco_do_executor()
    app, registro, orfaos = _app_com_sessao(monkeypatch, _visto, banco=banco, fim=_fim)
    registro.eventos = eventos      # uma linha do tempo só
    erros = []
    monkeypatch.setattr(R.logger, "error", lambda msg, *args: erros.append(msg % args))

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            _esperar(lambda: "vivo" in eventos)       # o handshake foi processado
            conn = registro.conexoes["ex-1"]
            ultimo_contato = conn.last_seen_at
            conn.last_seen_at = ultimo_contato - timedelta(minutes=2)   # o sinal de vida é anterior ao teardown
            ws.close()
            _esperar(lambda: eventos and eventos[-1][0] == "fim")

    # Início da sessão, e o fim depois de a presença sair. A sessão terminou
    # pelo close do executor, não por um erro no meio.
    assert eventos[0] == "register" and eventos[1] == ("inicio", "ex-1")
    assert eventos[-2] == "unregister"
    _, executor_id, visto_em = eventos[-1]
    assert executor_id == "ex-1"
    # O último contato da sessão, na coluna em UTC sem fuso — não o instante do teardown.
    assert visto_em == (ultimo_contato - timedelta(minutes=2)).replace(tzinfo=None)
    assert erros == []
    orfaos.assert_called_once_with("ex-1")


@pytest.mark.parametrize("falha", ["erro", "demora"])
def test_fim_da_sessao_sem_banco_nao_segura_o_teardown(monkeypatch, falha):
    """Banco fora: o carimbo desiste (com prazo) e a verificação de órfãos já
    foi agendada antes dele."""
    async def _fim(db, executor_id, visto_em):
        if falha == "erro":
            raise RuntimeError("banco fora")
        await asyncio.sleep(60)

    monkeypatch.setattr(R, "_FIM_DA_SESSAO_TIMEOUT", 0.05)
    avisos = []
    monkeypatch.setattr(R.logger, "warning", lambda msg, *args: avisos.append(msg % args))
    app, registro, orfaos = _app_com_sessao(monkeypatch, AsyncMock(), fim=_fim)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.close()
            _esperar(lambda: any("fim da sessão não gravado" in a for a in avisos))

    assert "unregister" in registro.eventos
    orfaos.assert_called_once_with("ex-1")


# ── Versão e system_info vão para o banco no handshake ───────────────────────
# A tela lê os dois do banco. A versão ficava só na conexão (memória do worker
# do WebSocket), e a coluna "versão" mostrava "—" para todo executor.

def _banco_do_executor():
    ag = SimpleNamespace(system_info=None, executor_version=None)
    resultado = SimpleNamespace(scalar_one_or_none=lambda: ag)
    return ag, SimpleNamespace(execute=AsyncMock(return_value=resultado), commit=AsyncMock())


def test_handshake_grava_versao_e_system_info_no_banco(monkeypatch):
    ag, banco = _banco_do_executor()
    app, registro, _ = _app_com_sessao(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": " 2.3.1 ", "protocol_version": "1.0",
                          "system_info": {"hostname": "maq-1", "cpu_cores": 8}})
            _esperar(lambda: ag.executor_version is not None)
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)

    assert ag.executor_version == "2.3.1"
    assert ag.system_info == {"hostname": "maq-1", "cpu_cores": 8.0}
    assert registro.conexoes == {} and banco.commit.await_count >= 1


def test_versao_invalida_nao_vai_ao_banco_nem_derruba_a_conexao(monkeypatch):
    """Maior que a coluna, ela estouraria o UPDATE no meio do loop de
    recebimento — e o erro fechava a conexão."""
    ag, banco = _banco_do_executor()
    app, registro, _ = _app_com_sessao(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "9" * 40, "protocol_version": "1.0"})
            ws.send_json({"type": "heartbeat"})
            _esperar(lambda: registro.eventos.count("vivo") == 2)   # handshake e heartbeat: seguiu viva
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)

    assert ag.executor_version is None
    banco.execute.assert_not_awaited()                        # nada a gravar


def test_versao_invalida_nao_impede_o_system_info(monkeypatch):
    """A versão ruim é descartada e o banco fica com a última boa; o resto do
    handshake grava normalmente."""
    ag, banco = _banco_do_executor()
    ag.executor_version = "2.3.0"
    app, registro, _ = _app_com_sessao(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": {"v": 2}, "protocol_version": "1.0",
                          "system_info": {"hostname": "maq-1"}})
            _esperar(lambda: ag.system_info is not None)
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)

    assert (ag.executor_version, ag.system_info) == ("2.3.0", {"hostname": "maq-1"})


def test_register_nao_recebe_a_versao_da_sessao_anterior(monkeypatch):
    """O banco agora guarda a versão: passada ao register, ela ia para o log de
    conexão e para o status das conexões até o handshake — a da sessão
    anterior, que pode ser de antes de uma atualização."""
    from app.api import dependencies

    app, registro, _ = _app_com_sessao(monkeypatch, AsyncMock(), banco=_banco_do_executor()[1])

    async def _autentica(**_k):
        return SimpleNamespace(executor_version="1.9.0", max_concurrent_jobs=4, max_queue_size=10)

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _autentica)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            _esperar(lambda: "register" in registro.eventos)
            versao_no_register = registro.conexoes["ex-1"].executor_version
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)

    assert versao_no_register is None



def test_so_o_primeiro_handshake_grava_no_banco(monkeypatch):
    """Um handshake repetido era um SELECT + UPDATE a cada mensagem, sem limite,
    e podia trocar o system_info só na memória deste worker."""
    ag, banco = _banco_do_executor()
    app, registro, _ = _app_com_sessao(monkeypatch, AsyncMock(), banco=banco)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.3.1", "protocol_version": "1.0",
                          "system_info": {"hostname": "maq-1"}})
            for i in range(3):
                ws.send_json({"type": "handshake", "executor_version": f"9.9.{i}", "protocol_version": "1.0",
                              "system_info": {"hostname": f"outra-{i}"}})
            ws.send_json({"type": "heartbeat"})
            _esperar(lambda: registro.eventos.count("vivo") >= 5)   # 4 handshakes + 1 heartbeat
            conn = registro.conexoes["ex-1"]
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)

    assert banco.execute.await_count == 1
    assert (ag.executor_version, ag.system_info) == ("2.3.1", {"hostname": "maq-1"})
    assert (conn.executor_version, conn.system_info) == ("2.3.1", {"hostname": "maq-1"})


# ── Revogado com a sessão aberta ─────────────────────────────────────────────

def test_sessao_de_executor_revogado_cai_com_4403(monkeypatch):
    """A vigia no handler de verdade: revogado com a sessão aberta — e o aviso
    do relay perdido —, o executor recebe o close 4403 (terminal para ele) e o
    teardown roda. Antes a sessão seguia viva até ele reconectar."""
    app, registro, orfaos = _app_com_sessao(monkeypatch, AsyncMock(), banco=_banco_do_executor()[1])
    monkeypatch.setattr(R, "_REVOGACAO_INTERVALO", 0.01)
    conferencia = AsyncMock(side_effect=[None, "Cert revogado."])
    monkeypatch.setattr(R, "motivo_da_revogacao", conferencia)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            with pytest.raises(WebSocketDisconnect) as fechou:
                ws.receive_text()
            # O executor responde ao close. No TestClient é isso que entrega a
            # desconexão ao receive pendente do app (no uvicorn o close do
            # servidor já o encerra); sair do contexto antes cancelaria a task
            # do app no meio do teardown.
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)

    assert fechou.value.code == 4403
    assert conferencia.await_count == 2
    orfaos.assert_called_once_with("ex-1")


def test_sessao_valida_nao_e_derrubada_pela_vigia(monkeypatch):
    app, registro, _ = _app_com_sessao(monkeypatch, AsyncMock(), banco=_banco_do_executor()[1])
    monkeypatch.setattr(R, "_REVOGACAO_INTERVALO", 0.01)
    conferencia = AsyncMock(return_value=None)
    monkeypatch.setattr(R, "motivo_da_revogacao", conferencia)

    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws/executores/ex-1") as ws:
            ws.send_json({"type": "handshake", "executor_version": "2.0", "protocol_version": "1.0"})
            _esperar(lambda: conferencia.await_count >= 3)
            ws.send_json({"type": "heartbeat"})
            _esperar(lambda: registro.eventos.count("vivo") == 2)   # seguiu viva
            ws.close()
            _esperar(lambda: "unregister" in registro.eventos)
