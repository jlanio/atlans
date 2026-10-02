# tests/unit/test_fix_main_queue.py
"""
Correcoes do entry point do executor (main.py), da fila de jobs (job_queue.py)
e da validacao de config (config.py).

Cobre:
  D2 — shutdown descartava silenciosamente os jobs que ainda estavam na fila
  D3 — EXECUTOR_MAX_CONCURRENT=0 subia o executor sem worker nenhum
  D4 — `cancel()` de job desconhecido vazava no set `_cancelled` e mentia "queued"
  B8 — uma unica fila de drive_events compartilhada por N SyncManagers
  D1 — task de background morrendo em silencio
"""
import asyncio
import logging

import pytest

from executor.job_queue import ExecutorJobQueue


def _job(job_id: str, priority: int = 5) -> dict:
    return {"envelope": {"job_id": job_id, "priority": priority}}


# ── D2: shutdown avisa os jobs que nunca chegaram a rodar ────────────────────

@pytest.mark.asyncio
async def test_shutdown_avisa_jobs_que_ficaram_na_fila():
    """Sem isto o servidor fechava como 'desconectou durante a execucao' um job
    que nem comecou — e nao havia como redespachar com seguranca."""
    liberar = asyncio.Event()
    avisados: list[tuple[str, str]] = []

    async def on_execute(message):
        if message["envelope"]["job_id"] == "bloqueia":
            await liberar.wait()

    async def on_cancelled(message):
        avisados.append((message["envelope"]["job_id"], message.get("cancel_reason") or ""))

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1,
                             max_queue_size=10, on_cancelled=on_cancelled)
    await queue.start(n_workers=1)

    await queue.enqueue(_job("bloqueia"))
    await asyncio.sleep(0.05)                 # worker pega o primeiro
    await queue.enqueue(_job("na-fila-1"))
    await queue.enqueue(_job("na-fila-2"))

    liberar.set()
    await queue.shutdown(timeout=2)

    ids = {job_id for job_id, _ in avisados}
    assert ids == {"na-fila-1", "na-fila-2"}
    assert all(motivo == ExecutorJobQueue.NAO_INICIADO for _, motivo in avisados)
    # A PriorityQueue de fato esvaziou. (O `get_capacity()["queued"]` NAO serve
    # mais como prova: depois do shutdown ele anuncia saturacao de proposito —
    # ver test_capacity_anuncia_saturacao_durante_o_shutdown.)
    assert queue._queue.qsize() == 0


@pytest.mark.asyncio
async def test_shutdown_nao_espera_polling_quando_nao_ha_job():
    """_wait_for_running virou Event: sem job em execucao o shutdown e imediato
    (o polling de 0.5s cobrava meio segundo de todo deploy)."""
    async def on_execute(message):
        return None

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=2, max_queue_size=10)
    await queue.start(n_workers=1)

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    await queue.shutdown(timeout=5)
    assert loop.time() - inicio < 0.4


@pytest.mark.asyncio
async def test_capacity_anuncia_saturacao_durante_o_shutdown():
    """Executor drenando nao pode continuar sendo o 'menos carregado' do pool.

    Reproduz a regra do servidor: `ExecutorConnection.is_full()` compara
    queued+running >= max_concurrent+max_queue, e `_resolve_candidates` põe por
    último quem essa mesma conta diz cheio. Com a carga real (fila drenada,
    jobs terminando) o executor em shutdown ficava em PRIMEIRO no ranking e todo
    job roteado voltava como "Executor em shutdown." sem failover.
    """
    async def on_execute(message):
        return None

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=4, max_queue_size=50)
    await queue.start(n_workers=1)

    antes = queue.get_capacity()
    assert antes["queued"] + antes["running"] < antes["max_concurrent"] + antes["max_queue"]

    await queue.shutdown(timeout=2)

    cap = queue.get_capacity()
    # Regra de is_full() do servidor — inclusive se ele clampar max_* para baixo.
    assert cap["queued"] + cap["running"] >= cap["max_concurrent"] + cap["max_queue"]
    # E a carga anunciada tem de ser maior que a de qualquer executor saudavel.
    assert cap["queued"] + cap["running"] > antes["queued"] + antes["running"]


