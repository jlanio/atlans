# tests/unit/test_reconciliacao_inventario.py
"""Reconciliação executor↔servidor e cancelamento de job desconhecido.

Casos reais que motivaram:
  * 22/09 — o titan seguiu conectado com três runs que nunca recebeu; eles
    ficaram "Em andamento" até ele desconectar, 16 min depois, e só então viraram
    "Executor desconectou durante a execução".
  * um executor foi morto pelo OOM do cgroup no meio de uma análise, voltou
    em 6 s e ninguém fechou a execução que ele rodava.
  * Cancelar um run que o executor não tinha era silêncio: o executor logava
    "unknown" e o run seguia "Em andamento" para sempre.
"""
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routers.executor_ws import inbox as IB
from app.api.routers.executor_ws import orfaos as ORF
from app.api.routers.executor_ws import resultados as RES
from app.models.base import Base
from app.models.workflow_run import WorkflowRun


# ═══ Servidor ════════════════════════════════════════════════════════════════

class _RedisFalso:
    def __init__(self, chegou=()):
        self.chegou = set(chegou)

    async def mget(self, chaves):
        return ["{}" if c in self.chegou else None for c in chaves]


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
    # Sem conexão registrada: o intervalo mínimo entre reconciliações não se aplica.
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: None)
    try:
        yield fabrica
    finally:
        await engine.dispose()


@pytest.fixture
def efeitos(monkeypatch):
    feito = {"contabilizados": [], "publicados": [], "cancelados": [], "redis": _RedisFalso()}

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
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: feito["redis"])
    return feito


async def _run(fabrica, *, status="running", host="executor:ex-1", idade_min=5.0):
    run = WorkflowRun(
        id_hash=str(uuid4()), task_id=str(uuid4()), workflow_hash="wf-1",
        workspace_id="ws-1", status=status, host=host, node_stats={},
        start_time=datetime.now(timezone.utc) - timedelta(minutes=idade_min),
    )
    async with fabrica() as s:
        s.add(run)
        await s.commit()
    return run.task_id


async def _linha(fabrica, task_id):
    async with fabrica() as s:
        return (await s.execute(select(WorkflowRun).where(WorkflowRun.task_id == task_id))).scalar_one()


def _inventario(ativos=(), resultados=(), truncado=False):
    return {"type": "inventario", "ativos": list(ativos), "resultados": list(resultados), "truncado": truncado}


async def test_run_que_o_executor_nao_tem_e_fechado_como_perdido(banco, efeitos):
    """O caso do titan: conectado, sem o job, e o run "Em andamento"."""
    perdido = await _run(banco)

    feito = await ORF._reconciliar_inventario("ex-1", _inventario())

    assert feito["fechados"] == 1
    linha = await _linha(banco, perdido)
    assert (linha.status, linha.error_category) == ("failed", "executor_lost")
    assert "não tinha mais esta execução" in linha.error_message
    assert efeitos["contabilizados"] == [perdido]
    assert efeitos["publicados"] == [perdido]


async def test_job_ainda_a_caminho_nao_e_fechado_como_perdido(banco, efeitos):
    """Um envio que estourou o prazo segue escoando pelo socket por tempo
    indefinido: com o ACK pendente vivo, o run não está perdido — fechá-lo
    deixaria o executor rodar, com efeitos, um job de run já encerrado."""
    a_caminho = await _run(banco)
    efeitos["redis"].chegou.add(f"executor:pending_ack:{a_caminho}")

    feito = await ORF._reconciliar_inventario("ex-1", _inventario())

    assert feito["fechados"] == 0
    assert (await _linha(banco, a_caminho)).status == "running"


async def test_run_fechado_como_perdido_recebe_cancel(banco, efeitos):
    """Se o job ainda chegar, o cancel chega depois dele pelo mesmo socket e o
    interrompe — ou vira lápide."""
    perdido = await _run(banco)

    await ORF._reconciliar_inventario("ex-1", _inventario())
    await asyncio.gather(*ORF._cancels_em_curso)   # saem em segundo plano

    assert ("ex-1", perdido) in efeitos["cancelados"]


