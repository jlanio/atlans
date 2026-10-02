# tests/unit/test_sessao_ws_do_executor.py
"""
A sessão WebSocket do executor, do accept ao teardown, pelo handler de verdade.

Caracterização: prende o que o executor vê no fio (as respostas `error` com o
`reason`, os códigos e motivos de close), o que o servidor faz a cada tipo de
mensagem (registry, banco, fila da drenadora), o que ele loga e a ordem do
teardown. Os executores em campo são de versões diferentes e não são
atualizados junto com o servidor: uma diferença aqui é mudança de protocolo.

O socket é um dublê direto, sem TestClient, para a linha do tempo ser
determinística: cada efeito entra em `linha` na ordem em que acontece, e os
envios ao executor (`fio`) saem pelo escritor real da saída do socket.
"""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from starlette.websockets import WebSocketDisconnect

from app.api import dependencies
from app.api.routers import executor_ws_router as R
from app.api.routers.executor_ws import inbox as IB
from app.core import executor_connections as ec
from flow.utils.protocolo_ws import PROTOCOL_VERSION, SUPPORTED_PROTOCOL_VERSIONS

ULTIMO_CONTATO = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
CERT = 'Subject="CN=executor-ex-1";SerialNumber="1a2b"'


class _WS:
    """O que o handler e a saída do socket (`_Saida`) usam de um WebSocket."""

    def __init__(self, linha, executor_id="ex-1"):
        self.linha = linha
        self.headers = {"x-forwarded-tls-client-cert-info": CERT}
        self.client = SimpleNamespace(host="10.1.2.3")
        self.url = SimpleNamespace(path=f"/ws/executores/{executor_id}")
        self.entrada: asyncio.Queue = asyncio.Queue()
        self.falhar_accept = False

    async def accept(self):
        self.linha.append(("accept",))
        if self.falhar_accept:
            raise RuntimeError("socket caiu no accept")

    async def receive_text(self):
        # Um receive de verdade passa pelo loop (é I/O de rede). Sem ceder a
        # vez aqui, no Python 3.12 — em que o `wait_for` já não cria uma task —
        # as mensagens enfileiradas seriam lidas em sequência e o escritor da
        # saída nunca rodaria entre uma e outra.
        await asyncio.sleep(0)
        item = await self.entrada.get()
        if isinstance(item, BaseException):
            raise item
        return item

    async def send_text(self, texto):
        self.linha.append(("fio", json.loads(texto)))

    async def close(self, code=1000, reason=""):
        self.linha.append(("close", code, reason))
        # O executor responde ao close: um receive pendente vê a desconexão.
        self.entrada.put_nowait(WebSocketDisconnect(code))

    def mandar(self, *mensagens):
        for m in mensagens:
            self.entrada.put_nowait(m if isinstance(m, (str, BaseException)) else json.dumps(m))

    def desconectar(self, code=1000):
        self.entrada.put_nowait(WebSocketDisconnect(code))


class _Registro:
    """O mínimo do registry que o handler usa — sem Redis."""

    def __init__(self, linha):
        self.linha = linha
        self.conexoes = {}
        self.guardar = True

    async def register(self, executor_id, ws, **kw):
        if self.guardar:
            self.conexoes[executor_id] = SimpleNamespace(
                handshake_received=False, websocket=ws, executor_version=None,
                system_info=None, last_seen_at=ULTIMO_CONTATO,
            )
        self.linha.append(("register", executor_id, kw))

    def get(self, executor_id):
        return self.conexoes.get(executor_id)

    async def update_last_seen(self, executor_id):
        self.linha.append(("vivo", executor_id))

    async def update_capacity(self, executor_id, capacidade):
        self.linha.append(("capacity", executor_id, capacidade))

    async def unregister(self, executor_id, expected_ws=None):
        self.linha.append(("unregister", executor_id, expected_ws))
        self.conexoes.pop(executor_id, None)


class _Banco:
    def __init__(self, linha):
        self.linha = linha
        self.executor = SimpleNamespace(system_info=None, executor_version=None)

    async def execute(self, _consulta):
        self.linha.append(("banco", "select"))
        return SimpleNamespace(scalar_one_or_none=lambda: self.executor)

    async def commit(self):
        self.linha.append(("banco", "commit", self.executor.executor_version, self.executor.system_info))


