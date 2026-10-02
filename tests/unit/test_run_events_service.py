"""`app/services/run_events_service.py` — eventos de um run sem WebSocket.

O laço subscribe → LRANGE → dedup → pub/sub saiu do handler do WS para um
gerador de `Lote`s que o servidor MCP também consome. Cada teste aqui fixa um
comportamento que o painel de execução já dependia (e que o WS continua a
observar através do gerador):

- o replay é UMA leitura, cortada no 1º `__workflow_complete__`, e um run já
  encerrado nunca vai ao vivo;
- a cauda do replay deduplica a fronteira com o pub/sub, mas um repetido
  legítimo depois dela passa;
- quando o buffer enche, stdout cai antes de ciclo de vida e `dropped` conta;
- canal quieto emite lote vazio de heartbeat; prazo estourado encerra sem
  `completo`;
- a conexão dedicada do assinante fecha em toda saída; Redis fora vira
  `RunEventsUnavailable`.

`esperar_run` combina o gerador com o poll do banco (SQLite em arquivo): o
complete ao vivo espera a linha ficar terminal; um cancel de run `pending`, que
não publica evento, termina pelo poll; sem Redis só o poll trabalha; o
progresso chega por nó distinto.

O contrato que o consumidor sem socket lê do resultado também está fixado aqui:
`viu_complete` separa "o grafo terminou, falta a linha" de "ainda rodando"
(inclusive quando as duas tarefas terminam no mesmo passo); um `on_progress`
que levanta não derruba a espera; falha transitória do banco é tolerada até o
teto e só então propaga; e a leitura que o poll já tinha em voo é reaproveitada
em vez de refeita.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, update

from app.core.constants import WORKFLOW_COMPLETE_NODE
from app.models.workflow_run import WorkflowRun
from app.services import run_events_service as svc


# ── Dublês ────────────────────────────────────────────────────────────────────


class FakePubSub:
    """`segurar=True` simula um run ainda vivo: o `listen()` nunca termina.

    `listens` conta quantas vezes o corpo do `listen()` chegou a rodar — é o
    que prova se o gerador foi ou não ouvir o ao vivo (um `listen()` só
    chamado, sem ser iterado, nunca executa o corpo).
    """

    def __init__(self, mensagens: list[str], *, segurar: bool = False):
        self._mensagens = mensagens
        self._segurar = segurar
        self.canais: list[str] = []
        self.listens = 0

    async def subscribe(self, canal: str) -> None:
        self.canais.append(canal)

    async def listen(self):
        self.listens += 1
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


def stdout(node: str, texto: str = "") -> str:
    return json.dumps({"node": node, "kind": "stdout", "status": "log", "msg": texto})


def lifecycle(node: str, status: str, duration_ms=None) -> str:
    ev = {"node": node, "kind": "lifecycle", "status": status}
    if duration_ms is not None:
        ev["duration_ms"] = duration_ms
    return json.dumps(ev)


COMPLETE = json.dumps({"node": WORKFLOW_COMPLETE_NODE, "kind": "lifecycle", "status": "completed"})


def _redis(historico: list[str]) -> MagicMock:
    rc = MagicMock()
    rc.lrange = AsyncMock(return_value=list(historico))
    return rc


async def _coletar(gen, *, maximo: int | None = None) -> list[svc.Lote]:
    """Consome o gerador (até `maximo` lotes) fechando-o como um cliente faria."""
    lotes: list[svc.Lote] = []
    try:
        async for lote in gen:
            lotes.append(lote)
            if maximo is not None and len(lotes) >= maximo:
                break
    finally:
        await gen.aclose()
    return lotes


def _nodes(lotes: list[svc.Lote]) -> list[str]:
    return [json.loads(raw)["node"] for lote in lotes for raw in lote.eventos]


# ── iter_run_events: replay ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_le_o_historico_em_uma_unica_chamada_e_entrega_em_lotes():
    historico = [stdout(f"n{i}") for i in range(1200)]
    rc = _redis(historico)
    sub = FakeSubClient(FakePubSub([COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _coletar(svc.iter_run_events("run-1", timeout_s=5))

    rc.lrange.assert_awaited_once_with("workflow:run-1:history", 0, -1)
    assert sub._pubsub.canais == ["workflow:run-1:events"]
    # O ENVIO continua paginado (500/500/200) e depois vem o complete ao vivo.
    assert [len(lote.eventos) for lote in lotes] == [500, 500, 200, 1]
    assert [lote.completo for lote in lotes] == [False, False, False, True]
    assert _nodes(lotes) == [f"n{i}" for i in range(1200)] + [WORKFLOW_COMPLETE_NODE]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_replay_corta_no_complete_e_nao_vai_ao_vivo():
    """Run já encerrado: último lote com `completo=True`, pub/sub nunca lido."""
    rc = _redis([stdout("n1"), COMPLETE, stdout("n2")])
    # Se o gerador fosse ao vivo, ficaria preso aqui — o teste travaria.
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _coletar(svc.iter_run_events("run-1", timeout_s=5)), timeout=2,
        )

    assert len(lotes) == 1
    assert lotes[0].completo is True
    assert lotes[0].dropped == 0 and lotes[0].heartbeat is False
    assert _nodes(lotes) == ["n1", WORKFLOW_COMPLETE_NODE]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_replay_marca_completo_so_no_ultimo_lote():
    historico = [stdout(f"n{i}") for i in range(7)] + [COMPLETE]
    rc = _redis(historico)
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _coletar(svc.iter_run_events("run-1", timeout_s=5, chunk=3))

    assert [len(lote.eventos) for lote in lotes] == [3, 3, 2]
    assert [lote.completo for lote in lotes] == [False, False, True]


@pytest.mark.asyncio
async def test_replay_vazio_vai_direto_ao_vivo():
    rc = _redis([])
    sub = FakeSubClient(FakePubSub([lifecycle("n1", "started"), COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _coletar(svc.iter_run_events("run-1", timeout_s=5))

    assert _nodes(lotes) == ["n1", WORKFLOW_COMPLETE_NODE]
    assert lotes[-1].completo is True


# ── iter_run_events: dedup da fronteira ───────────────────────────────────────


@pytest.mark.asyncio
async def test_dedup_descarta_a_cauda_do_replay_repetida_ao_vivo():
    duplicados = [stdout("n8", "linha"), stdout("n8", "linha"), stdout("n9")]
    novos = [stdout("n10"), stdout("n8", "linha")]
    rc = _redis(duplicados)
    sub = FakeSubClient(FakePubSub([*duplicados, *novos, COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _coletar(svc.iter_run_events("run-1", timeout_s=5))

    replay, ao_vivo = lotes[0], lotes[1:]
    assert _nodes([replay]) == ["n8", "n8", "n9"]
    # A `n8` repetida DEPOIS da fronteira é legítima e tem que passar.
    assert _nodes(ao_vivo) == ["n10", "n8", WORKFLOW_COMPLETE_NODE]


@pytest.mark.asyncio
async def test_dedup_desliga_na_primeira_mensagem_que_nao_casa():
    """Um repetido no MEIO do run não é engolido: o dedup é só de prefixo."""
    cauda = [stdout("n1", "x")]
    rc = _redis(cauda)
    sub = FakeSubClient(FakePubSub([stdout("n2"), stdout("n1", "x"), COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _coletar(svc.iter_run_events("run-1", timeout_s=5))

    assert _nodes(lotes[1:]) == ["n2", "n1", WORKFLOW_COMPLETE_NODE]


# ── iter_run_events: buffer, heartbeat, prazo, falhas ─────────────────────────


@pytest.mark.asyncio
async def test_buffer_cheio_descarta_stdout_antes_de_lifecycle_e_conta_dropped():
    mensagens = [
        stdout("s1"), stdout("s2"),
        lifecycle("n1", "completed"), lifecycle("n2", "completed"),
        COMPLETE,
    ]
    rc = _redis([])
    sub = FakeSubClient(FakePubSub(mensagens))

    # O pub/sub falso entrega tudo sem ceder o laço, então o produtor enche o
    # buffer antes de o consumidor drenar — é o cenário de browser lento.
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc), \
            patch.object(svc, "_QUEUE_MAXSIZE", 3):
        lotes = await _coletar(svc.iter_run_events("run-1", timeout_s=5))

    assert len(lotes) == 1
    assert lotes[0].dropped == 2
    assert _nodes(lotes) == ["n1", "n2", WORKFLOW_COMPLETE_NODE]
    assert lotes[0].completo is True


@pytest.mark.asyncio
async def test_complete_nunca_e_descartado_do_buffer():
    buf = svc._EventBuffer(2)
    buf.push(lifecycle("a", "started"), droppable=False)
    buf.push(COMPLETE, droppable=False)
    buf.push(lifecycle("b", "started"), droppable=False)
    assert buf.take_dropped() == 1
    assert buf.take_dropped_lifecycle() == 1
    assert [json.loads(raw)["node"] for raw in await buf.drain()] == [WORKFLOW_COMPLETE_NODE, "b"]


@pytest.mark.asyncio
async def test_canal_quieto_emite_heartbeat_vazio():
    rc = _redis([])
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _coletar(svc.iter_run_events("run-1", timeout_s=5, heartbeat_s=0.01), maximo=2),
            timeout=2,
        )

    assert len(lotes) == 2
    assert all(lote.heartbeat and lote.eventos == [] and not lote.completo for lote in lotes)
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_prazo_estourado_encerra_sem_completo():
    rc = _redis([stdout("n1")])
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _coletar(svc.iter_run_events("run-1", timeout_s=0.05, heartbeat_s=0.01)),
            timeout=2,
        )

    assert lotes[0].eventos == [stdout("n1")]
    assert not any(lote.completo for lote in lotes)
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_consumidor_que_para_no_meio_fecha_a_conexao_do_assinante():
    rc = _redis([])
    sub = FakeSubClient(FakePubSub([stdout("n1")], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _coletar(svc.iter_run_events("run-1", timeout_s=5), maximo=1), timeout=2,
        )

    assert _nodes(lotes) == ["n1"]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_redis_fora_vira_run_events_unavailable_e_fecha_o_assinante():
    sub = FakeSubClient(FakePubSub([]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(
                svc, "get_redis_pool",
                MagicMock(side_effect=RuntimeError("Redis pool não inicializado.")),
            ):
        with pytest.raises(svc.RunEventsUnavailable):
            await _coletar(svc.iter_run_events("run-1", timeout_s=5))

    assert sub.fechado is True


@pytest.mark.asyncio
async def test_falha_no_subscribe_tambem_e_run_events_unavailable():
    from redis.exceptions import ConnectionError as RedisConnectionError

    pubsub = FakePubSub([])
    pubsub.subscribe = AsyncMock(side_effect=RedisConnectionError("recusada"))
    sub = FakeSubClient(pubsub)

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        with pytest.raises(svc.RunEventsUnavailable):
            await _coletar(svc.iter_run_events("run-1", timeout_s=5))

    assert sub.fechado is True


# ── esperar_run ───────────────────────────────────────────────────────────────


@pytest.fixture
async def banco(tmp_path):
    """SQLite em ARQUIVO: o poll e quem atualiza o run usam sessões próprias, e
    em memória cada conexão veria um banco vazio diferente (um `StaticPool`
    compartilharia a mesma transação, e o rollback do poll desfaria o UPDATE)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.base import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'runs.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[WorkflowRun.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def sessao():
        async with fabrica() as s:
            try:
                yield s
            finally:
                await s.rollback()

    async with fabrica() as s:
        s.add(WorkflowRun(task_id="run-1", workflow_hash="wf-1", workspace_id="ws-1", status="running"))
        await s.commit()

    with patch.object(svc, "get_session_async", sessao):
        yield fabrica
    await engine.dispose()


