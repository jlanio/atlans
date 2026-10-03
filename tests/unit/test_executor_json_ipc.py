# tests/unit/test_executor_json_ipc.py
"""
NDJSON channel between the executor and a supervisor (the desktop app).

This is a CONTRACT test: the other side of the bridge is TypeScript, in a
separate build repository, and no type checker crosses the boundary. What
guarantees that both sides speak the same language are these cases.

Three things are locked down here:

  FRAMING       every line starts with `{"v":1,` and nothing else writes to
                stdout. That is what lets the reader discard an accidental
                `print()` from a workflow node without mistaking it for an event.

  COMPLETENESS  every `Snapshot` field appears in the serialized dict. Without
                this, a new field would be born invisible to the GUI and nobody
                would notice. The exception is deliberate and locked down in
                `test_snapshot_emitido_omite_os_campos_so_do_painel`: the NDJSON
                `snapshot` event drops `log_tail` and `system` from the dict.

  NON-BLOCKING  the observer runs with the stats lock held and is called from
                the flow engine threads. If it blocks, the executor stops.
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
    """Completeness: whoever adds a field to Snapshot gets the field in the JSON.
    If this test fails, someone replaced asdict with a manual list."""
    import dataclasses
    snap = _snapshot()
    d = snapshot_to_dict(snap)
    faltando = {f.name for f in dataclasses.fields(Snapshot)} - set(d)
    assert not faltando, f"campos ausentes na serializacao: {sorted(faltando)}"


@pytest.mark.asyncio
async def test_snapshot_emitido_omite_os_campos_so_do_painel():
    """The completeness above holds for `snapshot_to_dict`; the NDJSON `snapshot`
    event drops two fields on purpose.

    `log_tail` is up to 200 log lines RESENT every second, and the supervisor
    already receives the log incrementally through the `log` events — the tail
    only repeats what it has. `system` is hardware, which does not change from
    one tick to the next. Neither was read on the other side, and both went
    through the pipe, `JSON.parse` and a structured clone per window, at 1 Hz,
    with the executor idle. The `log_warn_count`/`log_error_count` counters are
    still sent: they are two integers and the GUI shows them.
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
    texto = json.dumps(d)          # raises if something is not JSON-safe
    assert json.loads(texto) == d


def test_tuplas_heterogeneas_viram_objetos_nomeados():
    """`slowest` and `last_finished` are tuples in the dataclass. In JSON they
    would become positional arrays, and on the other side `snap.slowest[1]` is
    an unnamed index that silently breaks if the order changes."""
    st = ExecutorStats()
    st.on_job_finished("j1", "error", 12.5, run_id="run-7")
    d = snapshot_to_dict(st.snapshot())

    assert d["slowest"] == {"run_id": "run-7", "duration_s": 12.5}
    assert d["last_finished"] == {"run_id": "run-7", "status": "error", "duration_s": 12.5}


def test_sem_jobs_os_dois_campos_sao_nulos():
    d = snapshot_to_dict(_snapshot())
    assert d["slowest"] is None and d["last_finished"] is None


def test_nan_e_infinito_viram_nulo():
    """`json.dumps` emits `NaN`/`Infinity` by default, which are NOT valid JSON:
    `JSON.parse` on the other side blows up and the whole channel dies because
    of a botched division in a metric."""
    from executor.stats import _json_safe
    assert _json_safe(float("nan"), 3) is None
    assert _json_safe(float("inf"), 3) is None
    assert _json_safe(float("-inf"), 3) is None
    assert json.dumps(_json_safe({"a": float("nan")}, 3)) == '{"a": null}'


def test_valor_exotico_degrada_para_texto():
    """`system` is assembled by sysinfo and may change. An unexpected value must
    not bring down the serialization and, with it, the channel."""
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
    """The reason the observer exists: `last_finished` keeps ONE job, so with a
    1s tick the first of two would disappear from the GUI history."""
    eventos, obs = _coletor()
    st = ExecutorStats(observer=obs)
    st.on_job_finished("j1", "ok", 1.0, run_id="r1")
    st.on_job_finished("j2", "error", 2.0, run_id="r2")

    jobs = [d for t, d in eventos if t == "job"]
    assert [j["run_id"] for j in jobs] == ["r1", "r2"]
    assert [j["status"] for j in jobs] == ["ok", "error"]