@pytest.fixture
def s(monkeypatch):
    """Uma sessão montada: socket, registry, banco e a linha do tempo."""
    linha: list = []
    registro = _Registro(linha)
    banco = _Banco(linha)
    ws = _WS(linha)

    async def _valida(**kw):
        linha.append(("mtls", kw))
        return SimpleNamespace(max_concurrent_jobs=4, max_queue_size=10)

    @asynccontextmanager
    async def _sessao_do_banco():
        yield banco

    async def _inicio(db, executor_id):
        linha.append(("inicio da sessao", executor_id))

    async def _fim(db, executor_id, visto_em):
        linha.append(("fim da sessao", executor_id, visto_em))

    async def _nada():
        return None

    def _orfaos(executor_id):
        linha.append(("orfaos", executor_id))
        return _nada()

    async def _purga(executor_id):
        linha.append(("purga", executor_id))
        return 0

    async def _enfileirar_mensagem(executor_id, inbox, descartes, msg_type, msg, frame_bytes):
        linha.append(("drenadora", msg_type, msg, frame_bytes))

    encerrar_envios = R.encerrar_envios

    def _encerrar_envios(sock):
        # A vigia já tem de estar cancelada quando os envios se encerram.
        vigias = [t.cancelling() for t in asyncio.all_tasks() if t.get_name().startswith("revogacao-")]
        linha.append(("encerrar_envios", vigias))
        return encerrar_envios(sock)

    def _gravando(nome):
        original = getattr(R, nome)

        def _chamada(*args):
            linha.append((nome,) + args)
            return original(*args)

        return _chamada

    drenagem = R._encerrar_drenagem

    async def _drenagem(inbox, drain_task):
        linha.append(("drenagem",))
        await drenagem(inbox, drain_task)

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _valida)
    monkeypatch.setattr(R, "get_session_async", _sessao_do_banco)
    monkeypatch.setattr(R, "update_agent_last_seen", _inicio)
    monkeypatch.setattr(R, "registrar_fim_da_sessao", _fim)
    monkeypatch.setattr(R, "executor_registry", registro)
    monkeypatch.setattr(R, "_fail_orphan_runs_if_gone", _orfaos)
    monkeypatch.setattr(R, "_enfileirar_mensagem", _enfileirar_mensagem)
    monkeypatch.setattr(R, "encerrar_envios", _encerrar_envios)
    monkeypatch.setattr(R, "_drop_rate_state", _gravando("_drop_rate_state"))
    monkeypatch.setattr(R, "encerrar_saida", _gravando("encerrar_saida"))
    monkeypatch.setattr(R, "_encerrar_drenagem", _drenagem)
    monkeypatch.setattr("app.core.artifact_cleanup.purgar_pendentes_do_executor", _purga)
    for nivel in ("debug", "info", "warning", "error"):
        monkeypatch.setattr(
            R.logger, nivel, lambda msg, *args, _nivel=nivel: linha.append(("log", _nivel, msg % args)),
        )
    return SimpleNamespace(linha=linha, registro=registro, banco=banco, ws=ws)


async def _rodar(s, executor_id="ex-1"):
    await asyncio.wait_for(R.agent_websocket(executor_id, s.ws), timeout=5)


def _abertura(s, executor_id="ex-1"):
    """O começo de toda sessão aceita, até o loop de recebimento."""
    return [
        ("mtls", {
            "header_value": CERT, "client_host": "10.1.2.3",
            "url_path": f"/ws/executores/{executor_id}", "db": s.banco,
            "expected_executor_id": executor_id, "require_public_key": True,
        }),
        ("accept",),
        ("register", executor_id, {"max_concurrent_limit": 4, "max_queue_limit": 10}),
        ("inicio da sessao", executor_id),
        ("log", "info", f"Executor '{executor_id}' conectado via WebSocket."),
        ("purga", executor_id),
    ]


def _teardown(s, executor_id="ex-1", *, fim=True):
    """O fim de toda sessão aceita, na ordem: envios, drenagem, presença, órfãos, carimbo."""
    passos = [
        ("encerrar_envios", [1]),
        ("drenagem",),
        ("unregister", executor_id, s.ws),
        ("_drop_rate_state", executor_id),
        ("encerrar_saida", s.ws),
        ("orfaos", executor_id),
    ]
    if fim:
        passos.append(("fim da sessao", executor_id, ULTIMO_CONTATO.replace(tzinfo=None)))
    return passos


