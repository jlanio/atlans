# executor/result_store.py
"""
Persistent store for job results pending delivery to the server.

Motivation: the executor's `_result_queue` is in-memory. If the WebSocket
connection drops and the executor process restarts (e.g. docker restart, kernel
OOM) before `_result_sender_loop` manages to send, the result is lost — the
workflow stays in the "running" state indefinitely on the server.

This module provides a lightweight SQLite "outbox" layer:
  - `put(result)`    — persists the result when it is produced
  - `mark_sent(id)`  — removes it after the server confirms receipt
  - `load_pending()` — at executor startup, returns what was never sent

No additional dependencies: uses the stdlib sqlite3 in WAL mode to
support concurrent writes between the executor and the sender_loop.

ROBUSTNESS: any failure (permissions, full disk, corrupted SQLite)
silently disables the store — it never brings the executor down. All
operations become no-ops and the behavior reverts to the pre-refactor
"in-memory outbox".
"""

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any

from executor import config
from executor.utils import ocultar_no_windows

logger = logging.getLogger(__name__)


# Name of the on-disk outbox. It used to be `.agent_results.sqlite`, from the
# time the component was called "agent"; renamed along with everything else to
# "executor". No migration on purpose: a pending outbox is seconds' worth of
# work, and the next boot recreates the file empty.
_DB_FILENAME = ".executor_results.sqlite"


def _default_db_path() -> str:
    """SQLite path — in ARTIFACTS_DIR so it is colocated with the artifacts."""
    base = config.ARTIFACTS_DIR or os.getcwd()
    return os.path.join(base, _DB_FILENAME)


_DB_PATH = _default_db_path()

# Suffixes of the files SQLite keeps next to the main database. -wal/-shm
# exist in WAL mode; -journal shows up when WAL does NOT engage — e.g. the
# outbox in a network/synced folder without shared memory, where SQLite
# SILENTLY falls back to rollback journal and writes
# .executor_results.sqlite-journal during each transaction. We hide all four
# so none of them shows up in Explorer.
_DB_SUFFIXES = ("", "-wal", "-shm", "-journal")

# Whether we have already reapplied the hide after the first write (see _hide_db_files).
_ocultado_pos_escrita: bool = False


def _hide_db_files() -> None:
    """Applies the hidden attribute (Windows) to the database and its satellite files.

    No-op outside Windows. The -wal/-shm/-journal files are born at different
    moments (WAL open, first write, rollback fallback): hiding one that does
    not exist yet is harmless — GetFileAttributesW fails and the helper gives up.
    """
    for sufixo in _DB_SUFFIXES:
        ocultar_no_windows(_DB_PATH + sufixo)


# SQLite accepts multiple threads with check_same_thread=False. We use an
# RLock (reentrant) to serialize writes — the public functions take the
# lock and call _get_conn(), which also needs to take the lock for the lazy
# init; with a non-reentrant Lock this would deadlock on first use.
_lock = threading.RLock()
_conn: sqlite3.Connection | None = None
# If initialization fails (permissions, full disk, etc.), disable the store
# instead of propagating — the executor keeps working without persistence.
_disabled: bool = False


