# tests/unit/test_exec_cliente_bordas.py
"""Bordas do executor-cliente expostas pela auditoria do lote de otimizacoes.

Cada teste fixa uma invariante que a otimizacao correspondente quebrou sem que
nenhum teste percebesse:

  A2  — o backoff de reconexao so pode recuar por causa de uma SESSAO que
        existiu. Medindo a tentativa inteira, um upgrade WS pendurado por 10s
        contava como "sessao que progrediu", o delay caia pela metade, o caller
        dobrava e o executor refazia handshake mTLS a cada ~1s por horas.
  A18/A26 — o lote de stdout tem que caber no frame: sem `extra['message']`
        duplicando o texto e fechando por BYTES antes de fechar por contagem.
        Acima de 64 KB o evento e reduzido aos campos de controle (sem `extra`)
        e o painel perde o lote inteiro em silencio.
  A19 — a barreira de fim de job mede "quanto falta" por RUN, mas "existe
        consumidor?" pela fila INTEIRA. Com o detector por run, um job curto
        atras do backlog de um job grande acusava sender morto com o WS vivo.
  A20 — validacao/descriptografia nao pode dividir pool com os nos, e capacity
        tem que ser honesto quando o pool dos nos satura.
  A44 — lifecycle descartado por PRESSAO (WS vivo) precisa ser reenviado assim
        que a fila folga; e `esquecer_run` tem que limpar o coletor tambem.
  A59 — todo re-enfileiramento e todo descarte definitivo fecham a conta da
        marca d'agua. Sem isso `alvo` era inalcancavel e a barreira cobrava o
        timeout de estagnacao inteiro em todo job com uma falha de envio.
"""
import asyncio
import json

import pytest

from executor import connection as conn_mod
from executor.connection import ExecutorConnection, _dumps_event
from executor.event_publisher import ColetorDeLifecycle
from executor.main import _FilaContada, _drenar_eventos_pendentes
from flow.utils.publisher.reducao import TETO_NODE_EVENT_BYTES


# ── A2: backoff mede a SESSAO, nao a tentativa ────────────────────────────────

def _conn():
    return ExecutorConnection(job_queue=None, result_queue=asyncio.Queue())


def test_backoff_nao_recua_quando_o_handshake_nunca_abriu(monkeypatch):
    """Upgrade pendurado: `_sessao_iniciada_em` fica None e o delay se mantem.

    Era o cenario critico: `open_timeout` de 10s contava como sessao de 10s,
    caia na faixa do meio e o backoff exponencial deixava de existir justamente
    para a falha mais cara para o servidor.
    """
    c = _conn()
    c._sessao_iniciada_em = None
    assert c._apply_session_backoff_reset(8) == 8


def test_backoff_recua_de_verdade_apos_sessao_media(monkeypatch):
    """Faixa do meio: tem que sobreviver ao dobro que o `run()` aplica depois.

    Com /2 o saldo era exatamente neutro (halve-then-double) e o delay oscilava
    entre dois valores para sempre.
    """
    c = _conn()
    agora = conn_mod.time.monotonic()
    monkeypatch.setattr(conn_mod.time, "monotonic", lambda: agora + 10.0)
    c._sessao_iniciada_em = agora
    recuado = c._apply_session_backoff_reset(8)
    # O caller faz `min(delay * 2, MAX)` logo em seguida.
    assert recuado * 2 < 8


def test_backoff_zera_apos_sessao_saudavel(monkeypatch):
    c = _conn()
    agora = conn_mod.time.monotonic()
    monkeypatch.setattr(conn_mod.time, "monotonic", lambda: agora + 120.0)
    c._sessao_iniciada_em = agora
    assert c._apply_session_backoff_reset(15) == 1


def test_backoff_mantem_acumulado_em_sessao_que_morre_no_nascimento(monkeypatch):
    c = _conn()
    agora = conn_mod.time.monotonic()
    monkeypatch.setattr(conn_mod.time, "monotonic", lambda: agora + 1.0)
    c._sessao_iniciada_em = agora
    assert c._apply_session_backoff_reset(4) == 4