HANDSHAKE = {"type": "handshake", "protocol_version": PROTOCOL_VERSION, "executor_version": "2.3.1"}


# ── A sessão, mensagem a mensagem ────────────────────────────────────────────


async def test_sessao_inteira_mensagem_a_mensagem(s):
    """Cada tipo do protocolo, na ordem em que o loop o trata, e o teardown.

    O schema é conferido ANTES do portão do handshake; tipo desconhecido (até
    um que não é texto) só vai ao debug; o segundo handshake só renova a
    presença."""
    s.ws.mandar(
        {"type": "heartbeat"},                         # antes do handshake
        {"type": "ack"},                               # schema antes do portão
        "{nao e json",
        {**HANDSHAKE, "system_info": {"hostname": "maq-1", "cpu_cores": 8}},
        {"type": "heartbeat"},
        {"type": "capacity", "queued": 1, "running": 2, "max_concurrent": 3, "max_queue": 4},
        {"type": "capacity", "queued": -1, "running": 0, "max_concurrent": 1, "max_queue": 1},
        {"type": "job_result", "job_id": "j1", "status": "ok"},
        {"type": "node_event", "run_id": "r1", "node": "n1"},
        {"type": "sync_event", "event": "file_uploaded"},
        {"type": "ack", "job_id": "j1", "status": "enqueued"},
        {"type": "inventario", "ativos": []},
        {"type": "coisa_nova"},
        {"type": ["lista"]},
        {"sem": "tipo"},
        {**HANDSHAKE, "executor_version": "9.9.9", "system_info": {"hostname": "outra"}},
    )
    s.ws.desconectar()

    await _rodar(s)

    json_invalido = "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
    assert s.linha == _abertura(s) + [
        ("log", "warning", "Executor 'ex-1' enviou 'heartbeat' antes de handshake — rejeitado."),
        ("fio", {"type": "error", "reason": "handshake_required"}),
        ("log", "warning", "Executor 'ex-1' enviou 'ack' com campos obrigatórios ausentes: ['job_id']"),
        ("fio", {"type": "error", "reason": "invalid_schema", "missing_fields": ["job_id"], "message_type": "ack"}),
        ("log", "warning", f"Executor 'ex-1' enviou JSON inválido (streak=1): {json_invalido} | raw='{{nao e json'"),
        ("fio", {"type": "error", "reason": "invalid_json", "detail": json_invalido}),
        ("banco", "select"),
        ("banco", "commit", "2.3.1", {"hostname": "maq-1", "cpu_cores": 8.0}),
        ("vivo", "ex-1"),
        ("vivo", "ex-1"),
        ("capacity", "ex-1", {
            "queued": 1, "running": 2, "max_concurrent": 3, "max_queue": 4,
            "disk_free_gb": None, "ram_available_gb": None,
        }),
        ("log", "warning", "Executor 'ex-1' enviou capacity inválida: ['queued: negativo (-1)']"),
        ("fio", {"type": "error", "reason": "invalid_capacity", "errors": ["queued: negativo (-1)"]}),
        ("drenadora", "job_result", {"type": "job_result", "job_id": "j1", "status": "ok"}, 54),
        ("drenadora", "node_event", {"type": "node_event", "run_id": "r1", "node": "n1"}, 52),
        ("drenadora", "sync_event", {"type": "sync_event", "event": "file_uploaded"}, 48),
        ("drenadora", "ack", {"type": "ack", "job_id": "j1", "status": "enqueued"}, 53),
        ("drenadora", "inventario", {"type": "inventario", "ativos": []}, 36),
        ("log", "debug", "Executor 'ex-1' enviou tipo desconhecido: coisa_nova"),
        ("log", "debug", "Executor 'ex-1' enviou tipo desconhecido: ['lista']"),
        ("log", "debug", "Executor 'ex-1' enviou tipo desconhecido: None"),
        ("vivo", "ex-1"),                              # 2º handshake: nada vai ao banco
        ("log", "info", "Executor 'ex-1' desconectou (WebSocketDisconnect)."),
    ] + _teardown(s)
    conn = s.registro.conexoes.get("ex-1")
    assert conn is None                                # saiu no unregister
    assert s.ws not in ec._saidas


