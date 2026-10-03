# executor/job_validator.py
"""
Validation of received jobs before any decryption.

Mandatory order (fail early, fail safe):
  1. Ed25519 signature                 — server authenticity
  2. target_executor_id                   — anti-misrouting
  3. temporal freshness                — temporal anti-replay
  4. unique nonce (in-memory cache)    — nonce anti-replay
  5. Decryption (in job_executor)      — integrity via GCM tag

Optional env:
  EXECUTOR_MAX_JOB_EXPIRY_SECONDS — ceiling on the envelope's declared DURATION
                                    (`expires_at - issued_at`, default 900s).
                                    Also goes into the floor of the nonce cache TTL.
  EXECUTOR_CLOCK_SKEW_SECONDS     — slack accepted between the server clock and
                                    the local one when checking expiry (default 300s).

Read by executor/_ambiente.py::ler_int: an invalid value (`abc`, negative) becomes
the default with a warning, instead of bringing down the executor import with
ValueError.
"""
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone

from executor import config
from executor._ambiente import ler_int
from executor.crypto import verify_signature

logger = logging.getLogger(__name__)


# ── Ceiling on an envelope's declared DURATION ────────────────────────────────
# The server issues envelopes with a TTL of EXECUTOR_JOB_TTL_SECONDS (default 300s,
# see app/core/job_crypto.py) and commands with 120s (app/core/control_crypto.py).
# Without a ceiling on this side, an envelope signed with `expires_at` 10 years
# from now passed the temporal check forever — and since the nonce cache is
# finite, it was enough to wait for the entry to leave the cache to replay it.
#
# The ceiling is applied to `expires_at - issued_at`, NOT to `expires_at` minus
# the local clock. The difference is decisive: both timestamps come from the SAME
# clock (the server's), so the measure is immune to clock skew. The first version
# of this fix compared `expires_at` with the local `datetime.now()` and, as a
# result, a host with broken NTP running 10 min behind started rejecting 100% of
# jobs — total unavailability caused by a problem that is not a security one.
# Measuring the declared duration blocks exactly the same eternal envelope without
# depending on any clock. 900s = 3x the server's default TTL: leaves room for the
# operator to raise the TTL. Minimum 1: with zero, every envelope (duration > 0)
# would be rejected.
_MAX_EXPIRY_HORIZON_SECONDS = ler_int("EXECUTOR_MAX_JOB_EXPIRY_SECONDS", 900, minimo=1)

# ── Clock skew tolerance ──────────────────────────────────────────────────────
# The EXPIRY check (`agora_local > expires_at`) inherently depends on the local
# clock — there is no way to anchor absolute freshness without it. That is why it
# gets explicit, configurable slack instead of zero slack: a few minutes of NTP
# drift cannot bring down the whole executor. Zero is accepted (it is the
# operator's choice); negative would reject the envelope before it expires.
_CLOCK_SKEW_TOLERANCE_SECONDS = ler_int("EXECUTOR_CLOCK_SKEW_SECONDS", 300, minimo=0)

# ── HARD clock skew ceiling ───────────────────────────────────────────────────
# The tolerance above is asymmetric by construction: it lets through the envelope
# that is already past `expires_at`, but nothing blocks the opposite case — a local
# clock that is BEHIND. With the clock set back, `agora_local` never reaches
# `expires_at` and the envelope stays acceptable for (lag + duration) LOCAL
# seconds, while the nonce is only remembered for the cache TTL. Once the TTL has
# passed, the same signed envelope is accepted again: a replay, silent, with
# nothing in the log linking the failure to the clock.
#
# The ceiling closes this in BOTH directions, measuring |agora_local - issued_at|.
# Above it the envelope is REJECTED with an NTP message. It is a deliberate choice
# to fail LOUDLY instead of staying silently replayable: a host with more than
# 15 min of drift is broken in a way the operator needs to know about, and the
# message says exactly what to fix. Between the tolerance and the ceiling the
# envelope is accepted, but `_warn_on_clock_skew` already warns.
_MAX_CLOCK_SKEW_SECONDS = ler_int("EXECUTOR_MAX_CLOCK_SKEW_SECONDS", 900, minimo=0)

