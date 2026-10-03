# flow/utils/fuso.py
"""
The default time zone for schedules: the one that applies when a schedule does not state its own.

Comes from the environment (AGENDAMENTO_FUSO_PADRAO), with UTC when nobody set it. Lives
in `flow/` because both sides need the SAME value and only this package is
shared by both: the ScheduleTrigger node (the executor packages `flow/` without `app/`) and
the server (`app/core/constants.py`). Diverging would make the next save of each
scheduled workflow recreate the schedule — see the constant on the server.

Standard library only: the module is imported at startup of both processes.
"""
from __future__ import annotations

import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FUSO_DE_RESERVA = "UTC"

# Files in the time zone database that zoneinfo opens but that are not time zones:
# the browser does not know them, and the screen would show a zone it cannot draw.
_NOT_TIMEZONES = frozenset({"localtime", "posixrules", "Factory"})


def default_schedule_timezone() -> str:
    """AGENDAMENTO_FUSO_PADRAO (an IANA time zone), or UTC when empty.

    A value that is not a time zone STOPS startup, instead of falling back to UTC: in an
    installation with schedules, a typo meaning UTC would recreate, on the
    next save, every schedule without an explicit time zone — hours out of place, with
    nothing to explain it. Like the invalid CORS origin in `app/core/config.py`.
    """
    valor = os.getenv("AGENDAMENTO_FUSO_PADRAO", "").strip()
    if not valor:
        return FUSO_DE_RESERVA
    erro = ValueError(
        f"AGENDAMENTO_FUSO_PADRAO={valor!r} não é um fuso IANA (ex.: America/Sao_Paulo, Europe/Lisbon, UTC)."
    )
    if valor in _NOT_TIMEZONES:
        raise erro
    try:
        ZoneInfo(valor)
    # OSError: a folder name in the database ("America") opens a directory.
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise erro from exc
    return valor