# ── A18/A26: o lote de stdout cabe no frame ───────────────────────────────────

def _stream(publicados):
    from flow.nodes.action.python_script import _LoggingStream

    return _LoggingStream(log_fn=lambda _l: None, publish_fn=publicados.append)


def test_lote_de_stdout_fecha_por_bytes_antes_do_teto_do_frame():
    """200 linhas longas nao podem virar um evento acima de 64 KB.

    O `for r in gdf.itertuples(): print(r)` do usuario: linhas de ~200 chars.
    Antes o lote so fechava em 200 linhas e, com o texto duplicado em
    `message`, o evento passava dos 64 KB e chegava ao painel sem `extra`.
    """
    from flow.nodes.action.python_script import _STDOUT_FLUSH_LINES

    publicados = []
    stream = _stream(publicados)
    linha = "x" * 200
    for _ in range(_STDOUT_FLUSH_LINES * 3):
        stream.write(linha + "\n")
    stream.flush()

    assert publicados, "nada foi publicado"
    for lote in publicados:
        evento = {"type": "node_event", "run_id": "r", "node": "n",
                  "kind": "stdout", "status": "log", "extra": {"lines": lote}}
        assert len(_dumps_event(evento)) <= TETO_NODE_EVENT_BYTES, (
            "lote serializado estourou o teto — o servidor descartaria as linhas"
        )


def test_linha_unica_gigante_e_truncada_com_marcacao():
    """`print(gdf.to_json())` de 70 KB nao pode levar junto as outras linhas."""
    publicados = []
    stream = _stream(publicados)
    stream.write("a" * 70_000 + "\n")
    stream.write("linha legitima\n")
    stream.flush()

    todas = [linha for lote in publicados for linha in lote]
    assert "linha legitima" in todas, "a linha boa foi perdida junto com a gigante"
    marcadas = [linha for linha in todas if "linha truncada" in linha]
    assert marcadas, "truncou em silencio — a saida pareceria completa"
    assert max(len(linha) for linha in todas) < 70_000


def test_reducao_de_evento_preserva_as_linhas_de_stdout():
    """Ultima rede: se ainda assim estourar, `extra['lines']` sobrevive cortado.

    Zerar `extra` fazia o painel mostrar kind=stdout com zero conteudo — a aba
    de saida do no ficava vazia, sem nenhum aviso.
    """
    evento = {
        "type": "node_event", "run_id": "r", "node": "n",
        "kind": "stdout", "status": "log",
        "extra": {"lines": ["y" * 500 for _ in range(400)]},
    }
    bruto = _dumps_event(evento)
    reduzido = json.loads(bruto)
    assert reduzido.get("__truncated__") is True
    assert reduzido["extra"]["lines"], "as linhas foram jogadas fora"
    assert len(bruto) <= TETO_NODE_EVENT_BYTES


def test_reducao_respeita_o_teto_mesmo_com_linhas_nao_ascii():
    """Corte por serializacao real, nao por contagem de caracteres.

    `json.dumps` escapa com ensure_ascii: uma linha de emoji cresce ate 6x. Uma
    estimativa em `len(str)` deixaria o evento reduzido estourar o teto de novo,
    justamente no ramo que existe para salvar o conteudo.
    """
    evento = {
        "type": "node_event", "run_id": "r", "node": "n",
        "kind": "stdout", "status": "log",
        "extra": {"lines": ["🛰️ção" * 200 for _ in range(300)]},
    }
    bruto = _dumps_event(evento)
    assert len(bruto) <= TETO_NODE_EVENT_BYTES
    assert json.loads(bruto)["extra"]["lines"]


# ── A19: estagnacao e propriedade da FILA, nao do run ─────────────────────────

