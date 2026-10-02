# tests/unit/test_executor_json_ipc.py
"""
Canal NDJSON entre o executor e um supervisor (o app desktop).

Isto e um teste de CONTRATO: o outro lado da ponte e TypeScript, num
repositorio de build separado, e nao ha type checker que atravesse a fronteira.
O que garante que os dois lados falam a mesma lingua sao estes casos.

Tres coisas sao travadas aqui:

  FRAMING       toda linha comeca por `{"v":1,` e nada mais escreve no stdout.
                E o que permite ao leitor descartar um `print()` acidental de um
                no de workflow sem confundi-lo com evento.

  COMPLETUDE    todo campo de `Snapshot` aparece no dict serializado. Sem isto,
                um campo novo nasceria invisivel para a GUI e ninguem notaria.
                A excecao e deliberada e esta travada em
                `test_snapshot_emitido_omite_os_campos_so_do_painel`: o evento
                `snapshot` do NDJSON tira `log_tail` e `system` do dict.

  NAO-BLOQUEIO  o observer roda com o lock do stats segurado e e chamado das
                threads do flow engine. Se ele bloquear, o executor para.
"""
import json
import logging
import threading
import time

import pytest

from executor.dashboard import json_runtime
from executor.stats import ExecutorStats, NullStats, Snapshot, snapshot_to_dict


# ── Serializacao ─────────────────────────────────────────────────────────────

def _snapshot(**kw) -> Snapshot:
    st = ExecutorStats(executor_id="exec-1", version="9.9.9", server_url="wss://x")
    st.system = {"cpu_cores": 8, "container": False}
    for k, v in kw.items():
        setattr(st, k, v)
    return st.snapshot()


def test_todo_campo_do_snapshot_sai_no_dict():
    """Completude: quem adiciona um campo ao Snapshot ganha o campo no JSON.
    Se este teste falhar, alguem trocou o asdict por uma lista manual."""
    import dataclasses
    snap = _snapshot()
    d = snapshot_to_dict(snap)
    faltando = {f.name for f in dataclasses.fields(Snapshot)} - set(d)
    assert not faltando, f"campos ausentes na serializacao: {sorted(faltando)}"


@pytest.mark.asyncio
async def test_snapshot_emitido_omite_os_campos_so_do_painel():
    """A completude acima vale para `snapshot_to_dict`; o evento `snapshot` do
    NDJSON tira dois campos de proposito.

    `log_tail` sao ate 200 linhas de log REENVIADAS a cada segundo, e o
    supervisor ja recebe log incremental pelos eventos `log` — o tail so repete
    o que ele tem. `system` e hardware, que nao muda de um tick para o outro.
    Nenhum dos dois era lido do outro lado, e os dois atravessavam o pipe, o
    `JSON.parse` e um structured clone por janela, a 1 Hz, com o executor
    ocioso. Os contadores `log_warn_count`/`log_error_count` continuam saindo:
    sao dois inteiros e a GUI os mostra.
    """
    st = ExecutorStats(executor_id="e1")
    st.system = {"cpu_cores": 8}
    st.on_log_record(logging.LogRecord("executor.sync", logging.WARNING, "", 0,
                                       "aviso", (), None), "SYNC  ", "WARN ")
    rt = _RuntimeIsolado()
    rt._stats = st
    rt._emitir_snapshot()

    msg = json.loads(rt.linhas()[-1])
    assert msg["t"] == "snapshot"
    assert "log_tail" not in msg["data"]
    assert "system" not in msg["data"]
    assert msg["data"]["log_warn_count"] == 1
    assert msg["data"]["log_error_count"] == 0


def test_dict_e_serializavel_e_sem_tipos_exoticos():
    d = snapshot_to_dict(_snapshot())
    texto = json.dumps(d)          # levanta se algo nao for JSON-safe
    assert json.loads(texto) == d


def test_tuplas_heterogeneas_viram_objetos_nomeados():
    """`slowest` e `last_finished` sao tuplas no dataclass. Em JSON virariam
    arrays posicionais, e do outro lado `snap.slowest[1]` e um indice sem nome
    que quebra em silencio se a ordem mudar."""
    st = ExecutorStats()
    st.on_job_finished("j1", "error", 12.5, run_id="run-7")
    d = snapshot_to_dict(st.snapshot())

    assert d["slowest"] == {"run_id": "run-7", "duration_s": 12.5}
    assert d["last_finished"] == {"run_id": "run-7", "status": "error", "duration_s": 12.5}


def test_sem_jobs_os_dois_campos_sao_nulos():
    d = snapshot_to_dict(_snapshot())
    assert d["slowest"] is None and d["last_finished"] is None