async def _mudar_status(fabrica, status: str, *, apos_s: float) -> None:
    await asyncio.sleep(apos_s)
    async with fabrica() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status=status))
        await s.commit()


@pytest.mark.asyncio
async def test_ler_status_do_run_por_task_id(banco):
    async with banco() as db:
        status, run = await svc.ler_status_do_run(db, "run-1")
        assert status == "running" and run.task_id == "run-1"
        assert await svc.ler_status_do_run(db, "nao-existe") == (None, None)


@pytest.mark.asyncio
async def test_esperar_run_complete_ao_vivo_espera_a_linha_ficar_terminal(banco):
    """O consumer publica o evento e SÓ DEPOIS grava a linha."""
    mensagens = [
        stdout("n1", "print ignorado"),
        lifecycle("n1", "started"),
        lifecycle("n1", "completed", duration_ms=1234),
        lifecycle("n1", "completed", duration_ms=1234),  # repetido: conta uma vez
        lifecycle("n2", "failed", duration_ms=80),
        COMPLETE,
    ]
    sub = FakeSubClient(FakePubSub(mensagens))
    progresso: list[tuple[int, int, str]] = []

    async def on_progress(n, total, msg):
        progresso.append((n, total, msg))

    atualizador = asyncio.create_task(_mudar_status(banco, "failed", apos_s=0.05))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=2, on_progress=on_progress, poll_s=1.0),
            timeout=3,
        )
    await atualizador

    assert resultado.status == "failed"
    assert resultado.run is not None and resultado.run.task_id == "run-1"
    assert resultado.concluidos == 2
    assert resultado.timed_out is False
    assert resultado.redis_indisponivel is False
    assert progresso == [(1, 2, "n1: completed (1,2 s)"), (2, 2, "n2: failed (80 ms)")]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_esperar_run_cancel_de_run_pending_termina_pelo_poll(banco):
    """Sem `__workflow_complete__` publicado: é o poll do banco que encerra."""
    sub = FakeSubClient(FakePubSub([], segurar=True))
    atualizador = asyncio.create_task(_mudar_status(banco, "cancelled", apos_s=0.05))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=3, poll_s=0.01), timeout=3,
        )
    await atualizador

    assert resultado.status == "cancelled"
    assert resultado.concluidos == 0
    assert resultado.timed_out is False
    # A task dos eventos foi cancelada e o assinante, fechado.
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_esperar_run_sem_redis_segue_so_pelo_poll(banco):
    sub = FakeSubClient(FakePubSub([]))
    atualizador = asyncio.create_task(_mudar_status(banco, "success", apos_s=0.05))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(
                svc, "get_redis_pool",
                MagicMock(side_effect=RuntimeError("Redis pool não inicializado.")),
            ):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
        )
    await atualizador

    assert resultado.redis_indisponivel is True
    assert resultado.status == "success"
    assert resultado.timed_out is False