@pytest.mark.asyncio
async def test_barreira_nao_desiste_enquanto_o_sender_drena_outro_run():
    """Job curto atras do backlog de um job grande na fila FIFO compartilhada.

    O detector por run acusava "consumidor parado (WS caido)" com o WebSocket
    perfeitamente vivo, e o `job_result` — que carrega o
    `__workflow_complete__` — era despachado na frente dos node_events do run.
    """
    fila = _FilaContada()
    for i in range(40):
        fila.put_nowait({"run_id": "B", "node": f"b{i}"})
    for i in range(3):
        fila.put_nowait({"run_id": "A", "node": f"a{i}"})

    async def _sender():
        while True:
            ev = await fila.get()
            await asyncio.sleep(0.02)   # sender lento, mas VIVO
            fila.confirmar_envio(ev)
            fila.task_done()

    task = asyncio.create_task(_sender())
    try:
        # 0,3s de estagnacao contra ~0,9s de backlog de B na frente de A.
        await asyncio.wait_for(
            _drenar_eventos_pendentes(fila, run_id="A", timeout=10.0, estagnado=0.3),
            timeout=5.0,
        )
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert fila.confirmados_por_run.get("A") == 3, (
        "a barreira saiu antes dos eventos do proprio run subirem"
    )


@pytest.mark.asyncio
async def test_barreira_ainda_desiste_quando_ninguem_drena():
    """A defesa original continua valendo: sem consumidor, nao se espera 30s."""
    fila = _FilaContada()
    for i in range(3):
        fila.put_nowait({"run_id": "A", "node": f"a{i}"})

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    await _drenar_eventos_pendentes(fila, run_id="A", timeout=30.0, estagnado=0.3)
    assert loop.time() - inicio < 2.0


# ── A59: marca d'agua fecha em requeue e em descarte ──────────────────────────

@pytest.mark.asyncio
async def test_requeue_nao_desbalanceia_a_marca_dagua(monkeypatch):
    """Uma falha transitoria de envio nao pode custar o timeout de estagnacao.

    `_put` conta todo put (inclusive o re-enfileiramento) e `confirmar_envio` so
    conta sucesso: sem contrapeso, `alvo` ficava 1 acima do alcancavel para
    sempre e a barreira so saia por estagnacao.
    """
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)

    class _WSFalhaUmaVez:
        def __init__(self):
            self.enviadas = []
            self._falhou = False

        async def send(self, raw):
            if not self._falhou:
                self._falhou = True
                raise RuntimeError("WS em estado invalido")
            self.enviadas.append(raw)

    fila = _FilaContada(maxsize=500)
    c = ExecutorConnection(job_queue=None, result_queue=asyncio.Queue(), event_queue=fila)
    fila.put_nowait({"run_id": "A", "node": "n1", "status": "completed"})

    task = asyncio.create_task(c._event_sender_loop(_WSFalhaUmaVez()))
    try:
        await asyncio.wait_for(fila.join(), timeout=3.0)
        loop = asyncio.get_running_loop()
        inicio = loop.time()
        await _drenar_eventos_pendentes(fila, run_id="A", timeout=10.0, estagnado=3.0)
        # Se a conta estivesse desbalanceada, a barreira so sairia em ~3s.
        assert loop.time() - inicio < 1.0
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert fila.confirmados_por_run["A"] == fila.enfileirados_por_run["A"]


def test_descarte_definitivo_fecha_a_conta():
    """Evento que nunca sera enviado nao pode deixar `alvo` inalcancavel."""
    fila = _FilaContada(maxsize=500)
    item = {"run_id": "A", "node": "n1"}
    fila.put_nowait(item)
    fila.resolver_sem_envio(item)
    assert fila.confirmados_por_run["A"] == fila.enfileirados_por_run["A"] == 1


# ── A44: coletor drenado com a sessao viva ────────────────────────────────────

def test_coletor_e_drenado_quando_a_fila_folga():
    """Lifecycle descartado por PRESSAO nao pode esperar uma reconexao.

    A fila enche por producao (workflow de 300 nos em debug_mode) muito mais
    vezes do que a sessao cai; drenar so na reconexao deixava os nos girando ate
    o fim do run e os eventos retidos em memoria.
    """
    fila = _FilaContada(maxsize=10)
    c = ExecutorConnection(job_queue=None, result_queue=asyncio.Queue(), event_queue=fila)
    fila.coletor.registrar(
        {"run_id": "A", "node": "n1", "kind": "lifecycle", "status": "completed"}
    )

    # Fila cheia: nao devolve nada (senao o remedio realimenta o descarte).
    for i in range(10):
        fila.put_nowait({"run_id": "B", "node": f"b{i}"})
    c._ressincronizar_lifecycle(so_com_folga=True)
    assert len(fila.coletor) == 1

    # Fila folgou: devolve.
    for _ in range(10):
        fila.get_nowait()
    c._ressincronizar_lifecycle(so_com_folga=True)
    assert len(fila.coletor) == 0
    assert fila.qsize() == 1


