# tests/unit/test_executor_stats.py
"""
Statistics collector for the executor panel (executor/stats.py).

Covers the pitfalls a metrics aggregator usually has:
  - division by zero before the first run
  - percentile with few samples
  - a sliding window that expires without taking the accumulated totals with it
  - a canceled job counted twice (arrives via on_execute AND via on_cancelled)
  - sync_event resend inflating the byte counters

The clock is injected in every case: no test sleeps.
"""
import logging

from executor.stats import ExecutorStats, NullStats, percentile


class _Clock:
    """Relogio manual — advance so quando o teste manda."""
    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def _stats(**kw) -> tuple[ExecutorStats, _Clock]:
    rel = _Clock()
    return ExecutorStats(clock=rel, **kw), rel


def _snap(st: ExecutorStats):
    return st.snapshot(capacity={}, recursos={}, processo={})


# ── Percentil ────────────────────────────────────────────────────────────────

def test_empty_and_single_percentile():
    """statistics.quantiles exige n>=2 e explodiria no executor recem-subido."""
    assert percentile([], 0.95) is None
    assert percentile([7.5], 0.95) == 7.5


def test_interpolated_percentile():
    """Same convention as numpy: p95 of 1..5 falls between 4 and 5."""
    assert percentile([1, 2, 3, 4, 5], 0.95) == 4.8
    assert percentile([1, 2, 3, 4, 5], 0.50) == 3.0


def test_percentile_with_one_hundred_samples():
    # 1 + (n-1)*q = 1 + 99*0.95 — o mesmo que numpy.percentile(..., 95) devolve.
    assert percentile(list(range(1, 101)), 0.95) == 95.05
    assert percentile(list(range(1, 101)), 0.50) == 50.5


# ── Success rate ─────────────────────────────────────────────────────────────

def test_success_rate_without_any_run():
    """A freshly started executor must not show '0% de sucesso' (0% success) — it
    would be a false alarm. And, first of all, the division must not blow up."""
    st, _ = _stats()
    assert _snap(st).success_rate == 1.0


def test_cancelled_counts_in_denominator_but_not_as_error():
    """A canceled job delivered no result: it weighs on the rate, but it is not a failure."""
    st, _ = _stats()
    for i in range(3):
        st.on_job_started(f"ok{i}")
        st.on_job_finished(f"ok{i}", "ok", 1.0)
    st.on_job_started("c")
    st.on_job_finished("c", "cancelled", 0.5)

    s = _snap(st)
    assert (s.total_ok, s.total_error, s.total_cancelled) == (3, 0, 1)
    assert s.success_rate == 0.75


def test_cancelled_stays_out_of_the_average_duration():
    """A job killed at 0.5s says nothing about how long a workflow takes —
    including it would pull the average down and hide real slowness."""
    st, _ = _stats()
    st.on_job_started("a")
    st.on_job_finished("a", "ok", 10.0)
    st.on_job_started("b")
    st.on_job_finished("b", "cancelled", 0.5)

    assert _snap(st).avg_duration_s == 10.0


# ── Double counting of cancellation ──────────────────────────────────────────

def test_cancelling_a_running_job_counts_only_once():
    """A job interrupted while running arrives TWICE: via the `finally` of
    on_execute (main.py) and via the queue's on_cancelled. Without the memory of
    finished ids, the total doubled."""
    st, _ = _stats()
    st.on_job_started("j1")
    st.on_job_finished("j1", "cancelled", 3.0)   # came from on_execute
    st.on_job_cancelled("j1", "cancelado pelo usuario")  # came from on_cancelled

    s = _snap(st)
    assert s.total_cancelled == 1
    assert s.last_hour_total == 1


def test_cancelling_a_job_that_never_ran_is_counted():
    """A job drained from the queue at shutdown never goes through on_execute — if
    on_cancelled also ignored it, it would vanish from the count."""
    st, _ = _stats()
    st.on_job_cancelled("na-fila", "Executor encerrando")
    assert _snap(st).total_cancelled == 1


# ── Janela sliding ────────────────────────────────────────────────────────

def test_one_hour_window_expires_but_the_total_remains():
    """'ultima hora' (last hour) and p95 use the window; the accumulated totals and
    the slowest job are since boot and must not vanish along with it."""
    st, rel = _stats()
    st.on_job_started("velho")
    st.on_job_finished("velho", "ok", 600.0)

    rel.advance(3601)

    st.on_job_started("novo")
    st.on_job_finished("novo", "ok", 5.0)

    s = _snap(st)
    assert s.last_hour_total == 1          # so o novo
    assert s.total_ok == 2                 # both
    assert s.slowest == ("velho", 600.0)   # sobrevive a expiration
    assert s.p95_duration_s == 5.0         # computed only over the window