async def test_run_de_job_descartado_no_relay_fecha_como_nao_entregue(banco, efeitos, monkeypatch):
    limpos = []

    async def _limpa(job_id, expected_executor_id=None):
        limpos.append((job_id, expected_executor_id))

    monkeypatch.setattr(ORF.executor_registry, "clear_pending_ack", _limpa)
    tid = await _run(banco, status="running")
    alheio = await _run(banco, status="running", host="executor:ex-2")
    terminou = await _run(banco, status="success")
    no_fechamento = await _run(banco, status="running")

    assert await ORF.fechar_run_nao_entregue("ex-1", tid) is True
    assert await ORF.fechar_run_nao_entregue("ex-1", alheio) is False     # host de outro
    assert await ORF.fechar_run_nao_entregue("ex-1", terminou) is False   # já terminal
    assert await ORF.fechar_run_nao_entregue("ex-1", no_fechamento, conexao_fechando=True) is True

    linha = await _linha(banco, tid)
    assert (linha.status, linha.error_category) == ("failed", "dispatch")
    assert "envio anterior" in linha.error_message
    # O motivo certo para quem lê: a conexão fechava, não havia fila.
    assert "sendo encerrada" in (await _linha(banco, no_fechamento)).error_message
    assert efeitos["contabilizados"] == [tid, no_fechamento]
    assert efeitos["publicados"] == [tid, no_fechamento]
    assert limpos == [(tid, "ex-1"), (no_fechamento, "ex-1")]


async def test_cancels_da_reconciliacao_nao_prendem_a_drenadora(banco, efeitos, monkeypatch):
    """A reconciliação roda na drenadora da conexão: com o socket congestionado,
    cada cancel inline podia esperar a vez pelo prazo inteiro, atrasando os
    job_results daquela conexão."""
    liberar = asyncio.Event()

    async def _cancel_lento(executor_id, data):
        await liberar.wait()
        efeitos["cancelados"].append((executor_id, data["job_id"]))
        return True

    monkeypatch.setattr(ORF.executor_registry, "send_json", _cancel_lento)
    perdido = await _run(banco)

    feito = await asyncio.wait_for(ORF._reconciliar_inventario("ex-1", _inventario()), timeout=2)

    assert feito["fechados"] == 1 and efeitos["cancelados"] == []
    liberar.set()
    await asyncio.gather(*ORF._cancels_em_curso)
    assert efeitos["cancelados"] == [("ex-1", perdido)]


async def test_o_que_o_executor_tem_fica_como_esta(banco, efeitos):
    rodando = await _run(banco)
    terminou = await _run(banco)   # resultado no outbox do executor, a caminho

    await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[rodando], resultados=[terminou]))

    assert (await _linha(banco, rodando)).status == "running"
    assert (await _linha(banco, terminou)).status == "running"
    assert efeitos["contabilizados"] == []


async def test_run_recente_nao_e_julgado(banco, efeitos):
    """Um job ainda em trânsito quando o executor montou o inventário não é perda."""
    novo = await _run(banco, idade_min=1)

    await ORF._reconciliar_inventario("ex-1", _inventario())

    assert (await _linha(banco, novo)).status == "running"


async def test_resultado_recem_chegado_ao_servidor_protege_o_run(banco, efeitos):
    """O job_result já passou pelo WS (chave com TTL de 300 s) e o consumer
    ainda vai fechar o run: fechá-lo aqui apagaria o desfecho real."""
    tid = await _run(banco)
    efeitos["redis"].chegou.add(f"executor:ex-1:results:{tid}")

    await ORF._reconciliar_inventario("ex-1", _inventario())

    assert (await _linha(banco, tid)).status == "running"


async def test_redis_fora_do_ar_adia_sem_fechar(banco, efeitos, monkeypatch):
    tid = await _run(banco)

    class _RedisQuebrado:
        async def mget(self, _chaves):
            raise ConnectionError("redis fora")

    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _RedisQuebrado())

    await ORF._reconciliar_inventario("ex-1", _inventario())

    assert (await _linha(banco, tid)).status == "running"


async def test_pending_que_o_executor_nao_tem_vira_nao_entregue(banco, efeitos):
    tid = await _run(banco, status="pending")

    await ORF._reconciliar_inventario("ex-1", _inventario())

    linha = await _linha(banco, tid)
    assert (linha.status, linha.error_category) == ("failed", "dispatch")
    assert "não chegou a rodar" in linha.error_message