if _MAX_CLOCK_SKEW_SECONDS < _CLOCK_SKEW_TOLERANCE_SECONDS:
    # Contradictory configuration: the ceiling would reject before the slack is used.
    # Align instead of aborting — the executor cannot fail to start because of
    # two badly combined env vars.
    logger.warning(
        "EXECUTOR_MAX_CLOCK_SKEW_SECONDS (%ds) é menor que "
        "EXECUTOR_CLOCK_SKEW_SECONDS (%ds) — o teto rígido venceria a tolerância. "
        "Usando %ds para os dois.",
        _MAX_CLOCK_SKEW_SECONDS, _CLOCK_SKEW_TOLERANCE_SECONDS, _CLOCK_SKEW_TOLERANCE_SECONDS,
    )
    _MAX_CLOCK_SKEW_SECONDS = _CLOCK_SKEW_TOLERANCE_SECONDS


def _nonce_ttl_seconds() -> float:
    """
    Effective TTL of the nonce cache.

    MANDATORY BINDING: a nonce may only be forgotten AFTER the corresponding
    envelope is no longer acceptable — otherwise a window opens in which the
    same job still passes the temporal check but the cache no longer remembers
    it (replay). Therefore the TTL covers the MAXIMUM ACCEPTANCE WINDOW measured
    on the LOCAL clock, which is what the cache uses (`time.monotonic`):

        maximum declared duration  (_MAX_EXPIRY_HORIZON_SECONDS)
      + slack granted on expiry (_CLOCK_SKEW_TOLERANCE_SECONDS)
      + maximum tolerated clock drift (_MAX_CLOCK_SKEW_SECONDS)

    The third term is what the first version forgot: without the hard ceiling
    the drift was unbounded and no finite TTL could cover the window. With the
    ceiling, the sum is finite and the invariant holds again by construction.
    """
    return max(
        config.NONCE_CACHE_TTL,
        _MAX_EXPIRY_HORIZON_SECONDS
        + _CLOCK_SKEW_TOLERANCE_SECONDS
        + _MAX_CLOCK_SKEW_SECONDS,
    )


# ── In-memory nonce cache ─────────────────────────────────────────────────────
# OrderedDict in insertion order: (nonce → monotonic insertion_timestamp).
# Bounded to avoid unbounded growth.
#
# KNOWN LIMITATION: the cache is in memory only, so an executor restart wipes
# it. The remaining defense in that window is the capped `expires_at` above — a
# replay only works within the short horizon and only if the process restarts
# exactly in that interval.
_nonce_cache: OrderedDict[str, float] = OrderedDict()
_NONCE_CACHE_MAX = 10_000


def _nonce_seen(nonce: str) -> bool:
    """
    Returns True if the nonce has already been processed (replay detected).
    Registers the nonce if it is new.
    """
    now = time.monotonic()
    ttl = _nonce_ttl_seconds()

    # PERF: the OrderedDict is in insertion order and the TTL is fixed, so the
    # expired ones are always a prefix. Purging from the start until the first
    # still-valid one costs O(expired) — the previous version scanned the 10k
    # entries on every job, on the hot path.
    while _nonce_cache:
        oldest_nonce, oldest_ts = next(iter(_nonce_cache.items()))
        if now - oldest_ts <= ttl:
            break
        _nonce_cache.pop(oldest_nonce, None)

    if nonce in _nonce_cache:
        return True  # replay

    # A capacity overflow only happens with >10k LEGITIMATE jobs (the signature has
    # already been verified before this point) within the TTL window. Silently
    # discarding the oldest — as was done before — removes a STILL VALID nonce and
    # opens a replay hole without leaving a trace. We keep the memory limit, but
    # the discard becomes loud so the operator can raise NONCE_CACHE_TTL/capacity.
    if len(_nonce_cache) >= _NONCE_CACHE_MAX:
        evicted, _ = _nonce_cache.popitem(last=False)
        logger.error(
            "Cache anti-replay cheio (%d entradas, TTL %.0fs): nonce '%s…' AINDA VÁLIDO "
            "foi descartado para dar lugar a um novo. Enquanto durar a saturação, um "
            "replay do job correspondente não seria detectado.",
            _NONCE_CACHE_MAX, ttl, evicted[:16],
        )

    _nonce_cache[nonce] = now
    return False


