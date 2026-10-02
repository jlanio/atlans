# tests/unit/test_na_fila_eterno.py
"""Execução presa em "Na fila" ('pending') para sempre — caso de 22/09.

O dispatch grava o run como 'pending' (já com o host do executor escolhido)
ANTES de enviar e só o promove para 'running' depois que `send_job` retorna. Um
worker da API que morre nessa janela deixava o run em 'pending' para sempre:
o watchdog de órfãos só olhava 'running' e ninguém mais fechava a linha.

Três defesas, uma por teste abaixo:
  * o ACK do executor promove 'pending' → 'running' (a prova de entrega vem
    do outro lado, por qualquer worker);
  * o watchdog fecha como 'failed' o 'pending' velho que nenhum executor
    confirmou;
  * o envio pelo WebSocket tem prazo — uma conexão parada não segura o
    despacho (e o agendador do worker) por até 10 min.
"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routers.executor_ws import inbox as IB
from app.api.routers.executor_ws import orfaos as ORF
from app.api.routers.executor_ws import resultados as RES
from app.core import executor_connections as ec
from app.models.base import Base
from app.models.workflow_run import WorkflowRun


# ── Banco de verdade (SQLite): o que se testa é o UPDATE condicional ─────────

@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[WorkflowRun.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _sessao():
        async with fabrica() as s:
            yield s

    monkeypatch.setattr(RES, "get_session_async", _sessao)
    monkeypatch.setattr(ORF, "get_session_async", _sessao)
    try:
        yield fabrica
    finally:
        await engine.dispose()


async def _criar_run(fabrica, *, status="pending", host="executor:ex-1", idade_min=0.0):
    run = WorkflowRun(
        id_hash=str(uuid4()), task_id=str(uuid4()), workflow_hash="wf-1",
        workspace_id="ws-1", status=status, host=host, node_stats={},
        start_time=datetime.now(timezone.utc) - timedelta(minutes=idade_min),
    )
    async with fabrica() as s:
        s.add(run)
        await s.commit()
    return run.task_id


async def _status(fabrica, task_id):
    async with fabrica() as s:
        run = await s.get(WorkflowRun, (await _pk(s, task_id)))
        return run.status, run.error_category, run.error_message


async def _pk(s, task_id):
    from sqlalchemy import select
    return (await s.execute(select(WorkflowRun.id).where(WorkflowRun.task_id == task_id))).scalar_one()


# ── 1. O ACK promove 'pending' → 'running' ───────────────────────────────────

@pytest.fixture
def ack_limpo(monkeypatch):
    monkeypatch.setattr(ec.executor_registry, "clear_pending_ack", AsyncMock(return_value="ex-1"))


async def test_ack_promove_o_run_que_o_dispatch_nao_chegou_a_promover(banco, ack_limpo):
    """O worker que despachou morreu depois do send_job: o executor tem o job e
    confirma. Antes o run ficava "Na fila" para sempre com o fluxo rodando."""
    tid = await _criar_run(banco)

    await RES._record_job_ack("ex-1", tid, "enqueued")

    assert (await _status(banco, tid))[0] == "running"


async def test_ack_em_rajada_nao_vira_um_update_por_mensagem(banco, ack_limpo, monkeypatch):
    """Cada ACK promove com UPDATE + COMMIT: sem teto, um executor com bug
    prendia uma conexão do banco em loop. Acima do teto o ACK só perde a
    promoção — o inventário a faz no minuto seguinte."""
    from app.api.routers.executor_ws import protocolo

    monkeypatch.setattr(protocolo, "_rate_state", {})
    monkeypatch.setattr(RES, "_JOB_RESULT_RATE_LIMIT", 2)
    ids = [await _criar_run(banco) for _ in range(3)]

    for tid in ids:
        await RES._record_job_ack("ex-1", tid, "enqueued")

    assert [(await _status(banco, tid))[0] for tid in ids] == ["running", "running", "pending"]


async def test_ack_de_outro_executor_nao_promove(banco, ack_limpo):
    tid = await _criar_run(banco, host="executor:ex-2")

    await RES._record_job_ack("ex-1", tid, "enqueued")

    assert (await _status(banco, tid))[0] == "pending"


@pytest.mark.parametrize("terminal", ["cancelled", "failed", "success"])
async def test_ack_nao_ressuscita_run_terminal(banco, ack_limpo, terminal):
    """Cancelado entre o INSERT e a entrega: o ACK atrasado não o traz de volta."""
    tid = await _criar_run(banco, status=terminal)

    await RES._record_job_ack("ex-1", tid, "enqueued")

    assert (await _status(banco, tid))[0] == terminal


async def test_dispatch_aceita_o_run_ja_promovido_pelo_ack():
    """O ACK costuma chegar ANTES do commit do próprio dispatch. Se o UPDATE do
    dispatch exigisse só 'pending', o rowcount 0 seria lido como cancelamento e
    o dispatch mandaria 'cancel' para um job saudável."""
    from app.services import workflow_execution_service as wes

    wf = MagicMock()
    wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
    wf.pinned_outputs = None
    wf.pin_metadata = None
    transicao = MagicMock(rowcount=1)
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=transicao)
    ag = MagicMock()
    ag.id_hash, ag.name, ag.public_key = "ag-1", "a1", "PEM"

    with patch.object(wes, "inject_credentials", new=AsyncMock(side_effect=lambda d, **k: d)), \
         patch.object(wes, "build_job_message", return_value={"ciphertext": ""}), \
         patch.object(wes, "executor_registry") as reg:
        reg.send_job = AsyncMock(return_value=True)
        reg.send_json = AsyncMock(return_value=True)
        await wes._dispatch_job(wf, {"nodes": []}, [ag], {}, False, db=db)

    stmt = db.execute.await_args_list[-1].args[0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "status IN ('pending', 'running')" in sql
    reg.send_json.assert_not_awaited()


async def test_ack_vai_pela_drenadora(monkeypatch):
    """A promoção é um UPDATE no Postgres: vai pela drenadora, não trava o loop
    de recepção."""
    vistos = []

    async def _ack(executor_id, job_id, status):
        vistos.append((executor_id, job_id, status))

    monkeypatch.setattr(IB, "_record_job_ack", _ack)
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("ack", {"job_id": "j1", "status": "enqueued"}, 10))
    inbox.put_nowait(IB._INBOX_STOP)

    await IB._drenar_inbox("ex-1", inbox)

    assert vistos == [("ex-1", "j1", "enqueued")]


async def test_ack_com_a_fila_cheia_e_processado_inline(monkeypatch):
    """Descartado, o ACK deixaria em 'pending' um job que o executor está rodando."""
    vistos = []

    async def _ack(executor_id, job_id, status):
        vistos.append(job_id)

    monkeypatch.setattr(IB, "_record_job_ack", _ack)
    inbox = IB._InboxQueue(maxsize=1)
    inbox.put_nowait(("node_event", {"run_id": "r", "node": "n", "kind": "stdout"}, 10))
    descartes = IB._novo_contador_de_descartes()

    await IB._enfileirar_mensagem("ex-1", inbox, descartes, "ack", {"job_id": "j1"}, 10)

    assert vistos == ["j1"]
    assert descartes["total"] == 0


# ── 2. O watchdog fecha o 'pending' que ninguém recebeu ──────────────────────

@pytest.fixture
def efeitos(monkeypatch):
    """Registra o que a varredura faz fora do banco."""
    feito = {"contabilizados": [], "publicados": [], "cancelados": []}

    async def _contabiliza(db, run, *a, **k):
        feito["contabilizados"].append(run.task_id)

    async def _publica(run_ids, *, status, mensagem, extra=None):
        # Nenhum destes runs falhou pelo conteúdo: repetir é seguro.
        assert (status, extra) == ("failed", {"error_category": "transient", "retryable": True})
        feito["publicados"].extend(run_ids)

    async def _cancel(executor_id, data):
        feito["cancelados"].append((executor_id, data["job_id"]))
        return True

    monkeypatch.setattr("app.core.run_result_consumer.account_terminal_run", _contabiliza)
    monkeypatch.setattr("app.services.run_events_service.publicar_conclusao", _publica)
    monkeypatch.setattr(ORF.executor_registry, "send_json", _cancel)
    # Por padrão todo host fala inventário (ou está fora do ar).
    monkeypatch.setattr(ORF, "_hosts_sem_inventario", AsyncMock(return_value=set()))
    return feito


async def test_varredura_fecha_o_pending_velho_e_preserva_o_resto(banco, efeitos):
    preso = await _criar_run(banco, idade_min=11)
    recente = await _criar_run(banco, idade_min=1)
    rodando = await _criar_run(banco, status="running", idade_min=30)
    cancelado = await _criar_run(banco, status="cancelled", idade_min=30)

    assert await ORF._fechar_runs_nao_entregues() == 1

    status, categoria, mensagem = await _status(banco, preso)
    assert (status, categoria) == ("failed", "dispatch")
    assert "não chegou a rodar" in mensagem
    assert (await _status(banco, recente))[0] == "pending"
    assert (await _status(banco, rodando))[0] == "running"
    assert (await _status(banco, cancelado))[0] == "cancelled"
    # Contabilizado uma vez, painel avisado e o host recebe o 'cancel' por
    # garantia (se o job chegou sem ACK, o executor o interrompe).
    assert efeitos["contabilizados"] == [preso]
    assert efeitos["publicados"] == [preso]
    assert efeitos["cancelados"] == [("ex-1", preso)]


async def test_varredura_concorrente_fecha_cada_run_uma_vez(banco, efeitos):
    """Os 4 workers rodam o watchdog: o UPDATE condicional faz um só vencer."""
    await _criar_run(banco, idade_min=20)

    assert await ORF._fechar_runs_nao_entregues() == 1
    assert await ORF._fechar_runs_nao_entregues() == 0
    assert len(efeitos["contabilizados"]) == 1


async def test_executor_antigo_online_tem_o_prazo_de_um_job(banco, efeitos, monkeypatch):
    """Executor sem inventário não tem como promover um job cujo ACK se perdeu
    com o worker que despachou. Fechar em 10 min cancelaria um job saudável;
    espera-se o teto de duração de um job."""
    monkeypatch.setattr(ORF, "_hosts_sem_inventario", AsyncMock(return_value={"executor:ex-velho"}))
    do_antigo = await _criar_run(banco, host="executor:ex-velho", idade_min=11)
    do_antigo_esquecido = await _criar_run(banco, host="executor:ex-velho", idade_min=7 * 60)
    do_novo = await _criar_run(banco, host="executor:ex-1", idade_min=11)
    sem_host = await _criar_run(banco, host=None, idade_min=11)

    assert await ORF._fechar_runs_nao_entregues() == 3

    assert (await _status(banco, do_antigo))[0] == "pending"
    for tid in (do_antigo_esquecido, do_novo, sem_host):
        assert (await _status(banco, tid))[0] == "failed"


async def test_quem_espera_e_o_executor_online_sem_inventario(monkeypatch):
    presenca = {"ex-velho": True, "ex-novo": True, "ex-fora": False, "ex-incerto": None}
    marcados = {"executor:ex-novo:inventario"}

    async def _presenca(executor_id):
        return presenca[executor_id]

    class _Redis:
        async def exists(self, chave):
            return int(chave in marcados)

    monkeypatch.setattr(ec, "_redis_presence_or_unknown", _presenca)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _Redis())

    esperar = await ORF._hosts_sem_inventario(
        [f"executor:{e}" for e in presenca] + [None, "manual"],
    )

    # Presença desconhecida também espera: a decisão é destrutiva.
    assert esperar == {"executor:ex-velho", "executor:ex-incerto"}


async def test_inventario_marca_o_executor_que_fala_inventario(banco, monkeypatch):
    gravadas = []

    class _Redis:
        async def setex(self, chave, ttl, valor):
            gravadas.append((chave, ttl))

        async def mget(self, chaves):
            return [None] * len(chaves)

    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _Redis())
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: None)

    await ORF._reconciliar_inventario("ex-1", {"type": "inventario", "ativos": [], "resultados": []})

    assert gravadas == [("executor:ex-1:inventario", ORF._TTL_MARCA_DE_INVENTARIO_S)]


# ── 3. O envio pelo WebSocket tem prazo ──────────────────────────────────────

class _RedisDeParada:
    def __init__(self):
        self.chaves = {}
        self.valores = {}                       # GET: a posse (`executor:conn_owner:{id}`)

    async def get(self, chave):
        return self.valores.get(chave)

    async def setex(self, chave, ttl, valor):
        self.chaves[chave] = ttl

    async def delete(self, chave):
        self.chaves.pop(chave, None)

    async def exists(self, chave):
        return int(chave in self.chaves)


class _WSLegado:
    """Imita o `--ws websockets` do uvicorn (websockets.legacy): escreve o frame
    INTEIRO e só então espera o drain — e o drain não aceita dois esperando
    (o `assert` de `_drain_helper`), nem no close."""

    def __init__(self):
        self.escritos = []
        self.escoou = asyncio.Event()
        self.fechado = None
        self._drenando = False

    async def send_text(self, texto):
        self.escritos.append(texto)
        assert not self._drenando, "drain concorrente"
        self._drenando = True
        try:
            await self.escoou.wait()
        finally:
            self._drenando = False

    async def close(self, code=1000, reason=""):
        assert not self._drenando, "drain concorrente no close"
        self.fechado = (code, reason)


@pytest.fixture
async def registro(monkeypatch):
    # Prazo de 50 ms por envio: "passar do prazo" leva milissegundos no teste.
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 0.05)
    redis = _RedisDeParada()

    async def _get_redis():
        return redis

    monkeypatch.setattr(ec, "_get_redis", _get_redis)
    reg = ec.ExecutorConnectionRegistry()
    reg.record_pending_ack = AsyncMock()
    reg.unregister = AsyncMock()
    reg.redis = redis
    yield reg
    # Encerra as saídas e tarefas soltas criadas pelo teste.
    for ws in list(ec._saidas.keys()):
        ec.encerrar_saida(ws)
    await asyncio.gather(*list(ec._tarefas_soltas), return_exceptions=True)


def _conectar(registro, ws, executor_id="ex-1"):
    conn = ec.ExecutorConnection(executor_id=executor_id, websocket=ws)
    registro._connections[executor_id] = conn
    return conn


async def _ate(condicao, prazo_s=2.0):
    fim = asyncio.get_running_loop().time() + prazo_s
    while not condicao():
        assert asyncio.get_running_loop().time() < fim, "condição não ficou verdadeira a tempo"
        await asyncio.sleep(0.005)


async def test_envio_para_conexao_parada_estoura_o_prazo(registro):
    """Antes o send_text esperava o drain até o ping timeout (10 min), com o run
    em "Na fila" e o agendador do worker parado atrás dele."""
    ws = _WSLegado()
    _conectar(registro, ws)

    enviado = await asyncio.wait_for(
        registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}), timeout=5,
    )

    # O frame já está no buffer e segue saindo: entregue SEM confirmação.
    # Tratar como recusa mandaria o job a outro executor — e os dois o rodariam.
    assert enviado is True
    registro.record_pending_ack.assert_awaited_once_with("j1", "ex-1")
    # Link lento não é conexão morta: derrubá-la apagava a presença e o
    # watchdog fechava todos os runs do executor como órfãos.
    registro.unregister.assert_not_awaited()
    assert ec._saida_de(ws).atrasada()
    # Os outros workers veem o atraso e param de relayar.
    await _ate(lambda: "executor:parada:ex-1" in registro.redis.chaves)


async def test_um_escritor_por_vez_e_quem_nao_saiu_da_fila_nao_e_escrito(registro):
    """Com o socket em backpressure, um segundo escritor disputava o drain do
    primeiro: AssertionError com o frame dele JÁ no buffer — tratado como
    falha, virava failover ou unregister. Na fila, um só escreve."""
    ws = _WSLegado()

    primeiro, segundo = await asyncio.gather(
        ec.enviar_ao_executor(ws, "job-grande"), ec.enviar_ao_executor(ws, "cancel"),
    )

    assert (primeiro, segundo) == (ec.ESCOANDO, ec.OCUPADO)
    assert ws.escritos == ["job-grande"]       # quem desistiu na fila não saiu

    ws.escoou.set()                             # o link voltou
    await _ate(lambda: not ec._saida_de(ws).atrasada())
    assert await ec.enviar_ao_executor(ws, "depois") == ec.ENVIADO
    assert ws.escritos == ["job-grande", "depois"]


async def test_com_envio_atrasado_quem_manda_nao_espera_o_prazo(registro, monkeypatch):
    """Com a escrita em curso além do próprio prazo, a mensagem nova esperaria
    atrás dela o prazo inteiro e sairia OCUPADO do mesmo jeito — prendendo o
    cancel, o controle e o laço de cancels do watchdog."""
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)

    resultado = await asyncio.wait_for(ec.enviar_ao_executor(ws, "cancel", "ex-1"), timeout=1)

    assert resultado == ec.OCUPADO
    assert list(ec._saida_de(ws).fila) == []   # nem entrou na fila


async def test_espera_conta_os_bytes_da_fila_e_nao_um_prazo_por_mensagem(registro, monkeypatch):
    """A base de 30 s somada por mensagem na frente fazia 40 eventos pequenos
    prenderem um cancel por 20 minutos."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)          # a escrita começou, dentro do prazo
    for _ in range(40):
        saida.enfileirar("evento")
    cancel = saida.enfileirar("cancel")

    # O próprio prazo + o que falta do envio em curso + os bytes da fila a 512 KB/s.
    assert saida._espera(cancel) < 2 * 30.0 + 1


