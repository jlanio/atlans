# executor/_ambiente.py
"""
Reading numbers from the executor's environment — the single place.

An invalid value in `.env` (non-numeric, or out of range) is a typo, not
intent: it falls back to the default, with a warning naming the variable and the
value, and NEVER crashes the import. There used to be two copies of this reader
(executor/config.py and executor/sync/sync_config.py, with different contracts)
and five raw `int(os.getenv(...))` calls in job_validator.py and renewal.py — with
them, an `EXECUTOR_CLOCK_SKEW_SECONDS=abc` killed the process with ValueError at
import, before main() ran and before the channel with the supervisor came up.

The warning is DEFERRED while logging is not configured: executor/config.py is
imported before configure_logging(), and a warning emitted there would land in
logging.lastResort (raw stderr, unformatted — with the panel on, garbage drawn
over the display). It is held until configure_logging() calls
emitir_avisos_adiados() (via executor.config.flush_startup_warnings). From then
on warnings go out DIRECTLY: job_validator, renewal and sync_config are
imported after boot, and there would be no other flush to deliver them.
"""
from __future__ import annotations

import logging
import math
import os

logger = logging.getLogger(__name__)

_AVISOS_ADIADOS: list[tuple[str, tuple]] = []
_logging_pronto = False


def avisar(msg: str, *args) -> None:
    """Configuration warning: held until logging comes up, direct afterwards."""
    if _logging_pronto:
        logger.warning(msg, *args)
    else:
        _AVISOS_ADIADOS.append((msg, args))


def emitir_avisos_adiados() -> None:
    """Emits the held warnings, now that there are real handlers."""
    global _logging_pronto
    for msg, args in _AVISOS_ADIADOS:
        logger.warning(msg, *args)
    _AVISOS_ADIADOS.clear()
    _logging_pronto = True


def _faixa(minimo, maximo) -> str:
    return f">= {minimo}" if maximo is None else f"entre {minimo} e {maximo}"


def ler_int(nome: str, padrao: int, minimo: int = 1, maximo: int | None = None) -> int:
    """Integer from the environment within [minimo, maximo]; outside it, the default with a warning.

    Missing or blank means the default, with no warning. The range exists because an
    absurd value does not fail — it works wrong: `EXECUTOR_MAX_CONCURRENT=0` brought
    the executor up with NO worker at all, online, reporting capacity 0 (and therefore
    PREFERRED by the server's least-loaded scheduler), ACKing jobs and
    never executing them — runs stuck in 'running' forever.
    """
    bruto = os.getenv(nome)
    if bruto is None or not bruto.strip():
        return padrao
    try:
        valor = int(bruto.strip())
    except ValueError:
        avisar("%s=%r nao e um inteiro — usando o padrao %d.", nome, bruto, padrao)
        return padrao
    if valor < minimo or (maximo is not None and valor > maximo):
        avisar("%s=%d fora da faixa (%s) — usando o padrao %d.",
               nome, valor, _faixa(minimo, maximo), padrao)
        return padrao
    return valor


def ler_float(nome: str, padrao: float, minimo: float, maximo: float | None = None) -> float:
    """Float version of ler_int. `nan` and `inf` are not numbers for this purpose."""
    bruto = os.getenv(nome)
    if bruto is None or not bruto.strip():
        return padrao
    try:
        valor = float(bruto.strip())
    except ValueError:
        valor = math.nan
    if not math.isfinite(valor):
        avisar("%s=%r nao e um numero — usando o padrao %s.", nome, bruto, padrao)
        return padrao
    if valor < minimo or (maximo is not None and valor > maximo):
        avisar("%s=%s fora da faixa (%s) — usando o padrao %s.",
               nome, valor, _faixa(minimo, maximo), padrao)
        return padrao
    return valor