# ── D4: cancel() de job desconhecido ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_de_job_desconhecido_retorna_unknown_sem_vazar():
    async def on_execute(message):
        return None

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1, max_queue_size=10)

    assert queue.cancel("nunca-visto") == "unknown"
    assert queue._cancelled == set(), "id desconhecido nao pode ficar marcado para sempre"


@pytest.mark.asyncio
async def test_cancel_de_job_enfileirado_continua_queued():
    """A resposta 'queued' precisa continuar valendo para job que ESTA na fila."""
    liberar = asyncio.Event()
    executados: list[str] = []

    async def on_execute(message):
        job_id = message["envelope"]["job_id"]
        if job_id == "bloqueia":
            await liberar.wait()
        executados.append(job_id)

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1, max_queue_size=10)
    await queue.start(n_workers=1)
    try:
        await queue.enqueue(_job("bloqueia"))
        await asyncio.sleep(0.05)
        await queue.enqueue(_job("na-fila"))

        assert queue.cancel("na-fila") == "queued"
        liberar.set()
        await asyncio.sleep(0.1)
        assert executados == ["bloqueia"]
    finally:
        await queue.shutdown(timeout=2)


# ── D3: faixas de config ─────────────────────────────────────────────────────

def test_env_int_rejeita_zero_e_lixo(monkeypatch, caplog):
    """MAX_CONCURRENT=0 deixava o executor online, com capacity 0 (preferido pelo
    scheduler least-loaded), aceitando jobs que nunca executariam."""
    from executor._ambiente import ler_int

    monkeypatch.setenv("_TESTE_INT", "0")
    with caplog.at_level(logging.WARNING):
        assert ler_int("_TESTE_INT", 4, minimo=1) == 4

    monkeypatch.setenv("_TESTE_INT", "nao-e-numero")
    assert ler_int("_TESTE_INT", 4, minimo=1) == 4

    monkeypatch.setenv("_TESTE_INT", "999999")
    assert ler_int("_TESTE_INT", 4, minimo=1, maximo=256) == 4

    monkeypatch.setenv("_TESTE_INT", "8")
    assert ler_int("_TESTE_INT", 4, minimo=1, maximo=256) == 8

    monkeypatch.delenv("_TESTE_INT")
    assert ler_int("_TESTE_INT", 4) == 4


def test_config_expoe_valores_saneados():
    from executor import config

    assert config.MAX_CONCURRENT >= 1
    assert config.MAX_QUEUE_SIZE >= 1
    assert config.JOB_TIMEOUT >= 1


def test_assert_configured_reclama_sem_executor_id(monkeypatch):
    """A exigencia mora aqui, e nao no import de config.py, que nao aborta mais."""
    from executor import config

    monkeypatch.setattr(config, "EXECUTOR_ID", "")
    with pytest.raises(SystemExit):
        config.assert_configured()


# ── B8: fan-out dos drive_events ─────────────────────────────────────────────

class _ManagerFake:
    def __init__(self, sync_dir: str, reivindica: set[str] | None = None):
        self.sync_dir = sync_dir
        self._reivindica = reivindica or set()

    def claims_event(self, msg: dict) -> bool:
        return msg.get("file", {}).get("original_name", "") in self._reivindica


class _ManagerSemContrato:
    """Manager que ainda nao implementou claims_event — nao pode quebrar o fan-out."""
    def __init__(self, sync_dir: str):
        self.sync_dir = sync_dir