async def test_handshake_sem_protocol_version_vale_como_1_0(s):
    """Executor antigo que não declara versão: vale "1.0". Sem versão nem
    system_info, nada vai ao banco."""
    s.ws.mandar({"type": "handshake"}, {"type": "heartbeat"})
    s.ws.desconectar()

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("vivo", "ex-1"),
        ("vivo", "ex-1"),
        ("log", "info", "Executor 'ex-1' desconectou (WebSocketDisconnect)."),
    ] + _teardown(s)


async def test_protocolo_nao_suportado_fecha_com_4426(s):
    """O `error` de versão é enfileirado e o close logo depois o descarta: o
    que chega ao executor é o close 4426."""
    s.ws.mandar({**HANDSHAKE, "protocol_version": "9.0"}, {"type": "heartbeat"})

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("log", "warning",
         f"Executor 'ex-1' declarou protocol_version='9.0' não suportado (aceitos: {sorted(SUPPORTED_PROTOCOL_VERSIONS)})."),
        ("close", 4426, "Unsupported protocol version."),
    ] + _teardown(s)


async def test_resposta_de_versao_nao_suportada_leva_a_versao_do_servidor(s, monkeypatch):
    """O corpo do `error` de versão (quando ele chega a sair)."""
    respostas = []
    monkeypatch.setattr(R, "enfileirar_ao_executor", lambda _ws, texto, _eid: respostas.append(json.loads(texto)))
    s.ws.mandar({**HANDSHAKE, "protocol_version": "9.0"})

    await _rodar(s)

    assert respostas == [{
        "type": "error", "reason": "unsupported_protocol_version",
        "server_protocol_version": PROTOCOL_VERSION, "supported": list(SUPPORTED_PROTOCOL_VERSIONS),
    }]


async def test_so_o_primeiro_handshake_passa_pelo_portao_da_versao(s):
    s.ws.mandar(HANDSHAKE, {**HANDSHAKE, "protocol_version": "9.0"})
    s.ws.desconectar()

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("banco", "select"),
        ("banco", "commit", "2.3.1", None),
        ("vivo", "ex-1"),
        ("vivo", "ex-1"),
        ("log", "info", "Executor 'ex-1' desconectou (WebSocketDisconnect)."),
    ] + _teardown(s)


async def test_json_invalido_em_sequencia_fecha_com_1003_e_um_valido_zera_a_conta(s):
    """Cinco seguidos derrubam; um válido no meio zera a sequência. A quinta
    resposta é enfileirada e descartada pelo close."""
    s.ws.mandar(HANDSHAKE, *(["x"] * 4), {"type": "heartbeat"}, *(["x"] * 5))

    await _rodar(s)

    detalhe = "Expecting value: line 1 column 1 (char 0)"

    def _invalido(n):
        return [
            ("log", "warning", f"Executor 'ex-1' enviou JSON inválido (streak={n}): {detalhe} | raw='x'"),
            ("fio", {"type": "error", "reason": "invalid_json", "detail": detalhe}),
        ]

    assert s.linha == _abertura(s) + [
        ("banco", "select"),
        ("banco", "commit", "2.3.1", None),
        ("vivo", "ex-1"),
        *_invalido(1), *_invalido(2), *_invalido(3), *_invalido(4),
        ("vivo", "ex-1"),
        *_invalido(1), *_invalido(2), *_invalido(3), *_invalido(4),
        ("log", "warning", f"Executor 'ex-1' enviou JSON inválido (streak=5): {detalhe} | raw='x'"),
        ("log", "error", "Executor 'ex-1' enviou 5 JSONs inválidos seguidos — desconectando."),
        ("close", 1003, "Too many invalid messages."),
    ] + _teardown(s)


async def test_json_invalido_longo_e_cortado_no_log_e_na_resposta(s):
    s.ws.mandar("{" + "a" * 500)
    s.ws.desconectar()

    await _rodar(s)

    [aviso] = [e for e in s.linha if e[0] == "log" and e[1] == "warning"]
    assert aviso[2].endswith("| raw=" + repr(("{" + "a" * 500)[:200]))
    [resposta] = [e[1] for e in s.linha if e[0] == "fio"]
    assert resposta == {"type": "error", "reason": "invalid_json",
                        "detail": "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"}


async def test_sem_heartbeat_fecha_com_4408(s, monkeypatch):
    monkeypatch.setattr(R, "_HEARTBEAT_TIMEOUT", 0.05)
    s.ws.mandar(HANDSHAKE)

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("banco", "select"),
        ("banco", "commit", "2.3.1", None),
        ("vivo", "ex-1"),
        ("log", "warning", "Executor 'ex-1' sem heartbeat por 0s — desconectando."),
        ("close", 4408, "Heartbeat timeout."),
    ] + _teardown(s)