async def test_pending_que_o_executor_tem_e_promovido(banco, efeitos):
    """ACK perdido: o inventário é a segunda prova de entrega."""
    tid = await _run(banco, status="pending", idade_min=0.5)

    feito = await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[tid]))

    assert feito["promovidos"] == 1
    assert (await _linha(banco, tid)).status == "running"


async def test_zumbi_que_o_servidor_ja_fechou_recebe_cancel(banco, efeitos):
    """Cancelado com o executor fora do ar: ele volta ainda rodando o job."""
    tid = await _run(banco, status="cancelled")

    feito = await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[tid]))
    await asyncio.gather(*ORF._cancels_em_curso)   # saem em segundo plano

    assert feito["parados"] == 1
    assert efeitos["cancelados"] == [("ex-1", tid)]


async def test_inventario_truncado_nao_fecha_por_ausencia(banco, efeitos):
    perdido = await _run(banco)
    pendente = await _run(banco, status="pending", idade_min=0.5)

    feito = await ORF._reconciliar_inventario(
        "ex-1", _inventario(ativos=[pendente], truncado=True),
    )

    assert feito["fechados"] == 0
    assert (await _linha(banco, perdido)).status == "running"
    assert (await _linha(banco, pendente)).status == "running"   # promover continua valendo


async def test_runs_de_outro_executor_nao_sao_tocados(banco, efeitos):
    alheio = await _run(banco, host="executor:ex-2")
    alheio_pendente = await _run(banco, host="executor:ex-2", status="pending", idade_min=0.5)

    await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[alheio_pendente]))

    assert (await _linha(banco, alheio)).status == "running"
    assert (await _linha(banco, alheio_pendente)).status == "pending"


async def test_inventario_malformado_e_ignorado(banco, efeitos):
    tid = await _run(banco)

    assert await ORF._reconciliar_inventario("ex-1", {"type": "inventario", "ativos": "tudo"}) == {}
    assert (await _linha(banco, tid)).status == "running"


async def test_intervalo_minimo_entre_reconciliacoes(banco, efeitos, monkeypatch):
    """Um executor com bug não transforma o inventário num SELECT por mensagem."""
    conn = SimpleNamespace(
        ultima_reconciliacao=0.0, connected_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: conn)
    await _run(banco)

    primeira = await ORF._reconciliar_inventario("ex-1", _inventario())
    segunda = await ORF._reconciliar_inventario("ex-1", _inventario())

    assert primeira["fechados"] == 1
    assert segunda == {}


async def test_conexao_recem_aberta_nao_fecha_por_ausencia(banco, efeitos, monkeypatch):
    """Reconexão: o inbox da conexão ANTERIOR ainda pode estar drenando o
    job_result de um run que terminou antes da queda. O primeiro inventário da
    sessão nova não o lista — fechar agora faria o resultado verdadeiro ser
    recusado logo depois. Promover e parar zumbis não esperam."""
    conn = SimpleNamespace(ultima_reconciliacao=0.0, connected_at=datetime.now(timezone.utc))
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: conn)
    terminou_antes_da_queda = await _run(banco)
    na_fila = await _run(banco, status="pending")

    feito = await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[na_fila]))

    assert feito == {"promovidos": 1, "parados": 0, "fechados": 0}
    assert (await _linha(banco, terminou_antes_da_queda)).status == "running"
    assert (await _linha(banco, na_fila)).status == "running"


async def test_inventario_vai_pela_drenadora_depois_do_job_result(monkeypatch):
    """Na mesma fila: o job_result enviado antes do inventário é gravado antes
    de o inventário ser conferido — senão o run recém-terminado pareceria perdido."""
    ordem = []

    async def _resultado(executor_id, msg, frame_bytes=0, **_kw):
        ordem.append(("job_result", msg["job_id"]))

    async def _reconcilia(executor_id, msg):
        ordem.append(("inventario", tuple(msg["ativos"])))

    monkeypatch.setattr(IB, "_handle_job_result", _resultado)
    monkeypatch.setattr(IB, "_reconciliar_inventario", _reconcilia)
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("job_result", {"job_id": "j1"}, 10))
    inbox.put_nowait(("inventario", _inventario(), 10))
    inbox.put_nowait(IB._INBOX_STOP)

    await IB._drenar_inbox("ex-1", inbox)

    assert ordem == [("job_result", "j1"), ("inventario", ())]


