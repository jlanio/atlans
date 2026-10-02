# tests/unit/test_despacho_ocupacao.py
"""
Ordem dos candidatos no despacho (`_situacoes`/`_chave_de_ordem`/
`_elegiveis_ordenados` em workflow_execution_service).

Antes, a carga vinha só do `capacity` que o executor manda a cada 10 s, e só
no worker da API que segura o WebSocket dele: nos outros workers o executor
contava zero, e numa rajada todos os jobs iam para quem estava vazio no último
relatório. Com o pool ocioso, o empate caía na ordem do banco — o primeiro
executor levava tudo.

  - A carga é a CONTADA pelo servidor (runs `pending`/`running` do host no
    banco), numa consulta isolada por SAVEPOINT na conexão. A declarada
    (local ou publicada no Redis) só entra quando a contagem não sai, e para
    dizer se o executor está cheio.
  - Com vaga livre: sorteio ponderado pelas vagas livres — decisões
    simultâneas se espalham. Sem vaga: menor ocupação relativa às vagas.
    Cheios (pelo relatório ou pela contagem): por último.
"""
from __future__ import annotations

import collections
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core import executor_connections as ec
from app.models.workflow_run import WorkflowRun
from app.services import workflow_execution_service as wes

from ._mcp_harness import RedisFalso, banco_em_memoria


# ── Fábricas ──────────────────────────────────────────────────────────────────

def _executor(id_hash, *, vagas=4, fila=50):
    return SimpleNamespace(
        id_hash=id_hash, name=id_hash, status="active", public_key="PEM",
        max_concurrent_jobs=vagas, max_queue_size=fila,
    )


def _capacidade(running=0, queued=0, max_concurrent=4, max_queue=50):
    return {"running": running, "queued": queued,
            "max_concurrent": max_concurrent, "max_queue": max_queue}


def _registro(declaradas=None):
    """Registry falso: todos presentes; a capacidade declarada vem do dict
    (ausente = nunca declarou), e `send_job` aceita tudo e anota o escolhido."""
    declaradas = declaradas or {}
    reg = MagicMock()
    reg.presence_or_unknown = AsyncMock(return_value=True)

    async def _read_capacities(ids):
        return {i: (dict(declaradas[i]) if declaradas.get(i) else None) for i in ids}

    reg.read_capacities = AsyncMock(side_effect=_read_capacities)
    reg.escolhidos = []

    async def _send_job(executor_id, job_msg):
        reg.escolhidos.append(executor_id)
        return True

    reg.send_job = AsyncMock(side_effect=_send_job)
    reg.send_json = AsyncMock(return_value=True)
    return reg


def _wf():
    wf = MagicMock()
    wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
    wf.pinned_outputs = wf.pin_metadata = None
    return wf


async def _runs(fabrica, executor_id, status, n):
    async with fabrica() as db:
        for _ in range(n):
            db.add(WorkflowRun(
                task_id=str(uuid4()), workflow_hash="wf-1", workspace_id="ws-1",
                status=status, host=f"executor:{executor_id}",
            ))
        await db.commit()


def _ordem(candidatos):
    return [c.id_hash for c in candidatos]


def _erro_do_banco(*, conexao_perdida=False):
    return OperationalError(
        "SELECT host, count(*) ...", {}, Exception("lock timeout"),
        connection_invalidated=conexao_perdida,
    )


def _sessao_falsa(execute):
    """Sessão cuja conexão anota o savepoint e roda `execute` na consulta."""
    eventos: list[str] = []

    class _Ponto:
        async def __aenter__(self):
            eventos.append("SAVEPOINT")

        async def __aexit__(self, tipo, *_):
            eventos.append("ROLLBACK TO SAVEPOINT" if tipo else "RELEASE SAVEPOINT")
            return False

    async def _execute(consulta):
        eventos.append("SELECT")
        return await execute(consulta)

    conexao = MagicMock()
    conexao.begin_nested = MagicMock(side_effect=lambda: _Ponto())
    conexao.execute = AsyncMock(side_effect=_execute)
    db = MagicMock()
    db.connection = AsyncMock(return_value=conexao)
    return db, eventos