@pytest.mark.asyncio
async def test_esperar_run_prazo_estourado_devolve_timed_out(banco):
    sub = FakeSubClient(FakePubSub([lifecycle("n1", "completed")], segurar=True))
    progresso: list[tuple[int, int, str]] = []

    async def on_progress(n, total, msg):
        progresso.append((n, total, msg))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=0.1, total_nos=4, on_progress=on_progress, poll_s=0.02),
            timeout=3,
        )

    assert resultado.timed_out is True
    assert resultado.status == "running"
    assert resultado.concluidos == 1
    assert progresso == [(1, 4, "n1: completed")]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_esperar_run_soma_eventos_descartados(banco):
    mensagens = [stdout("s1"), stdout("s2"), lifecycle("n1", "completed"), COMPLETE]
    sub = FakeSubClient(FakePubSub(mensagens))
    atualizador = asyncio.create_task(_mudar_status(banco, "success", apos_s=0.02))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_QUEUE_MAXSIZE", 2), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=1.0), timeout=3,
        )
    await atualizador

    assert resultado.eventos_descartados == 2
    assert resultado.concluidos == 1
    assert resultado.status == "success"


@pytest.mark.asyncio
async def test_esperar_run_replay_ja_completo_nao_ouve_o_pubsub(banco):
    """Histórico já com o marcador: o `listen()` não chega a ser iterado.

    O dublê conta as entradas no corpo do `listen()` e ficaria preso nele para
    sempre (`segurar=True`); o `poll_s` é maior que o prazo do teste, então
    quem termina a espera é o replay. Se o gerador fosse ao vivo, o
    `wait_for` de 1 s estouraria em vez de devolver resultado.
    """
    pubsub = FakePubSub([], segurar=True)
    sub = FakeSubClient(pubsub)
    atualizador = asyncio.create_task(_mudar_status(banco, "success", apos_s=0.02))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nos=1, poll_s=30.0), timeout=1,
        )
    await atualizador

    # Inscrito (a ordem SUBSCRIBE-antes-do-LRANGE não muda), mas nunca ouvido.
    assert pubsub.canais == ["workflow:run-1:events"]
    assert pubsub.listens == 0
    assert resultado.viu_complete is True
    assert resultado.status == "success"
    assert resultado.concluidos == 1
    assert resultado.timed_out is False
    assert sub.fechado is True
    assert (await _linha(banco)).status == "success"


