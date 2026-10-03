# executor/stats.py
"""
Executor statistics collector.

Aggregates in memory everything the dashboard shows. Pure stdlib, no psutil
and no rich: `connection.py` and `main.py` import this module, and cannot
depend on anything that suggests a graphical interface.

Two halves:

  WRITE    — `on_*` methods, called from the hooks. All O(1), all
             best-effort (they never raise: broken telemetry must not
             bring down a workflow execution).

  READ     — `snapshot()`, called once per dashboard tick. Receives as
             parameters the values that are read "on the spot" (queue
             capacity, system resources), so as not to hold references to
             live executor objects.

Nothing here parses log messages. The durations, states and counters come
from the structured data that already flows through the executor — a log
message is Portuguese text that changes without notice, and a metric that
depends on it breaks silently at the first rewrite.
"""
from __future__ import annotations

import dataclasses
import functools
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

logger = logging.getLogger("executor.stats")

_DEFAULT_WINDOW_S = 3600.0     # "ultima hora"
_MAX_SAMPLES = 5000          # memory ceiling on a high-throughput executor
_DEFAULT_TAIL = 200            # log lines kept for the footer
_DEDUPE_SYNC = 256            # recent sync events, to ignore resends


# ── Output structures ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RunningJob:
    job_id: str
    run_id: str | None
    elapsed_s: float
    node: str | None          # name of the node being executed
    nodes_done: int
    nodes_total: int | None


@dataclass(frozen=True, slots=True)
class LogLine:
    ts: str
    level: str
    alias: str
    msg: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    # identidade
    executor_id: str
    version: str
    server_url: str
    system: Mapping[str, object]
    uptime_s: float
    # How long the counts have been measuring. Same as uptime, except after a
    # reset via the 'z' key — that is what lets the dashboard say "zerado ha 5m"
    # (reset 5m ago) instead of leaving the operator thinking the executor just
    # started.
    contando_ha_s: float

    # workflows
    total_ok: int
    total_error: int
    total_cancelled: int
    success_rate: float
    last_hour_total: int
    last_hour_error: int
    throughput_per_min: float

    # timings (1 h window, except `slowest`, which is since boot)
    avg_duration_s: float | None
    p50_duration_s: float | None
    p95_duration_s: float | None
    slowest: tuple[str, float] | None
    last_finished: tuple[str, str, float] | None
    running: tuple[RunningJob, ...]

    # recursos
    proc_cpu_pct: float | None
    proc_cpu_pct_norm: float | None
    proc_rss_mb: float | None
    proc_threads: int | None
    cpu_cores: float | None
    ram_available_gb: float | None
    ram_total_gb: float | None
    disk_free_gb: float | None
    disk_total_gb: float | None
    # Disk OF THE ARTIFACTS FOLDER — may be a different drive than the system's,
    # and it is the one that decides whether a workflow can write its result.
    # With local locality (LGPD) the artifact has a single copy, and it is on
    # this disk.
    artifacts_disk_free_gb: float | None
    artifacts_disk_total_gb: float | None
    wf_cpu_peak_pct: float | None
    wf_mem_peak_mb: float | None
    nodes_executed_total: int
    nodes_failed_total: int

    # fila e conexao
    queued: int
    running_count: int
    max_concurrent: int
    max_queue: int
    result_queue_size: int
    outbox_pending: int
    conn_state: str
    conn_since_s: float | None
    reconnects: int
    heartbeat_age_s: float | None
    next_retry_in_s: float | None

    # geosync
    sync_dirs: tuple[str, ...]
    sync_files_up: int
    sync_bytes_up: int
    sync_files_down: int
    sync_bytes_down: int
    sync_errors: int
    sync_conflicts: int
    sync_current: str | None
    # Manifest inventory, published by the manager at the end of each cycle.
    # `total` is what the executor KNOWS — not what exists in Drive, which
    # would require a network call on every tick.
    sync_total: int
    sync_synced: int
    sync_pending: int

    # rodape
    log_tail: tuple[LogLine, ...]
    log_warn_count: int
    log_error_count: int