@pytest.fixture
async def fabrica():
    async with banco_em_memoria() as f:
        yield f


@pytest.fixture
def estavel():
    """Sorteio fixo em 0,5, para as asserções de ordem exata: com vaga, quem
    tem mais vagas livres vem primeiro; empate fica na ordem de entrada."""
    with patch.object(wes, "_desempate", lambda: 0.5):
        yield


async def _ordenar(fabrica, reg, pool):
    async with fabrica() as db:
        with patch.object(wes, "executor_registry", reg):
            return _ordem(await wes._elegiveis_ordenados(db, pool))


# ══════════════════════════════════════════════════════════════════════════════
# A carga que ordena
# ══════════════════════════════════════════════════════════════════════════════

class TestCarga:
    @pytest.mark.asyncio
    async def test_contada_pelo_servidor_vence_a_declarada_defasada(self, fabrica, estavel):
        # A declarou 0 no último relatório, mas o servidor já lhe despachou 3.
        await _runs(fabrica, "A", "running", 3)
        reg = _registro({"A": _capacidade(), "B": _capacidade()})
        assert await _ordenar(fabrica, reg, [_executor("A"), _executor("B")]) == ["B", "A"]

    @pytest.mark.asyncio
    async def test_declarada_defasada_nao_infla_a_carga(self, fabrica, estavel):
        # O último relatório de A (até 10 s atrás) dizia 3 rodando; já
        # terminaram — o banco não mostra nenhum. B tem 1 de verdade. Pela
        # maior das duas, A parecia mais ocupado que B.
        await _runs(fabrica, "B", "running", 1)
        reg = _registro({"A": _capacidade(running=3), "B": _capacidade()})
        assert await _ordenar(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_declarada_e_contada_nao_se_somam(self, fabrica, estavel):
        # O caso comum: relatório e banco veem os MESMOS 2 jobs de A. Somados,
        # A pareceria lotado (4 de 4) e perderia para B, que tem 3.
        await _runs(fabrica, "A", "running", 2)
        await _runs(fabrica, "B", "running", 3)
        reg = _registro({"A": _capacidade(running=2), "B": _capacidade()})
        assert await _ordenar(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_pending_conta_e_terminal_nao(self, fabrica, estavel):
        # O INSERT do despacho grava `pending` com o host: já ocupa. Runs
        # encerrados não ocupam ninguém.
        await _runs(fabrica, "A", "pending", 2)
        for status in ("success", "failed", "cancelled"):
            await _runs(fabrica, "B", status, 5)
        assert await _ordenar(fabrica, _registro(), [_executor("A"), _executor("B")]) == ["B", "A"]


# ══════════════════════════════════════════════════════════════════════════════
# Cheios vão por último
# ══════════════════════════════════════════════════════════════════════════════

class TestCheios:
    @pytest.mark.asyncio
    async def test_cheio_pela_declarada_vai_por_ultimo(self, fabrica, estavel):
        # Em drenagem o executor se anuncia cheio para sair da frente (queued =
        # teto da fila + concorrência), sem run nenhum no banco. Pela ocupação
        # relativa (59/8) ele passava na frente de um executor de 1 vaga com 8
        # jobs (9/1) — e era tentado só para o send_job recusar.
        drenando = _capacidade(running=0, queued=50 + 8, max_concurrent=8)
        await _runs(fabrica, "pequeno", "running", 8)
        reg = _registro({"drenando": drenando, "pequeno": _capacidade(max_concurrent=1)})
        ordem = await _ordenar(fabrica, reg, [_executor("drenando", vagas=8), _executor("pequeno", vagas=1)])
        assert ordem == ["pequeno", "drenando"]

    @pytest.mark.asyncio
    async def test_fila_cheia_pela_contagem_vai_por_ultimo(self, fabrica):
        # O relatório de "grande" (16 vagas, fila 50) tem até 10 s e ainda diz
        # 56 de 66 — mas o servidor já lhe despachou 66: a fila local dele está
        # cheia, e o próximo job seria RECUSADO por ele depois de o envio ter
        # sido aceito — run falhado, sem failover. "pequeno" tem 16 de 54.
        # Pela ocupação relativa (67/16 < 17/4), "grande" vinha primeiro, e
        # continuava primeiro a cada run falhado. Sem sorteio fixo: não é sorte.
        await _runs(fabrica, "grande", "running", 66)
        await _runs(fabrica, "pequeno", "running", 16)
        reg = _registro({
            "grande": _capacidade(running=16, queued=40, max_concurrent=16),
            "pequeno": _capacidade(running=4, queued=12),
        })
        pool = [_executor("grande", vagas=16), _executor("pequeno")]
        for _ in range(50):
            assert await _ordenar(fabrica, reg, pool) == ["pequeno", "grande"]

    @pytest.mark.asyncio
    async def test_executor_em_outro_worker_cheio_pela_capacidade_do_redis(
        self, fabrica, estavel, monkeypatch,
    ):
        # O registry REAL: "local" tem o WebSocket neste worker; "remoto" está
        # noutro, e o relatório dele (cheio) só existe no Redis. Antes, daqui,
        # "remoto" contava zero. A leitura é uma ida só ao Redis (MGET).
        redis = RedisFalso()
        await redis.set(ec._capacity_key("remoto"), json.dumps(_capacidade(running=4, queued=50)))

        async def _get_redis():
            return redis

        monkeypatch.setattr(ec, "_get_redis", _get_redis)
        reg = ec.ExecutorConnectionRegistry()
        reg._connections["local"] = SimpleNamespace(capacity=_capacidade(running=1))
        reg.presence_or_unknown = AsyncMock(return_value=True)

        assert await _ordenar(fabrica, reg, [_executor("remoto"), _executor("local")]) == ["local", "remoto"]
        leituras = [c for c in redis.chamadas if c[0] in ("get", "mget")]
        assert leituras == [("mget", (ec._capacity_key("remoto"),))]


# ══════════════════════════════════════════════════════════════════════════════
# Vagas e fila
# ══════════════════════════════════════════════════════════════════════════════

class TestVagas:
    @pytest.mark.asyncio
    async def test_com_vaga_quem_tem_mais_vagas_livres_sai_na_frente(self, fabrica, estavel):
        # 4 jobs em 8 vagas deixam 4 livres; 1 em 2 deixa 1. O sorteio é
        # ponderado 4:1 — sem o sorteio fixo, "pequeno" ainda sai na frente 1
        # vez em 5, e é isso que espalha decisões simultâneas.
        await _runs(fabrica, "grande", "running", 4)
        await _runs(fabrica, "pequeno", "running", 1)
        reg = _registro({
            "grande": _capacidade(max_concurrent=8),
            "pequeno": _capacidade(max_concurrent=2),
        })
        ordem = await _ordenar(fabrica, reg, [_executor("pequeno", vagas=2), _executor("grande", vagas=8)])
        assert ordem == ["grande", "pequeno"]

    @pytest.mark.asyncio
    async def test_sem_vaga_em_nenhum_vai_para_a_menor_fila_relativa(self, fabrica, estavel):
        # Os dois lotados: o job vai esperar. 12 jobs em 8 vagas (4 na fila
        # para 8 rodando) andam mais rápido que 3 em 2 (1 na fila para 2) —
        # pela contagem absoluta (3 < 12) o job ia para o pequeno.
        await _runs(fabrica, "grande", "running", 12)
        await _runs(fabrica, "pequeno", "running", 3)
        reg = _registro({
            "grande": _capacidade(max_concurrent=8),
            "pequeno": _capacidade(max_concurrent=2),
        })
        ordem = await _ordenar(fabrica, reg, [_executor("pequeno", vagas=2), _executor("grande", vagas=8)])
        assert ordem == ["grande", "pequeno"]

    @pytest.mark.asyncio
    async def test_vagas_declaradas_menores_que_o_teto_do_banco_valem(self, fabrica, estavel):
        # O banco permite 8, mas o executor sobe com EXECUTOR_MAX_CONCURRENT=2:
        # com 1 job ele está pela metade, não a um oitavo.
        await _runs(fabrica, "A", "running", 1)
        await _runs(fabrica, "B", "running", 2)
        reg = _registro({"A": _capacidade(max_concurrent=2), "B": _capacidade(max_concurrent=4)})
        ordem = await _ordenar(fabrica, reg, [_executor("A", vagas=8), _executor("B", vagas=4)])
        assert ordem == ["B", "A"]

    @pytest.mark.asyncio
    async def test_vagas_nao_passam_do_teto_do_banco(self, fabrica, estavel):
        # Antes do primeiro `capacity`, o worker que segura o WebSocket tem um
        # valor provisório (4). O teto do registro é 1: com 1 job, A está
        # lotado — em todos os workers, não só nos que não têm o WebSocket.
        await _runs(fabrica, "A", "running", 1)
        await _runs(fabrica, "B", "running", 2)
        reg = _registro({"A": _capacidade(max_concurrent=4), "B": _capacidade(max_concurrent=4)})
        ordem = await _ordenar(fabrica, reg, [_executor("A", vagas=1), _executor("B", vagas=4)])
        assert ordem == ["B", "A"]

    @pytest.mark.asyncio
    async def test_sem_capacidade_declarada_as_vagas_vem_do_banco(self, fabrica, estavel):
        # Nunca mandou `capacity`: vale o teto do registro.
        await _runs(fabrica, "A", "running", 2)
        await _runs(fabrica, "B", "running", 2)
        ordem = await _ordenar(fabrica, _registro(), [_executor("A", vagas=2), _executor("B", vagas=8)])
        assert ordem == ["B", "A"]


# ══════════════════════════════════════════════════════════════════════════════
# Rajadas: o despacho real, com o INSERT de cada run no banco
# ══════════════════════════════════════════════════════════════════════════════

async def _rajada(fabrica, reg, pool, n):
    """Despacha `n` jobs em sequência pelo `_dispatch_job` real. A capacidade
    declarada fica congelada (o relatório de 10 s não chega no meio)."""
    wf, definicao = _wf(), {"nodes": [], "edges": []}
    with patch.object(wes, "executor_registry", reg), \
         patch.object(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **_: d)), \
         patch.object(wes, "build_job_message", MagicMock(return_value={"envelope": {}})):
        for _ in range(n):
            async with fabrica() as db:
                candidatos = await wes._elegiveis_ordenados(db, pool)
                await wes._dispatch_job(wf, definicao, candidatos, {}, False, db=db)
    return collections.Counter(reg.escolhidos)


class TestRajada:
    @pytest.mark.asyncio
    async def test_rajada_se_divide_entre_executores_ociosos(self, fabrica):
        # Antes: 30 jobs, 30 para o primeiro do banco.
        reg = _registro({e: _capacidade() for e in ("A", "B", "C")})
        pool = [_executor("A"), _executor("B"), _executor("C")]
        recebidos = await _rajada(fabrica, reg, pool, 30)
        assert recebidos == {"A": 10, "B": 10, "C": 10}

    @pytest.mark.asyncio
    async def test_rajada_segue_a_proporcao_das_vagas(self, fabrica, estavel):
        reg = _registro({
            "grande": _capacidade(max_concurrent=8),
            "pequeno": _capacidade(max_concurrent=2),
        })
        pool = [_executor("grande", vagas=8), _executor("pequeno", vagas=2)]
        recebidos = await _rajada(fabrica, reg, pool, 10)
        assert recebidos == {"grande": 8, "pequeno": 2}

    @pytest.mark.asyncio
    async def test_rajada_em_pool_misto_nao_passa_da_fila_de_ninguem(self, fabrica, estavel):
        # 16 vagas + fila 50 (cabem 66) e 4 vagas + fila 50 (cabem 54), relatório
        # congelado em zero. Pela ocupação relativa, "grande" recebia ~4 jobs
        # para cada 1 de "pequeno" e passava dos 66 antes de "pequeno" chegar
        # à metade — cada excedente, um run falhado na fila local dele.
        reg = _registro({
            "grande": _capacidade(max_concurrent=16),
            "pequeno": _capacidade(max_concurrent=4),
        })
        pool = [_executor("grande", vagas=16), _executor("pequeno", vagas=4)]
        recebidos = await _rajada(fabrica, reg, pool, 110)
        assert recebidos["grande"] <= 66 and recebidos["pequeno"] <= 54
        assert sum(recebidos.values()) == 110

    @pytest.mark.asyncio
    async def test_run_encerrado_libera_a_vaga(self, fabrica, estavel):
        # A e B com um job cada; o de A termina — o próximo vai para A.
        reg = _registro({e: _capacidade() for e in ("A", "B")})
        pool = [_executor("A"), _executor("B")]
        await _rajada(fabrica, reg, pool, 2)
        async with fabrica() as db:
            run_de_a = (await db.execute(
                select(WorkflowRun).where(WorkflowRun.host == "executor:A")
            )).scalar_one()
            run_de_a.status = "success"
            await db.commit()
        reg.escolhidos.clear()
        recebidos = await _rajada(fabrica, reg, [_executor("B"), _executor("A")], 1)
        assert recebidos == {"A": 1}


# ══════════════════════════════════════════════════════════════════════════════
# Sorteio
# ══════════════════════════════════════════════════════════════════════════════

class TestSorteio:
    @pytest.mark.asyncio
    async def test_empate_e_sorteado(self, fabrica):
        # Com o pool ocioso, qualquer um pode ser o primeiro — não mais o
        # primeiro do banco sempre. 300 sorteios entre 3: a chance de um deles
        # nunca liderar é desprezível (~3·(2/3)^300).
        reg = _registro({e: _capacidade() for e in ("A", "B", "C")})
        pool = [_executor("A"), _executor("B"), _executor("C")]
        primeiros = collections.Counter()
        async with fabrica() as db:
            with patch.object(wes, "executor_registry", reg):
                for _ in range(300):
                    primeiros[(await wes._elegiveis_ordenados(db, pool))[0].id_hash] += 1
        assert set(primeiros) == {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_decisoes_simultaneas_se_espalham(self, fabrica):
        # Vários despachos ao mesmo tempo partem do MESMO retrato: nenhum INSERT
        # entre eles. Com o mínimo estrito, todos iam para A. Agora cada um
        # sorteia pelas vagas livres (A 4, B 3, C 3): esperado ~40/30/30%.
        await _runs(fabrica, "B", "running", 1)
        await _runs(fabrica, "C", "running", 1)
        pool = [_executor("A"), _executor("B"), _executor("C")]
        primeiros = collections.Counter()
        async with fabrica() as db:
            with patch.object(wes, "executor_registry", _registro()):
                for _ in range(300):
                    primeiros[(await wes._elegiveis_ordenados(db, pool))[0].id_hash] += 1
        # Margens de pelo menos 5 desvios-padrão: não é teste de gerador aleatório.
        assert 60 <= primeiros["A"] <= 180
        assert primeiros["B"] >= 45 and primeiros["C"] >= 45

    @pytest.mark.asyncio
    async def test_sem_vaga_nunca_passa_na_frente_de_quem_tem_vaga(self, fabrica):
        # O sorteio só vale entre quem tem vaga livre: A lotado (4 de 4) nunca
        # vem antes de B com uma vaga, por mais que o sorteio favoreça A.
        await _runs(fabrica, "A", "running", 4)
        await _runs(fabrica, "B", "running", 3)
        for _ in range(50):
            assert await _ordenar(fabrica, _registro(), [_executor("A"), _executor("B")]) == ["B", "A"]


# ══════════════════════════════════════════════════════════════════════════════
# A consulta ao banco: savepoint, falhas e atalhos
# ══════════════════════════════════════════════════════════════════════════════

class TestConsulta:
    @pytest.mark.asyncio
    async def test_um_candidato_so_nao_consulta_carga(self):
        db = MagicMock()
        db.connection = AsyncMock()
        reg = _registro()
        with patch.object(wes, "executor_registry", reg):
            ordem = await wes._elegiveis_ordenados(db, [_executor("A"), _executor("B")], excluir={"B"})
        assert _ordem(ordem) == ["A"]
        db.connection.assert_not_awaited()
        reg.read_capacities.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_banco_falhando_ordena_pela_declarada_num_savepoint(self, estavel):
        # No Postgres, um erro nesta consulta abortaria a transação do request e
        # o INSERT do run falharia logo depois. O savepoint — na CONEXÃO, não na
        # sessão — isola a falha; a ordem cai para a carga declarada.
        async def _falha(_consulta):
            raise _erro_do_banco()

        db, eventos = _sessao_falsa(_falha)
        reg = _registro({"A": _capacidade(running=3), "B": _capacidade()})
        with patch.object(wes, "executor_registry", reg), \
             patch.object(wes._logger, "warning") as aviso:
            ordem = await wes._elegiveis_ordenados(db, [_executor("A"), _executor("B")])
        assert eventos == ["SAVEPOINT", "SELECT", "ROLLBACK TO SAVEPOINT"]
        assert _ordem(ordem) == ["B", "A"]
        assert "Carga contada pelo servidor indisponível" in aviso.call_args.args[0]
        db.begin_nested.assert_not_called()

    @pytest.mark.asyncio
    async def test_conexao_perdida_sobe(self):
        # Conexão invalidada não é degradação: o INSERT adiante falharia de
        # todo jeito, e com "Can't reconnect until invalid transaction is
        # rolled back" no lugar do erro de verdade.
        async def _falha(_consulta):
            raise _erro_do_banco(conexao_perdida=True)

        db, _ = _sessao_falsa(_falha)
        with patch.object(wes, "executor_registry", _registro()), pytest.raises(OperationalError):
            await wes._elegiveis_ordenados(db, [_executor("A"), _executor("B")])

    @pytest.mark.asyncio
    async def test_erro_que_nao_e_do_banco_sobe(self):
        # Só erro do driver vira "ordena pela declarada". Um TypeError aqui é
        # bug nosso, e engolido ele se esconderia atrás de um aviso.
        async def _bug(_consulta):
            raise TypeError("bug")

        db, _ = _sessao_falsa(_bug)
        with patch.object(wes, "executor_registry", _registro()), pytest.raises(TypeError):
            await wes._elegiveis_ordenados(db, [_executor("A"), _executor("B")])

    @pytest.mark.asyncio
    async def test_contagem_nao_descarrega_o_pendente_da_sessao(self, fabrica):
        # `Session.begin_nested()` faz flush antes do SAVEPOINT. Se a sessão do
        # chamador tivesse algo pendente e inválido, o erro do flush seria
        # engolido aqui como "contagem indisponível", com a transação perdida.
        # Com o savepoint na conexão, a contagem não toca no que está pendente.
        await _runs(fabrica, "A", "running", 1)
        async with fabrica() as db:
            existente = (await db.execute(select(WorkflowRun))).scalar_one()
            duplicado = WorkflowRun(
                task_id=existente.task_id, workflow_hash="wf-1", workspace_id="ws-1",
                status="pending", host="executor:B",
            )
            db.add(duplicado)
            contadas = await wes._contadas_pelo_servidor(db, ["A", "B"])
            assert contadas == {"A": 1}
            assert duplicado in db.new

    @pytest.mark.asyncio
    async def test_leitura_de_capacidade_que_estoura_conta_como_nao_declarada(self, fabrica, estavel):
        await _runs(fabrica, "B", "running", 1)
        reg = _registro()
        reg.read_capacities = AsyncMock(side_effect=RuntimeError("redis fora"))
        assert await _ordenar(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_capacidade_malformada_nao_derruba_a_ordem(self, fabrica, estavel):
        # A capacidade vem de fora (executor → Redis): lixo conta como nada
        # declarado — nem cheio, nem vagas —, e as vagas vêm do banco.
        await _runs(fabrica, "B", "running", 1)
        reg = _registro({
            "A": {"running": "muitos", "queued": None, "max_concurrent": True},
            "B": _capacidade(),
        })
        assert await _ordenar(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]