@pytest.mark.asyncio
async def test_esperar_run_complete_sem_linha_terminal_devolve_viu_complete(banco):
    """Consumer parado: o grafo terminou, a linha não. Quem chama precisa saber.

    Sem `viu_complete` o resultado era indistinguível de um run ainda rodando:
    `status="running"` e `timed_out=False`, porque o prazo geral nem chegou
    perto de estourar.
    """
    sub = FakeSubClient(FakePubSub([lifecycle("n1", "completed"), COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01), \
            patch.object(svc, "_POLL_POS_COMPLETE_MAX_S", 0.05):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nos=1, poll_s=30.0), timeout=3,
        )

    assert resultado.viu_complete is True
    assert resultado.status == "running"
    assert resultado.timed_out is False
    assert resultado.concluidos == 1


@pytest.mark.asyncio
async def test_esperar_run_sem_complete_nao_marca_viu_complete(banco):
    """Fim que não publica evento: `viu_complete` fica False mesmo com desfecho."""
    sub = FakeSubClient(FakePubSub([], segurar=True))
    atualizador = asyncio.create_task(_mudar_status(banco, "cancelled", apos_s=0.02))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
        )
    await atualizador

    assert resultado.status == "cancelled"
    assert resultado.viu_complete is False


@pytest.mark.asyncio
async def test_esperar_run_reaproveita_a_leitura_em_curso_apos_o_complete(banco):
    """A leitura que o poll já tinha em voo não é jogada fora (latência dobrada).

    A leitura é lenta de propósito, então o complete do replay chega com ela em
    curso: o `shield` a deixa terminar e o resultado tem que sair DELA. Uma
    segunda ida ao banco aqui seria um round-trip inteiro no caminho mais
    comum da espera.
    """
    leituras: list[str] = []
    real = svc.ler_status_do_run

    async def ler_devagar(db, run_id):
        leituras.append(run_id)
        await asyncio.sleep(0.05)
        return await real(db, run_id)

    async with banco() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status="success"))
        await s.commit()

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(svc, "ler_status_do_run", ler_devagar):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nos=1, poll_s=30.0), timeout=3,
        )

    assert resultado.status == "success"
    assert resultado.viu_complete is True
    assert leituras == ["run-1"]