async def test_fechar_resolve_a_fila_mesmo_sem_o_escritor_ter_rodado(registro, monkeypatch):
    """Um escritor cancelado antes do primeiro passo nunca chega ao próprio
    `except`: quem estava na fila esperava o prazo inteiro por um OCUPADO."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    envio = saida.enfileirar("job")             # o escritor ainda não teve a vez

    saida.encerrar()

    assert await asyncio.wait_for(saida.aguardar(envio), timeout=1) == ec.FECHANDO
    assert ws.escritos == []


async def test_resposta_de_erro_enfileira_sem_prender_o_loop_de_recebimento(registro, monkeypatch):
    """Quem responde é o loop de recebimento, o único que renova a presença:
    preso atrás de um frame lento, a presença de um executor vivo vencia."""
    from app.api.routers import executor_ws_router as rota

    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)          # socket congestionado

    rota._responder_erro(ws, "ex-1", "invalid_json")   # síncrono

    assert [e.texto for e in saida.fila] == ['{"type": "error", "reason": "invalid_json"}']
    ws.escoou.set()
    await _ate(lambda: len(ws.escritos) == 2)


async def test_resposta_de_erro_com_envio_atrasado_e_descartada(registro):
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO

    assert ec.enfileirar_ao_executor(ws, "erro", "ex-1") is False
    assert list(ec._saida_de(ws).fila) == []


async def test_mensagem_atras_de_transferencia_saudavel_espera_a_vez(registro, monkeypatch):
    """Uma transferência grande DENTRO do próprio prazo não quarentena o
    executor: quem chega atrás espera o que está na frente e sai depois (antes
    o relay desistia em 5 s, fechava o run e marcava o executor como parado)."""
    # Prazo = 0,1 s + 1 s por 512 KB: o frame grande tem ~1,1 s; o pequeno, 0,1 s.
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 0.1)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    grande_texto = "x" * (512 * 1024)
    grande = saida.enfileirar(grande_texto)
    await asyncio.sleep(0.05)                   # a escrita começou

    seguinte = asyncio.create_task(saida.enviar("relayado"))
    await asyncio.sleep(0.4)                    # além do prazo do pequeno, dentro do do grande
    ws.escoou.set()

    assert await saida.aguardar(grande) == ec.ENVIADO
    assert await seguinte == ec.ENVIADO         # esperou o que estava na frente
    assert ws.escritos == [grande_texto, "relayado"]
    assert not saida.atrasada()
    assert "executor:parada:ex-1" not in registro.redis.chaves


async def test_fechar_no_meio_de_um_envio_nao_vaza_cancelamento(registro):
    """O close cancela a espera do escritor. Quem ainda aguardava o próprio
    envio recebia CancelledError — que escapa de `except Exception`: o dispatch
    deixava o run em 'pending' e o agendador do worker morria calado."""
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    envio = saida.enfileirar("job")
    na_fila = saida.enfileirar("depois")
    await asyncio.sleep(0.01)

    aguardando = asyncio.create_task(saida.aguardar(envio))
    await asyncio.sleep(0.01)
    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")

    assert await aguardando == ec.ESCOANDO       # escrito; não CancelledError
    assert await saida.aguardar(na_fila) == ec.FECHANDO
    assert ws.fechado == (4408, "Heartbeat timeout.")
    assert await saida.enviar("mais") == ec.FECHANDO
    assert ws.escritos == ["job"]


async def test_close_chega_ao_fim_mesmo_se_quem_pediu_desistir_de_esperar(registro):
    """O unregister espera o close no máximo 2 s; cancelar o close no meio o
    abandonava para sempre (socket e buffer vivos até o TCP desistir)."""
    fechou = asyncio.Event()

    class _WSDemorado(_WSLegado):
        async def close(self, code=1000, reason=""):
            await asyncio.sleep(0.1)
            self.fechado = (code, reason)
            fechou.set()

    ws = _WSDemorado()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ec.fechar_ws_do_executor(ws, code=4409), timeout=0.01)

    await asyncio.wait_for(fechou.wait(), timeout=2)
    assert ws.fechado == (4409, "")


async def test_conexao_parada_fica_fora_do_despacho_direto(registro):
    ws = _WSLegado()
    _conectar(registro, ws)
    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is True   # atrasou

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j2"}}) is False
    assert ws.escritos == [ws.escritos[0]]      # o segundo não entrou atrás do atrasado


class _Publicados(list):
    redis = None


@pytest.fixture
def relay_publicado(monkeypatch):
    """O caminho relay com presença e capacidade livres; devolve os canais em
    que algo foi publicado (um destinatário cada)."""
    monkeypatch.setattr(ec, "_redis_check_presence", AsyncMock(return_value=True))
    monkeypatch.setattr(ec, "_redis_read_capacity", AsyncMock(return_value={}))
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    publicados = _Publicados()

    class _RedisComPublish(_RedisDeParada):
        async def publish(self, canal, envelope):
            publicados.append(canal)
            return 1

    publicados.redis = redis = _RedisComPublish()

    async def _get_redis():
        return redis

    monkeypatch.setattr(ec, "_get_redis", _get_redis)
    return publicados


@pytest.fixture
def fechados(monkeypatch):
    """Runs que o relay deu por não entregues: (executor, job, conexão fechando)."""
    from app.api.routers.executor_ws import orfaos

    fechados = []

    async def _fecha(executor_id, job_id, *, conexao_fechando=False):
        fechados.append((executor_id, job_id, conexao_fechando))
        return True

    monkeypatch.setattr(orfaos, "fechar_run_nao_entregue", _fecha)
    return fechados


async def test_socket_substituido_cai_no_relay_sem_marcar_parada(registro, relay_publicado):
    """Numa troca de conexão o socket antigo leva segundos para fechar. Antes os
    envios dele respondiam "parado" e marcavam por um minuto um executor que já
    estava saudável noutro worker."""
    ws = _WSLegado()
    _conectar(registro, ws)
    ec._saida_de(ws, "ex-1").encerrar(substituida=True)   # takeover em andamento

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is True

    assert relay_publicado == [ec._relay_channel("ex-1")]   # foi pelo relay
    assert ws.escritos == []
    assert "executor:parada:ex-1" not in relay_publicado.redis.chaves


async def test_executor_indo_embora_recusa_o_envio_em_vez_de_relayar(registro, relay_publicado):
    """Heartbeat, erro de protocolo, disconnect: sem sessão nova, o único ouvinte
    do relay era o listener deste mesmo socket, que descartava o job depois de o
    publish contar um destinatário — o send_job respondia True e o run ia a
    'running' sem o job nunca sair."""
    ws = _WSLegado()
    _conectar(registro, ws)
    ec._saida_de(ws, "ex-1")
    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False
    assert await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"}) is False

    assert relay_publicado == [] and ws.escritos == []
    registro.record_pending_ack.assert_not_awaited()


async def test_mensagem_de_controle_com_prazo_estourado_conta_como_entregue(registro, monkeypatch):
    """Um cancel que estoura o prazo segue saindo: quem cancelou não pode tratar
    o executor como fora do ar (e fechar o run com o job ainda rodando)."""
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    ws = _WSLegado()
    _conectar(registro, ws)

    assert await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"}) is True
    registro.unregister.assert_not_awaited()


async def test_cancel_atras_de_envio_atrasado_nao_e_escrito_nem_derruba(registro, monkeypatch):
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    ws = _WSLegado()
    _conectar(registro, ws)
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO

    enviado = await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"})

    # Nada saiu: quem cancelou recebe False (e o cancel_run, com o executor vivo,
    # devolve 503 em vez de fechar o run com o job rodando).
    assert enviado is False
    assert ws.escritos == ["job-grande"]
    registro.unregister.assert_not_awaited()


async def test_erro_de_envio_so_derruba_a_propria_conexao(registro):
    """Se o executor reconectou neste worker enquanto o envio falhava, a conexão
    nova fica."""
    ws = MagicMock()
    ws.send_text = AsyncMock(side_effect=RuntimeError("socket fechado"))
    _conectar(registro, ws)

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False

    registro.unregister.assert_awaited_once_with("ex-1", expected_ws=ws)


async def test_outros_workers_nao_relayam_para_socket_atrasado(registro, monkeypatch):
    monkeypatch.setattr(ec, "_redis_check_presence", AsyncMock(return_value=True))
    monkeypatch.setattr(ec, "_redis_read_capacity", AsyncMock(return_value={}))
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    await ec._redis_marcar_parada("ex-1")

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False
    assert await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"}) is False
    registro.record_pending_ack.assert_not_awaited()


async def test_a_marca_de_parada_some_quando_a_escrita_termina(registro):
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO
    await _ate(lambda: "executor:parada:ex-1" in registro.redis.chaves)

    ws.escoou.set()

    await _ate(lambda: "executor:parada:ex-1" not in registro.redis.chaves)
    assert not ec._saida_de(ws).atrasada()


async def test_relay_enfileira_e_segue_sem_prender_o_listener(registro, monkeypatch):
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    envelope = ec.build_relay_envelope('{"type": "job", "envelope": {"job_id": "j-relay"}}', executor_id="ex-1")

    continua = await asyncio.wait_for(ec._handle_relay_message("ex-1", ws, "dono", envelope), timeout=0.02)

    assert continua is True
    registro.unregister.assert_not_awaited()
    # Quem escreve é o escritor do socket, depois. Até o 3.11 o `wait_for` rodava
    # a corrotina numa task à parte e as voltas do laço davam tempo ao escritor
    # antes daqui; do 3.12 em diante ela roda na própria task e volta direto.
    await _ate(lambda: ws.escritos == ['{"type": "job", "envelope": {"job_id": "j-relay"}}'])


_JOB_RELAYADO = '{"type": "job", "envelope": {"job_id": "j-relay"}}'


async def test_job_relayado_que_nao_saiu_da_fila_tem_o_run_fechado(registro, monkeypatch, fechados):
    """Quem publicou no relay já deu o job por entregue. Sem sair da fila, o
    run ficava "Em andamento" até o ACK pendente vencer (10 min)."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO
    envelope = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", envelope) is True

    await _ate(lambda: fechados == [("ex-1", "j-relay", False)])
    assert ws.escritos == ["job-grande"]