def test_sample_ceiling_limits_the_memory():
    """A high-throughput executor must not grow the deque without limit."""
    st, _ = _stats(max_samples=50)
    for i in range(300):
        st.on_job_started(f"j{i}")
        st.on_job_finished(f"j{i}", "ok", 1.0)

    s = _snap(st)
    assert s.last_hour_total == 50
    assert s.total_ok == 300


# ── Running jobs and nodes ───────────────────────────────────────────────────

def test_active_job_reports_how_long_it_has_been_running():
    st, rel = _stats()
    st.on_job_started("j", run_id="r1")
    rel.advance(42)

    ativos = _snap(st).running
    assert len(ativos) == 1
    assert ativos[0].elapsed_s == 42
    assert ativos[0].run_id == "r1"


def test_current_node_and_progress_come_from_node_events():
    st, _ = _stats()
    st.on_job_started("j", run_id="r1")
    st.on_event({"run_id": "r1", "node": "n1", "status": "completed",
                 "extra": {"node_name": "buffer", "nodes_total": 9}})
    st.on_event({"run_id": "r1", "node": "n2", "status": "started",
                 "extra": {"node_name": "spatial_join", "nodes_total": 9}})

    job = _snap(st).running[0]
    assert job.node == "spatial_join"
    assert (job.nodes_done, job.nodes_total) == (1, 9)


def test_unknown_run_id_matches_when_there_is_ONE_candidate():
    """If the payload carries a run_id different from the job_id, matching by
    elimination still works — as long as there is no ambiguity."""
    st, _ = _stats()
    st.on_job_started("j")  # no run_id
    st.on_event({"run_id": "descoberto", "node": "n1", "status": "started",
                 "extra": {"node_name": "read_file"}})

    job = _snap(st).running[0]
    assert job.run_id == "descoberto"
    assert job.node == "read_file"


def test_ambiguous_run_id_is_NOT_assigned_to_anyone():
    """With MAX_CONCURRENT simultaneous jobs without run_id, picking 'the first'
    stuck one job's node onto another. A panel that lies is worse than an
    incomplete panel: with no single candidate, the event is discarded."""
    st, _ = _stats()
    st.on_job_started("jA")
    st.on_job_started("jB")
    st.on_event({"run_id": "run-de-um-deles", "node": "n1", "status": "started",
                 "extra": {"node_name": "buffer"}})

    assert all(job.node is None for job in _snap(st).running)
    assert all(job.run_id is None for job in _snap(st).running)


def test_run_id_given_on_start_resolves_the_ambiguity():
    """That is why main.on_execute passes run_id=job_id: the server dispatches
    with run_id == job_id, so the matching is exact even with 4 jobs in flight."""
    st, _ = _stats()
    st.on_job_started("jA", run_id="jA")
    st.on_job_started("jB", run_id="jB")
    st.on_event({"run_id": "jB", "node": "n1", "status": "started",
                 "extra": {"node_name": "buffer"}})

    by_task_id = {j.job_id: j for j in _snap(st).running}
    assert by_task_id["jB"].node == "buffer"
    assert by_task_id["jA"].node is None


def test_flow_metrics_feed_the_peaks():
    st, _ = _stats()
    st.on_job_started("j")
    st.on_job_finished("j", "ok", 1.0, metrics={"run": {
        "nodes_executed": 9, "nodes_failed": 2,
        "cpu_peak_pct": 91.0, "mem_peak_mb": 1420.0,
    }})

    s = _snap(st)
    assert (s.nodes_executed_total, s.nodes_failed_total) == (9, 2)
    assert (s.wf_cpu_peak_pct, s.wf_mem_peak_mb) == (91.0, 1420.0)


def test_malformed_metrics_breaks_nothing():
    """Broken telemetry must not prevent the job from being counted."""
    st, _ = _stats()
    st.on_job_started("j")
    st.on_job_finished("j", "ok", 1.0, metrics={"run": {"nodes_executed": "muitos"}})
    assert _snap(st).total_ok == 1


# ── GeoSync ──────────────────────────────────────────────────────────────────

def _sync(evento, dataset, ts, **kw):
    return {"type": "sync_event", "event": evento, "dataset": dataset,
            "timestamp": ts, **kw}


