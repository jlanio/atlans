# tests/unit/test_executor_control_restart.py
"""Encerramento do executor por mensagem `control` do servidor.

Regressao: `main()` aguardava apenas o `shutdown_event`, alimentado unicamente
por handler de sinal do SO. Quando o servidor encerrava a conexao (revoked /
shutdown / config_changed), `conn.run()` retornava, o `conn_task` terminava e
ninguem observava — o processo ficava vivo, desconectado e sem reiniciar,
porque `restart_requested` so e lido DEPOIS daquele await.

Agravantes por caminho:
  - revoked / shutdown  -> nao emitiam sinal algum (pendurava em qualquer SO)
  - config_changed      -> emitia SIGTERM so em POSIX (pendurava no Windows,
                           onde add_signal_handler nem registra o handler)

Sintoma relatado: "qualquer alteracao de atribuicao na plataforma quebra o
executor, sem restart automatico".
"""
import asyncio
import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from executor.connection import ExecutorConnection

_EXECUTOR_ID = "executor-de-teste"


@pytest.fixture
def servidor_confiavel(monkeypatch):
    """Estabelece a confiança executor↔servidor e devolve um assinador de comandos.

    Deliberadamente usa o assinador REAL do servidor (`app.core.control_crypto`)
    contra o verificador REAL do executor (`executor.job_validator`). Se os bytes
    canônicos dos dois lados divergirem — ordem de chaves, `ensure_ascii`,
    `separators` — todo comando do servidor passa a ser descartado em produção,
    e é este teste que precisa quebrar primeiro.
    """
    from app.core import control_crypto, job_crypto

    priv = Ed25519PrivateKey.generate()
    priv_b64 = base64.b64encode(
        priv.private_bytes_raw()
    ).decode()
    pub_b64 = base64.b64encode(
        priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()

    # Servidor: chave de assinatura. Executor: chave pública fixada + identidade.
    monkeypatch.setattr(job_crypto, "EXECUTOR_SIGNING_KEY", priv_b64)
    monkeypatch.setattr("executor.config.SERVER_SIGNING_PUBLIC_KEY", pub_b64)
    monkeypatch.setattr("executor.config.EXECUTOR_ID", _EXECUTOR_ID)

    def assinar(payload: dict, executor_id: str = _EXECUTOR_ID) -> dict:
        return control_crypto.build_signed_control(payload, executor_id)

    return assinar


class _FakeWS:
    """WebSocket que entrega uma lista fixa de mensagens e grava os envios."""

    def __init__(self, mensagens):
        self._mensagens = [json.dumps(m) for m in mensagens]
        self.enviadas = []

    def __aiter__(self):
        async def _gen():
            for m in self._mensagens:
                yield m
        return _gen()

    async def send(self, raw):
        self.enviadas.append(json.loads(raw))


def _conexao():
    return ExecutorConnection(job_queue=None, result_queue=asyncio.Queue())


# ── control encerra o receive_loop e marca a intencao correta ─────────────────

@pytest.mark.asyncio
async def test_config_changed_pede_restart_sem_emitir_sinal(monkeypatch, servidor_confiavel):
    """Nao pode depender de os.kill: no Windows nao ha handler registrado."""
    matou = []
    monkeypatch.setattr("os.kill", lambda *a: matou.append(a))

    conn = _conexao()
    ws = _FakeWS([servidor_confiavel(
        {"type": "control", "action": "config_changed", "reason": "workspace atribuiu"}
    )])

    await conn._receive_loop(ws)

    assert conn.restart_requested is True
    assert conn._should_reconnect is False
    assert matou == [], "o executor nao deve auto-enviar sinal para reiniciar"


@pytest.mark.asyncio
async def test_revoked_encerra_e_marca_deny_terminal(servidor_confiavel):
    """Executor revogado nao pede restart E marca `terminal_deny`.

    O flag existe para quem supervisiona o processo. Sem ele o executor saia
    como se tivesse encerrado normalmente, e um supervisor (o app desktop, ou
    `restart: on-failure` do Docker) o religava — contra um servidor que ja
    respondeu 4404. O sintoma era um loop de reinicio a cada 2s, com o log
    repetindo "Executor nao encontrado" para sempre.
    """
    conn = _conexao()
    ws = _FakeWS([servidor_confiavel(
        {"type": "control", "action": "revoked", "reason": "revogado pelo admin"}
    )])

    await conn._receive_loop(ws)

    assert conn._should_reconnect is False
    assert conn.restart_requested is False
    assert conn.terminal_deny is not None
    assert "revogado pelo admin" in conn.terminal_deny


@pytest.mark.asyncio
async def test_shutdown_encerra_sem_marcar_deny(servidor_confiavel):
    """`shutdown` NAO e deny: o enrollment continua valido.

    Confundir os dois faria o app oferecer "refazer enrollment" — descartando o
    certificado — para uma parada de manutencao perfeitamente normal.
    """
    conn = _conexao()
    ws = _FakeWS([servidor_confiavel(
        {"type": "control", "action": "shutdown", "reason": "manutencao"}
    )])

    await conn._receive_loop(ws)

    assert conn._should_reconnect is False
    assert conn.restart_requested is False
    assert conn.terminal_deny is None


@pytest.mark.asyncio
async def test_config_changed_nao_marca_deny(servidor_confiavel):
    """Reatribuicao de workspace pede reinicio, nao re-enrollment."""
    conn = _conexao()
    ws = _FakeWS([servidor_confiavel(
        {"type": "control", "action": "config_changed", "reason": "workspace alterado"}
    )])

    await conn._receive_loop(ws)

    assert conn.restart_requested is True
    assert conn.terminal_deny is None


def test_close_4404_e_classificado_como_terminal():
    """O outro caminho do mesmo problema: o deny chega como close code, e nao
    como mensagem `control`, quando o servidor recusa ja no accept()."""
    from websockets.exceptions import ConnectionClosedError
    from websockets.frames import Close

    from executor.connection import _classify_connection_error

    for code in (4401, 4403, 4404):
        exc = ConnectionClosedError(Close(code, "Executor nao encontrado."), None)
        _msg, _tb, terminal = _classify_connection_error(exc)
        assert terminal is True, f"close {code} deveria ser terminal"

    # 1000/1001 sao encerramentos normais — reconectar e o certo.
    exc = ConnectionClosedError(Close(1001, "going away"), None)
    assert _classify_connection_error(exc)[2] is False


@pytest.mark.asyncio
async def test_acao_de_control_desconhecida_nao_derruba_a_conexao(servidor_confiavel):
    conn = _conexao()
    ws = _FakeWS([servidor_confiavel({"type": "control", "action": "acao_futura_qualquer"})])

    await conn._receive_loop(ws)

    assert conn._should_reconnect is True
    assert conn.restart_requested is False


# ── S7: comando sem assinatura valida nao pode ter efeito ────────────────────

@pytest.mark.asyncio
async def test_control_sem_assinatura_e_ignorado(servidor_confiavel):
    """O buraco original: bastava escrever no WS para derrubar o executor."""
    conn = _conexao()
    ws = _FakeWS([{"type": "control", "action": "shutdown", "reason": "injetado"}])

    await conn._receive_loop(ws)

    assert conn._should_reconnect is True, "shutdown nao assinado nao pode derrubar o executor"
    assert conn.restart_requested is False


@pytest.mark.asyncio
async def test_purge_artifacts_sem_assinatura_nao_apaga_nada(tmp_path, monkeypatch):
    """`purge_artifacts` APAGA ARQUIVO do disco do usuario.

    Sem a exigencia de assinatura, quem conseguisse escrever no WebSocket teria
    um canal de destruicao de dados — pior que o buraco original do shutdown,
    que so derrubava o processo.
    """
    raiz = tmp_path / "artifacts"
    (raiz / "ws-1" / "run-1").mkdir(parents=True)
    alvo = raiz / "ws-1" / "run-1" / "dado.geojson"
    alvo.write_bytes(b"dado do cliente")
    monkeypatch.setenv("EXECUTOR_ARTIFACTS_DIR", str(raiz))

    conn = _conexao()
    ws = _FakeWS([{
        "type": "control", "action": "purge_artifacts", "reason": "injetado",
        "artifacts": [{"id_hash": "a1", "local_path": "ws-1/run-1/dado.geojson"}],
    }])

    await conn._receive_loop(ws)

    assert alvo.is_file(), "purge nao assinado apagou o arquivo"
    assert alvo.read_bytes() == b"dado do cliente"


@pytest.mark.asyncio
async def test_purge_artifacts_assinado_apaga_e_mantem_a_conexao(
    tmp_path, monkeypatch, servidor_confiavel,
):
    """Limpeza nao e deny: o executor apaga e continua trabalhando."""
    raiz = tmp_path / "artifacts"
    (raiz / "ws-1" / "run-1").mkdir(parents=True)
    alvo = raiz / "ws-1" / "run-1" / "dado.geojson"
    alvo.write_bytes(b"expirado")
    monkeypatch.setenv("EXECUTOR_ARTIFACTS_DIR", str(raiz))

    conn = _conexao()
    ws = _FakeWS([servidor_confiavel({
        "type": "control", "action": "purge_artifacts", "reason": "Retencao expirada.",
        "artifacts": [{"id_hash": "a1", "local_path": "ws-1/run-1/dado.geojson"}],
    })])

    await conn._receive_loop(ws)

    assert not alvo.exists()
    assert conn._should_reconnect is True, "limpeza nao pode encerrar o executor"
    assert conn.terminal_deny is None


@pytest.mark.asyncio
async def test_control_assinado_para_outro_executor_e_ignorado(servidor_confiavel):
    """Comando legitimo capturado no canal de outro executor nao pode ser reusado."""
    conn = _conexao()
    ws = _FakeWS([servidor_confiavel(
        {"type": "control", "action": "shutdown"}, executor_id="outro-executor",
    )])

    await conn._receive_loop(ws)

    assert conn._should_reconnect is True


@pytest.mark.asyncio
async def test_control_com_payload_adulterado_e_ignorado(servidor_confiavel):
    """A assinatura cobre a mensagem inteira, nao so o bloco `auth`."""
    msg = servidor_confiavel({"type": "control", "action": "config_changed"})
    msg["action"] = "shutdown"  # troca a acao mantendo auth+signature originais

    conn = _conexao()
    ws = _FakeWS([msg])

    await conn._receive_loop(ws)

    assert conn._should_reconnect is True
    assert conn.restart_requested is False


@pytest.mark.asyncio
async def test_replay_do_mesmo_control_e_rejeitado(servidor_confiavel):
    """Segundo uso do mesmo nonce nao passa — o primeiro ja o consumiu."""
    msg = servidor_confiavel({"type": "control", "action": "shutdown"})

    conn1 = _conexao()
    await conn1._receive_loop(_FakeWS([msg]))
    assert conn1._should_reconnect is False, "o primeiro envio deve valer"

    conn2 = _conexao()
    await conn2._receive_loop(_FakeWS([msg]))
    assert conn2._should_reconnect is True, "replay do mesmo comando deve ser recusado"


@pytest.mark.asyncio
async def test_cancel_sem_assinatura_nao_chega_na_fila(servidor_confiavel):
    """`cancel` tambem muda estado (interrompe job) — exige assinatura."""
    cancelados = []

    class _FilaFake:
        def cancel(self, job_id):
            cancelados.append(job_id)
            return "running"

    conn = ExecutorConnection(job_queue=_FilaFake(), result_queue=asyncio.Queue())
    await conn._receive_loop(_FakeWS([{"type": "cancel", "job_id": "job-alheio"}]))
    assert cancelados == [], "cancel nao assinado nao pode interromper job"

    await conn._receive_loop(_FakeWS([
        servidor_confiavel({"type": "cancel", "job_id": "job-legitimo"}),
    ]))
    assert cancelados == ["job-legitimo"]


# ── main(): observar o fim da conexao, nao so o sinal ────────────────────────

@pytest.mark.asyncio
async def test_fim_da_conexao_libera_o_wait_sem_sinal():
    """Reproduz o await de main(): o fim do conn_task tem de liberar sozinho.

    Antes, `await shutdown_event.wait()` isolado nunca retornava — o processo
    ficava pendurado apos o servidor encerrar a conexao.
    """
    shutdown_event = asyncio.Event()  # nunca setado: ninguem manda sinal

    async def _conexao_que_encerra():
        await asyncio.sleep(0)  # simula run() retornando por control

    conn_task = asyncio.create_task(_conexao_que_encerra())
    stop_task = asyncio.create_task(shutdown_event.wait())

    done, _ = await asyncio.wait(
        {stop_task, conn_task}, return_when=asyncio.FIRST_COMPLETED, timeout=2,
    )
    stop_task.cancel()

    assert conn_task in done, "o fim da conexao precisa liberar o wait de main()"


# ── Auto-restart quando nao ha supervisor (rodando direto no python) ─────────

def test_argv_de_restart_preserva_execucao_como_modulo(monkeypatch):
    """`python -m executor` nao pode virar `python .../__main__.py` — quebraria
    os imports do pacote."""
    import __main__ as main_mod
    from executor import main as executor_main

    class _Spec:
        name = "executor.__main__"

    monkeypatch.setattr(main_mod, "__spec__", _Spec(), raising=False)
    monkeypatch.setattr(executor_main.sys, "argv", ["/qualquer/executor/__main__.py"])

    argv = executor_main._build_restart_argv()
    assert argv[1:3] == ["-m", "executor"]


def test_argv_de_restart_para_script_direto(monkeypatch):
    import __main__ as main_mod
    from executor import main as executor_main

    monkeypatch.setattr(main_mod, "__spec__", None, raising=False)
    monkeypatch.setattr(executor_main.sys, "argv", ["executor/main.py", "--flag"])

    argv = executor_main._build_restart_argv()
    assert argv[1:] == ["executor/main.py", "--flag"]


def test_em_container_nao_faz_exec_e_deixa_o_supervisor_reiniciar(monkeypatch):
    from executor import main as executor_main

    chamou = []
    monkeypatch.setattr(executor_main, "_AUTO_RESTART_MODE", "auto")
    monkeypatch.setattr(executor_main, "_in_container", lambda: True)
    monkeypatch.setattr(executor_main.os, "execve", lambda *a: chamou.append(a))

    executor_main._restart_process()
    assert chamou == [], "em container o restart e do supervisor (exit 1)"


def test_fora_de_container_executa_exec(monkeypatch):
    from executor import main as executor_main

    chamou = []
    monkeypatch.setattr(executor_main, "_AUTO_RESTART_MODE", "auto")
    monkeypatch.setattr(executor_main, "_in_container", lambda: False)
    monkeypatch.setattr(executor_main.os, "execve", lambda *a: chamou.append(a))

    executor_main._restart_process()
    assert len(chamou) == 1, "rodando direto no python, o executor precisa se re-executar"


def test_guarda_anti_loop_interrompe_apos_limite(monkeypatch):
    """Se a causa persistir, parar e melhor que spin infinito de re-exec."""
    from executor import main as executor_main
    import time

    chamou = []
    monkeypatch.setattr(executor_main, "_AUTO_RESTART_MODE", "always")
    monkeypatch.setattr(executor_main, "_in_container", lambda: False)
    monkeypatch.setattr(executor_main.os, "execve", lambda *a: chamou.append(a))
    monkeypatch.setenv(executor_main._RESTART_COUNT_VAR, str(executor_main._MAX_RESTARTS))
    monkeypatch.setenv(executor_main._RESTART_SINCE_VAR, str(int(time.time())))

    executor_main._restart_process()
    assert chamou == []


def test_contador_reseta_apos_a_janela(monkeypatch):
    from executor import main as executor_main
    import time

    chamou = []
    monkeypatch.setattr(executor_main, "_AUTO_RESTART_MODE", "always")
    monkeypatch.setattr(executor_main, "_in_container", lambda: False)
    monkeypatch.setattr(executor_main.os, "execve", lambda *a: chamou.append(a))
    monkeypatch.setenv(executor_main._RESTART_COUNT_VAR, str(executor_main._MAX_RESTARTS))
    # Janela antiga: o contador deve zerar e o restart voltar a ser permitido.
    monkeypatch.setenv(
        executor_main._RESTART_SINCE_VAR,
        str(int(time.time()) - executor_main._RESTART_WINDOW_SEC - 60),
    )

    executor_main._restart_process()
    assert len(chamou) == 1


def test_modo_never_desabilita(monkeypatch):
    from executor import main as executor_main

    chamou = []
    monkeypatch.setattr(executor_main, "_AUTO_RESTART_MODE", "never")
    monkeypatch.setattr(executor_main.os, "execve", lambda *a: chamou.append(a))

    executor_main._restart_process()
    assert chamou == []
