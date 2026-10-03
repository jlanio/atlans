# executor/logging_setup.py
"""
Executor logging configuration.

Extracted from main.py, which carried 130 lines of logging setup before the
first line of logic. Everything lives here: the console's colored formatter,
the rotating file handlers and the switch to dashboard mode.

Two modes:

  CONSOLE (default) — identical to the historical behavior: an UNFILTERED
                      colored StreamHandler on the root, plus the optional
                      LOG_FILE_AGENT / LOG_FILE_WORKFLOW files (filtered).

  PAINEL            — the console leaves the root and a CATCH-ALL rotating
                      handler takes its place. The terminal is free for the
                      dashboard and nothing is lost: the file becomes the
                      faithful mirror of what used to go to the screen.

The distinction between "filtered" and "catch-all" matters and is not a detail:
the console never had a filter, so it brought `websockets`, `asyncio`, `boto3`
and any third-party library to the terminal. The existing file handlers are
filtered by prefix (`executor`/`httpx` and `flow`/`node`/`app`) and together
do NOT cover those loggers. Swapping the console for them would lose records —
the opposite of the goal, which is to move the step-by-step log to disk, not
erase it.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import pathlib
import sys

_LOG_FORMAT = "%(asctime)s  %(levelname)-5s  %(name)s  %(message)s"  # used in the files

_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5

# The variables are read from the environment, not from `executor.config`, so
# this module has no dependency at all inside the package — but the reading
# happens in `configure_logging()`, NEVER at import. What populates the
# environment with the contents of `.env` is config.py's `load_dotenv()`;
# reading at import would make the result depend on the order in which modules
# are imported, and a `LOG_LEVEL=DEBUG` in .env would be silently ignored.
_log_color = "auto"


def _log_level() -> int:
    return getattr(logging, os.getenv("LOG_LEVEL", "INFO").strip().upper(), logging.INFO)


class LoggingSetupError(RuntimeError):
    """Failure preparing the file log — the dashboard must NOT turn on."""


def _rotating(path: str) -> logging.handlers.RotatingFileHandler:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    return logging.handlers.RotatingFileHandler(
        path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )


class _PrefixFilter(logging.Filter):
    """Accepts only records whose logger starts with one of the given prefixes."""
    def __init__(self, *prefixes: str):
        super().__init__()
        self._prefixes = prefixes

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name == p or record.name.startswith(p + ".") for p in self._prefixes)


# ── Colored formatter for the console ────────────────────────────────────────

_R   = "\033[0m"   # reset
_B   = "\033[1m"   # bold
_DIM = "\033[2m"   # dim

_LEVEL_COLOR = {
    logging.DEBUG:    "\033[37m",   # branco/cinza
    logging.INFO:     "\033[36m",   # ciano
    logging.WARNING:  "\033[33m",   # amarelo
    logging.ERROR:    "\033[31m",   # vermelho
    logging.CRITICAL: "\033[35m",   # magenta
}
LEVEL_LABEL = {
    logging.DEBUG:    "DEBUG",
    logging.INFO:     "INFO ",
    logging.WARNING:  "WARN ",
    logging.ERROR:    "ERROR",
    logging.CRITICAL: "CRIT ",
}
# 6-char aliases per subsystem. Public because the dashboard footer reuses
# them as the source column — the same taxonomy in both places.
LOGGER_ALIAS: dict[str, str] = {
    "executor":                 "AGENT ",
    "executor.connection":      "CONN  ",
    "executor.job_queue":       "QUEUE ",
    "executor.job_executor":    "EXEC  ",
    "executor.event_publisher": "EVENT ",
    "executor.job_validator":   "VALID ",
    "executor.crypto":          "CRYPTO",
    "executor.sync":            "SYNC  ",
    "executor.sync.manager":    "SYNC  ",
    "executor.sync.uploader":   "SYNC  ",
    "executor.sync.downloader": "SYNC  ",
    "executor.sync.watcher":    "SYNC  ",
    "httpx":                 "HTTP  ",
    "flow":                  "FLOW  ",
}


def alias_for(name: str) -> str:
    """The subsystem's 6-char alias. Falls back to the name's prefix if unknown."""
    if name in LOGGER_ALIAS:
        return LOGGER_ALIAS[name]
    for key, val in LOGGER_ALIAS.items():
        if name.startswith(key + "."):
            return val
    return name[:6].ljust(6)


class _ColoredFormatter(logging.Formatter):
    def __init__(self, cor: str | None = None):
        super().__init__()
        modo = (cor if cor is not None else _log_color).strip().lower()
        if modo == "always":
            self._color = True
        elif modo == "never":
            self._color = False
        else:  # auto — colored only if stderr is a real TTY
            self._color = sys.stderr.isatty()

    def _alias(self, name: str) -> str:
        return alias_for(name)

    def format(self, record: logging.LogRecord) -> str:
        ts    = self.formatTime(record, "%H:%M:%S")
        level = LEVEL_LABEL.get(record.levelno, record.levelname[:5])
        alias = self._alias(record.name)
        msg   = record.getMessage()
        # The `logging.Formatter` contract: a ready `exc_text` takes precedence over
        # formatting `exc_info`. Secret redaction (flow/utils/segredos_vivos)
        # delivers the redacted traceback in `exc_text` and nulls `exc_info`; only
        # looking at `exc_info` made the console lose the whole traceback.
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            msg += "\n" + record.exc_text

        if self._color:
            c    = _LEVEL_COLOR.get(record.levelno, "")
            bold = _B if record.levelno >= logging.ERROR else ""
            colored_msg = f"{c}{msg}{_R}" if record.levelno >= logging.WARNING else msg
            return (
                f"{_DIM}{ts}{_R}  "
                f"{c}{bold}{level}{_R}  "
                f"{_DIM}{alias}{_R}  "
                f"{colored_msg}"
            )
        return f"{ts}  {level}  {alias}  {msg}"


# ── Module state ─────────────────────────────────────────────────────────────

_configured = False
_console: logging.Handler | None = None
_detached_console: logging.Handler | None = None
_catch_all: logging.Handler | None = None
# Filtered LOG_FILE_AGENT handler, kept so it can be removed when the
# catch-all takes over the SAME file (otherwise every line would come out twice).
_agent_file: logging.Handler | None = None
_agent_file_path: str | None = None


def configure_logging() -> None:
    """Installs the root logger, the console and the optional files. Idempotent.

    Reads the variables HERE, not at import: the executor's `.env` only enters
    the environment when `executor.config` runs `load_dotenv()`.
    """
    global _configured, _console, _agent_file, _agent_file_path, _log_color
    if _configured:
        return
    _configured = True

    # Secret redaction by default (DSN with password, Bearer, Basic, PAT...) on
    # EVERY record of the process, before any handler — the console, the
    # files and the dashboard. The executor decrypts DSNs and builds
    # authentication headers, and logged all of that unmasked; the list is the
    # same as the API's.
    from flow.utils.redacao_log import install_in_process
    install_in_process()

    _log_color = os.getenv("LOG_COLOR", "auto")

    plain = logging.Formatter(_LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(_log_level())

    # Console: all logs, unfiltered, with the colored formatter.
    _console = logging.StreamHandler()
    _console.setFormatter(_ColoredFormatter(_log_color))
    root.addHandler(_console)

    # Executor file: executor.* and httpx loggers (no colors)
    agente = os.getenv("LOG_FILE_AGENT") or ""
    if agente:
        _agent_file = _rotating(agente)
        _agent_file.setFormatter(plain)
        _agent_file.addFilter(_PrefixFilter("executor", "httpx"))
        _agent_file_path = agente
        root.addHandler(_agent_file)

    # Workflow file: flow.*, node.* and app.* loggers (no colors)
    workflow = os.getenv("LOG_FILE_WORKFLOW") or ""
    if workflow:
        h = _rotating(workflow)
        h.setFormatter(plain)
        h.addFilter(_PrefixFilter("flow", "node", "app"))
        root.addHandler(h)

    # Silenciar logs ruidosos do httpx (HTTP Request: GET/POST ...)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Validation warnings accumulated during the import of config.py, which runs
    # before this point. Emitted now that there is somewhere to send them.
    try:
        from executor.config import flush_startup_warnings
        flush_startup_warnings()
    except Exception:  # pragma: no cover — config indisponivel (uso isolado)
        pass


def resolve_agent_log_path() -> str:
    """Path of the agent log file in dashboard mode.

    LOG_FILE_AGENT takes precedence — whoever already configured it keeps
    control of the destination. Without it, the default derives from
    EXECUTOR_LOG_DIR / ARTIFACTS_DIR, following the same ~/AtlansExecutor
    convention used by the artifacts.
    """
    explicito = os.getenv("LOG_FILE_AGENT") or ""
    if explicito:
        return explicito

    from executor import config
    return str(pathlib.Path(config.LOG_DIR) / "executor.log")


def ensure_file_mirror() -> str:
    """Ensures the CATCH-ALL rotating handler — the console's mirror on disk.

    Idempotent: called the first time the dashboard turns on and never undone.
    The file keeps receiving everything even after the console comes back,
    whether via the keyboard shortcut or via shutdown.

    Returns the effective path. Raises LoggingSetupError if it cannot open
    it — the caller MUST abort the dashboard in that case: turning on the
    dashboard without the file would swap the step-by-step log for nothing.
    """
    global _catch_all, _agent_file

    path = resolve_agent_log_path()
    if _catch_all is not None:
        return path

    root = logging.getLogger()

    # Does the filtered LOG_FILE_AGENT handler point to this same file? It goes
    # away BEFORE the catch-all opens: otherwise every `executor.*` line would
    # come out twice, and two RotatingFileHandlers with the same file open fight
    # when rotating (on Windows, renaming an open file fails).
    if _agent_file is not None and _agent_file_path == path:
        root.removeHandler(_agent_file)
        _agent_file.close()
        _agent_file = None

    try:
        catch_all = _rotating(path)
    except OSError as exc:
        raise LoggingSetupError(f"Nao foi possivel abrir o log em '{path}': {exc}") from exc

    catch_all.setFormatter(logging.Formatter(_LOG_FORMAT))
    # Unfiltered, on purpose: this handler replaces the console, which also
    # had no filter. It is the mirror of what used to go to the screen.
    root.addHandler(catch_all)
    _catch_all = catch_all
    return path


def detach_console() -> None:
    """Takes the console off the root — the screen is free for the dashboard. Idempotent."""
    global _detached_console
    if _console is None or _detached_console is not None:
        return
    logging.getLogger().removeHandler(_console)
    _detached_console = _console


def switch_to_dashboard_mode() -> str:
    """Turns on dashboard mode: ensures the file mirror and frees the screen.

    Reversible: `restore_console_mode()` brings the log back to the terminal
    without closing the file, and a new call here hands the screen back to the
    dashboard. That is what supports the keyboard toggle.
    """
    path = ensure_file_mirror()
    detach_console()
    return path


def restore_console_mode() -> None:
    """Reattaches the console. Idempotent — can be called from several exit
    paths (normal shutdown, atexit, KeyboardInterrupt) without duplicating handlers.

    The file handlers stay where they are: after the dashboard closes, the
    log keeps being written until the process dies.
    """
    global _detached_console
    if _detached_console is None:
        return
    root = logging.getLogger()
    if _detached_console not in root.handlers:
        root.addHandler(_detached_console)
    _detached_console = None


# ── Runtime log level ────────────────────────────────────────────────────────
# Keeps the level configured at boot so the toggle knows what to go back to.
_base_level: int | None = None


def em_debug() -> bool:
    return logging.getLogger().level <= logging.DEBUG


def toggle_debug() -> bool:
    """Turns DEBUG on/off without restarting the executor. Returns the new state.

    Diagnosing an error required stopping the process, editing LOG_LEVEL in .env
    and starting again — losing exactly the state one wanted to investigate.
    Since no handler has its own level (only LogTailHandler, fixed at WARNING),
    changing the root is enough for the file to start receiving DEBUG right away.
    """
    global _base_level
    root = logging.getLogger()
    if _base_level is None:
        _base_level = root.level or logging.INFO

    if em_debug():
        root.setLevel(_base_level)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        return False

    root.setLevel(logging.DEBUG)
    # httpx/httpcore at DEBUG dump every HTTP frame and drown the rest — what the
    # operator wants to see is `executor.*` and `flow.*`. They stay at INFO.
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    return True