@pytest.mark.asyncio
async def test_esperar_run_callback_que_falha_nao_derruba_a_espera(banco, caplog):
    """`on_progress` do chamador quebrado: avisa uma vez e segue contando."""
    mensagens = [
        lifecycle("n1", "completed"),
        lifecycle("n2", "completed"),
        lifecycle("n3", "failed"),
        COMPLETE,
    ]
    sub = FakeSubClient(FakePubSub(mensagens))
    chamadas: list[int] = []

    async def on_progress(n, total, msg):
        chamadas.append(n)
        raise RuntimeError("consumidor do progresso caiu")

    atualizador = asyncio.create_task(_mudar_status(banco, "failed", apos_s=0.02))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        with caplog.at_level("WARNING"):
            resultado = await asyncio.wait_for(
                svc.esperar_run(
                    "run-1", timeout_s=5, total_nos=3, on_progress=on_progress, poll_s=1.0,
                ),
                timeout=3,
            )
    await atualizador

    # Notificou uma vez, desistiu de notificar — e contou os três assim mesmo.
    assert chamadas == [1]
    assert resultado.concluidos == 3
    assert resultado.status == "failed"
    assert resultado.viu_complete is True
    avisos = [r for r in caplog.records if "callback falhou" in r.message]
    assert len(avisos) == 1