def test_nan_e_infinito_viram_nulo():
    """`json.dumps` emite `NaN`/`Infinity` por padrao, que NAO sao JSON valido:
    `JSON.parse` do outro lado estoura e o canal inteiro morre por causa de uma
    divisao malfeita numa metrica."""
    from executor.stats import _json_safe
    assert _json_safe(float("nan"), 3) is None
    assert _json_safe(float("inf"), 3) is None
    assert _json_safe(float("-inf"), 3) is None
    assert json.dumps(_json_safe({"a": float("nan")}, 3)) == '{"a": null}'


def test_valor_exotico_degrada_para_texto():
    """`system` e montado por sysinfo e pode mudar. Um valor inesperado nao pode
    derrubar a serializacao e, com ela, o canal."""
    class Esquisito:
        def __str__(self): return "esquisito"

    snap = _snapshot()
    d = snapshot_to_dict(snap)
    from executor.stats import _json_safe
    assert _json_safe(Esquisito(), 3) == "esquisito"
    assert isinstance(d["system"], dict)


# ── Observer ─────────────────────────────────────────────────────────────────

def _coletor():
    eventos = []
    return eventos, lambda tipo, dados: eventos.append((tipo, dados))


def test_dois_jobs_no_mesmo_tick_geram_dois_eventos():
    """A razao de o observer existir: `last_finished` guarda UM job, entao com
    tick de 1s o primeiro de dois desapareceria do historico da GUI."""
    eventos, obs = _coletor()
    st = ExecutorStats(observer=obs)
    st.on_job_finished("j1", "ok", 1.0, run_id="r1")
    st.on_job_finished("j2", "error", 2.0, run_id="r2")

    jobs = [d for t, d in eventos if t == "job"]
    assert [j["run_id"] for j in jobs] == ["r1", "r2"]
    assert [j["status"] for j in jobs] == ["ok", "error"]


def test_cancelamento_de_job_em_execucao_emite_uma_vez_so():
    """`on_job_cancelled` delega para `on_job_finished` quando o job esta
    rodando. Emitir nos dois faria a GUI contar o cancelamento em dobro."""
    eventos, obs = _coletor()
    st = ExecutorStats(observer=obs)
    st.on_job_started("j1", run_id="r1")
    eventos.clear()
    st.on_job_cancelled("j1")

    cancelados = [d for t, d in eventos if t == "job" and d["event"] == "cancelled"]
    assert len(cancelados) == 1


def test_job_descartado_sem_rodar_tambem_emite():
    eventos, obs = _coletor()
    st = ExecutorStats(observer=obs)
    st.on_job_cancelled("j-nunca-rodou", motivo="fila cheia")

    cancelados = [d for t, d in eventos if t == "job" and d["event"] == "cancelled"]
    assert len(cancelados) == 1
    assert cancelados[0]["motivo"] == "fila cheia"


def test_conexao_emite_transicoes():
    eventos, obs = _coletor()
    st = ExecutorStats(observer=obs)
    st.on_connecting()
    st.on_connected()
    st.on_disconnected(proximo_retry_s=8.0)

    estados = [d["state"] for t, d in eventos if t == "conn"]
    assert estados == ["connecting", "connected", "reconnecting"]
    assert eventos[-1][1]["next_retry_in_s"] == 8.0


def test_observer_que_levanta_nao_derruba_o_hook():
    """Mesma regra dos demais hooks: telemetria quebrada nao pode derrubar a
    execucao de um workflow."""
    def explode(tipo, dados):
        raise RuntimeError("boom")

    st = ExecutorStats(observer=explode)
    st.on_job_started("j1")              # nao deve levantar
    st.on_job_finished("j1", "ok", 1.0)
    assert st.snapshot().total_ok == 1


def test_sem_observer_nada_muda():
    st = ExecutorStats()
    st.on_job_finished("j1", "ok", 1.0)
    assert st.snapshot().total_ok == 1


# ── Framing e emissao ────────────────────────────────────────────────────────

class _RuntimeIsolado(json_runtime.JsonRuntime):
    """JsonRuntime sem thread nem event loop: `emitir` enfileira, e o teste le
    o buffer direto. Isola o formato do transporte."""

    def __init__(self):
        super().__init__(NullStats(), capacity_source=None, result_queue=None,
                         intervalo=1.0)

    def linhas(self):
        with self._cond:
            return list(self._buffer)


