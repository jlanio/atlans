"""
Error taxonomy.

Classifies a failure into a stable CATEGORY so the server can decide what to do
with it (show it to the user, redeliver to another executor, send it to the
dead-letter) — instead of treating every failure as an opaque string.

Lives in `flow/` because it is used at both levels: the whole job (executor/) and
each individual node (flow/executor/core.py, which publishes the category in the
event so the run panel can say "retrying won't help, fix the input").

Categories and retry semantics:

  user       — invalid input/configuration (e.g. missing column, missing CRS);
               the user must fix it.                  → NOT retryable
  validation — rejected by the job's security validation.    → NOT retryable
  timeout    — exceeded the time limit.               → retryable (may be transient)
  resource   — out of resources (memory).             → NOT retryable as is
               (needs smaller data or a larger executor)
  transient  — operational/infra failure (network, connection). → retryable
  internal   — unexpected/unknown.                    → terminal (don't redeliver blindly)

`retryable` is derived from the category — it is the hint the future redelivery
logic uses to decide between re-dispatch and dead-letter.
"""
import asyncio

# categoria → retryable
_RETRYABLE = {
    "user": False,
    "validation": False,
    "timeout": True,
    "resource": False,
    "transient": True,
    "internal": False,
}


def is_retryable(category: str) -> bool:
    return _RETRYABLE.get(category, False)


def _chain(exc: BaseException):
    """Walks the exception and its chain (__cause__/__context__) without repeating.

    Nodes wrap the original error in a RuntimeError (`raise RuntimeError(...)
    from e`), so the root cause (e.g. MemoryError from the intersection) sits in
    __cause__ — the chain must be inspected, not just the top."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        yield cur
        cur = cur.__cause__ or cur.__context__


def classify_error(exc: BaseException) -> str:
    """Returns the failure's category (string), inspecting the exception chain."""
    types = tuple(type(e) for e in _chain(exc))

    def has(*cls: type) -> bool:
        return any(issubclass(t, cls) for t in types)

    # Order matters: from most specific/informative to generic.
    if has(MemoryError):
        return "resource"
    # asyncio.TimeoutError is an alias of TimeoutError in 3.11+ (the executor runs 3.12).
    if has(asyncio.TimeoutError, TimeoutError):
        return "timeout"
    if has(ConnectionError):
        return "transient"
    if has(ValueError, TypeError, KeyError, IndexError):
        return "user"
    return "internal"