# ── Main validation ───────────────────────────────────────────────────────────

class JobValidationError(Exception):
    """Raised when a security validation fails."""


# ── Frescor temporal (compartilhado por job e control) ────────────────────────

# Minimum interval between two clock skew warnings. The warning is diagnostic and
# runs on the hot path of every job — without throttling it would become one
# WARNING line per job and drown the log precisely when the operator needs to
# read it.
_SKEW_WARN_INTERVAL_SECONDS = 300.0
# None = never warned. Anchoring at 0.0 made `now_mono - 0.0 < 300` swallow the
# FIRST warning while the host had less than 5 min of uptime — on Linux
# `time.monotonic()` is the machine's uptime. In other words, the warning vanished
# precisely in the scenario where it matters: a container starting on a freshly
# created VM, with NTP still off. After the first warning the throttle works
# normally.
_last_skew_warn_monotonic: float | None = None


def _parse_iso_utc(value: str, field: str) -> datetime:
    """ISO8601 → tz-aware datetime. Without a timezone, assumes UTC (the server always
    sends an offset, but a naive envelope cannot become a TypeError in the subtraction)."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise JobValidationError(f"Campo '{field}' inválido: {exc}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _warn_on_clock_skew(now_utc: datetime, issued_at: datetime) -> None:
    """Warns when the local clock diverges from the server's beyond the tolerance.

    Purely diagnostic: rejects nothing. It exists because a clock failure
    disguises itself as an attack — without this warning the operator only sees
    the rejection, which talks about replay, and goes hunting for an adversary
    that does not exist.
    """
    global _last_skew_warn_monotonic

    skew = (now_utc - issued_at).total_seconds()
    if abs(skew) <= _CLOCK_SKEW_TOLERANCE_SECONDS:
        return
    now_mono = time.monotonic()
    if (
        _last_skew_warn_monotonic is not None
        and now_mono - _last_skew_warn_monotonic < _SKEW_WARN_INTERVAL_SECONDS
    ):
        return
    _last_skew_warn_monotonic = now_mono
    logger.warning(
        "Relógio local diverge do servidor em %.0fs (%s) — tolerância %ds, "
        "teto rígido %ds. Ainda estamos aceitando envelopes, mas corrija o NTP "
        "deste host: ao passar do teto TODO job e TODO comando serão recusados "
        "(de propósito — com deriva grande o anti-replay deixa de proteger).",
        skew,
        "local ATRASADO" if skew < 0 else "local ADIANTADO",
        _CLOCK_SKEW_TOLERANCE_SECONDS,
        _MAX_CLOCK_SKEW_SECONDS,
    )


def _assert_fresh(
    issued_at_str: str | None,
    expires_at_str: str | None,
    *,
    kind: str,
    prefix: str = "",
) -> None:
    """Validates the freshness of a signed envelope. Raises JobValidationError.

    Two checks of different natures:

    (a) DECLARED DURATION — `expires_at - issued_at` against the ceiling. A
        comparison between two instants of the same clock (the server's), hence
        immune to clock skew. It is what closes the replay hole of the "eternal"
        envelope.

    (b) EXPIRY — `agora_local > expires_at`, with explicit skew slack.
        Depends on the local clock by definition; the slack keeps broken NTP
        from turning into a 100% job rejection.

    `issued_at` is MANDATORY: without it there is no way to measure (a) and the
    only alternative would be to go back to anchoring the ceiling on the local
    clock. Server and executor ship together and both issuers (job_crypto and
    control_crypto) already send it.
    """
    if not expires_at_str:
        raise JobValidationError(f"{kind} sem campo '{prefix}expires_at'.")
    if not issued_at_str:
        raise JobValidationError(
            f"{kind} sem campo '{prefix}issued_at' — sem ele a duração declarada "
            "do envelope não pode ser limitada. Servidor desatualizado."
        )

    issued_at = _parse_iso_utc(issued_at_str, f"{prefix}issued_at")
    expires_at = _parse_iso_utc(expires_at_str, f"{prefix}expires_at")

    duracao = (expires_at - issued_at).total_seconds()
    if duracao <= 0:
        raise JobValidationError(
            f"{kind} com '{prefix}expires_at' ({expires_at_str}) anterior ou igual a "
            f"'{prefix}issued_at' ({issued_at_str}) — envelope malformado, rejeitado."
        )
    if duracao > _MAX_EXPIRY_HORIZON_SECONDS:
        raise JobValidationError(
            f"{kind} declara validade de {duracao:.0f}s ({issued_at_str} → "
            f"{expires_at_str}), acima do teto de {_MAX_EXPIRY_HORIZON_SECONDS}s. "
            "Envelope de vida longa demais volta a ser replayável assim que o nonce "
            "sai do cache — rejeitado. (Não é relógio: a duração é medida entre dois "
            "carimbos do próprio servidor.)"
        )

    now_utc = datetime.now(timezone.utc)

    # (c) HARD SKEW CEILING — before expiry, on purpose: when the clock is way
    # off, "expired" is the symptom and "clock" is the cause, and the cause is
    # what the operator needs to read. Symmetric: it catches both a clock that is
    # ahead (which would reject everything as expired) and one that is BEHIND —
    # the latter triggers no other check and is precisely what opened the replay
    # window described in _nonce_ttl_seconds.
    skew = (now_utc - issued_at).total_seconds()
    if abs(skew) > _MAX_CLOCK_SKEW_SECONDS:
        # skew = agora_local - issued_at. Negative => the local clock has not yet
        # reached the instant at which the server issued, i.e. it is BEHIND.
        direcao = "atrasado" if skew < 0 else "adiantado"
        raise JobValidationError(
            f"{kind} rejeitado: o relógio local está {abs(skew):.0f}s {direcao} em "
            f"relação ao servidor (emitido em {issued_at_str}), acima do teto de "
            f"{_MAX_CLOCK_SKEW_SECONDS}s. NÃO é replay — CORRIJA O NTP DESTE HOST. "
            "Enquanto a deriva persistir, TODOS os jobs e comandos serão recusados: "
            "é intencional, porque aceitar envelope de um relógio tão fora tornaria "
            "o anti-replay ineficaz (ver _nonce_ttl_seconds)."
        )

    atraso = (now_utc - expires_at).total_seconds()
    if atraso > _CLOCK_SKEW_TOLERANCE_SECONDS:
        raise JobValidationError(
            f"{kind} expirado em {expires_at_str} (há {atraso:.0f}s, além da "
            f"tolerância de skew de {_CLOCK_SKEW_TOLERANCE_SECONDS}s) — rejeitado. "
            "Se TODOS os envelopes estão sendo rejeitados assim, suspeite do relógio "
            "local adiantado (NTP) antes de suspeitar de replay."
        )

    _warn_on_clock_skew(now_utc, issued_at)


def validate_job(message: dict) -> None:
    """
    Runs all security validations in sequence.
    Raises JobValidationError with a detailed reason if any check fails.

    Does NOT decrypt the payload — that is the executor's responsibility.
    """
    envelope = message.get("envelope")
    if not isinstance(envelope, dict):
        raise JobValidationError("Mensagem sem envelope válido.")

    # ── 1. Assinatura Ed25519 ─────────────────────────────────────────────────
    if not verify_signature(message, config.SERVER_SIGNING_PUBLIC_KEY):
        raise JobValidationError("Assinatura Ed25519 inválida — job rejeitado.")

    # ── 2. Correct recipient ──────────────────────────────────────────────────
    if envelope.get("target_executor_id") != config.EXECUTOR_ID:
        raise JobValidationError(
            f"Job destinado a '{envelope.get('target_executor_id')}', "
            f"mas este executor é '{config.EXECUTOR_ID}'."
        )

    # ── 3. Validade temporal ──────────────────────────────────────────────────
    _assert_fresh(envelope.get("issued_at"), envelope.get("expires_at"), kind="Job")

    # ── 4. Unique nonce (anti-replay) ─────────────────────────────────────────
    nonce = envelope.get("nonce")
    if not nonce:
        raise JobValidationError("Envelope sem campo 'nonce'.")
    if _nonce_seen(nonce):
        raise JobValidationError(f"Nonce '{nonce[:16]}…' já foi processado — replay rejeitado.")

    # ── 5. Required fields ────────────────────────────────────────────────────
    for field in ("job_id", "job_type", "workspace_id"):
        if not envelope.get(field):
            raise JobValidationError(f"Campo obrigatório ausente no envelope: '{field}'.")


# ── Server → executor commands (control / cancel) ─────────────────────────────
# Counterpart of app/core/control_crypto.py. See the docstring there for the
# wire format and the reason it exists.

def _control_canonical_bytes(message: dict) -> bytes:
    """Signed bytes: the whole message minus `signature`.

    Must produce EXACTLY the same bytes as
    `app.core.control_crypto.canonical_bytes` — hence the fixed `sort_keys`,
    `ensure_ascii` and `separators` on both sides.
    """
    import json
    unsigned = {k: v for k, v in message.items() if k != "signature"}
    return json.dumps(
        unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode()


def validate_control_message(message: dict) -> None:
    """Validates the signature and freshness of a `control`/`cancel` from the server.

    Same check order as the job (fail early, fail safe): signature →
    recipient → deadline → nonce. Shares the anti-replay cache of
    `validate_job`: the nonce space is the same (32 random bytes from the
    server), so an entry can only be consumed once, whether by a job or by a
    command.

    Raises JobValidationError. Does NOT return a bool: a forgotten
    `if not valida(...)` in some caller would become a silent bypass.
    """
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(message, dict):
        raise JobValidationError("Comando não é um objeto JSON.")

    signature_b64 = message.get("signature")
    if not signature_b64:
        raise JobValidationError(
            f"Comando '{message.get('type')}' sem assinatura — rejeitado. "
            "Servidor desatualizado ou mensagem injetada."
        )

    auth = message.get("auth")
    if not isinstance(auth, dict):
        raise JobValidationError("Comando sem bloco 'auth' válido.")

    # ── 1. Assinatura Ed25519 ─────────────────────────────────────────────────
    server_pub = config.SERVER_SIGNING_PUBLIC_KEY
    if not server_pub:
        raise JobValidationError(
            "Chave pública de assinatura do servidor indisponível — "
            "impossível validar o comando."
        )
    try:
        pub_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(server_pub))
        pub_key.verify(base64.b64decode(signature_b64), _control_canonical_bytes(message))
    except Exception as exc:
        raise JobValidationError(
            f"Assinatura inválida no comando '{message.get('type')}': {exc}"
        ) from exc

    # ── 2. Correct recipient ──────────────────────────────────────────────────
    # Without this, a legitimate command captured on one executor's channel could
    # be replayed against any other.
    target = auth.get("target_executor_id")
    if target != config.EXECUTOR_ID:
        raise JobValidationError(
            f"Comando destinado a '{target}', mas este executor é '{config.EXECUTOR_ID}'."
        )

    # ── 3. Temporal validity ──────────────────────────────────────────────────
    # Same criterion as the job: a ceiling on the declared duration (immune to
    # skew) and expiry with skew slack. It is worth stressing why the slack here
    # is safe: revoking an executor does NOT depend on it obeying `control/revoked`
    # — the server closes the WS with 4403 and the cert blacklist blocks the
    # reconnect (see app/api/routers/executores_router.py). The command's temporal
    # check is a defense against replay, not the revocation mechanism.
    _assert_fresh(
        auth.get("issued_at"), auth.get("expires_at"), kind="Comando", prefix="auth.",
    )

    # ── 4. Unique nonce (anti-replay) ─────────────────────────────────────────
    nonce = auth.get("nonce")
    if not nonce:
        raise JobValidationError("Comando sem 'auth.nonce'.")
    if _nonce_seen(nonce):
        raise JobValidationError(
            f"Nonce '{nonce[:16]}…' já processado — replay de comando rejeitado."
        )