async def test_inventario_com_a_fila_cheia_e_descartado(monkeypatch):
    """Periódico: o próximo chega em um minuto; não vale back-pressure."""
    chamado = []
    monkeypatch.setattr(IB, "_reconciliar_inventario", lambda *a: chamado.append(a))
    inbox = IB._InboxQueue(maxsize=1)
    inbox.put_nowait(("job_result", {"job_id": "x"}, 10))
    descartes = IB._novo_contador_de_descartes()

    await IB._enfileirar_mensagem("ex-1", inbox, descartes, "inventario", _inventario(), 10)

    assert descartes["total"] == 1 and chamado == []


# ── Consumer: o primeiro desfecho vale ───────────────────────────────────────

def _db_do_consumer(run):
    selecionado = MagicMock()
    selecionado.scalar_one_or_none.return_value = run
    db = AsyncMock()
    db.execute = AsyncMock(return_value=selecionado)
    return db


def _payload(status):
    return {"task_id": "run-1", "status": status, "stats": {},
            "end_time": datetime.now(timezone.utc).isoformat()}


async def test_desfecho_tardio_diferente_nao_sobrescreve_o_primeiro(monkeypatch):
    """O resultado verdadeiro (success) e um tardio (um 'cancelled' vindo de um
    cancel que cruzou com o fim do job) passaram os dois pela checagem do WS
    antes de o primeiro ser gravado. O consumer gravava os dois, e o último
    vencia: um sucesso virava cancelado — e o uso era contado duas vezes."""
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="success", node_stats={})
    db = _db_do_consumer(run)
    grava = AsyncMock()
    fase = AsyncMock(return_value=rrc.PHASE_OK)
    monkeypatch.setattr(rrc, "_update_run_status", grava)
    monkeypatch.setattr(rrc, "_run_phase", fase)

    assert await rrc._process_result(db, _payload("cancelled")) is True

    assert run.status == "success"
    grava.assert_not_awaited()
    fase.assert_not_awaited()          # nem uso, nem métricas, nem notificação
    db.commit.assert_awaited()         # solta a trava do FOR UPDATE
    # Dois workers com o mesmo run: o segundo espera o commit do primeiro.
    from sqlalchemy.dialects import postgresql
    select_do_run = db.execute.await_args_list[0].args[0]
    assert "FOR UPDATE" in str(select_do_run.compile(dialect=postgresql.dialect()))


async def test_resultado_verdadeiro_corrige_o_desfecho_que_o_servidor_deduziu(monkeypatch):
    """O servidor fechou o run como perdido (executor caiu, reconciliação) com o
    resultado verdadeiro já na fila: o resultado corrige o palpite, como sempre
    corrigiu. Só um desfecho REAL (ou o cancelamento do usuário) é definitivo."""
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="failed", error_category="executor_lost", node_stats={})
    grava = AsyncMock()
    monkeypatch.setattr(rrc, "_update_run_status", grava)
    monkeypatch.setattr(rrc, "_run_phase", AsyncMock(return_value=rrc.PHASE_OK))

    assert await rrc._process_result(_db_do_consumer(run), _payload("success")) is True

    grava.assert_awaited_once()


async def test_cancelamento_do_usuario_nao_e_desfeito_por_resultado_tardio(monkeypatch):
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="cancelled", node_stats={})
    grava = AsyncMock()
    monkeypatch.setattr(rrc, "_update_run_status", grava)

    assert await rrc._process_result(_db_do_consumer(run), _payload("success")) is True

    grava.assert_not_awaited()


async def test_orfao_nao_sobrescreve_resultado_gravado_no_meio(banco, efeitos, monkeypatch):
    """Entre o SELECT dos órfãos e o commit, o consumer gravou o resultado
    verdadeiro. O UPDATE por PK do ORM o sobrescrevia com 'failed' — e o uso
    era contado duas vezes."""
    from sqlalchemy import update as sa_update

    run_id = await _run(banco)
    real = ORF.get_session_async

    @asynccontextmanager
    async def _com_corrida():
        async with real() as sessao:
            original = sessao.execute
            feito = {"n": 0}

            async def _execute(stmt, *a, **k):
                resultado = await original(stmt, *a, **k)
                feito["n"] += 1
                if feito["n"] == 1:   # logo depois do SELECT, o consumer grava
                    async with banco() as outra:
                        await outra.execute(
                            sa_update(WorkflowRun).where(WorkflowRun.task_id == run_id)
                            .values(status="success")
                        )
                        await outra.commit()
                return resultado

            sessao.execute = _execute
            yield sessao

    monkeypatch.setattr(ORF, "get_session_async", _com_corrida)

    await ORF._fail_orphan_runs("ex-1")

    assert (await _linha(banco, run_id)).status == "success"
    assert efeitos["contabilizados"] == [] and efeitos["publicados"] == []