async def test_job_relayado_para_socket_substituido_fica_com_a_sessao_nova(registro, monkeypatch, fechados):
    """Depois do takeover o listener da sessão NOVA também recebe a mensagem e a
    entrega — fechar o run pelo listener antigo o daria por não entregue."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    ec._saida_de(ws, "ex-1").encerrar(substituida=True)
    envelope = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", envelope) is True
    await asyncio.sleep(0.05)

    assert fechados == [] and ws.escritos == []


async def test_job_relayado_para_executor_indo_embora_tem_o_run_fechado(registro, monkeypatch, fechados):
    """Sem sessão nova (heartbeat, disconnect), este listener era o único
    destinatário: descartar calado deixava o run 'running' sem o job sair."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    ec._saida_de(ws, "ex-1").encerrar()
    envelope = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", envelope) is True

    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    assert ws.escritos == []


async def test_socket_fechado_antes_de_qualquer_envio_tambem_fica_fechando(registro, monkeypatch, fechados):
    """Um executor ocioso que cai por heartbeat não tinha saída: o relay criava
    uma nova, o escritor batia no socket fechado e o job relayado se perdia sem
    fechar o run (o erro do socket não o fecha)."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)

    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False
    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    assert ws.escritos == []
    registro.unregister.assert_not_awaited()     # FECHANDO, não o caminho de erro


async def test_job_na_fila_quando_chega_o_takeover_tem_o_run_fechado(registro, monkeypatch, fechados):
    """O que estava na fila foi publicado ANTES do takeover, e o listener da
    sessão nova só subscreve depois de anunciá-lo: ninguém mais o entrega."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)          # socket ocupado, dentro do prazo
    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    registro.redis.valores[ec._conn_owner_key("ex-1")] = "sessao-nova"   # já assumiu
    takeover = ec.build_relay_envelope(
        json.dumps({"__internal__": {"takeover": {"owner": "sessao-nova"}}}), executor_id="ex-1",
    )

    assert await ec._handle_relay_message("ex-1", ws, "dono", takeover) is False

    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    assert ws.escritos == ["job-grande"] and ws.fechado[0] == 4409
    assert saida.substituida and saida.avisada