def _get_conn() -> sqlite3.Connection | None:
    """Returns the singleton connection, or None if the store was disabled.

    The whole init (makedirs + connect + pragma + CREATE) is wrapped in a
    generic try/except: any exception marks the store as disabled instead of
    propagating.

    SEC: the file is created with mode 0600 (only the owner reads/writes).
    Protects persisted payloads from being read by other processes on the host.
    """
    global _conn, _disabled
    if _disabled:
        return None
    if _conn is not None:
        return _conn
    with _lock:
        if _disabled:
            return None
        if _conn is None:
            try:
                parent = os.path.dirname(_DB_PATH) or "."
                os.makedirs(parent, exist_ok=True)
                # Creates the file with 0600 before sqlite3 opens it — if it already
                # exists with other permissions, forces chmod to close the vector.
                if not os.path.exists(_DB_PATH):
                    fd = os.open(_DB_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    os.close(fd)
                else:
                    try:
                        os.chmod(_DB_PATH, 0o600)
                    except OSError:
                        pass  # filesystems sem suporte a chmod (Windows, etc.)
                c = sqlite3.connect(_DB_PATH, check_same_thread=False, isolation_level=None)
                # WAL: readers don't block writers; better for the outbox pattern.
                c.execute("PRAGMA journal_mode=WAL")
                c.execute("PRAGMA synchronous=NORMAL")
                c.execute("""
                    CREATE TABLE IF NOT EXISTS pending_results (
                        job_id     TEXT PRIMARY KEY,
                        payload    TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        attempts   INTEGER NOT NULL DEFAULT 0
                    )
                """)
                # Journal of jobs accepted and still WITHOUT a result (see
                # `registrar_em_voo`). Only ids and timestamps: none of the payload.
                c.execute("""
                    CREATE TABLE IF NOT EXISTS jobs_em_voo (
                        job_id TEXT PRIMARY KEY,
                        estado TEXT NOT NULL,
                        desde  REAL NOT NULL
                    )
                """)
                # Hides the outbox on Windows (on Linux/macOS the dot is enough).
                # It lives in ARTIFACTS_DIR (by default ~/AtlansExecutor/artifacts,
                # the executor's own folder; the operator can point it at a data
                # folder the user browses) and deleting it throws away results of
                # jobs not yet confirmed by the server. Hidden AFTER the CREATE
                # TABLE because only then do the WAL-mode -wal/-shm files exist;
                # SQLite reopens hidden files without trouble (winOpen uses
                # OPEN_EXISTING/OPEN_ALWAYS, not CREATE_ALWAYS, so it doesn't run
                # into CreateFile's hidden-file restriction). The first put()
                # reapplies it to catch the -wal/-journal that only appears on the
                # 1st write.
                _hide_db_files()
                _conn = c
            except Exception as exc:
                _disabled = True
                logger.warning(
                    "result_store desabilitado — não foi possível inicializar SQLite em %s: %s. "
                    "Resultados não sobreviverão a crash do executor, mas a execução normal continua.",
                    _DB_PATH, exc,
                )
                return None
    return _conn


# Fields safe to persist in the outbox — OUTPUT and STATS are left out
# because they may contain injected credentials (connectionString, tokens) or
# sensitive outputs (customer GeoJSON, personal data).
# The server only consumes job_id/run_id/status/error to update the WorkflowRun
# (it measures the duration with its own clock) — the other fields are sent
# directly over WS when the connection is alive (they don't go through the outbox).
# `error_category` is included because the replay needs it: without the
# category, the failure resent at boot reached the server as a generic "internal".
_SAFE_RESULT_FIELDS = {"job_id", "run_id", "status", "error", "error_category"}


def _sanitize(result: dict[str, Any]) -> dict[str, Any]:
    """Removes sensitive fields before persisting to disk."""
    out = {k: v for k, v in result.items() if k in _SAFE_RESULT_FIELDS}
    # Truncates error so the file doesn't bloat if it comes with a huge stack trace.
    err = out.get("error")
    if isinstance(err, str) and len(err) > 500:
        out["error"] = err[:500] + "…"
    return out


def put(result: dict[str, Any]) -> None:
    """Persists a result — idempotent per job_id.

    If the same job_id already exists (e.g. retry), the payload is replaced.
    Call BEFORE enqueuing for the sender — guarantees that an executor restart
    does not lose the result. Never raises: failures are only logged.
    """
    global _ocultado_pos_escrita
    job_id = str(result.get("job_id") or "unknown")
    try:
        # Sanitizes before serializing — the outbox NEVER writes output/stats to disk.
        payload = json.dumps(_sanitize(result), default=str)
    except (TypeError, ValueError) as exc:
        logger.warning("result_store.put: payload não-serializável para job '%s': %s", job_id, exc)
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            # In one transaction: the result enters the outbox and the job leaves the
            # journal together. Done separately, a crash between the two would
            # leave at boot an "orphan" that already has a result — and the
            # executor would report as interrupted a job that finished. Explicit
            # BEGIN/COMMIT because the connection is autocommit
            # (`isolation_level=None`): on it `with conn` opens no transaction at all.
            conn.execute("BEGIN")
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO pending_results (job_id, payload, created_at) "
                    "VALUES (?, ?, ?)",
                    (job_id, payload, time.time()),
                )
                conn.execute("DELETE FROM jobs_em_voo WHERE job_id = ?", (job_id,))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            if not _ocultado_pos_escrita:
                # The 1st write materializes the -wal/-shm (and, in the fallback without
                # WAL, the -journal) that the CREATE TABLE — a no-op when the table
                # already exists — may not have created in _get_conn. We reapply
                # ONCE to catch these newborn files; subsequent writes don't pay
                # for the syscall.
                _hide_db_files()
                _ocultado_pos_escrita = True
    except Exception as exc:
        # Non-fatal: the store is a robustness upgrade, not a requirement.
        logger.warning("result_store.put falhou para job '%s': %s", job_id, exc)