async def test_orfao_fecha_o_run_que_ficou_rodando(banco, efeitos):
    run_id = await _run(banco)

    await ORF._fail_orphan_runs("ex-1")

    linha = await _linha(banco, run_id)
    assert (linha.status, linha.error_category) == ("failed", "executor_lost")
    assert linha.duration_seconds and linha.duration_seconds > 0
    assert efeitos["contabilizados"] == [run_id] and efeitos["publicados"] == [run_id]


async def test_reentrega_do_mesmo_desfecho_segue_como_antes(monkeypatch):
    """Dead letter reprocessado: as fases rodam de novo, sem recontar o uso."""
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="success", node_stats={})
    grava = AsyncMock()
    chamadas = []

    async def _fase(db, run, task_id, label, fn, *args):
        chamadas.append((label, args[-1] if label == "uso diario" else None))
        return rrc.PHASE_OK

    monkeypatch.setattr(rrc, "_update_run_status", grava)
    monkeypatch.setattr(rrc, "_run_phase", _fase)

    assert await rrc._process_result(_db_do_consumer(run), _payload("success")) is True

    grava.assert_awaited_once()
    assert ("uso diario", False) in chamadas   # first_close=False: não reconta


# ── cancel_run com o executor fora do ar ─────────────────────────────────────

def _mock_db(*resultados):
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=list(resultados))
    return db


def _select(run):
    r = MagicMock()
    r.scalar_one_or_none.return_value = run
    return r


async def test_cancelar_com_o_executor_fora_do_ar_fecha_no_servidor():
    """Antes era 503 e o run perdido não tinha como ser limpo pela tela."""
    from app.services import workflow_execution_service as wes

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws", status="running",
                      host="executor:ex-1", node_stats={})
    db = _mock_db(_select(run), MagicMock(rowcount=1))

    with patch.object(wes, "executor_registry") as reg, \
         patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()) as contabiliza:
        reg.send_json = AsyncMock(return_value=False)
        reg.presence_or_unknown = AsyncMock(return_value=False)
        outcome = await wes.cancel_run(db, "run-1", user_id="u", como_admin=True)

    assert outcome == "cancelled"
    assert run.status == "cancelled"
    assert "fora do ar" in run.error_message
    contabiliza.assert_awaited_once()
    # Condicional: um job_result que chegue no meio vence.
    sql = str(db.execute.await_args_list[-1].args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "status IN ('pending', 'running')" in sql


async def test_cancelar_offline_perde_para_o_resultado_que_chegou():
    from app.services import workflow_execution_service as wes

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws", status="running",
                      host="executor:ex-1", node_stats={})
    db = _mock_db(_select(run), MagicMock(rowcount=0))

    async def _refresh(obj):
        obj.status = "success"

    db.refresh = AsyncMock(side_effect=_refresh)
    with patch.object(wes, "executor_registry") as reg:
        reg.send_json = AsyncMock(return_value=False)
        reg.presence_or_unknown = AsyncMock(return_value=False)
        outcome = await wes.cancel_run(db, "run-1", user_id="u", como_admin=True)

    assert outcome == "already_finished"
    assert run.status == "success"


# ═══ Executor ════════════════════════════════════════════════════════════════

@pytest.fixture
def store(tmp_path, monkeypatch):
    from executor import result_store
    monkeypatch.setattr(result_store, "_DB_PATH", str(tmp_path / "outbox.sqlite"))
    monkeypatch.setattr(result_store, "_conn", None)
    monkeypatch.setattr(result_store, "_disabled", False)
    monkeypatch.setattr(result_store, "_trava_do_diario", None)
    monkeypatch.setattr(result_store, "_esperando_posse", False)
    monkeypatch.setattr(result_store, "_INTERVALO_DE_POSSE_S", 0.02)
    yield result_store
    result_store.close()
    # Quem subiu sem a trava tenta de novo em segundo plano: espera essa volta
    # terminar para ela não vazar para o próximo teste.
    for _ in range(300):
        if not result_store._esperando_posse:
            break
        time.sleep(0.01)
    if result_store._trava_do_diario is not None:
        result_store._trava_do_diario.close()


