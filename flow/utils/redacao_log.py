# flow/utils/redacao_log.py
"""PATTERN-based secret redaction in the log — Bearer, Basic, DSN with password, PAT,
AWS key, PEM block.

Lives in flow/ because flow is in all three images (API, executor and the executor
packaged in the desktop app). The list used to live in `app/core/utils/logger.py`, and
only the app's loggers used it: the executor, which decrypts DSNs and builds
authentication headers, logged with no masking at all. The app re-exports from
here — a single list.

Two ways to turn it on:

- `SecretScrubFilter`: per-logger filter (the app's `get_logger` attaches it).
- `install_in_process()`: the LogRecord factory, through which EVERY record
  in the process passes — including third-party libraries' and those of handlers
  that don't exist yet (the executor installs several: console, files, panel).
  It is the same hook `segredos_vivos` uses for the secrets in use.
"""
import logging
import re
import threading

# ── Secret scrubbing ─────────────────────────────────────────────────────────
# Patterns we redact BEFORE the log goes to stdout/file. Prevents:
#   - A traceback with a request body containing `"password": "..."` from leaking
#   - An Authorization header with a JWT from reaching Loki/CloudWatch
#   - Enrollment OTPs (single-use but still useful for a postmortem if
#     captured) from staying in plaintext
#   - GitHub PATs / AWS keys / Ed25519 privates from matching accidentally
#
# `_SCRUB_PATTERNS` runs in order — the most specific come first so they are
# not masked by generic rules (e.g. "Bearer <jwt>" before
# "token=..."). `_REDACTED` keeps the same visual length on any
# match — it does not leak the original secret's size.
_REDACTED = "<REDACTED>"

_SCRUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Authorization: Bearer <jwt> — case-insensitive
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[\w.\-]+"), rf"\1{_REDACTED}"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{20,}"), rf"\1{_REDACTED}"),
    # Authorization: Basic <base64(user:password)> — the Basic password (the
    # "wfs" credential and http_basic) travels like this, and a proxy or WAF that
    # echoes the request headers returns it like this, trivially reversible.
    (re.compile(r"(?i)(authorization\s*[:=]\s*basic\s+)[A-Za-z0-9+/=_\-]{8,}"), rf"\1{_REDACTED}"),

    # JSON keys sensiveis: "password":"...", "otp":"...", "api_key":"...",
    # "access_token":"...", "refresh_token":"...", "secret":"..."
    (re.compile(
        r'(?i)("(?:password|passwd|otp|api[_-]?key|access[_-]?token|'
        r'refresh[_-]?token|secret|private[_-]?key|fernet[_-]?key|'
        r'signing[_-]?key)"\s*:\s*")[^"]+(")'
    ), rf"\1{_REDACTED}\2"),

    # `authkey` is the key of GeoServer's authkey module, which the WFS node sends in
    # the URL — already encoded: `%2B`, `%2F` and co. are part of it, and the
    # generic rule below would stop at the first `%`, leaving the rest of the key.
    (re.compile(r"(?i)\b(authkey)=([^&#\s\"'<>]{6,})"), rf"\1={_REDACTED}"),

    # Query / form: otp=..., password=..., token=... (nao pega palavras curtas).
    (re.compile(
        r"(?i)\b(otp|password|token|api[_-]?key|access[_-]?token|refresh[_-]?token|secret)"
        r"=([\w.\-]{6,})"
    ), rf"\1={_REDACTED}"),

    # GitHub Personal Access Tokens (github_pat_..., ghp_..., ghs_..., etc)
    (re.compile(r"\b(github_pat_|ghp_|ghs_|gho_|ghu_|ghr_)[A-Za-z0-9_]{20,}"), _REDACTED),

    # Atlans personal access tokens (atl_pat_ + 43 url-safe chars) — the
    # "Bearer atl_pat_..." case already falls under the Bearer rule; this one catches
    # the bare token. No `\b`: the prefix is specific enough, and a token glued to
    # another word ("id=atl_pat_...", "_atl_pat_...") must also disappear.
    (re.compile(r"atl_pat_[A-Za-z0-9_\-]{43}"), _REDACTED),

    # DSN / URL with an embedded credential, such as
    #   postgresql://user:senha@host/db  ou  https://user:senha@api/...  # pragma: allowlist secret
    # asyncpg/SQLAlchemy failures embed the whole DSN in the message, and
    # legacy `connectionString` is stored like this. Only the password goes: scheme,
    # user and host stay so diagnostics remain useful. It comes before the
    # generic keys (AWS, sk-) so none of them masks the match halfway.
    #
    # The three ceilings are what keep the cost linear: without them, each letter
    # of a long text without "://" opened a scan to the end (100 KB cost 26 s
    # of synchronous CPU on the event loop, because the filter runs on EVERY log).
    # The user is optional — `redis://:senha@host` is the canonical form of
    # REDIS_URL — and the password is greedy up to the last "@" before "/" or a
    # space, otherwise `user:p@ss@host` would leave the password's tail behind.
    (re.compile(r"(?i)\b([a-z][a-z0-9+.\-]{0,31}://[^/\s:@]*:)[^\s/]{1,256}(@)"), rf"\1{_REDACTED}\2"),

    # AWS access keys
    (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), _REDACTED),

    # OpenAI / Anthropic style (sk-... com 30+ chars)
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"), _REDACTED),

    # PEM privates — bloco inteiro
    (re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY-----"
        r".*?-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY-----",
        re.DOTALL,
    ), _REDACTED),
]


