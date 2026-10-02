# tests/unit/test_executor_supervisor.py
"""
Watchdog do processo supervisor (anti-orfao).

O cenario que ele existe para evitar: o usuario mata o app desktop pelo
Gerenciador de Tarefas; o Electron morre sem encerrar o filho; o executor
continua vivo, sem janela e sem tray, segurando a conexao WebSocket sob o mesmo
EXECUTOR_ID. Na proxima vez que o app subir, o servidor ve duas conexoes do
mesmo executor.

O caso mais sutil coberto aqui e o **reuso de PID**: o sistema operacional
reaproveita numeros de processo, e um watchdog que so compara o PID concluiria
que o supervisor esta vivo quando na verdade outro programa herdou o numero.
"""
import asyncio

import pytest

from executor import supervisor


# ── Leitura da variavel ──────────────────────────────────────────────────────

def test_sem_variavel_nao_ha_o_que_vigiar(monkeypatch):
    """Rodar `python -m executor` na mao nao define a variavel — o watchdog
    simplesmente nao sobe."""
    monkeypatch.delenv(supervisor.VAR_PID, raising=False)
    assert supervisor.pid_configurado() is None


@pytest.mark.parametrize("valor", ["", "   ", "abc", "0", "-5", "12.5"])
def test_valor_invalido_desativa_em_vez_de_derrubar(monkeypatch, valor):
    """Uma variavel malformada nao pode impedir o executor de subir."""
    monkeypatch.setenv(supervisor.VAR_PID, valor)
    assert supervisor.pid_configurado() is None


def test_valor_valido_e_lido(monkeypatch):
    monkeypatch.setenv(supervisor.VAR_PID, " 4321 ")
    assert supervisor.pid_configurado() == 4321


# ── Identidade do processo ───────────────────────────────────────────────────

class _ProcFalso:
    def __init__(self, *, rodando=True, criado=1000.0, status="running"):
        self._rodando, self._criado, self._status = rodando, criado, status

    def is_running(self): return self._rodando
    def create_time(self): return self._criado
    def status(self): return self._status


def _monitor(proc, criado=1000.0):
    m = supervisor.MonitorSupervisor(4321, intervalo=0.01)
    m._proc, m._criado_em = proc, criado
    return m


def test_supervisor_vivo():
    assert _monitor(_ProcFalso()).vivo() is True


def test_supervisor_encerrado():
    assert _monitor(_ProcFalso(rodando=False)).vivo() is False


def test_pid_reciclado_por_outro_processo_conta_como_morto():
    """O nucleo do teste: mesmo PID, `create_time` diferente — e outro programa
    que herdou o numero, nao o supervisor. So comparar o PID deixaria o orfao
    vivo para sempre."""
    assert _monitor(_ProcFalso(criado=2000.0), criado=1000.0).vivo() is False


def test_zumbi_nao_conta_como_vivo():
    """Processo zumbi ainda responde True ao `is_running()`, mas nao supervisiona
    ninguem."""
    import psutil
    assert _monitor(_ProcFalso(status=psutil.STATUS_ZOMBIE)).vivo() is False


def test_excecao_do_psutil_conta_como_morto():
    """NoSuchProcess, AccessDenied num processo que trocou de dono — todos
    significam 'o supervisor que eu conhecia se foi'."""
    class _Explode:
        def is_running(self): raise RuntimeError("sumiu")

    assert _monitor(_Explode()).vivo() is False


def test_sem_vincular_conta_como_morto():
    assert supervisor.MonitorSupervisor(4321).vivo() is False


# ── Vinculo ──────────────────────────────────────────────────────────────────

def test_vincular_no_proprio_processo_funciona():
    import os
    m = supervisor.MonitorSupervisor(os.getpid())
    assert m.vincular() is True
    assert m.vivo() is True


def test_vincular_em_pid_inexistente_falha_sem_levantar():
    # PID absurdo: acima do limite de qualquer sistema em uso.
    m = supervisor.MonitorSupervisor(2 ** 31 - 1)
    assert m.vincular() is False


# ── Loop ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vigiar_dispara_o_shutdown_quando_o_supervisor_some():
    disparos = []
    m = _monitor(_ProcFalso(rodando=False))
    await asyncio.wait_for(m.vigiar(lambda: disparos.append(True)), timeout=2.0)
    assert disparos == [True]


@pytest.mark.asyncio
async def test_vigiar_nao_dispara_enquanto_vivo():
    disparos = []
    m = _monitor(_ProcFalso())
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(m.vigiar(lambda: disparos.append(True)), timeout=0.1)
    assert disparos == []


@pytest.mark.asyncio
async def test_handler_que_levanta_nao_deixa_a_task_estourar():
    """A task e observada por `_observar_task`; um erro aqui viraria ERROR no
    log a cada boot."""
    m = _monitor(_ProcFalso(rodando=False))
    await asyncio.wait_for(
        m.vigiar(lambda: (_ for _ in ()).throw(RuntimeError("boom"))), timeout=2.0)


@pytest.mark.asyncio
async def test_criar_task_sem_variavel_devolve_none(monkeypatch):
    monkeypatch.delenv(supervisor.VAR_PID, raising=False)
    assert supervisor.criar_task(lambda: None) is None


@pytest.mark.asyncio
async def test_supervisor_ja_morto_no_start_encerra_na_hora(monkeypatch):
    """Se o supervisor morreu entre o spawn e o boot, encerrar ja e o certo:
    ninguem vai consumir o canal NDJSON nem parar este processo depois."""
    monkeypatch.setenv(supervisor.VAR_PID, str(2 ** 31 - 1))
    disparos = []
    assert supervisor.criar_task(lambda: disparos.append(True)) is None
    assert disparos == [True]


@pytest.mark.asyncio
async def test_criar_task_com_supervisor_vivo_sobe_a_task(monkeypatch):
    import os
    monkeypatch.setenv(supervisor.VAR_PID, str(os.getpid()))
    task = supervisor.criar_task(lambda: None, intervalo=0.01)
    assert task is not None
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