def test_job_aceito_fica_no_diario_ate_o_resultado(store):
    store.registrar_em_voo("j1")
    store.registrar_em_voo("j2")
    store.marcar_executando("j2")

    store.put({"job_id": "j1", "run_id": "j1", "status": "ok"})

    # O resultado tira o job do diário na mesma transação — senão a tabela
    # cresceria uma linha por job durante toda a vida do processo.
    linhas = store._get_conn().execute("SELECT job_id FROM jobs_em_voo").fetchall()
    assert [r[0] for r in linhas] == ["j2"]
    # j1 terminou (resultado no outbox); j2 morreu no meio.
    assert [o["job_id"] for o in store.carregar_em_voo()] == ["j2"]
    assert store.carregar_em_voo()[0]["estado"] == store.ESTADO_EXECUTANDO
    assert store.job_ids_pendentes() == ["j1"]


def test_outbox_guarda_a_categoria_para_o_replay(store):
    store.put({"job_id": "j1", "status": "error", "error": "x", "error_category": "executor_lost"})
    assert store.load_pending()[0]["error_category"] == "executor_lost"


def test_orfao_do_boot_vira_falha_com_a_causa(store, monkeypatch):
    """O caso do OOM: morto no meio, o executor volta e reporta o que perdeu."""
    from executor import main as M

    monkeypatch.setattr("executor.sysinfo._get_cgroup_ram_total", lambda: 2 * 1024 ** 3)
    store.registrar_em_voo("rodando")
    store.marcar_executando("rodando")
    store.registrar_em_voo("na-fila")

    assert M._fechar_orfaos_do_boot_anterior() == 2

    resultados = {r["job_id"]: r for r in store.load_pending()}
    assert resultados["rodando"]["status"] == "error"
    assert resultados["rodando"]["error_category"] == "executor_lost"
    assert "no meio desta execução" in resultados["rodando"]["error"]
    assert "2,0 GB" in resultados["rodando"]["error"]
    assert "antes de começar" in resultados["na-fila"]["error"]
    # Saíram do diário: o próximo boot não os reporta de novo.
    assert store.carregar_em_voo() == []