def test_cancelamento_de_job_em_execucao_emite_uma_vez_so():
    """`on_job_cancelled` delegates to `on_job_finished` when the job is running.
    Emitting in both would make the GUI count the cancellation twice."""
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
    """Same rule as the other hooks: broken telemetry must not bring down the
    execution of a workflow."""
    def explode(tipo, dados):
        raise RuntimeError("boom")

    st = ExecutorStats(observer=explode)
    st.on_job_started("j1")              # must not raise
    st.on_job_finished("j1", "ok", 1.0)
    assert st.snapshot().total_ok == 1


def test_sem_observer_nada_muda():
    st = ExecutorStats()
    st.on_job_finished("j1", "ok", 1.0)
    assert st.snapshot().total_ok == 1


# ── Framing e emissao ────────────────────────────────────────────────────────

class _RuntimeIsolado(json_runtime.JsonRuntime):
    """JsonRuntime with no thread or event loop: `emitir` enqueues, and the test
    reads the buffer directly. Isolates the format from the transport."""

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
    """A pathological `log_tail` must not become a megabytes-long line that
    freezes the parser on the other side."""
    rt = _RuntimeIsolado()
    rt.emitir("snapshot", {"lixo": "x" * (json_runtime._LINHA_MAX + 10)})

    msg = json.loads(rt.linhas()[0])
    assert msg["t"] == "warn"
    assert "tamanho" in msg["data"]["motivo"]


def test_buffer_cheio_descarta_o_mais_antigo_e_conta():
    """When full, the OLDEST is dropped: for snapshots, which replace each other,
    the consumer wants the current state, not the one from 40s ago. The drop is
    counted and reported in the next snapshot — silent loss would be worse."""
    rt = _RuntimeIsolado()
    for i in range(json_runtime._BUFFER_MAX + 25):
        rt.emitir("snapshot", {"i": i})

    linhas = rt.linhas()
    assert len(linhas) == json_runtime._BUFFER_MAX
    assert rt._descartados == 25
    assert json.loads(linhas[0])["data"]["i"] == 25      # the first 25 were dropped


def test_emitir_nunca_levanta_com_dado_impossivel():
    rt = _RuntimeIsolado()
    rt.emitir("snapshot", {"self": object()})   # not serializable
    assert rt.linhas() == []                    # discarded, without an exception


def test_emitir_e_rapido_o_bastante_para_rodar_sob_lock():
    """The observer holds the stats `_lock` and is called from the flow engine
    threads. If `emitir` did I/O here, `on_log_record` would block and the whole
    executor would stop. 2000 events need to cost much less than a tick."""
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
    """Without this, the GUI waits forever for a response that never comes."""
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
    """`NullStats` had no `reset` — the command raised AttributeError with the
    collector turned off."""
    rt = _RuntimeIsolado()
    rt._executar_comando({"cmd": "reset_stats"})
    assert json.loads(rt.linhas()[-1])["ok"] is True


@pytest.mark.parametrize("cmd", json_runtime.COMANDOS)
def test_todo_comando_anunciado_no_hello_e_aceito(cmd):
    """The `hello` publishes the list of commands. Announcing one that answers
    'desconhecido' (unknown) would be lying to the other side of the bridge."""
    rt = _RuntimeIsolado()
    rt._ao_sair = lambda: None
    rt._ao_reconectar = lambda: True
    rt._ao_sincronizar = lambda: 1
    rt._executar_comando({"cmd": cmd})
    ack = json.loads(rt.linhas()[-1])
    assert ack["ok"] is True, f"{cmd}: {ack.get('detail')}"


# ── Log handler ──────────────────────────────────────────────────────────────

# ── Wiring (what the unit tests above did NOT cover) ─────────────────────────

@pytest.mark.asyncio
async def test_dashboard_start_json_liga_o_observer():
    """Regression: the observer mechanism was correct and tested, but nobody
    WIRED it — `dashboard.start(modo="json")` created the runtime and never
    called `stats.set_observer`.

    The symptom was not an error: the channel kept emitting snapshots normally,
    the panel metrics were correct, and only the run history stayed permanently
    empty. The snapshot's `last_finished` keeps ONE job, so the consumer has no
    way to rebuild the list from it.
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
    """An observer pointing to a closed runtime would enqueue every new job into a
    buffer that nobody drains."""
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
    """`ok` says the command was valid and was executed, not that anything changed.

    Same convention as `reconnect`, which answers ok even with no backoff to
    interrupt. Treating "no folder" as a failure would make the UI show a red
    error for a perfectly normal configuration.
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
    """A missing handler is a wiring bug, not user state — and it has to hurt."""
    rt = _RuntimeIsolado()
    rt._ao_sincronizar = None
    rt._executar_comando({"cmd": "sync_now"})
    assert json.loads(rt.linhas()[-1])["ok"] is False