async def test_json_que_nao_e_objeto_derruba_a_sessao_com_log_de_erro(s):
    """Uma lista passa pelo parse e quebra no `.get`: a sessão cai pelo
    `except` genérico, sem resposta nem close do servidor."""
    s.ws.mandar(HANDSHAKE, "[1, 2]", {"type": "heartbeat"})

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("banco", "select"),
        ("banco", "commit", "2.3.1", None),
        ("vivo", "ex-1"),
        ("log", "error", "Erro no WebSocket do executor 'ex-1': 'list' object has no attribute 'get'"),
    ] + _teardown(s)


async def test_erro_no_meio_do_loop_loga_e_faz_o_teardown(s):
    async def _quebra(executor_id, capacidade):
        raise RuntimeError("redis fora")

    s.registro.update_capacity = _quebra
    s.ws.mandar(HANDSHAKE, {"type": "capacity", "queued": 0, "running": 0, "max_concurrent": 1, "max_queue": 1})

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("banco", "select"),
        ("banco", "commit", "2.3.1", None),
        ("vivo", "ex-1"),
        ("log", "error", "Erro no WebSocket do executor 'ex-1': redis fora"),
    ] + _teardown(s)


async def test_banco_fora_no_inicio_da_sessao_ainda_faz_o_teardown(s, monkeypatch):
    """O `update_agent_last_seen` fica DENTRO do try: com o banco fora, a
    conexão não fica registrada sem ninguém lendo o socket."""
    async def _banco_fora(db, executor_id):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(R, "update_agent_last_seen", _banco_fora)

    await _rodar(s)

    # A purga é uma task à parte, agendada na abertura: roda na primeira espera
    # do teardown, e a posição exata dela depende da versão do asyncio.
    assert ("purga", "ex-1") in s.linha
    assert [e for e in s.linha if e != ("purga", "ex-1")] == _abertura(s)[:3] + [
        ("log", "error", "Erro no WebSocket do executor 'ex-1': banco fora"),
    ] + _teardown(s)


# ── A recusa na autenticação ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "razao,codigo",
    [*sorted(dependencies._MTLS_WS_CODE.items()), ("razao_nova", 4401)],
)
async def test_recusa_mtls_aceita_e_fecha_com_o_codigo_da_razao(s, monkeypatch, razao, codigo):
    """O deny chega ao executor como close 44xx (terminal para ele), nunca como
    status HTTP. Razão desconhecida vira 4401; o motivo do close é cortado."""
    detalhe = "d" * 150

    async def _nega(**kw):
        s.linha.append(("mtls", kw["expected_executor_id"]))
        raise dependencies.ExecutorMtlsError(razao, detalhe)

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _nega)
    saidas_antes = len(ec._saidas)

    assert await R.agent_websocket("ex-1", s.ws) is None

    assert s.linha == [
        ("mtls", "ex-1"),
        ("log", "warning", f"Executor 'ex-1' recusado na autenticação mTLS ({razao}) — fechando com code={codigo}."),
        ("accept",),
        ("close", codigo, "d" * 100),
        ("encerrar_saida", s.ws),
    ]
    assert s.registro.conexoes == {} and len(ec._saidas) == saidas_antes


async def test_recusa_mtls_sem_detalhe_fecha_com_motivo_vazio(s, monkeypatch):
    async def _nega(**_kw):
        raise dependencies.ExecutorMtlsError("revoked", None)

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _nega)

    await R.agent_websocket("ex-1", s.ws)

    assert ("close", 4403, "") in s.linha


async def test_recusa_mtls_com_o_socket_ja_caido_so_loga_em_debug(s, monkeypatch):
    async def _nega(**_kw):
        raise dependencies.ExecutorMtlsError("expired", "cert vencido")

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _nega)
    s.ws.falhar_accept = True

    assert await R.agent_websocket("ex-1", s.ws) is None

    assert s.linha == [
        ("log", "warning", "Executor 'ex-1' recusado na autenticação mTLS (expired) — fechando com code=4401."),
        ("accept",),
        ("log", "debug", "Falha ao notificar deny ao executor 'ex-1': socket caiu no accept"),
        ("encerrar_saida", s.ws),
    ]