@pytest.mark.asyncio
async def test_esperar_run_tolera_falhas_transitorias_do_poll(banco, caplog):
    """Blip do banco com o canal de eventos são: a espera continua."""
    from sqlalchemy.exc import SQLAlchemyError

    real = svc.ler_status_do_run
    tentativas = {"n": 0}

    async def ler_instavel(db, run_id):
        tentativas["n"] += 1
        if tentativas["n"] <= svc._POLL_FALHAS_CONSECUTIVAS_MAX - 1:
            raise SQLAlchemyError("checkout do pool estourou")
        return await real(db, run_id)

    sub = FakeSubClient(FakePubSub([], segurar=True))
    atualizador = asyncio.create_task(_mudar_status(banco, "success", apos_s=0.02))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", ler_instavel):
        with caplog.at_level("WARNING"):
            resultado = await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
            )
    await atualizador

    assert resultado.status == "success"
    assert resultado.timed_out is False
    assert any("Poll do run run-1 falhou" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_esperar_run_propaga_quando_o_poll_falha_alem_do_teto(banco):
    """Indisponibilidade real (não um soluço): o erro sobe para quem chamou."""
    from sqlalchemy.exc import SQLAlchemyError

    chamadas = {"n": 0}

    async def sempre_falha(db, run_id):
        chamadas["n"] += 1
        raise SQLAlchemyError("banco fora")

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", sempre_falha):
        with pytest.raises(SQLAlchemyError):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
            )

    assert chamadas["n"] == svc._POLL_FALHAS_CONSECUTIVAS_MAX


async def _linha(fabrica) -> WorkflowRun:
    async with fabrica() as s:
        return (await s.execute(select(WorkflowRun).where(WorkflowRun.task_id == "run-1"))).scalar_one()


@pytest.mark.asyncio
async def test_esperar_run_viu_complete_quando_as_duas_tarefas_terminam_juntas(banco):
    """Eventos e poll terminando no MESMO passo do laço.

    É uma corrida real — o `__workflow_complete__` chega enquanto a leitura do
    poll volta — e nela `asyncio.wait` devolve as DUAS tarefas em `done`. A
    janela dura um passo do laço, então é forçada aqui por um dublê que espera
    as duas antes de devolver. Sair direto pelo desfecho do poll, sem olhar o
    resultado dos eventos, entregava `viu_complete=False` para um run cujo
    grafo comprovadamente terminou.
    """
    wait_real = asyncio.wait

    async def wait_as_duas(tarefas, **kw):
        done, pendentes = await wait_real(tarefas, **kw)
        if pendentes:
            await wait_real(pendentes)
            done, pendentes = done | pendentes, set()
        return done, pendentes

    async with banco() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status="success"))
        await s.commit()

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(asyncio, "wait", wait_as_duas):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
        )

    assert resultado.status == "success"
    assert resultado.viu_complete is True
    assert resultado.concluidos == 1


# ── esperar_run: prazos, desfechos e descarte (caracterização) ───────────────
#
# Presos antes de dividir o laço em partes: o prazo que chega ao gerador e ao
# poll, o que volta em cada desfecho (inclusive os de erro) e quais eventos NÃO
# contam como progresso.


def _desfecho(resultado: svc.ResultadoEspera) -> tuple:
    return (
        resultado.status, resultado.concluidos, resultado.eventos_descartados,
        resultado.timed_out, resultado.redis_indisponivel, resultado.viu_complete,
    )


async def _marcar_terminal(fabrica, status: str) -> None:
    async with fabrica() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status=status))
        await s.commit()