# ── Serialization ────────────────────────────────────────────────────────────
# This is the same READ half described at the top of the module, only for a
# consumer that is not the terminal. It lives here, and not in the dashboard/
# package, so that the data's source and the data's format cannot diverge:
# whoever adds a field to Snapshot gets the field in the JSON without doing
# anything, and there is a test that fails if a field is left out.
#
# `json` doesn't violate the header's "nothing that suggests a graphical
# interface" rule: it is a serialization stdlib module, not a presentation one.

def _json_safe(valor, casas: int):
    """Recursively converts to types that `json` accepts.

    Rounding cuts noise: `uptime_s` with 12 decimal places changes every tick
    and says nothing. The fallback to `str` is deliberate — an exotic value
    coming from `system` (which is built by sysinfo and may change) degrades to
    text instead of breaking the whole serialization and, with it, the channel
    to the app.
    """
    if valor is None or isinstance(valor, (bool, int, str)):
        return valor
    if isinstance(valor, float):
        # inf/nan are not valid JSON; they become null instead of breaking the parser.
        return round(valor, casas) if valor == valor and abs(valor) != float("inf") else None
    if isinstance(valor, dict):
        return {str(k): _json_safe(v, casas) for k, v in valor.items()}
    if isinstance(valor, (list, tuple, set, frozenset)):
        return [_json_safe(v, casas) for v in valor]
    return str(valor)


def snapshot_to_dict(s: Snapshot, *, casas: int = 3) -> dict:
    """Serializes a `Snapshot` into a dict ready for `json.dumps`.

    The only fields that don't come straight out of `asdict` are `slowest` and
    `last_finished`: in the dataclass they are heterogeneous tuples, which in
    JSON would become positional arrays like `["run-7","error",12.4]`. On the
    other side of the bridge that becomes `snap.slowest[1]` — an unnamed index
    nobody can read and that breaks silently if the order changes. They become
    named objects.
    """
    d = dataclasses.asdict(s)

    d["slowest"] = (
        {"run_id": s.slowest[0], "duration_s": s.slowest[1]} if s.slowest else None
    )
    d["last_finished"] = (
        {"run_id": s.last_finished[0], "status": s.last_finished[1],
         "duration_s": s.last_finished[2]}
        if s.last_finished else None
    )
    return _json_safe(d, casas)


# ── Percentil ────────────────────────────────────────────────────────────────

def percentile(ordenados: Sequence[float], q: float) -> float | None:
    """Percentile by linear interpolation (same convention as numpy).

    `statistics.quantiles` doesn't work here: it requires n >= 2 and returns
    the cut points of a distribution, not the value at q. With few samples —
    the common case on an executor that just started — we need something that
    works with n=1.
    """
    n = len(ordenados)
    if n == 0:
        return None
    if n == 1:
        return float(ordenados[0])
    pos = (n - 1) * q
    baixo = int(pos)
    alto = min(baixo + 1, n - 1)
    frac = pos - baixo
    return float(ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * frac)


def _fmt_ts(epoch: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(epoch))


def _locked(metodo):
    """Serializes access to the collector's state — see the note on `_lock`."""
    @functools.wraps(metodo)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return metodo(self, *args, **kwargs)
    return wrapper


# ── Coletor ──────────────────────────────────────────────────────────────────

@dataclass
class _RunState:
    """Live state of a running job, built from the node events."""
    job_id: str
    run_id: str | None = None
    started_at: float = 0.0
    node: str | None = None
    nodes_done: int = 0
    nodes_total: int | None = None