async def _rodar_fanout(entrada, managers, filas, eventos):
    from executor.main import _drive_event_fanout

    task = asyncio.create_task(_drive_event_fanout(entrada, managers, filas))
    for ev in eventos:
        entrada.put_nowait(ev)
    await asyncio.wait_for(entrada.join(), timeout=2.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def _evento(nome: str) -> dict:
    return {"action": "file_created", "file": {"original_name": nome, "id_hash": "x"}}


@pytest.mark.asyncio
async def test_fanout_entrega_ao_manager_que_reivindica():
    """Fila unica compartilhada acordava UM waiter: com 2 pastas cada evento ia
    para um manager sorteado e o dono nunca via."""
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a", {"a.gpkg"}), _ManagerFake("/b", {"b.gpkg"})]
    filas = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _rodar_fanout(entrada, managers, filas, [_evento("b.gpkg"), _evento("a.gpkg")])

    assert filas[0].qsize() == 1 and filas[1].qsize() == 1
    assert filas[0].get_nowait()["file"]["original_name"] == "a.gpkg"
    assert filas[1].get_nowait()["file"]["original_name"] == "b.gpkg"


@pytest.mark.asyncio
async def test_fanout_manda_orfao_para_o_primario():
    """Arquivo novo nao esta em manifesto nenhum — vai para o primeiro manager."""
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a"), _ManagerFake("/b")]
    filas = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _rodar_fanout(entrada, managers, filas, [_evento("novo.gpkg")])

    assert filas[0].qsize() == 1
    assert filas[1].qsize() == 0


@pytest.mark.asyncio
async def test_fanout_tolera_manager_sem_claims_event():
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerSemContrato("/a"), _ManagerFake("/b", {"b.gpkg"})]
    filas = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _rodar_fanout(entrada, managers, filas, [_evento("b.gpkg"), _evento("?.gpkg")])

    assert filas[1].qsize() == 1   # reivindicado
    assert filas[0].qsize() == 1   # orfao cai no primario


@pytest.mark.asyncio
async def test_fanout_descarta_com_log_quando_fila_do_destino_enche(caplog):
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a")]
    filas = [asyncio.Queue(maxsize=1)]

    with caplog.at_level(logging.WARNING, logger="executor"):
        await _rodar_fanout(entrada, managers, filas, [_evento("1.gpkg"), _evento("2.gpkg")])

    assert filas[0].qsize() == 1
    assert any("cheia" in r.getMessage() for r in caplog.records)


# ── P5: espera pelos node_events sem barreira global de 30s ──────────────────

def _fila_eventos(n: int = 0):
    from executor.main import _FilaContada

    fila = _FilaContada()
    for i in range(n):
        fila.put_nowait({"node": f"n{i}"})
    return fila


async def _sender_fake(fila, intervalo: float, enviados: list | None = None):
    """Consumidor com o MESMO contrato do _event_sender_loop.

    São TRÊS passos, e a distinção importa: `task_done()` é incondicional (fecha
    o saldo do join mesmo quando o item volta para a fila), enquanto
    `confirmar_envio()` só acontece quando o `ws.send` retornou — é ele que a
    barreira de fim de job observa.
    """
    while True:
        ev = await fila.get()
        await asyncio.sleep(intervalo)
        fila.confirmar_envio(ev)
        fila.task_done()
        if enviados is not None:
            enviados.append(ev)


@pytest.mark.asyncio
async def test_drenagem_desiste_rapido_quando_ninguem_drena():
    """Com o WS caido o job pagava os 30s inteiros SEGURANDO o slot do semaforo."""
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(5)

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    await _drenar_eventos_pendentes(fila, timeout=30.0, estagnado=0.3)
    decorrido = loop.time() - inicio

    assert decorrido < 2.0, "nao pode esperar o timeout cheio sem ninguem drenando"
    assert fila.qsize() == 5


@pytest.mark.asyncio
async def test_drenagem_espera_enquanto_ha_progresso():
    """Sender vivo: a espera continua ate os eventos deste job serem enviados."""
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(6)

    sender = asyncio.create_task(_sender_fake(fila, 0.1))
    try:
        await _drenar_eventos_pendentes(fila, timeout=10.0, estagnado=0.3)
        assert fila.confirmados == 6
    finally:
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)