def mark_sent(job_id: str) -> None:
    """Removes the result from the store after successful delivery to the server."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "DELETE FROM pending_results WHERE job_id = ?",
                (str(job_id),),
            )
    except Exception as exc:
        logger.warning("result_store.mark_sent falhou para job '%s': %s", job_id, exc)


def increment_attempts(job_id: str) -> None:
    """Increments the attempt counter — useful for logs/telemetry."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "UPDATE pending_results SET attempts = attempts + 1 WHERE job_id = ?",
                (str(job_id),),
            )
    except Exception as exc:
        logger.debug("result_store.increment_attempts: %s", exc)


def load_pending() -> list[dict]:
    """Returns all pending results, oldest first.

    Call at executor startup to drain and re-enqueue what was not sent
    before the previous crash. Never raises: failures return [].
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return []
            rows = conn.execute(
                "SELECT payload FROM pending_results ORDER BY created_at ASC"
            ).fetchall()
    except Exception as exc:
        logger.warning("result_store.load_pending falhou: %s", exc)
        return []

    out: list[dict] = []
    for (payload,) in rows:
        try:
            out.append(json.loads(payload))
        except json.JSONDecodeError as exc:
            logger.warning("result_store: payload corrompido, pulando: %s", exc)
    return out


def count_pending() -> int:
    """How many results are awaiting delivery. Never raises: failures return 0.

    Exists for the dashboard, which needs the number every few seconds and
    cannot use `load_pending()` — that one deserializes every payload, which at
    1 Hz would be pure waste.
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return 0
            row = conn.execute("SELECT COUNT(*) FROM pending_results").fetchone()
            return int(row[0]) if row else 0
    except Exception as exc:
        logger.debug("result_store.count_pending: %s", exc)
        return 0


def job_ids_pendentes() -> list[str] | None:
    """Ids with a result not yet confirmed by the server. Never raises.

    Goes into the inventory the executor sends to the server: a job whose
    result is here has finished, and the server must not close the run as lost
    just because it left the execution queue.

    None when the outbox exists but could not be read (`database is locked`,
    I/O — plausible on desktop, with a synced folder or under antivirus).
    Returning [] in that case would assert "nothing pending" and the server
    would close as lost runs whose result is here. A disabled outbox really is
    []: nothing is persisted, and the in-memory queue is counted by the caller.
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return []
            rows = conn.execute("SELECT job_id FROM pending_results").fetchall()
        return [r[0] for r in rows]
    except Exception as exc:
        logger.warning("Outbox ilegível ao listar os resultados pendentes: %s", exc)
        return None


# ── Journal of in-flight jobs ─────────────────────────────────────────────────
# An accepted job enters here and only leaves when its result enters the outbox
# (`put` deletes the row in the same transaction). Whatever is left at boot
# belongs to a process that died without producing a result — out of memory,
# kill, machine crash — and becomes a failure with the probable cause instead
# of a run stuck in "Em andamento" (in progress) on the server. Real case: an
# executor killed by the cgroup OOM came back 6 s later and nobody closed the
# run it was executing.

STATE_QUEUED = "fila"
STATE_RUNNING = "executando"


def registrar_em_voo(job_id: str) -> None:
    """Records an accepted job in the local queue. Never raises."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "INSERT OR REPLACE INTO jobs_em_voo (job_id, estado, desde) VALUES (?, ?, ?)",
                (str(job_id), STATE_QUEUED, time.time()),
            )
    except Exception as exc:
        logger.debug("result_store.registrar_em_voo: %s", exc)