class ExecutorStats:
    """Aggregator. One instance per process, created in main() when the dashboard is on."""

    def __init__(
        self,
        *,
        executor_id: str = "",
        version: str = "",
        server_url: str = "",
        clock: Callable[[], float] = time.monotonic,
        window_s: float = _DEFAULT_WINDOW_S,
        max_samples: int = _MAX_SAMPLES,
        tail: int = _DEFAULT_TAIL,
        observer: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.executor_id = executor_id
        self.version = version
        self.server_url = server_url
        # Receives (type, data) on every relevant state change, for whoever
        # needs the event right away instead of waiting for the next tick — the
        # rich dashboard doesn't (it repaints the whole snapshot), but the
        # desktop app does: `last_finished` holds ONE job, so two finishing
        # within the same second would make the first vanish from the history.
        #
        # CONTRACT: the observer runs with `_lock` held and is called from any
        # thread. It MUST be O(1) and non-blocking — typically an append to a
        # bounded buffer. An observer that does I/O here blocks
        # `on_log_record`, which is called from the flow engine's threads, and
        # the whole executor stalls.
        self._observer = observer
        self._clock = clock
        self._window = window_s
        self._t0 = clock()

        # Most hooks run on the event loop, but `on_log_record` doesn't: the
        # flow engine logs from inside `asyncio.to_thread`, so it arrives on
        # the thread that emitted the record. Without the lock, an `append`
        # during `snapshot()` raises "deque mutated during iteration" — and
        # since the runtime turns the dashboard off after 3 consecutive render
        # failures, an executor with active enough logging lost the dashboard
        # on its own.
        # Reentrant because `on_job_cancelled` delegates to `on_job_finished`.
        self._lock = threading.RLock()

        self.system: dict = {}
        self.sync_dirs: tuple[str, ...] = ()

        # Baseline of the COUNTERS, separate from the process's `_t0`. The 'z' key
        # moves only this one: uptime remains how long the executor has been up
        # (system information), while the counts restart from zero. Without
        # the separation, throughput right after a reset would divide 0 runs by
        # hours of uptime and show ~0 wf/min forever.
        self._counters_since = self._t0

        # workflows — cumulative counters live OUTSIDE the sliding window,
        # otherwise "total since boot" would become "total in the last hour".
        self._ok = 0
        self._error = 0
        self._cancelado = 0
        self._durations_sum = 0.0
        self._n_durations = 0
        self._slowest: tuple[str, float] | None = None
        self._last_finished: tuple[str, str, float] | None = None
        self._nodes_executed = 0
        self._nodes_failed = 0
        self._wf_cpu_peak: float | None = None
        self._wf_mem_peak: float | None = None

        # janela sliding: (ts, duration_s, status)
        self._jobs_window: deque[tuple[float, float, str]] = deque(maxlen=max_samples)

        # jobs em execucao
        self._running: dict[str, _RunState] = {}
        self._run_para_job: dict[str, str] = {}
        # Ids already counted. A job cancelled while running arrives TWICE:
        # through on_execute's `finally` and through the queue's on_cancelled.
        # Without this short memory it would appear twice in the total.
        self._finished: deque[str] = deque(maxlen=256)
        self._finished_set: set[str] = set()

        # conexao
        self._conn_state = "offline"
        self._conn_since: float | None = None
        self._reconnects = 0
        self._last_heartbeat: float | None = None
        self._next_retry: float | None = None

        # geosync
        self._sync_up_arq = 0
        self._sync_up_bytes = 0
        self._sync_down_arq = 0
        self._sync_down_bytes = 0
        self._sync_errors = 0
        self._sync_conflicts = 0
        self._sync_current: str | None = None
        self._sync_total = 0
        self._sync_synced = 0
        self._sync_pending = 0
        # Resending an event via the connection's _requeue_event would make the SAME
        # upload count twice. The timestamp is fixed at emit and survives the
        # requeue, so it serves as an identity key.
        self._sync_seen: deque[tuple] = deque(maxlen=_DEDUPE_SYNC)
        self._sync_seen_set: set[tuple] = set()

        # log
        self._tail: deque[LogLine] = deque(maxlen=tail)
        self._logs_window: deque[tuple[float, int]] = deque(maxlen=max_samples)

    @_locked
    def reset(self) -> None:
        """Resets the session counts without touching the live state.

        What is RESET: workflows, timings, node metrics, GeoSync, reconnections
        and the alert buffer. What REMAINS: the running jobs (they really are
        running), the connection state and the process uptime.
        """
        agora = self._clock()
        self._counters_since = agora

        self._ok = self._error = self._cancelado = 0
        self._durations_sum = 0.0
        self._n_durations = 0
        self._slowest = None
        self._last_finished = None
        self._nodes_executed = self._nodes_failed = 0
        self._wf_cpu_peak = self._wf_mem_peak = None
        self._jobs_window.clear()

        self._sync_up_arq = self._sync_up_bytes = 0
        self._sync_down_arq = self._sync_down_bytes = 0
        self._sync_errors = self._sync_conflicts = 0

        self._reconnects = 0
        self._tail.clear()
        self._logs_window.clear()

        # `_finished` and `_sync_seen` are NOT reset: they are deduplication
        # memories, not counters. Clearing them would make an event resent
        # right after the reset count again.

    def set_observer(self, observer: Callable[[str, dict], None] | None) -> None:
        """Attaches (or detaches) the observer after construction.

        Exists because of a circular dependency at boot: the collector is
        created in `main()` so that the queues and the connection are born with
        it, but whoever consumes the events — the NDJSON channel runtime — only
        exists later, and needs the collector itself as an argument. One of the
        two has to be wired in two steps.

        The same CONTRACT as the constructor parameter applies: O(1) and
        non-blocking.
        """
        self._observer = observer

    def _emit(self, tipo: str, dados: dict) -> None:
        """Delivers to the observer, best-effort. Same rule as the `on_*` hooks:
        broken telemetry never brings down a workflow execution."""
        obs = self._observer
        if obs is None:
            return
        try:
            obs(tipo, dados)
        except Exception:
            pass

    # ── Escrita: jobs ────────────────────────────────────────────────────────

    @_locked
    def on_job_started(self, job_id: str, run_id: str | None = None) -> None:
        st = _RunState(job_id=job_id, run_id=run_id, started_at=self._clock())
        self._running[job_id] = st
        if run_id:
            self._run_para_job[run_id] = job_id
        self._emit("job", {"event": "started", "job_id": job_id, "run_id": run_id})

    @_locked
    def on_job_finished(
        self,
        job_id: str,
        status: str,
        duration_s: float,
        *,
        run_id: str | None = None,
        metrics: Mapping | None = None,
    ) -> None:
        st = self._running.pop(job_id, None)
        rid = run_id or (st.run_id if st else None) or job_id
        if st and st.run_id:
            self._run_para_job.pop(st.run_id, None)

        self._mark_finished(job_id)
        agora = self._clock()
        if status == "ok":
            self._ok += 1
        elif status == "cancelled":
            self._cancelado += 1
        else:
            status = "error"
            self._error += 1

        self._jobs_window.append((agora, duration_s, status))
        self._last_finished = (rid, status, duration_s)

        # Cancelled doesn't count toward the average: a job killed at 2s says
        # nothing about how long a workflow takes, and would drag the average down.
        if status != "cancelled":
            self._durations_sum += duration_s
            self._n_durations += 1
            if self._slowest is None or duration_s > self._slowest[1]:
                self._slowest = (rid, duration_s)

        self._absorb_metrics(metrics)
        run = (metrics or {}).get("run") or {}
        self._emit("job", {
            "event": "cancelled" if status == "cancelled" else "finished",
            "job_id": job_id, "run_id": rid, "status": status,
            "duration_s": duration_s,
            "nodes_executed": run.get("nodes_executed"),
            "nodes_failed": run.get("nodes_failed"),
        })

    @_locked
    def on_job_cancelled(self, job_id: str, motivo: str | None = None) -> None:
        """Cancellation reported by the queue.

        Arrives for the job that was interrupted while running (already counted
        by on_execute's `finally`) and for the one discarded without ever
        running (not counted anywhere). We tell them apart by the memory of
        finished ids: without it, the first case would be added twice.
        """
        if job_id in self._finished_set:
            return
        if job_id in self._running:
            # Delegates — on_job_finished is the one that emits, otherwise the event
            # would go out twice for the same cancellation.
            self.on_job_finished(job_id, "cancelled", 0.0)
            return
        self._mark_finished(job_id)
        self._cancelado += 1
        self._jobs_window.append((self._clock(), 0.0, "cancelled"))
        self._emit("job", {
            "event": "cancelled", "job_id": job_id, "run_id": None,
            "status": "cancelled", "duration_s": 0.0, "motivo": motivo,
        })

    def _mark_finished(self, job_id: str) -> None:
        if job_id in self._finished_set:
            return
        if len(self._finished) == self._finished.maxlen:
            self._finished_set.discard(self._finished[0])
        self._finished.append(job_id)
        self._finished_set.add(job_id)

    def _absorb_metrics(self, metrics: Mapping | None) -> None:
        """Extrai o bloco `run` de stats['__metrics__'] (flow/metrics/collector)."""
        if not metrics:
            return
        try:
            run = metrics.get("run") or {}
            self._nodes_executed += int(run.get("nodes_executed") or 0)
            self._nodes_failed += int(run.get("nodes_failed") or 0)
            cpu = run.get("cpu_peak_pct")
            if cpu is not None:
                self._wf_cpu_peak = max(self._wf_cpu_peak or 0.0, float(cpu))
            mem = run.get("mem_peak_mb")
            if mem is not None:
                self._wf_mem_peak = max(self._wf_mem_peak or 0.0, float(mem))
        except Exception:
            pass  # malformed telemetry is no reason for anything to break

    # ── Escrita: eventos da fila (node events + sync events) ─────────────────

    @_locked
    def on_event(self, event: Mapping) -> None:
        try:
            if event.get("type") == "sync_event":
                self._on_sync_event(event)
            else:
                self._on_node_event(event)
        except Exception:
            pass

    def _on_node_event(self, event: Mapping) -> None:
        run_id = event.get("run_id")
        if not run_id:
            return
        job_id = self._run_para_job.get(run_id)
        st = self._running.get(job_id) if job_id else None
        if st is None:
            # The payload brought a run_id different from the job_id. Match by
            # elimination — but ONLY if there is exactly one candidate: with
            # several concurrent jobs without run_id, picking "the first" would
            # attribute one job's node to another, and a dashboard that lies is
            # worse than an incomplete one.
            candidatos = [c for c in self._running.values() if c.run_id is None]
            if len(candidatos) != 1:
                return
            st = candidatos[0]
            st.run_id = run_id
            self._run_para_job[run_id] = st.job_id

        status = (event.get("status") or "").lower()
        extra = event.get("extra") or {}
        nome = extra.get("node_name") or event.get("node")

        if status in ("started", "running"):
            st.node = nome
        elif status in ("completed", "failed", "skipped", "pinned", "cached"):
            st.nodes_done += 1
            st.node = None

        total = extra.get("nodes_total")
        if total:
            try:
                st.nodes_total = int(total)
            except (TypeError, ValueError):
                pass

    def _on_sync_event(self, event: Mapping) -> None:
        chave = (event.get("event"), event.get("dataset"), event.get("timestamp"))
        if chave in self._sync_seen_set:
            return  # resend via _requeue_event — already counted
        if len(self._sync_seen) == self._sync_seen.maxlen:
            self._sync_seen_set.discard(self._sync_seen[0])
        self._sync_seen.append(chave)
        self._sync_seen_set.add(chave)

        nome = event.get("event")
        dataset = event.get("dataset") or ""
        try:
            total_bytes = int(event.get("total_bytes") or 0)
        except (TypeError, ValueError):
            total_bytes = 0

        if nome == "file_uploaded":
            self._sync_up_arq += max(int(event.get("file_count") or 1), 1)
            self._sync_up_bytes += total_bytes
            self._sync_current = None
        elif nome == "file_downloaded":
            self._sync_down_arq += 1
            self._sync_down_bytes += total_bytes
            self._sync_current = None
        elif nome == "file_uploading":
            self._sync_current = f"↑ {dataset}"
        elif nome == "file_downloading":
            self._sync_current = f"↓ {dataset}"
        elif nome == "sync_error":
            self._sync_errors += 1
            self._sync_current = None
        elif nome == "conflict_detected":
            self._sync_conflicts += 1
        elif nome in ("sync_complete", "sync_started"):
            self._sync_current = None
        elif nome == "sync_inventory":
            # Replaces, doesn't accumulate: it is a snapshot of the manifest, not an
            # event counter.
            try:
                self._sync_total = int(event.get("total") or 0)
                self._sync_synced = int(event.get("synced") or 0)
                self._sync_pending = int(event.get("pending") or 0)
            except (TypeError, ValueError):
                pass

        self._emit("sync", {
            "event": nome, "dataset": dataset, "total_bytes": total_bytes,
        })

    # ── Escrita: conexao ─────────────────────────────────────────────────────

    @_locked
    def on_connecting(self) -> None:
        self._conn_state = "reconnecting" if self._reconnects or self._conn_since else "connecting"
        self._emit("conn", {"state": self._conn_state, "reconnects": self._reconnects})

    @_locked
    def on_connected(self) -> None:
        if self._conn_since is not None:
            self._reconnects += 1
        self._conn_state = "connected"
        self._conn_since = self._clock()
        self._next_retry = None
        self._emit("conn", {"state": "connected", "reconnects": self._reconnects})

    @_locked
    def on_disconnected(self, *, next_retry_s: float | None = None, terminal: bool = False) -> None:
        self._conn_state = "terminal" if terminal else "reconnecting"
        self._next_retry = None if terminal else next_retry_s
        self._last_heartbeat = None
        self._emit("conn", {
            "state": self._conn_state, "reconnects": self._reconnects,
            "next_retry_in_s": self._next_retry,
        })

    @_locked
    def on_heartbeat(self) -> None:
        self._last_heartbeat = self._clock()

    # ── Escrita: log ─────────────────────────────────────────────────────────

    @_locked
    def on_log_record(self, record: logging.LogRecord, alias: str, level: str) -> None:
        try:
            self._tail.append(LogLine(
                ts=_fmt_ts(record.created),
                level=level.strip(),
                alias=alias.strip(),
                msg=record.getMessage(),
            ))
            self._logs_window.append((self._clock(), record.levelno))
        except Exception:
            pass

    # ── Leitura ──────────────────────────────────────────────────────────────

    def _prune(self) -> None:
        limite = self._clock() - self._window
        while self._jobs_window and self._jobs_window[0][0] < limite:
            self._jobs_window.popleft()
        while self._logs_window and self._logs_window[0][0] < limite:
            self._logs_window.popleft()

    @_locked
    def snapshot(
        self,
        *,
        capacity: Mapping | None = None,
        recursos: Mapping | None = None,
        processo: Mapping | None = None,
        outbox_pending: int = 0,
        result_queue_size: int = 0,
    ) -> Snapshot:
        self._prune()
        agora = self._clock()
        cap = capacity or {}
        rec = recursos or {}
        proc = processo or {}

        duracoes = sorted(d for _, d, s in self._jobs_window if s != "cancelled")
        hour_total = len(self._jobs_window)
        hour_errors = sum(1 for _, _, s in self._jobs_window if s == "error")

        finished = self._ok + self._error + self._cancelado
        # 1.0 on a freshly started executor: showing "0% de sucesso" (0% success)
        # before the first run would be a false alarm.
        taxa = (self._ok / finished) if finished else 1.0

        uptime = agora - self._t0
        # Throughput measures from the COUNTERS baseline, not the process's: after
        # a reset, dividing the new runs by hours of uptime would give ~0.
        measuring_for = agora - self._counters_since
        throughput = (hour_total / (min(measuring_for, self._window) / 60.0)) if measuring_for > 1 else 0.0

        running = tuple(
            RunningJob(
                job_id=st.job_id,
                run_id=st.run_id,
                elapsed_s=agora - st.started_at,
                node=st.node,
                nodes_done=st.nodes_done,
                nodes_total=st.nodes_total,
            )
            for st in sorted(self._running.values(), key=lambda s: s.started_at)
        )

        return Snapshot(
            executor_id=self.executor_id,
            version=self.version,
            server_url=self.server_url,
            system=dict(self.system),
            uptime_s=uptime,
            contando_ha_s=measuring_for,
            total_ok=self._ok,
            total_error=self._error,
            total_cancelled=self._cancelado,
            success_rate=taxa,
            last_hour_total=hour_total,
            last_hour_error=hour_errors,
            throughput_per_min=round(throughput, 2),
            avg_duration_s=(self._durations_sum / self._n_durations) if self._n_durations else None,
            p50_duration_s=percentile(duracoes, 0.50),
            p95_duration_s=percentile(duracoes, 0.95),
            slowest=self._slowest,
            last_finished=self._last_finished,
            running=running,
            proc_cpu_pct=proc.get("cpu_pct"),
            proc_cpu_pct_norm=proc.get("cpu_pct_norm"),
            proc_rss_mb=proc.get("rss_mb"),
            proc_threads=proc.get("threads"),
            cpu_cores=proc.get("cpu_cores") or self.system.get("cpu_cores"),
            ram_available_gb=rec.get("ram_available_gb"),
            ram_total_gb=self.system.get("ram_total_gb"),
            disk_free_gb=rec.get("disk_free_gb"),
            disk_total_gb=self.system.get("disk_total_gb"),
            artifacts_disk_free_gb=rec.get("artifacts_disk_free_gb"),
            artifacts_disk_total_gb=rec.get("artifacts_disk_total_gb"),
            wf_cpu_peak_pct=self._wf_cpu_peak,
            wf_mem_peak_mb=self._wf_mem_peak,
            nodes_executed_total=self._nodes_executed,
            nodes_failed_total=self._nodes_failed,
            queued=int(cap.get("queued") or 0),
            running_count=int(cap.get("running") or 0),
            max_concurrent=int(cap.get("max_concurrent") or 0),
            max_queue=int(cap.get("max_queue") or 0),
            result_queue_size=result_queue_size,
            outbox_pending=outbox_pending,
            conn_state=self._conn_state,
            conn_since_s=(agora - self._conn_since) if self._conn_since is not None else None,
            reconnects=self._reconnects,
            heartbeat_age_s=(agora - self._last_heartbeat) if self._last_heartbeat else None,
            next_retry_in_s=self._next_retry,
            sync_dirs=self.sync_dirs,
            sync_total=self._sync_total,
            sync_synced=self._sync_synced,
            sync_pending=self._sync_pending,
            sync_files_up=self._sync_up_arq,
            sync_bytes_up=self._sync_up_bytes,
            sync_files_down=self._sync_down_arq,
            sync_bytes_down=self._sync_down_bytes,
            sync_errors=self._sync_errors,
            sync_conflicts=self._sync_conflicts,
            sync_current=self._sync_current,
            log_tail=tuple(self._tail),
            log_warn_count=sum(1 for _, lv in self._logs_window if lv == logging.WARNING),
            log_error_count=sum(1 for _, lv in self._logs_window if lv >= logging.ERROR),
        )


class NullStats:
    """Same surface, everything a no-op.

    Exists so that `connection.py` and `main.py` call `self._stats.on_X()`
    without any `if stats is not None` scattered around — with the dashboard
    off, the cost is one empty function call per event.
    """
    executor_id = ""
    version = ""
    server_url = ""
    system: dict = {}
    sync_dirs: tuple = ()

    # Accepts the same kwargs as ExecutorStats (including `observer`) so that
    # switching between the two is an `if` in the constructor, and nothing more.
    def __init__(self, *a, **k) -> None: ...

    # `reset` was missing: the dashboard calls `stats.reset()` on the 'z' key and
    # the IPC `reset_stats` command does the same. With the collector off this
    # raised AttributeError instead of doing nothing.
    def reset(self, *a, **k) -> None: ...
    def set_observer(self, *a, **k) -> None: ...
    def on_job_started(self, *a, **k) -> None: ...
    def on_job_finished(self, *a, **k) -> None: ...
    def on_job_cancelled(self, *a, **k) -> None: ...
    def on_event(self, *a, **k) -> None: ...
    def on_connecting(self, *a, **k) -> None: ...
    def on_connected(self, *a, **k) -> None: ...
    def on_disconnected(self, *a, **k) -> None: ...
    def on_heartbeat(self, *a, **k) -> None: ...
    def on_log_record(self, *a, **k) -> None: ...
    def snapshot(self, *a, **k) -> None: return None