async def test_falha_fora_do_mtls_na_autenticacao_sobe_sem_accept(s, monkeypatch):
    async def _quebra(**_kw):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(dependencies, "validate_executor_mtls", _quebra)

    with pytest.raises(RuntimeError, match="banco fora"):
        await R.agent_websocket("ex-1", s.ws)

    assert s.linha == []


# ── A abertura ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("resultado", [3, 0, RuntimeError("disco fora")])
async def test_purga_na_reconexao_loga_o_que_purgou_ou_a_falha(s, monkeypatch, resultado):
    async def _purga(executor_id):
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    monkeypatch.setattr("app.core.artifact_cleanup.purgar_pendentes_do_executor", _purga)
    s.ws.desconectar()

    await _rodar(s)

    logs = [e for e in s.linha if e[0] == "log" and "artefato" in e[2]]
    if resultado == 3:
        assert logs == [("log", "info", "Executor 'ex-1': 3 artefato(s) local(is) vencido(s) purgado(s) na reconexão.")]
    elif resultado == 0:
        assert logs == []
    else:
        assert logs == [("log", "warning",
                         "Executor 'ex-1': falha ao purgar artefatos pendentes na reconexão (disco fora). "
                         "O ciclo periódico tenta de novo.")]
    assert not R._purge_tasks_pendentes


async def test_tarefas_da_sessao_levam_o_prefixo_do_executor(s, monkeypatch):
    """Os nomes aparecem em dump de tasks e no debug do asyncio."""
    executor_id = "exec-0123456789"
    s.ws = _WS(s.linha, executor_id)
    nomes = []

    async def _inicio(db, eid):
        nomes.extend(sorted(
            t.get_name() for t in asyncio.all_tasks()
            if t.get_name().split("-")[0] in ("purge", "inbox", "revogacao")
        ))

    liberar = asyncio.Event()

    def _orfaos(eid):
        return liberar.wait()

    monkeypatch.setattr(R, "update_agent_last_seen", _inicio)
    monkeypatch.setattr(R, "_fail_orphan_runs_if_gone", _orfaos)
    s.ws.desconectar()

    await _rodar(s, executor_id)

    assert nomes == ["inbox-exec-012", "purge-exec-012", "revogacao-exec-012"]
    assert [t.get_name() for t in R._orphan_check_tasks] == ["orphan-check-exec-012"]
    liberar.set()
    await asyncio.sleep(0.01)
    assert not R._orphan_check_tasks


async def test_ip_da_conexao_vai_com_o_job_result(s, monkeypatch):
    """O job_result grava o IP DESTA conexão (o do socket), não o de quem
    estiver no registro quando a drenadora chegar nele."""
    gravados = []

    async def _grava(executor_id, msg, frame_bytes, executor_ip=None):
        gravados.append((executor_id, msg["job_id"], frame_bytes, executor_ip))

    monkeypatch.setattr(R, "_enfileirar_mensagem", IB._enfileirar_mensagem)
    monkeypatch.setattr(IB, "_handle_job_result", _grava)
    s.ws.mandar(HANDSHAKE, {"type": "job_result", "job_id": "j1", "status": "ok"})
    s.ws.desconectar()

    await _rodar(s)

    assert gravados == [("ex-1", "j1", 54, "10.1.2.3")]


# ── Quando o registro não é mais desta sessão ────────────────────────────────


async def test_registro_tomado_por_outra_sessao_nao_carimba_o_fim(s):
    """Outra sessão registrou por cima entre o register e a conferência: o
    "visto há" é dela, e o fim desta não é gravado."""
    register = s.registro.register

    async def _tomado(executor_id, ws, **kw):
        await register(executor_id, ws, **kw)
        s.registro.conexoes[executor_id].websocket = object()

    s.registro.register = _tomado
    s.ws.mandar({"type": "heartbeat"})
    s.ws.desconectar()

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("log", "warning", "Executor 'ex-1' enviou 'heartbeat' antes de handshake — rejeitado."),
        ("fio", {"type": "error", "reason": "handshake_required"}),
        ("log", "info", "Executor 'ex-1' desconectou (WebSocketDisconnect)."),
    ] + _teardown(s, fim=False)