def test_orfaos_de_outro_processo_vivo_nao_viram_falha(store):
    """Desktop: o app morto à força deixa o Python antigo drenando e a reabertura
    sobe outro processo com o mesmo outbox. Os jobs no diário são do antigo, que
    ainda os termina — convertê-los faria o resultado verdadeiro ser recusado."""
    fcntl = pytest.importorskip("fcntl")
    from executor import main as M

    store.registrar_em_voo("do-processo-antigo")
    store.marcar_executando("do-processo-antigo")
    with open(store._DB_PATH + ".dono", "a+b") as dono_vivo:
        fcntl.flock(dono_vivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        assert M._fechar_orfaos_do_boot_anterior() == 0

    assert store.load_pending() == []
    assert [o["job_id"] for o in store.carregar_em_voo()] == ["do-processo-antigo"]


def test_quem_subiu_sem_a_trava_assume_quando_o_outro_sai(store):
    """A segura a trava; B sobe e não a consegue; A sai. Se B não tentasse de
    novo, um terceiro (C) pegaria a trava livre e converteria em falha os jobs
    VIVOS de B — o caso que a trava existe para evitar."""
    fcntl = pytest.importorskip("fcntl")
    a = open(store._DB_PATH + ".dono", "a+b")
    fcntl.flock(a.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    assert store.tomar_posse_do_diario() is False    # B sobe com A vivo
    a.close()                                         # A sai
    for _ in range(300):
        if store._trava_do_diario is not None:
            break
        time.sleep(0.01)

    assert store._trava_do_diario is not None         # B virou o dono
    with open(store._DB_PATH + ".dono", "a+b") as c:  # C sobe agora
        with pytest.raises(BlockingIOError):
            fcntl.flock(c.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_posse_do_diario_fica_com_o_processo(store):
    fcntl = pytest.importorskip("fcntl")

    assert store.tomar_posse_do_diario() is True
    assert store.tomar_posse_do_diario() is True   # idempotente no mesmo processo
    with open(store._DB_PATH + ".dono", "a+b") as outro:
        with pytest.raises(BlockingIOError):
            fcntl.flock(outro.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_causa_sem_limite_de_container():
    from executor import main as M
    assert M._causa_da_interrupcao("executando", None).endswith("falta de memória na máquina.")


async def test_fila_lista_os_ativos_e_guarda_lapide():
    from executor.job_queue import ExecutorJobQueue

    cancelados = []

    async def _on_cancelled(message):
        cancelados.append((message["envelope"]["job_id"], message.get("cancel_reason")))

    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=_on_cancelled)
    await fila.enqueue({"envelope": {"job_id": "j1"}})

    assert fila.job_ids_ativos() == ["j1"]

    await fila.encerrar_desconhecido("j9", "motivo")

    assert cancelados == [("j9", "motivo")]
    assert fila.cancelado_antes_de_chegar("j9") is True
    assert fila.cancelado_antes_de_chegar("j9") is False   # a lápide é consumida


def _conexao_nova(result_queue=None):
    from executor.job_queue import ExecutorJobQueue

    return _conexao(ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=AsyncMock()), result_queue)


def test_resultado_enviado_ha_pouco_segue_no_inventario(store, monkeypatch):
    """`mark_sent` apaga o outbox assim que o send retorna, mas o servidor pode
    ainda nem ter processado o resultado (a conexão caiu logo depois). Sem esta
    memória o inventário da sessão nova dizia "não tenho" e o servidor fechava o
    run como perdido — recusando o resultado verdadeiro em seguida."""
    from executor import connection as C

    conn = _conexao_nova()
    store.put({"job_id": "j1", "status": "ok"})
    conn._lembrar_enviado("j1")
    store.mark_sent("j1")

    assert conn._montar_inventario()["resultados"] == ["j1"]

    agora = time.monotonic()
    monkeypatch.setattr(C.time, "monotonic", lambda: agora + C._ENVIADOS_TTL_S + 1)
    assert conn._montar_inventario()["resultados"] == []   # passou do prazo: perdido


async def test_cancel_de_job_que_acabou_de_terminar_nao_vira_cancelado(store):
    """O resultado verdadeiro saiu; um 'cancelled' sintético por cima dele podia
    vencer no consumer do servidor e apagar um sucesso."""
    conn = _conexao_nova()
    conn._lembrar_enviado("j1")

    assert await conn._encerrar_cancelamento_desconhecido("j1") == "resultado_pendente"
    assert conn._queue.cancelado_antes_de_chegar("j1") is False   # nenhuma lápide


async def test_cancel_com_resultado_na_fila_em_memoria_nao_vira_cancelado(store):
    fila = asyncio.Queue()
    fila.put_nowait({"job_id": "j1", "status": "ok"})
    conn = _conexao_nova(fila)

    assert await conn._encerrar_cancelamento_desconhecido("j1") == "resultado_pendente"


async def test_outbox_ilegivel_nao_afirma_ausencia(store, monkeypatch):
    """Ler [] de um outbox travado diria "nada pendente": o servidor fecharia
    como perdidos runs cujo resultado está no disco. O inventário pula a volta
    e o cancel não inventa desfecho."""
    conn = _conexao_nova()
    monkeypatch.setattr(store, "_get_conn", MagicMock(side_effect=RuntimeError("database is locked")))

    assert store.job_ids_pendentes() is None
    # O inventário sai, marcado `truncado`: o servidor promove e para zumbis mas
    # não fecha por ausência — e a marca de "fala inventário" não vence (senão a
    # varredura dos 'pending' trataria o executor como antigo).
    assert conn._montar_inventario()["truncado"] is True
    assert await conn._encerrar_cancelamento_desconhecido("j1") == "outbox_ilegivel"


def test_executor_movimentado_nao_desliga_a_propria_reconciliacao(store):
    """Os enviados há pouco só ocupam o espaço que sobra e não marcam
    `truncado` — a ~3 jobs/s eles encheriam o inventário e o servidor nunca
    mais fecharia um run perdido deste executor."""
    from executor import connection as C

    conn = _conexao_nova()
    for i in range(C._INVENTARIO_MAX + 500):
        conn._lembrar_enviado(f"j{i}")

    inventario = conn._montar_inventario()

    assert inventario["truncado"] is False
    assert len(inventario["resultados"]) == C._INVENTARIO_MAX
    assert inventario["resultados"][0] == f"j{C._INVENTARIO_MAX + 499}"   # mais recentes primeiro


def test_lapide_vence(monkeypatch):
    from executor import job_queue as JQ

    fila = JQ.ExecutorJobQueue(on_execute=AsyncMock())
    fila.lapidar("j1")
    agora = time.monotonic()
    monkeypatch.setattr(JQ.time, "monotonic", lambda: agora + JQ._LAPIDE_TTL_S + 1)

    assert fila.cancelado_antes_de_chegar("j1") is False


def _conexao(fila, resultados=None):
    from executor.connection import ExecutorConnection
    return ExecutorConnection(job_queue=fila, result_queue=resultados or asyncio.Queue())


async def test_cancel_de_job_desconhecido_fecha_e_descarta_o_atrasado(store):
    from executor.job_queue import ExecutorJobQueue

    cancelados = []

    async def _on_cancelled(message):
        cancelados.append(message["envelope"]["job_id"])

    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=_on_cancelled)
    conn = _conexao(fila)

    assert await conn._encerrar_cancelamento_desconhecido("j1") == "encerrado"
    assert cancelados == ["j1"]

    # O job chega depois do cancelamento: é descartado sem rodar e sem ACK.
    ws = MagicMock()
    ws.send = AsyncMock()
    await conn._handle_job(ws, {"envelope": {"job_id": "j1"}})

    assert fila.job_ids_ativos() == []
    ws.send.assert_not_awaited()


async def test_cancel_de_job_que_ja_terminou_nao_mente(store):
    """Resultado no outbox: o verdadeiro está a caminho; nada de 'cancelled' por cima."""
    from executor.job_queue import ExecutorJobQueue

    on_cancelled = AsyncMock()
    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=on_cancelled)
    store.put({"job_id": "j1", "run_id": "j1", "status": "ok"})

    assert await _conexao(fila)._encerrar_cancelamento_desconhecido("j1") == "resultado_pendente"
    on_cancelled.assert_not_awaited()


