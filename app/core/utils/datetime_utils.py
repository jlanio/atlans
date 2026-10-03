"""Datetime helpers — avoid Python 3.12+'s deprecated `datetime.utcnow()`.

Context: `datetime.utcnow()` was deprecated in 3.12 and will be removed in
future versions. The official replacement is `datetime.now(timezone.utc)`,
which returns a timezone-aware datetime.

However, many of the project's SQLAlchemy columns are `DateTime` (without
`timezone=True`) and expect naive values. To preserve that contract,
`utc_now_naive()` strips the tzinfo before returning.
"""
from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Returns a naive UTC datetime (no tzinfo).

    Drop-in replacement for `datetime.utcnow()` — compatible with SQLAlchemy
    DateTime columns without timezone. Preserves the project's historical
    behavior.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