def marcar_executando(job_id: str) -> None:
    """The job left the queue and started running. Never raises."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "UPDATE jobs_em_voo SET estado = ?, desde = ? WHERE job_id = ?",
                (STATE_RUNNING, time.time(), str(job_id)),
            )
    except Exception as exc:
        logger.debug("result_store.marcar_executando: %s", exc)


def carregar_em_voo() -> list[dict]:
    """Journal jobs that have NO result in the outbox — the orphans of the
    previous process, oldest first. Never raises: failures return [].

    The `NOT IN` is defense in depth: `put` already deletes the row in the same
    transaction, but a database inherited from a version without that
    transaction must not cause a completed job to be reported as interrupted.
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return []
            rows = conn.execute(
                "SELECT job_id, estado, desde FROM jobs_em_voo "
                "WHERE job_id NOT IN (SELECT job_id FROM pending_results) "
                "ORDER BY desde ASC"
            ).fetchall()
            conn.execute(
                "DELETE FROM jobs_em_voo WHERE job_id IN (SELECT job_id FROM pending_results)"
            )
    except Exception as exc:
        logger.warning("result_store.carregar_em_voo falhou: %s", exc)
        return []
    return [{"job_id": r[0], "estado": r[1], "desde": r[2]} for r in rows]


# ── Journal ownership ─────────────────────────────────────────────────────────
# File next to the outbox, locked for the lifetime of the process — see
# `take_journal_ownership`.
_trava_do_diario = None
_esperando_posse = False
_lock_da_posse = threading.Lock()
_INTERVALO_DE_POSSE_S = 5.0


def _try_lock() -> str:
    """'travou' (locked), 'ocupada' (another live process holds it) or 'sem_suporte' (unsupported)."""
    global _trava_do_diario
    with _lock_da_posse:
        if _trava_do_diario is not None:
            return "travou"
        caminho = _DB_PATH + ".dono"
        try:
            os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
            arquivo = open(caminho, "a+b")
        except OSError as exc:
            logger.debug("Trava do diário indisponível (%s): %s", caminho, exc)
            return "sem_suporte"
        try:
            if os.name == "nt":
                import msvcrt
                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError):
            arquivo.close()
            return "ocupada"
        except OSError as exc:
            arquivo.close()
            logger.debug("Trava do diário sem suporte aqui (%s): %s", caminho, exc)
            return "sem_suporte"
        _trava_do_diario = arquivo
    ocultar_no_windows(caminho)
    return "travou"


def _wait_for_ownership() -> None:
    global _esperando_posse
    try:
        while (resultado := _try_lock()) == "ocupada":
            time.sleep(_INTERVALO_DE_POSSE_S)
        if resultado == "travou":
            logger.info("Diário de jobs: posse assumida (o processo anterior saiu).")
    finally:
        _esperando_posse = False


def take_journal_ownership() -> bool:
    """Exclusive lock on the journal for this process. False if ANOTHER live
    process holds it.

    On desktop, a force-killed app leaves the child Python draining (up to
    150 s), and reopening starts a second process with the same outbox: the
    jobs in the journal belong to that process, which is still finishing them —
    converting them into failures would make its real result be rejected. The
    operating system releases the lock when the process dies, however it dies.

    Without the lock right now, this process keeps trying in the background:
    when the other one exits, it becomes the owner — otherwise a THIRD one
    started later would grab the free lock and convert THIS one's live jobs.

    With no way to lock (platform or file system without support) returns True:
    the previous behavior.
    """
    global _esperando_posse
    if _try_lock() != "ocupada":
        return True
    with _lock_da_posse:
        if not _esperando_posse:
            _esperando_posse = True
            threading.Thread(target=_wait_for_ownership, name="posse-do-diario", daemon=True).start()
    return False


def close() -> None:
    """Closes the SQLite connection. Call at executor shutdown."""
    global _conn, _ocultado_pos_escrita
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None
        # Re-arms the post-write re-hiding: a reconnect recreates the WAL files
        # and needs to hide them again on the next write.
        _ocultado_pos_escrita = False