async def test_job_aceito_entra_no_diario(store):
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    ws = MagicMock()
    ws.send = AsyncMock()

    await _conexao(fila)._handle_job(ws, {"envelope": {"job_id": "j1"}})

    assert [o["job_id"] for o in store.carregar_em_voo()] == ["j1"]


async def test_inventario_junta_ativos_outbox_e_fila_em_memoria(store):
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    await fila.enqueue({"envelope": {"job_id": "ativo"}})
    store.put({"job_id": "no-outbox", "status": "ok"})
    memoria = asyncio.Queue()
    memoria.put_nowait({"job_id": "so-na-memoria", "status": "ok"})

    inv = _conexao(fila, memoria)._montar_inventario()

    assert inv["type"] == "inventario"
    assert inv["ativos"] == ["ativo"]
    assert inv["resultados"] == ["no-outbox", "so-na-memoria"]
    assert inv["truncado"] is False


async def test_inventario_grande_vai_marcado_truncado(store, monkeypatch):
    from executor import connection as CX
    from executor.job_queue import ExecutorJobQueue

    monkeypatch.setattr(CX, "_INVENTARIO_MAX", 2)
    fila = ExecutorJobQueue(on_execute=AsyncMock())
    for i in range(3):
        await fila.enqueue({"envelope": {"job_id": f"j{i}"}})

    inv = _conexao(fila)._montar_inventario()

    assert len(inv["ativos"]) == 2 and inv["truncado"] is True


async def test_contrato_o_inventario_do_executor_passa_no_schema_do_servidor(store):
    """Os dois lados do protocolo, sem mock no meio: o que o executor manda é o
    que o servidor exige."""
    from app.api.routers.executor_ws.protocolo import _missing_fields
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    inv = _conexao(fila)._montar_inventario()

    assert _missing_fields(inv["type"], inv) == []
    assert ORF._ids_do_inventario(inv["ativos"]) == set()
    assert ORF._ids_do_inventario(inv["resultados"]) == set()