@pytest.mark.asyncio
async def test_esperar_run_repassa_aos_eventos_so_o_prazo_que_resta(banco):
    prazos: list[float] = []

    async def eventos_falsos(run_id, *, timeout_s):
        prazos.append(timeout_s)
        await asyncio.Event().wait()
        yield  # pragma: no cover - nunca chega aqui

    atualizador = asyncio.create_task(_mudar_status(banco, "success", apos_s=0.02))
    with patch.object(svc, "iter_run_events", eventos_falsos):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=7, total_nos=1, poll_s=0.01), timeout=3,
        )
    await atualizador

    assert len(prazos) == 1 and 6.5 < prazos[0] <= 7
    assert _desfecho(resultado) == ("success", 0, 0, False, False, False)


@pytest.mark.asyncio
async def test_esperar_run_poll_longo_nao_passa_do_prazo(banco):
    """`poll_s` maior que o prazo: a espera acaba no prazo, não no próximo poll."""
    sub = FakeSubClient(FakePubSub([], segurar=True))
    inicio = asyncio.get_running_loop().time()

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=0.1, total_nos=1, poll_s=30.0), timeout=3,
        )

    assert asyncio.get_running_loop().time() - inicio < 1.5
    assert _desfecho(resultado) == ("running", 0, 0, True, False, False)
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_esperar_run_run_que_nao_existe_estoura_o_prazo_sem_linha(banco):
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("nao-existe", timeout_s=0.1, total_nos=1, poll_s=0.02), timeout=3,
        )

    assert resultado.run is None
    assert _desfecho(resultado) == (None, 0, 0, True, False, False)


@pytest.mark.asyncio
async def test_esperar_run_erro_generico_nos_eventos_segue_pelo_poll(banco, caplog):
    async def eventos_quebrados(run_id, *, timeout_s):
        raise ValueError("canal quebrou")
        yield  # pragma: no cover - gerador

    atualizador = asyncio.create_task(_mudar_status(banco, "failed", apos_s=0.02))
    with patch.object(svc, "iter_run_events", eventos_quebrados), \
            caplog.at_level("ERROR"):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
        )
    await atualizador

    assert _desfecho(resultado) == ("failed", 0, 0, False, False, False)
    assert any(
        r.getMessage() == "Erro ao acompanhar eventos do run run-1; seguindo só pelo poll: canal quebrou"
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_esperar_run_redis_fora_avisa_e_marca_redis_indisponivel(banco, caplog):
    atualizador = asyncio.create_task(_mudar_status(banco, "cancelled", apos_s=0.02))
    sub = FakeSubClient(FakePubSub([]))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", MagicMock(side_effect=RuntimeError("sem pool"))), \
            caplog.at_level("WARNING"):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
        )
    await atualizador

    assert _desfecho(resultado) == ("cancelled", 0, 0, False, True, False)
    assert any(
        r.getMessage() == (
            "Eventos do run run-1 indisponíveis; seguindo só pelo poll: "
            "Redis indisponível para os eventos do run run-1: sem pool"
        )
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_esperar_run_devolve_a_linha_desprendida_e_legivel(banco):
    """`run` volta sem sessão, com os atributos já carregados."""
    async with banco() as s:
        await s.execute(
            update(WorkflowRun).where(WorkflowRun.task_id == "run-1")
            .values(status="success", node_stats={"n1": {"status": "completed"}}),
        )
        await s.commit()

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
        )

    assert resultado.run.node_stats == {"n1": {"status": "completed"}}
    assert resultado.run.workflow_hash == "wf-1"


def _leitura_pos_complete(falhas: int):
    """1ª leitura: 'running' (o consumer ainda não gravou); depois `falhas`
    falhas transitórias seguidas; depois a linha de verdade."""
    from sqlalchemy.exc import SQLAlchemyError

    real = svc.ler_status_do_run
    chamadas = {"n": 0}

    async def ler(db, run_id):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            _status, run = await real(db, run_id)
            return "running", run
        if chamadas["n"] <= 1 + falhas:
            raise SQLAlchemyError("conexão reciclada")
        return await real(db, run_id)

    return ler, chamadas