def test_esquecer_run_limpa_o_coletor():
    """Sem isto, um reenvio tardio recriava as entradas por-run ja expurgadas."""
    fila = _FilaContada()
    fila.coletor.registrar({"run_id": "A", "node": "n1", "kind": "lifecycle"})
    fila.coletor.registrar({"run_id": "B", "node": "n1", "kind": "lifecycle"})
    fila.esquecer_run("A")
    restantes = fila.coletor.drenar()
    assert [e["run_id"] for e in restantes] == ["B"]


def test_coletor_esquece_run_isoladamente():
    coletor = ColetorDeLifecycle()
    coletor.registrar({"run_id": "A", "node": "n1", "kind": "lifecycle"})
    coletor.registrar({"run_id": "A", "node": "n2", "kind": "lifecycle"})
    assert len(coletor) == 2
    coletor.esquecer_run("A")
    assert len(coletor) == 0


# ── A20: pool do plano de controle separado e capacity honesto ────────────────

def test_validacao_nao_usa_o_pool_dos_nos():
    """Thread orfa de PythonScript nao pode impedir o executor de aceitar job.

    `asyncio.to_thread` cai no pool DEFAULT do loop, que e onde rodam os nos —
    inclusive o script arbitrario do usuario, que o timeout do no nao consegue
    cancelar. Com a validacao ali, 16 threads presas faziam todo job novo travar
    antes mesmo de ser aceito ou recusado.
    """
    import inspect
    from executor import job_executor

    assert job_executor._CONTROL_POOL._max_workers <= 4
    codigo = inspect.getsource(job_executor.execute_job)
    assert "run_in_executor(\n            _CONTROL_POOL" in codigo or "_CONTROL_POOL" in codigo
    assert "asyncio.to_thread(_validar_e_descriptografar" not in codigo


class _PoolFalso:
    def __init__(self, workers, vivas, pendentes):
        self._max_workers = workers
        self._threads = set(range(vivas))

        class _Q:
            def qsize(_self):
                return pendentes

        self._work_queue = _Q()


class _FilaDeJobsFalsa:
    def get_capacity(self):
        return {"queued": 0, "running": 0, "max_concurrent": 4, "max_queue": 50}


def test_capacity_anuncia_saturacao_quando_o_pool_dos_nos_trava(monkeypatch):
    """Threads presas nao aparecem em queued/running, que contam JOBS.

    O executor continuava se anunciando ocioso com o pipeline inteiro parado e o
    servidor seguia despachando jobs que morriam pendurados em 'running'.
    """
    monkeypatch.setattr(conn_mod, "_get_dynamic_metrics", lambda: {})
    c = ExecutorConnection(
        job_queue=_FilaDeJobsFalsa(), result_queue=asyncio.Queue(),
        thread_pool=_PoolFalso(workers=16, vivas=16, pendentes=5),
    )
    # A primeira amostra nao basta — um pico de despacho satura por instantes.
    assert c._montar_capacity()["queued"] == 0
    cap = c._montar_capacity()
    assert cap["queued"] >= cap["max_queue"] + cap["max_concurrent"]


def test_capacity_normal_quando_o_pool_tem_folga(monkeypatch):
    monkeypatch.setattr(conn_mod, "_get_dynamic_metrics", lambda: {})
    c = ExecutorConnection(
        job_queue=_FilaDeJobsFalsa(), result_queue=asyncio.Queue(),
        thread_pool=_PoolFalso(workers=16, vivas=16, pendentes=0),
    )
    for _ in range(5):
        assert c._montar_capacity()["queued"] == 0
