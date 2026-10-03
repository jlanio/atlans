# flow/utils/backoff.py
"""
Single policy for waiting between attempts.

Before this module, exponential backoff was handwritten in ten places
scattered across seven files — the shared HTTP helper, the WFS and HTTP
Request nodes, the database wait at API startup, the two Redis reconnection
loops and the two in GeoSync — each with its own decision about growth,
ceiling and what counts as transient.

Only ONE of them spread its attempts out: the reconnection loop in
`executor/connection.py`, whose comment explains why and which
`executor/config.py` documents. The other nine retried in unison. And that
matters: when the server comes back from an outage, the whole executor fleet
hits it at the same instant, against a rate limit that is a single
platform-wide bucket — the recovery turns into a second takedown. The right
approach already existed in-house and had no way to spread, because it had
nowhere to live.

The jitter here is PROPORTIONAL (50–100% of the interval), not additive, for two
reasons: it is the form already validated in the executor, and it preserves the
ceiling — a jitter added to the interval can exceed `teto`, a multiplied one never.

Why not `tenacity`: it would replace the retry LOOP, not this policy, and only
two of the ten places have a loop separable from the domain logic — the others
carry TLS error classification, a circuit breaker, persisted scheduling or
reset on a healthy session. Besides, `flow/` runs in the Docker executor and in
the desktop one with the dependencies of the executor's lock file
(`executor/requirements-full.txt`, with hashes): adding the dependency without
regenerating the lock would break both at import. This module adds no
dependency at all — it depends only on `random`.
"""
import random

# Floor of the jitter range: the actual wait falls between 50% and 100% of the
# computed interval. Same range as `executor/connection.py`, which got it right
# first.
FATOR_JITTER_MIN = 0.5

# Exponent ceiling. `base ** tentativa` is FLOATING-POINT arithmetic, and
# overflows (`OverflowError`) around 2**1024 — the INTEGER `2 ** n` this
# module replaced had arbitrary precision and never overflowed. Attempt
# counters with no upper bound really exist in the codebase: the GeoSync
# cycle's `consecutive_errors` only resets on a successful cycle, and the HTTP
# Request node's `tentativas` comes from the canvas.
#
# Capping here changes no returned value: with `base > 1`, `inicial * 2**64`
# already exceeds 1e18, many orders of magnitude above any real `teto`, and
# the `min` saturates anyway.
_EXPOENTE_MAX = 64


def com_jitter(segundos: float) -> float:
    """Spreads out an already computed wait.

    For when the interval does NOT grow exponentially — the fixed reconnection
    ladders (`_RECONNECT_DELAYS`) are as synchronized as a power of two, and for
    the same reason: everyone who went down together comes back together.
    """
    if segundos <= 0:
        return 0.0
    return segundos * (FATOR_JITTER_MIN + random.random() * (1.0 - FATOR_JITTER_MIN))


def espera_exponencial(
    tentativa: int,
    *,
    teto: float,
    inicial: float = 1.0,
    base: float = 2.0,
) -> float:
    """Wait after the `tentativa`-th failure (0 = the first), already spread out.

    The ceiling is applied BEFORE the jitter, so the return value never exceeds it.
    """
    if tentativa < 0:
        tentativa = 0
    # `base <= 1` does not grow, so it does not overflow — and capping the exponent
    # there WOULD CHANGE the result, instead of just avoiding the overflow.
    if base > 1 and tentativa > _EXPOENTE_MAX:
        tentativa = _EXPOENTE_MAX
    return com_jitter(min(inicial * (base ** tentativa), teto))