@pytest.mark.asyncio
async def test_esperar_run_poll_pos_complete_tolera_falhas_transitorias(banco, caplog):
    await _marcar_terminal(banco, "success")
    ler, chamadas = _leitura_pos_complete(falhas=svc._POLL_FALHAS_CONSECUTIVAS_MAX - 1)
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(svc, "ler_status_do_run", ler), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01), \
            caplog.at_level("WARNING"):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nos=1, poll_s=30.0), timeout=3,
        )

    assert _desfecho(resultado) == ("success", 1, 0, False, False, True)
    assert chamadas["n"] == 1 + svc._POLL_FALHAS_CONSECUTIVAS_MAX
    avisos = [r.getMessage() for r in caplog.records if "Poll pós-complete" in r.getMessage()]
    assert avisos == [
        f"Poll pós-complete do run run-1 falhou ({i}/{svc._POLL_FALHAS_CONSECUTIVAS_MAX}): conexão reciclada"
        for i in range(1, svc._POLL_FALHAS_CONSECUTIVAS_MAX)
    ]


@pytest.mark.asyncio
async def test_esperar_run_poll_pos_complete_propaga_no_teto(banco):
    from sqlalchemy.exc import SQLAlchemyError

    ler, chamadas = _leitura_pos_complete(falhas=99)
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([COMPLETE])), \
            patch.object(svc, "ler_status_do_run", ler), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        with pytest.raises(SQLAlchemyError):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=30, total_nos=1, poll_s=30.0), timeout=3,
            )

    assert chamadas["n"] == 1 + svc._POLL_FALHAS_CONSECUTIVAS_MAX


@pytest.mark.asyncio
async def test_esperar_run_erro_que_nao_e_transitorio_propaga_na_primeira(banco):
    chamadas = {"n": 0}

    async def ler(db, run_id):
        chamadas["n"] += 1
        raise ValueError("bug na consulta")

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", ler):
        with pytest.raises(ValueError, match="bug na consulta"):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=5, total_nos=1, poll_s=0.01), timeout=3,
            )

    assert chamadas["n"] == 1
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_esperar_run_falha_transitoria_depois_do_prazo_propaga_sem_esperar_o_teto(banco):
    from sqlalchemy.exc import SQLAlchemyError

    chamadas = {"n": 0}

    async def ler_lento(db, run_id):
        chamadas["n"] += 1
        await asyncio.sleep(0.1)
        raise SQLAlchemyError("pool esgotado")

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", ler_lento):
        with pytest.raises(SQLAlchemyError):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=0.05, total_nos=1, poll_s=0.01), timeout=3,
            )

    assert chamadas["n"] == 1


@pytest.mark.asyncio
async def test_esperar_run_so_conta_ciclo_de_vida_valido_e_descarta_o_que_vem_depois_do_complete(banco):
    """O que NÃO é progresso: stdout/debug, JSON inválido ou que não é objeto,
    kind que não é ciclo de vida, evento sem nó, status que não é de fim — e o
    que o histórico guardou DEPOIS do `__workflow_complete__` (outro ciclo)."""
    historico = [
        "nao-e-json",
        "[1, 2]",
        json.dumps({"node": "n0", "status": "completed"}),  # sem kind: ciclo de vida
        stdout("n1", "print"),
        json.dumps({"node": "n1", "kind": "debug", "status": "completed"}),
        json.dumps({"kind": "lifecycle", "status": "completed"}),
        json.dumps({"node": "n2", "kind": "lifecycle", "status": "skipped"}),
        json.dumps({"node": "n3", "kind": "metric", "status": "completed"}),
        lifecycle("n4", "failed", duration_ms=2500),
        COMPLETE,
        lifecycle("n5", "completed"),
    ]
    await _marcar_terminal(banco, "failed")
    progresso: list[tuple[int, int, str]] = []

    async def on_progress(n, total, msg):
        progresso.append((n, total, msg))

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis(historico)):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nos=6, on_progress=on_progress, poll_s=30.0),
            timeout=3,
        )

    assert progresso == [(1, 6, "n0: completed"), (2, 6, "n4: failed (2,5 s)")]
    assert _desfecho(resultado) == ("failed", 2, 0, False, False, True)
    assert sub._pubsub.listens == 0