def _scrub(text: str) -> str:
    """Applies all patterns in order and returns the redacted text."""
    for pattern, replacement in _SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# Public name of the same function: whoever redacts text that LEAVES the server
# (run errors, definitions, event payloads) uses the same pattern list as
# the log — a single place to add a new format. `_scrub` stays for the
# existing callers.
scrub_text = _scrub


class SecretScrubFilter(logging.Filter):
    """
    Filter that redacts secrets in record.msg + record.args BEFORE the formatter
    is called. Attached to every logger created by `get_logger()` — prevents
    file and console handlers, or any sink (Loki, Sentry), from seeing the
    plaintext.

    Fails open: if the scrub raises an exception (catastrophic regex on a huge str),
    the filter lets the record through unmodified. Losing the log would be worse
    than a log with a secret.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # bare msg (before interpolating args)
            if isinstance(record.msg, str):
                record.msg = _scrub(record.msg)
            # interpolated args: substitute in each string of the tuple
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: _scrub(v) if isinstance(v, str) else v
                                   for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(_scrub(a) if isinstance(a, str) else a
                                        for a in record.args)
        except Exception:
            pass
        return True



# Arguments the pattern pass has already seen in full: text (redacted one by
# one) and numbers (carry no secret). With all of them like this, the interpolated
# message has nothing more to show.
_SIMPLE_ARGS = (str, int, float, bool, type(None))


def _redact_record(registro: logging.LogRecord) -> None:
    """The `SecretScrubFilter` plus what only shows up INTERPOLATED: an argument
    that is not a string (the asyncpg exception carries the DSN in its `str()`), and
    the exception's traceback. The record keeps its shape (`msg`/`args` one by one)
    when nothing changes in the interpolation — some formatters read `record.args`."""
    # 1. The secrets IN USE (`segredos_vivos`) first, by exact value. The
    #    patterns stop at the first `%`, `+` or `/` of the value (`token=Kq7v%2B…`)
    #    and, running first, cut off the needle the exact replacement looks for:
    #    the tail of the key ended up in the log. It doesn't matter in which order
    #    the two factories were installed — this one applies both, in this order.
    from flow.utils import segredos_vivos

    formas = segredos_vivos._forms
    if formas:
        segredos_vivos._clean(registro, formas)
    # 2. The patterns on `msg` and on each text argument.
    _secret_filter_do_flow.filter(registro)
    # 3. The interpolated message, only when it has something more to show: a `msg`
    #    that is not text, or an argument that is neither text nor a number.
    #    Rescanning the whole message every time doubled the cost of every record.
    args = registro.args
    valores = args.values() if isinstance(args, dict) else (args or ())
    if not isinstance(registro.msg, str) or not all(isinstance(v, _SIMPLE_ARGS) for v in valores):
        try:
            mensagem = registro.getMessage()
        except Exception:
            mensagem = None
        if mensagem is not None:
            redigida = _scrub(mensagem)
            if redigida != mensagem:
                registro.msg, registro.args = redigida, None
    # 4. The traceback: formatted once and stored in `exc_text` (the formatter uses it
    #    ready-made instead of formatting `exc_info` again).
    if registro.exc_info and not registro.exc_text:
        texto = logging.Formatter().formatException(registro.exc_info)
        redacted = _scrub(texto)
        registro.exc_text = redacted
        if redacted != texto:
            registro.exc_info = None
    if registro.stack_info:
        registro.stack_info = _scrub(registro.stack_info)


_secret_filter_do_flow = SecretScrubFilter()
_lock = threading.Lock()
_installed = False


def install_in_process() -> None:
    """Redacts every log record of this process. Idempotent.

    Fails open, like the filter: if the redaction raises, the record goes on as
    it came — losing the log would be worse.
    """
    global _installed
    with _lock:
        if _installed:
            return
        anterior = logging.getLogRecordFactory()

        def fabrica(*args, **kwargs):
            registro = anterior(*args, **kwargs)
            try:
                _redact_record(registro)
            except Exception:  # logging never brings down the caller
                pass
            return registro

        logging.setLogRecordFactory(fabrica)
        _installed = True
