"""Datetime helpers for the flow module — avoids the deprecated `datetime.utcnow()`
of Python 3.12+.

Intentionally duplicated from app/core/utils/datetime_utils.py because `flow/` is
also run by the remote executor (`executor/` package), which does not import `app.*`.
Keeping a local copy avoids coupling the executor to the server module.
"""
from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Returns a naive UTC datetime (no tzinfo).

    Drop-in replacement for `datetime.utcnow()` — compatible with SQLAlchemy
    DateTime columns without timezone and with ISO serialization without a `Z` suffix.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_from_timestamp_naive(ts: float) -> datetime:
    """Converts a Unix timestamp to a naive UTC datetime.

    Drop-in replacement for `datetime.utcfromtimestamp(ts)` — deprecated in
    Python 3.12. Preserves the original's naive behavior.
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