def test_toda_linha_tem_o_framing():
    rt = _RuntimeIsolado()
    rt.emitir("hello", {"pid": 1})
    rt.emitir("state", {"phase": "booting"})
    rt.emitir("ack", None, cmd="ping", ok=True)

    linhas = rt.linhas()
    assert len(linhas) == 3
    for linha in linhas:
        assert linha.startswith('{"v":1,'), linha
        assert "\n" not in linha            # o \n e adicionado na escrita
        msg = json.loads(linha)
        assert msg["v"] == json_runtime.PROTOCOLO
        assert isinstance(msg["ts"], float)


def test_linha_gigante_vira_aviso_em_vez_de_estourar():
    """Um `log_tail` patologico nao pode virar uma linha de megabytes que trava
    o parser do outro lado."""
    rt = _RuntimeIsolado()
    rt.emitir("snapshot", {"lixo": "x" * (json_runtime._LINHA_MAX + 10)})

    msg = json.loads(rt.linhas()[0])
    assert msg["t"] == "warn"
    assert "tamanho" in msg["data"]["motivo"]


def test_buffer_cheio_descarta_o_mais_antigo_e_conta():
    """Ao encher, o mais ANTIGO cai: para snapshots, que se substituem, o
    consumidor quer o estado atual, nao o de 40s atras. O descarte e contado e
    reportado no proximo snapshot — perda silenciosa seria pior."""
    rt = _RuntimeIsolado()
    for i in range(json_runtime._BUFFER_MAX + 25):
        rt.emitir("snapshot", {"i": i})

    linhas = rt.linhas()
    assert len(linhas) == json_runtime._BUFFER_MAX
    assert rt._descartados == 25
    assert json.loads(linhas[0])["data"]["i"] == 25      # os 25 primeiros cairam


def test_emitir_nunca_levanta_com_dado_impossivel():
    rt = _RuntimeIsolado()
    rt.emitir("snapshot", {"self": object()})   # nao serializavel
    assert rt.linhas() == []                    # descartado, sem excecao


def test_emitir_e_rapido_o_bastante_para_rodar_sob_lock():
    """O observer segura o `_lock` do stats e e chamado das threads do flow
    engine. Se `emitir` fizesse I/O aqui, `on_log_record` travaria e o executor
    inteiro pararia. 2000 eventos precisam custar bem menos que um tick."""
    rt = _RuntimeIsolado()
    inicio = time.perf_counter()
    for i in range(2000):
        rt.emitir("job", {"event": "finished", "i": i})
    assert time.perf_counter() - inicio < 1.0