async def test_sem_conexao_no_registro_o_portao_do_handshake_nao_se_aplica(s):
    """Sem estado de conexão para conferir, o portão não barra; o handshake
    ainda grava no banco e nada é carimbado no fim."""
    s.registro.guardar = False
    s.ws.mandar({"type": "heartbeat"}, {**HANDSHAKE, "protocol_version": "9.0"})
    s.ws.desconectar()

    await _rodar(s)

    assert s.linha == _abertura(s) + [
        ("vivo", "ex-1"),
        ("banco", "select"),
        ("banco", "commit", "2.3.1", None),
        ("vivo", "ex-1"),
        ("log", "info", "Executor 'ex-1' desconectou (WebSocketDisconnect)."),
    ] + _teardown(s, fim=False)


# ── O teardown ───────────────────────────────────────────────────────────────


async def test_descartes_por_fila_cheia_sao_somados_no_teardown(s, monkeypatch):
    async def _descarta(executor_id, inbox, descartes, msg_type, msg, frame_bytes):
        descartes["total"] += 1

    monkeypatch.setattr(R, "_enfileirar_mensagem", _descarta)
    s.ws.mandar(HANDSHAKE, *[{"type": "node_event", "run_id": "r1", "node": f"n{i}"} for i in range(2)])
    s.ws.desconectar()

    await _rodar(s)

    teardown = _teardown(s)
    assert s.linha[-len(teardown) - 1:] == teardown[:2] + [
        ("log", "warning", "Executor 'ex-1': 2 mensagem(ns) descartada(s) por fila cheia nesta conexão."),
    ] + teardown[2:]


async def test_drenagem_que_nao_termina_cancela_espera_as_gravacoes_e_resgata(s, monkeypatch):
    """A drenagem final passa do prazo: a drenadora é cancelada, o job_result
    em gravação ganha a carência, e o resgate dos pendentes roda (e loga se
    falhar) — antes de a presença sair."""
    liberar = asyncio.Event()

    async def _grava(executor_id, msg, frame_bytes, executor_ip=None):
        s.linha.append(("gravando", msg["job_id"]))
        await liberar.wait()
        s.linha.append(("gravado", msg["job_id"]))

    async def _resgate(executor_id, inbox):
        s.linha.append(("resgate", executor_id))
        raise RuntimeError("redis fora")

    monkeypatch.setattr(R, "_enfileirar_mensagem", IB._enfileirar_mensagem)
    monkeypatch.setattr(IB, "_handle_job_result", _grava)
    monkeypatch.setattr(R, "_resgatar_job_results_pendentes", _resgate)
    monkeypatch.setattr(R, "_INBOX_FLUSH_TIMEOUT", 0.05)
    monkeypatch.setattr(R, "_INBOX_CANCEL_GRACE", 0.05)
    s.ws.mandar(HANDSHAKE, {"type": "job_result", "job_id": "j1", "status": "ok"})
    sessao = asyncio.create_task(_rodar(s))
    while ("gravando", "j1") not in s.linha:           # a drenadora já pegou o job_result
        await asyncio.sleep(0.005)
    s.ws.desconectar()

    await sessao
    liberar.set()
    await asyncio.sleep(0.01)

    teardown = _teardown(s)
    assert s.linha == _abertura(s) + [
        ("banco", "select"),
        ("banco", "commit", "2.3.1", None),
        ("vivo", "ex-1"),
        ("gravando", "j1"),
        ("log", "info", "Executor 'ex-1' desconectou (WebSocketDisconnect)."),
    ] + teardown[:2] + [
        ("log", "warning",
         "Executor 'ex-1': drenagem final não concluiu em 0s () — eventos residuais podem ter sido perdidos."),
        ("log", "error",
         "Executor 'ex-1': 1 gravação(ões) de job_result ainda em voo após 0s de carência — "
         "run pode ficar sem conclusão."),
        ("resgate", "ex-1"),
        ("log", "error", "Executor 'ex-1': resgate dos job_result pendentes não concluiu: redis fora"),
    ] + teardown[2:] + [("gravado", "j1")]


async def test_sem_loop_para_os_orfaos_o_watchdog_assume(s, monkeypatch):
    def _sem_loop(executor_id):
        s.linha.append(("orfaos", executor_id))
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(R, "_fail_orphan_runs_if_gone", _sem_loop)
    s.ws.desconectar()

    await _rodar(s)

    teardown = _teardown(s)
    assert s.linha[-3:] == [
        teardown[-2],
        ("log", "debug", "Sem loop para agendar verificação de órfãos de 'ex-1' — watchdog assume."),
        teardown[-1],
    ]
