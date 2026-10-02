"""Helpers de datetime para o módulo flow — evita o deprecated `datetime.utcnow()`
do Python 3.12+.

Duplicado intencionalmente de app/core/utils/datetime_utils.py porque `flow/` é
executado também pelo executor remoto (pacote `executor/`), que não importa `app.*`.
Manter uma cópia local evita acoplar o executor ao módulo do servidor.
"""
from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Retorna datetime UTC naive (sem tzinfo).

    Substituto drop-in para `datetime.utcnow()` — compatível com colunas
    SQLAlchemy DateTime sem timezone e com serialização ISO sem sufixo `Z`.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_from_timestamp_naive(ts: float) -> datetime:
    """Converte Unix timestamp em datetime UTC naive.

    Substituto drop-in para `datetime.utcfromtimestamp(ts)` — deprecado em
    Python 3.12. Preserva o comportamento naive do original.
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