def test_geosync_sums_upload_and_download_separately():
    st, _ = _stats()
    st.on_event(_sync("file_uploaded", "a", 1.0, total_bytes=1000, file_count=3))
    st.on_event(_sync("file_downloaded", "b", 2.0, total_bytes=500))

    s = _snap(st)
    assert (s.sync_files_up, s.sync_bytes_up) == (3, 1000)
    assert (s.sync_files_down, s.sync_bytes_down) == (1, 500)


def test_geosync_ignores_resend_of_the_same_event():
    """connection._requeue_event re-enqueues the event when the send fails;
    without dedupe, the same upload would count on every attempt."""
    st, _ = _stats()
    ev = _sync("file_uploaded", "a", 1.0, total_bytes=1000)
    st.on_event(ev)
    st.on_event(dict(ev))   # mesmo (evento, dataset, timestamp)

    s = _snap(st)
    assert s.sync_files_up == 1
    assert s.sync_bytes_up == 1000


def test_geosync_without_total_bytes_still_counts_the_file():
    """Tolerance for a manager that does not pass total_bytes yet: better to count
    the file with 0 bytes than to lose the whole event."""
    st, _ = _stats()
    st.on_event(_sync("file_uploaded", "a", 1.0))
    s = _snap(st)
    assert (s.sync_files_up, s.sync_bytes_up) == (1, 0)


def test_geosync_shows_ongoing_transfer_and_clears_when_done():
    st, _ = _stats()
    st.on_event(_sync("file_uploading", "municipios.shp", 1.0))
    assert "municipios.shp" in _snap(st).sync_current

    st.on_event(_sync("file_uploaded", "municipios.shp", 2.0, total_bytes=10))
    assert _snap(st).sync_current is None


def test_geosync_counts_errors_and_conflicts():
    st, _ = _stats()
    st.on_event(_sync("sync_error", "a", 1.0))
    st.on_event(_sync("conflict_detected", "b", 2.0))
    s = _snap(st)
    assert (s.sync_errors, s.sync_conflicts) == (1, 1)


# ── Conexao ──────────────────────────────────────────────────────────────────

def test_first_connection_does_not_count_as_reconnection():
    st, _ = _stats()
    st.on_connecting()
    st.on_connected()
    s = _snap(st)
    assert s.conn_state == "connected"
    assert s.reconnects == 0


def test_reconnection_is_counted_and_the_retry_shows():
    st, rel = _stats()
    st.on_connected()
    st.on_disconnected(next_retry_s=2.5)

    s = _snap(st)
    assert s.conn_state == "reconnecting"
    assert s.next_retry_in_s == 2.5

    st.on_connected()
    assert _snap(st).reconnects == 1


def test_heartbeat_age_is_reset_on_disconnect():
    """An old heartbeat from a dead session must not show up as 'ha 4s' (4s ago)
    in the next one — it would be saying all is well while the WS is down."""
    st, rel = _stats()
    st.on_connected()
    st.on_heartbeat()
    rel.advance(12)
    assert _snap(st).heartbeat_age_s == 12

    st.on_disconnected(next_retry_s=1.0)
    assert _snap(st).heartbeat_age_s is None


def test_terminal_deny_marks_its_own_state():
    st, _ = _stats()
    st.on_connected()
    st.on_disconnected(terminal=True)
    s = _snap(st)
    assert s.conn_state == "terminal"
    assert s.next_retry_in_s is None


# ── Log ──────────────────────────────────────────────────────────────────────

def test_footer_keeps_the_last_lines_and_counts_per_level():
    st, _ = _stats(tail=3)
    for i in range(5):
        rec = logging.LogRecord("executor.sync", logging.WARNING, "", 0,
                                "aviso %d", (i,), None)
        st.on_log_record(rec, "SYNC  ", "WARN ")
    rec = logging.LogRecord("executor.connection", logging.ERROR, "", 0,
                            "caiu", (), None)
    st.on_log_record(rec, "CONN  ", "ERROR")

    s = _snap(st)
    assert len(s.log_tail) == 3                 # ring buffer respeitado
    assert s.log_tail[-1].msg == "caiu"
    assert s.log_tail[-1].level == "ERROR"
    assert (s.log_warn_count, s.log_error_count) == (5, 1)


# ── NullStats ────────────────────────────────────────────────────────────────

def test_null_stats_covers_the_whole_collector_surface():
    """connection.py and main.py call the hooks without any `if`. A new method in
    ExecutorStats without the matching no-op would become an AttributeError in
    production, on the hot path — and only with the panel turned off."""
    metodos = {n for n in dir(ExecutorStats)
               if n.startswith("on_") or n == "snapshot"}
    faltando = metodos - set(dir(NullStats))
    assert not faltando, f"NullStats nao implementa: {sorted(faltando)}"


