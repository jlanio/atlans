"""Substring search in the database: the term the user types is LITERAL.

`%` and `_` are LIKE wildcards. Without escaping them, searching for "a_b" also
returns "aXb", and "___" matches any row — the search looks like a broken
filter and, on a list of accounts, turns into enumeration of the whole
database. The escape (and the `\\` that introduces it) was copied by hand into
every service with a search, and the copy forgotten in the admin user search
left `_` as a wildcard. This is the single version; whoever searches by
substring uses `contem`.
"""
from __future__ import annotations

# The escape character goes explicitly in the query's `ESCAPE`: the LIKE default
# changes from database to database (PostgreSQL already uses `\`, SQLite has none).
_ESCAPE = "\\"


def escape_like(termo: str) -> str:
    """`termo` with `\\`, `%` and `_` escaped — literals inside a LIKE."""
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contem(coluna, termo: str, *, ignore_case: bool = True):
    """Condition "`coluna` contains `termo`", with the term treated as text.

    `ILIKE` by default, like the screens' searches. `ignore_case=False` gives
    plain `LIKE`, for a column that is already stored normalized (no accents,
    lowercase) — there the case difference was already resolved on write.
    """
    padrao = f"%{escape_like(termo)}%"
    if ignore_case:
        return coluna.ilike(padrao, escape=_ESCAPE)
    return coluna.like(padrao, escape=_ESCAPE)