@pytest.mark.asyncio
async def test_drenagem_nao_desiste_com_produtor_mais_rapido_que_o_sender():
    """O bug que a heuristica de qsize introduziu.

    Fila compartilhada: o job B continua produzindo node_events mais rapido do
    que a rede entrega, entao o qsize NUNCA diminui — a versao anterior lia isso
    como "sem conexao", desistia em 3s e despachava o job_result de A com os
    eventos finais de A ainda por enviar (UI fechava o run com o grafo
    congelado). Aqui o sender esta vivo e progredindo: a barreira tem de esperar.
    """
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(0)
    enviados: list[dict] = []
    # Backlog grande o bastante para que, na janela de `estagnado`, o sender nem
    # chegue perto dos eventos de A — e o corte prematuro doa de verdade.
    for i in range(40):
        fila.put_nowait({"node": f"backlog-{i}"})
    # Os dois ultimos eventos sao do job que acabou de terminar: estao no FIM da
    # FIFO, exatamente atras do backlog alheio.
    fila.put_nowait({"node": "A-node-final"})
    fila.put_nowait({"node": "A-workflow-complete"})

    async def _produtor():
        # Mais rapido que o sender: o qsize so cresce.
        while True:
            await asyncio.sleep(0.02)
            fila.put_nowait({"node": "B-ruido"})

    sender = asyncio.create_task(_sender_fake(fila, 0.03, enviados))
    produtor = asyncio.create_task(_produtor())
    try:
        await _drenar_eventos_pendentes(fila, timeout=10.0, estagnado=0.3)
        nomes = [e["node"] for e in enviados]
        assert "A-node-final" in nomes and "A-workflow-complete" in nomes, (
            "o resultado nao pode ser despachado antes dos eventos do proprio job"
        )
        assert fila.qsize() > 0, "o cenario so vale se o produtor alheio esta a frente"
    finally:
        for t in (sender, produtor):
            t.cancel()
        await asyncio.gather(sender, produtor, return_exceptions=True)


@pytest.mark.asyncio
async def test_drenagem_nao_espera_eventos_de_outros_jobs():
    """A barreira e por marca d'agua: so cobre o que ja estava na fila.

    O `join()` global fazia o job A esperar tambem pelos eventos que o job B
    enfileirasse DEPOIS — com B produzindo sem parar, a espera nunca terminava.
    """
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(3)

    async def _produtor():
        while True:
            await asyncio.sleep(0.01)
            fila.put_nowait({"node": "B-depois"})

    sender = asyncio.create_task(_sender_fake(fila, 0.0))
    produtor = asyncio.create_task(_produtor())
    loop = asyncio.get_running_loop()
    inicio = loop.time()
    try:
        await _drenar_eventos_pendentes(fila, timeout=10.0, estagnado=0.5)
        assert loop.time() - inicio < 2.0, "nao pode esperar producao de outros jobs"
    finally:
        for t in (sender, produtor):
            t.cancel()
        await asyncio.gather(sender, produtor, return_exceptions=True)


@pytest.mark.asyncio
async def test_drenagem_cobre_eventos_publicados_via_call_soon_threadsafe():
    """ExecutorEventPublisher enfileira por callback do loop, nao na hora.

    Sem o yield inicial a marca d'agua era tirada antes de os ultimos eventos do
    job entrarem na fila — a barreira 'passava' sem cobrir nada.
    """
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(0)
    enviados: list[dict] = []
    loop = asyncio.get_running_loop()
    loop.call_soon(fila.put_nowait, {"node": "A-node-final"})

    sender = asyncio.create_task(_sender_fake(fila, 0.0, enviados))
    try:
        await _drenar_eventos_pendentes(fila, timeout=5.0, estagnado=0.3)
        assert [e["node"] for e in enviados] == ["A-node-final"]
    finally:
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)


@pytest.mark.asyncio
async def test_aguardar_confirmacao_desiste_sem_consumidor_no_shutdown():
    """Guard do shutdown: `conn_task` vivo em backoff nao e sender vivo.

    Antes o shutdown pagava 30s garantidos de `wait_for(join(), 30)` sempre que a
    conexao estava em backoff de reconexao (task viva, nenhum sender).
    """
    from executor.main import _aguardar_confirmacao

    fila = _fila_eventos(3)
    loop = asyncio.get_running_loop()
    inicio = loop.time()
    ok = await _aguardar_confirmacao(fila, rotulo="resultado", timeout=30, estagnado=0.4)
    assert ok is False
    assert loop.time() - inicio < 2.0