# ── Reset (tecla 'z') ────────────────────────────────────────────────────────

def test_reset_zeroes_counts_and_preserves_what_is_alive():
    st, rel = _stats()
    st.on_job_started("terminado", run_id="rt")
    st.on_job_finished("terminado", "ok", 10.0)
    st.on_event(_sync("file_uploaded", "a", 1.0, total_bytes=1000))
    st.on_log_record(logging.LogRecord("executor", logging.WARNING, "", 0, "x", (), None),
                     "AGENT ", "WARN ")
    st.on_connected()
    st.on_job_started("rodando", run_id="rr")   # this one must NOT vanish
    rel.advance(30)

    st.reset()
    s = _snap(st)

    assert (s.total_ok, s.total_error, s.total_cancelled) == (0, 0, 0)
    assert s.sync_files_up == 0 and s.sync_bytes_up == 0
    assert s.slowest is None and s.last_finished is None
    assert s.log_tail == ()
    # What is actually still happening remains.
    assert [j.job_id for j in s.running] == ["rodando"]
    assert s.conn_state == "connected"


def test_reset_does_not_zero_the_process_uptime():
    """Uptime is system information — how long the executor has been up.
    Resetting it would make it look like the process restarted."""
    st, rel = _stats()
    rel.advance(600)
    st.reset()
    rel.advance(60)

    s = _snap(st)
    assert s.uptime_s == 660
    assert s.contando_ha_s == 60


def test_throughput_uses_the_counters_mark_not_the_uptime():
    """Without the separate marker, dividing the new runs by hours of uptime
    would give ~0 wf/min forever after a reset."""
    st, rel = _stats()
    rel.advance(7200)          # executor up for 2h
    st.reset()
    rel.advance(60)            # 1 min medindo
    for i in range(10):
        st.on_job_started(f"j{i}")
        st.on_job_finished(f"j{i}", "ok", 1.0)

    assert _snap(st).throughput_per_min == 10.0


def test_reset_preserves_the_deduplication_memory():
    """`_finished` and `_sync_seen` are dedupe memories, not counters.
    Clearing them would make an event resent right after the reset count again."""
    st, _ = _stats()
    st.on_event(_sync("file_uploaded", "a", 1.0, total_bytes=500))
    st.reset()
    st.on_event(_sync("file_uploaded", "a", 1.0, total_bytes=500))  # mesmo evento

    assert _snap(st).sync_files_up == 0


# ── Concorrencia ─────────────────────────────────────────────────────────────

def test_write_from_another_thread_does_not_break_the_snapshot():
    """`on_log_record` arrives on the thread that emitted the record — the flow
    engine logs from inside `asyncio.to_thread`. Without a lock, the `append`
    during `snapshot()` raised 'deque mutated during iteration', and since the
    runtime turns off the panel after 3 render failures, the executor lost the panel."""
    import threading

    st = ExecutorStats(max_samples=200, tail=200)
    parar = threading.Event()
    erros: list[str] = []

    def escrevendo():
        rec = logging.LogRecord("executor.sync", logging.WARNING, "", 0, "x", (), None)
        i = 0
        while not parar.is_set():
            i += 1
            st.on_log_record(rec, "SYNC  ", "WARN ")
            st.on_event({"type": "sync_event", "event": "file_uploaded",
                         "dataset": f"d{i}", "timestamp": float(i), "total_bytes": 1})

    def lendo():
        while not parar.is_set():
            try:
                st.snapshot(capacity={}, recursos={}, processo={})
            except Exception as exc:
                erros.append(repr(exc))
                return

    threads = [threading.Thread(target=escrevendo) for _ in range(3)] + \
              [threading.Thread(target=lendo) for _ in range(2)]
    for t in threads:
        t.start()
    parar.wait(1.5)
    parar.set()
    for t in threads:
        t.join(timeout=5)

    assert not erros, f"snapshot() quebrou sob concorrencia: {erros[:3]}"


def test_null_stats_accepts_the_real_calls():
    n = NullStats()
    n.on_job_started("j", run_id="r")
    n.on_job_finished("j", "ok", 1.0, run_id="r", metrics={})
    n.on_job_cancelled("j", "motivo")
    n.on_event({"type": "sync_event"})
    n.on_connecting()
    n.on_connected()
    n.on_disconnected(next_retry_s=1.0, terminal=False)
    n.on_heartbeat()
    assert n.snapshot() is None