async def test_job_nao_e_dado_por_nao_entregue_se_outra_sessao_tem_a_posse(registro, monkeypatch, fechados):
    """O executor reconectou noutro worker sem o aviso chegar aqui (a posse da
    sessão antiga venceu no meio do close do heartbeat): a sessão nova também
    recebe o job e o entrega. Fechar o run faria o inventário mandar parar o
    job em execução."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")
    registro.redis.valores[ec._conn_owner_key("ex-1")] = "sessao-nova"

    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    await asyncio.gather(*list(ec._tarefas_soltas), return_exceptions=True)

    assert fechados == [] and ws.escritos == []


async def test_fila_da_posse_perdida_nao_e_dada_por_nao_entregue(registro, monkeypatch, fechados):
    """Posse perdida sem o aviso de takeover: a sessão nova pode ter recebido o
    que estava na fila daqui — só o aviso garante que não."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    monkeypatch.setattr(ec, "_redis_renew_presence", AsyncMock(return_value=False))
    ws = _WSLegado()
    conn = _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)
    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    registro.redis.valores[ec._conn_owner_key("ex-1")] = "sessao-nova"
    conn.last_presence_renew = time.monotonic() - ec._PRESENCE_RENEW_INTERVAL - 1

    await registro._renew_presence_or_drop(conn)
    await asyncio.gather(*list(ec._tarefas_soltas), return_exceptions=True)

    assert saida.substituida and not saida.avisada
    assert fechados == []