# ── D1: task de background observada ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_de_background_com_excecao_e_logada(caplog):
    """Um FileNotFoundError trivial matava o GeoSync em silencio."""
    from executor.main import _observar_task

    async def _explode():
        raise FileNotFoundError("pasta sumiu")

    task = asyncio.create_task(_explode(), name="geosync-teste")
    _observar_task(task)
    with caplog.at_level(logging.ERROR, logger="executor"):
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)   # deixa o done_callback rodar

    assert any("geosync-teste" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_task_cancelada_nao_vira_erro():
    from executor.main import _observar_task

    async def _dorme():
        await asyncio.sleep(30)

    task = asyncio.create_task(_dorme(), name="geosync-cancelada")
    _observar_task(task)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    # Nao levantar nada ja e o contrato: o callback retorna cedo em cancelamento.


# ── Aviso imediato de drenagem ───────────────────────────────────────────────
# `get_capacity()` passa a anunciar saturacao assim que `_shutting_down` vira
# True, mas quem ENVIA e o `_capacity_loop`, que dorme 10s ANTES de cada envio.
# Nessa janela o `_resolve_candidates` do servidor ainda elegia este executor
# pelo least-loaded e o job voltava como "Executor em shutdown." — run FAILED
# sem failover, o mesmo problema que o anuncio de saturacao existe para evitar.


@pytest.mark.asyncio
async def test_shutdown_avisa_drenagem_antes_de_qualquer_espera():
    """A ordem e o ponto: avisar DEPOIS de drenar/esperar nao fecharia a janela.

    Precisa haver um job ENFILEIRADO para a ordem ser observavel — `_drain_queued`
    so produz efeito visivel (`on_cancelled`) se tiver o que drenar. Sem isso as
    duas ordens produzem a mesma lista e o teste passa dos dois jeitos.
    """
    ordem: list[str] = []

    async def _executa(_msg):
        await asyncio.sleep(60)  # nunca conclui; o job fica preso na fila

    async def _cancelado(_msg, reason=None):
        ordem.append("drenou-fila")

    fila = ExecutorJobQueue(
        on_execute=_executa, max_concurrent=1, max_queue_size=4,
        on_cancelled=_cancelado,
    )

    async def _avisa():
        ordem.append("avisou-drenagem")

    fila.set_on_draining(_avisa)
    # Sem start(): nenhum worker consome, entao o job fica na fila ate o drain.
    assert await fila.enqueue(_job("preso"))
    await fila.shutdown(timeout=1)

    assert "drenou-fila" in ordem, "o job enfileirado precisa ter sido drenado"
    assert ordem[0] == "avisou-drenagem", (
        "o aviso precisa sair na PRIMEIRA coisa do shutdown; qualquer trabalho "
        f"antes dele reabre a janela de dispatch. Ordem observada: {ordem}"
    )


@pytest.mark.asyncio
async def test_aviso_de_drenagem_carrega_capacidade_saturada():
    """De nada adianta avisar na hora se o numero anunciado nao tira o executor
    do topo do ranking least-loaded."""
    capturado: dict = {}

    fila = ExecutorJobQueue(on_execute=lambda _m: None, max_concurrent=2, max_queue_size=5)

    async def _avisa():
        capturado.update(fila.get_capacity())

    fila.set_on_draining(_avisa)
    await fila.start()
    await fila.shutdown(timeout=1)

    # is_full() do servidor: queued + running >= max_concurrent + max_queue
    soma = capturado["queued"] + capturado["running"]
    assert soma >= capturado["max_concurrent"] + capturado["max_queue"], (
        f"capacidade anunciada ({soma}) nao satura o is_full() do servidor"
    )


@pytest.mark.asyncio
async def test_falha_no_aviso_nao_impede_o_shutdown():
    """O aviso e best-effort: se o WS ja caiu, encerrar ainda tem que funcionar."""
    async def _explode():
        raise RuntimeError("WS ja fechado")

    fila = ExecutorJobQueue(on_execute=lambda _m: None, max_concurrent=1, max_queue_size=2)
    fila.set_on_draining(_explode)
    await fila.start()
    await fila.shutdown(timeout=1)  # nao pode levantar
