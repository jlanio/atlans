# executor/dashboard/log_sink.py
"""
Handler that feeds the dashboard's alerts footer.
"""
from __future__ import annotations

import logging

from executor.logging_setup import LEVEL_LABEL, alias_for


class LogTailHandler(logging.Handler):
    """Forwards WARNING+ to the collector, which keeps them in a ring buffer.

    This is the only point where the dashboard touches the logging pipeline — on
    purpose: here the message text *is* the data. No statistics come from here;
    they come from the structured hooks.

    Without this block the dashboard would be actively worse than the log: an
    executor stuck in a reconnect loop would show counters going up and no clue
    to the cause.

    Formats in `emit`, not in render: keeping a live `LogRecord` would also hold
    on to everything `record.args` references, for minutes.
    """

    def __init__(self, stats, level: int = logging.WARNING):
        super().__init__(level=level)
        self._stats = stats

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._stats.on_log_record(
                record,
                alias_for(record.name),
                LEVEL_LABEL.get(record.levelno, record.levelname[:5]),
            )
        except Exception:
            pass  # handleError() would write to stderr — exactly what the dashboard occupies


class JsonLogHandler(LogTailHandler):
    """Besides feeding the ring buffer, emits `{"t":"log"}` on the NDJSON channel.

    Inherits from `LogTailHandler` on purpose: the GUI's alerts panel and the
    rich dashboard's footer show the SAME information, and having two extractions
    of the `LogRecord` would be the gateway for them to diverge.

    The parent's `emit` never raises, so the event goes out even if the collector
    chokes on the record.
    """

    def __init__(self, stats, runtime, level: int = logging.WARNING):
        super().__init__(stats, level=level)
        self._runtime = runtime

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        try:
            self._runtime.emitir("log", {
                "ts": record.created,
                "level": LEVEL_LABEL.get(record.levelno, record.levelname[:5]).strip(),
                "alias": alias_for(record.name).strip(),
                "logger": record.name,
                "msg": record.getMessage(),
            })
        except Exception:
            # Do not log here: a logger.error() inside a log handler is
            # recursion — the next emit would call this very block.
            pass