async def test_socket_morto_no_relay_fecha_o_run(registro, monkeypatch, fechados):
    """O executor desconectou e o handler ainda drena a fila: o job relayado
    batia no socket morto, e nem o erro nem o listener encerrado fechavam o run
    (a reconciliação o pulava pelo ACK pendente por 10 min)."""
    ws = MagicMock()
    ws.send_text = AsyncMock(side_effect=RuntimeError("Unexpected ASGI message 'websocket.send'"))
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    primeiro = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")
    segundo = ec.build_relay_envelope('{"type": "job", "envelope": {"job_id": "j-2"}}', executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", primeiro) is True
    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    # O próximo nem entra na fila (o erro fica guardado): o listener encerra, e o run fecha.
    assert await ec._handle_relay_message("ex-1", ws, "dono", segundo) is False
    await _ate(lambda: fechados == [("ex-1", "j-relay", True), ("ex-1", "j-2", True)])


async def test_takeover_e_anunciado_mesmo_sem_dono_anterior(registro, monkeypatch):
    """A posse de uma sessão que ainda está fechando (heartbeat) vence no meio do
    close: sem dono anterior, o aviso não saía e o listener dela não sabia que
    tinha sido substituído."""
    monkeypatch.setattr(ec, "_redis_claim_presence", AsyncMock(return_value=None))
    monkeypatch.setattr(ec, "_redis_store_capacity", AsyncMock())
    anuncios = []

    async def _anuncia(executor_id, owner_token):
        anuncios.append(executor_id)

    async def _escuta(*_a):
        await asyncio.sleep(3600)

    monkeypatch.setattr(registro, "_announce_takeover", _anuncia)
    monkeypatch.setattr(ec, "_executor_pubsub_listener", _escuta)
    ws = MagicMock()
    ws.client = None

    await registro.register("ex-1", ws)

    assert anuncios == ["ex-1"]
    registro._listener_tasks["ex-1"].cancel()


async def test_sessao_antiga_nao_apaga_a_capacidade_da_nova(monkeypatch):
    """Depois de um takeover a chave de capacidade já é da sessão nova."""
    reg = ec.ExecutorConnectionRegistry()
    apagou = AsyncMock()
    monkeypatch.setattr(ec, "_redis_delete_capacity", apagou)
    monkeypatch.setattr(ec, "fechar_ws_do_executor", AsyncMock())
    for liberou, esperado in ((False, 0), (True, 1), (None, 2)):
        monkeypatch.setattr(ec, "_redis_release_presence", AsyncMock(return_value=liberou))
        reg._connections["ex-1"] = ec.ExecutorConnection(executor_id="ex-1", websocket=MagicMock())

        await reg.unregister("ex-1")

        assert apagou.await_count == esperado, liberou


async def test_drive_event_nao_engrossa_a_fila_atras_de_envio_atrasado(registro):
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO

    assert await ec._handle_drive_message("ex-1", ws, ec.build_signed_envelope('{"type": "drive_event"}')) is True

    assert list(ec._saida_de(ws).fila) == []


async def test_takeover_sai_antes_de_o_listener_novo_subscrever(registro, monkeypatch):
    """Com o listener novo já subscrito, o que fosse publicado antes do takeover
    chegaria às DUAS sessões (job rodando duas vezes) — e a antiga, ao fechar,
    não saberia se a nova o recebeu."""
    ordem = []
    monkeypatch.setattr(ec, "_redis_claim_presence", AsyncMock(return_value="dono-antigo"))
    monkeypatch.setattr(ec, "_redis_store_capacity", AsyncMock())

    async def _escuta(*_a):
        ordem.append("listener")
        await asyncio.sleep(3600)

    async def _anuncia(executor_id, owner_token):
        await asyncio.sleep(0)                  # o publish de verdade espera o Redis
        ordem.append("takeover")

    monkeypatch.setattr(ec, "_executor_pubsub_listener", _escuta)
    monkeypatch.setattr(registro, "_announce_takeover", _anuncia)
    ws = MagicMock()
    ws.client = None

    await registro.register("ex-1", ws)
    await _ate(lambda: len(ordem) == 2)

    assert ordem == ["takeover", "listener"]
    registro._listener_tasks["ex-1"].cancel()


async def test_posse_perdida_manda_o_resto_pelo_relay(registro, monkeypatch):
    """A renovação achou outro dono: até o unregister (que espera a trava), o que
    for mandado a este executor vai à sessão nova pelo relay, não ao socket velho."""
    monkeypatch.setattr(ec, "_redis_renew_presence", AsyncMock(return_value=False))
    ws = _WSLegado()                            # nada saiu ainda por este socket
    conn = _conectar(registro, ws)
    conn.last_presence_renew = time.monotonic() - ec._PRESENCE_RENEW_INTERVAL - 1

    await registro._renew_presence_or_drop(conn)

    registro.unregister.assert_awaited_once_with("ex-1", expected_ws=ws)
    saida = ec._saidas[ws]
    assert saida.fechando and saida.substituida
    assert registro._conexao_para_envio("ex-1") is None


async def test_reconexao_limpa_a_marca_de_parada(registro, monkeypatch):
    """Socket novo, nada escoando: a marca da sessão anterior recusaria o relay
    para um executor saudável."""
    monkeypatch.setattr(ec, "_redis_claim_presence", AsyncMock(return_value=None))
    monkeypatch.setattr(ec, "_redis_store_capacity", AsyncMock())

    async def _escuta(*_a):
        await asyncio.sleep(3600)

    monkeypatch.setattr(ec, "_executor_pubsub_listener", _escuta)
    await ec._redis_marcar_parada("ex-1")
    ws = MagicMock()
    ws.client = None

    await registro.register("ex-1", ws)

    assert "executor:parada:ex-1" not in registro.redis.chaves
    registro._listener_tasks["ex-1"].cancel()


def test_prazo_cresce_com_o_tamanho_do_frame():
    assert ec._prazo_de_envio(0) == ec._PRAZO_DE_ENVIO_BASE_S
    # 16 MB (o teto do frame) ganha ~32 s a mais que um frame vazio.
    assert ec._prazo_de_envio(16 * 1024 * 1024) == pytest.approx(ec._PRAZO_DE_ENVIO_BASE_S + 32)


def test_a_api_fixa_a_implementacao_de_websocket_que_o_envio_pressupoe():
    """A `_Saida` conta com o frame inteiro escrito antes do drain (o
    `websockets` legacy do uvicorn). Na `websockets-sansio`/`wsproto` a escrita
    espera o socket ANTES — um prazo estourado seria um job dado por entregue
    sem ter saído. O `auto` escolhe a certa hoje; o pino impede a troca muda."""
    from pathlib import Path

    import yaml

    raiz = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load((raiz / "docker-compose.yml").read_text(encoding="utf-8"))
    for servico in ("api-prod", "api"):
        assert "--ws websockets" in compose["services"][servico]["command"], servico
    assert '"--ws", "websockets"' in (raiz / "Dockerfile.api").read_text(encoding="utf-8")