def test_emitir_e_seguro_entre_threads():
    rt = _RuntimeIsolado()
    def trabalhar():
        for i in range(500):
            rt.emitir("job", {"i": i})

    ts = [threading.Thread(target=trabalhar) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(rt.linhas()) == json_runtime._BUFFER_MAX     # nada corrompido


# ── Comandos ─────────────────────────────────────────────────────────────────

def test_comando_shutdown_dispara_o_handler():
    chamou = []
    rt = _RuntimeIsolado()
    rt._ao_sair = lambda: chamou.append(True)
    rt._executar_comando({"cmd": "shutdown", "id": "c1"})

    assert chamou == [True]
    ack = json.loads(rt.linhas()[-1])
    assert ack["t"] == "ack" and ack["ok"] is True and ack["id"] == "c1"


def test_comando_reconnect_reporta_se_havia_backoff():
    rt = _RuntimeIsolado()
    rt._ao_reconectar = lambda: False
    rt._executar_comando({"cmd": "reconnect"})
    assert "nao ha espera" in json.loads(rt.linhas()[-1])["detail"]


def test_comando_desconhecido_responde_ack_negativo():
    """Sem isto, a GUI espera para sempre por uma resposta que nunca vem."""
    rt = _RuntimeIsolado()
    rt._executar_comando({"cmd": "formatar_disco"})
    ack = json.loads(rt.linhas()[-1])
    assert ack["ok"] is False and "desconhecido" in ack["detail"]


def test_comando_que_levanta_vira_ack_negativo():
    rt = _RuntimeIsolado()
    rt._ao_sair = lambda: (_ for _ in ()).throw(RuntimeError("falhou"))
    rt._executar_comando({"cmd": "shutdown"})
    ack = json.loads(rt.linhas()[-1])
    assert ack["ok"] is False and "falhou" in ack["detail"]


def test_reset_stats_funciona_com_null_stats():
    """`NullStats` nao tinha `reset` — o comando levantava AttributeError com o
    coletor desligado."""
    rt = _RuntimeIsolado()
    rt._executar_comando({"cmd": "reset_stats"})
    assert json.loads(rt.linhas()[-1])["ok"] is True


@pytest.mark.parametrize("cmd", json_runtime.COMANDOS)
def test_todo_comando_anunciado_no_hello_e_aceito(cmd):
    """O `hello` publica a lista de comandos. Anunciar um que responde
    'desconhecido' seria mentir para o outro lado da ponte."""
    rt = _RuntimeIsolado()
    rt._ao_sair = lambda: None
    rt._ao_reconectar = lambda: True
    rt._ao_sincronizar = lambda: 1
    rt._executar_comando({"cmd": cmd})
    ack = json.loads(rt.linhas()[-1])
    assert ack["ok"] is True, f"{cmd}: {ack.get('detail')}"


# ── Handler de log ───────────────────────────────────────────────────────────

# ── Ligacao (o que os testes de unidade acima NAO cobriam) ───────────────────

@pytest.mark.asyncio
async def test_dashboard_start_json_liga_o_observer():
    """Regressao: o mecanismo do observer estava certo e testado, mas ninguem o
    LIGAVA — `dashboard.start(modo="json")` criava o runtime e nunca chamava
    `stats.set_observer`.

    O sintoma nao era um erro: o canal seguia emitindo snapshots normalmente, as
    metricas do painel ficavam corretas, e so o historico de execucoes ficava
    permanentemente vazio. `last_finished` do snapshot guarda UM job, entao o
    consumidor nao tem como reconstruir a lista a partir dele.
    """
    from executor import dashboard

    st = ExecutorStats(executor_id="e1")
    rt = await dashboard.start(
        st, modo=dashboard.MODO_JSON,
        capacity_source=None, result_queue=None, intervalo=60.0,
    )
    assert rt is not None
    try:
        st.on_job_finished("j1", "ok", 1.5, run_id="r1")
        with rt._cond:
            linhas = list(rt._buffer)
        jobs = [json.loads(l) for l in linhas if json.loads(l)["t"] == "job"]
        assert len(jobs) == 1
        assert jobs[0]["data"]["run_id"] == "r1"
    finally:
        await rt.stop()


@pytest.mark.asyncio
async def test_stop_desliga_o_observer():
    """Observer apontando para um runtime fechado enfileiraria cada job novo num
    buffer que ninguem drena."""
    from executor import dashboard

    st = ExecutorStats(executor_id="e1")
    rt = await dashboard.start(
        st, modo=dashboard.MODO_JSON,
        capacity_source=None, result_queue=None, intervalo=60.0,
    )
    assert rt is not None
    await rt.stop()

    st.on_job_finished("j2", "ok", 1.0)
    assert st._observer is None


def test_json_log_handler_emite_e_alimenta_o_ring():
    from executor.dashboard.log_sink import JsonLogHandler

    rt = _RuntimeIsolado()
    st = ExecutorStats()
    handler = JsonLogHandler(st, rt)
    handler.emit(logging.LogRecord(
        "executor.connection", logging.WARNING, __file__, 1,
        "reconectando em %ds", (8,), None,
    ))

    msg = json.loads(rt.linhas()[-1])
    assert msg["t"] == "log"
    assert msg["data"]["msg"] == "reconectando em 8s"
    assert msg["data"]["level"] == "WARN"
    # E o MESMO registro alimenta o rodape do painel rich.
    assert st.snapshot().log_tail[-1].msg == "reconectando em 8s"


# ── sync_now ─────────────────────────────────────────────────────────────────

def test_sync_now_sem_pasta_configurada_NAO_e_falha():
    """`ok` diz que o comando era valido e foi executado, nao que algo mudou.

    Mesma convencao de `reconnect`, que responde ok mesmo sem backoff para
    interromper. Tratar "nao ha pasta" como falha faria a UI mostrar erro
    vermelho para uma configuracao perfeitamente normal.
    """
    rt = _RuntimeIsolado()
    rt._ao_sincronizar = lambda: 0
    rt._executar_comando({"cmd": "sync_now"})
    ack = json.loads(rt.linhas()[-1])
    assert ack["ok"] is True
    assert "nenhuma pasta" in ack["detail"]


def test_sync_now_relata_quantas_pastas_acordou():
    rt = _RuntimeIsolado()
    rt._ao_sincronizar = lambda: 2
    rt._executar_comando({"cmd": "sync_now"})
    ack = json.loads(rt.linhas()[-1])
    assert ack["ok"] is True and "2 pasta" in ack["detail"]


def test_sync_now_sem_handler_e_falha_de_ligacao():
    """Handler ausente e bug de wiring, nao estado do usuario — e precisa doer."""
    rt = _RuntimeIsolado()
    rt._ao_sincronizar = None
    rt._executar_comando({"cmd": "sync_now"})
    assert json.loads(rt.linhas()[-1])["ok"] is False
