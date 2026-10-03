# executor/config.py
"""
Executor settings loaded from environment variables.

Required variables:
  EXECUTOR_ID                  — executor UUID (obtained when the admin creates it)
  EXECUTOR_SERVER_URL          — the installation's executors host (wss://...).
                                 No default: enroll writes it to .env.

Credentials (mTLS cert) are persisted in EXECUTOR_CERT_DIR (default ./certs/).
Each executor must enroll exactly once (the ready-made command comes from the
installation's enrollment screen):
  python -m executor enroll --otp=<OTP_FORNECIDO_PELO_ADMIN> --server=https://agents.<dominio>

Optional variables:
  SERVER_SIGNING_PUBLIC_KEY    — base64 of the server's Ed25519 public key.
                                 Operator override: without it, the key
                                 pinned at enrollment applies (see executor/server_key.py)
  EXECUTOR_CERT_DIR            — directory for cert.pem/chain.pem/ca.pem/key.pem (default: ./certs)
  EXECUTOR_PRIVATE_KEY         — base64 of the X25519 private key (envelope encryption)
                              If not provided, read from EXECUTOR_PRIVATE_KEY_PATH
  EXECUTOR_PRIVATE_KEY_PATH    — path of the X25519 private key
  EXECUTOR_VERSION             — software version outside the Docker image (default: "1.0.0";
                                 in the image the one written at build applies — executor/versao.py)
  EXECUTOR_MAX_CONCURRENT      — concurrent executions (default: 4)
  EXECUTOR_MAX_QUEUE_SIZE      — maximum local queue (default: 50)
  EXECUTOR_JOB_TIMEOUT         — per-job timeout in seconds (default: 3600)
  EXECUTOR_RECONNECT_MAX_DELAY — maximum reconnect delay in seconds (default: 15)
  NONCE_CACHE_TTL           — TTL of the anti-replay cache in seconds (default: 600)
  EXECUTOR_MAX_JOB_EXPIRY_SECONDS — ceiling on the envelope's declared duration
                                 (expires_at - issued_at), default 900s
  EXECUTOR_CLOCK_SKEW_SECONDS  — clock slack in the expiration check
                                 (default: 300s)
  EXECUTOR_MAX_CLOCK_SKEW_SECONDS — HARD ceiling on local clock drift
                                 (default: 900s). Above it every job/command is
                                 refused, pointing at NTP, instead of accepted: with
                                 large drift the acceptance window exceeds the TTL
                                 of the nonce cache and anti-replay stops holding.
                                 Raising this value requires raising NONCE_CACHE_TTL
                                 along with it — there is a test for the invariant.
                                 The four are read inside
                                 executor/job_validator.py, alongside the comment
                                 that explains the reason for each value.
  EXECUTOR_HOST_ALIASES        — hostname mapping "db=localhost:5433,..."
  EXECUTOR_DASHBOARD           — auto|on|off|json (see the panel block below)
  EXECUTOR_SUPERVISOR_PID      — PID of whoever started this process (the desktop
                                 app). Set by the supervisor, never by
                                 hand. Turns on the watchdog in executor/supervisor.py,
                                 which shuts the executor down in an orderly way if the
                                 supervisor dies, and turns off the internal
                                 auto-restart — with a supervisor, restarting is its
                                 job.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from executor._ambiente import avisar, emitir_avisos_adiados, ler_float, ler_int
from executor.versao import versao_do_executor

# Carrega .env — EXECUTOR_ENV_PATH permite ao Electron definir um path customizado.
_env_path = os.getenv("EXECUTOR_ENV_PATH") or str(Path(__file__).parent / ".env")
load_dotenv(dotenv_path=_env_path)

# Disables the OGR VRT drivers in GDAL BEFORE any import of geopandas/
# pyogrio (GDAL reads GDAL_SKIP when it registers the drivers). Without this, a file
# or WFS response with <OGRVRTDataSource> content makes GDAL read a local file
# on the executor (mTLS cert, credentials) or do SSRF via /vsicurl. File reading
# also refuses VRT by content (flow/utils/leitura_geo.py); this is the
# defense in depth that covers even a VRT embedded in a .zip.
_gdal_skip = {s for s in os.environ.get("GDAL_SKIP", "").split(",") if s}
os.environ["GDAL_SKIP"] = ",".join(sorted(_gdal_skip | {"OGR_VRT", "VRT"}))


# Numbers from the environment are read by executor/_ambiente.py (ler_int/ler_float):
# an invalid value becomes the default with a warning, never a ValueError at import. This
# module runs BEFORE logging is configured, so the warnings are held
# there until configure_logging() calls flush_startup_warnings() — the name
# that executor/logging_setup.py imports from here.
flush_startup_warnings = emitir_avisos_adiados


# Server URL. No default: an executor never talks to an installation that
# nobody chose. Enroll writes the value to .env (see executor/enrollment.py).
SERVER_URL: str = os.getenv("EXECUTOR_SERVER_URL", "").strip()

# TOLERANT read: aborting at import killed the process with ValueError before
# main() ran, and before the channel with the supervisor came up — the failure arrived
# as a raw traceback, without saying what to do. The requirement lives in
# assert_configured(), called inside main() once the channel is up.
EXECUTOR_ID:                 str = os.getenv("EXECUTOR_ID", "").strip()
SERVER_SIGNING_PUBLIC_KEY: str = os.getenv("SERVER_SIGNING_PUBLIC_KEY", "")

# ── mTLS cert directory ───────────────────────────────────────────────────────
_default_cert_dir = "/data/certs" if os.path.isdir("/data") else "./certs"
EXECUTOR_CERT_DIR: str = os.getenv("EXECUTOR_CERT_DIR", _default_cert_dir)

# Paths of the individual files inside the cert dir.
EXECUTOR_CERT_PATH:  str = str(Path(EXECUTOR_CERT_DIR) / "cert.pem")
EXECUTOR_CA_PATH:    str = str(Path(EXECUTOR_CERT_DIR) / "ca.pem")
EXECUTOR_KEY_PATH:   str = str(Path(EXECUTOR_CERT_DIR) / "key.pem")
# X25519 private key to decrypt job envelopes (generated at enroll).
EXECUTOR_X25519_KEY_PATH: str = str(Path(EXECUTOR_CERT_DIR) / "x25519_key.pem")

# Backward compat: the envelope decryption code still reads EXECUTOR_PRIVATE_KEY_PATH.
EXECUTOR_PRIVATE_KEY:      str | None = os.getenv("EXECUTOR_PRIVATE_KEY")
EXECUTOR_PRIVATE_KEY_PATH: str = os.getenv("EXECUTOR_PRIVATE_KEY_PATH", EXECUTOR_X25519_KEY_PATH)


def _cleanup_renewal_orphans() -> None:
    """
    Removes orphan `.new` files in EXECUTOR_CERT_DIR. They are left behind when
    enroll or renewal (enrollment._persistir_bundle) writes the `<nome>.new` files
    but the process dies before the atomic `os.replace`. Without cleanup, they pile up
    forever. The 10 min threshold avoids racing with a renewal in progress.
    """
    import time as _time
    cert_dir = Path(EXECUTOR_CERT_DIR)
    if not cert_dir.is_dir():
        return
    cutoff = _time.time() - 10 * 60
    for orphan in cert_dir.glob("*.new"):
        try:
            if orphan.stat().st_mtime < cutoff:
                orphan.unlink()
        except OSError:
            pass


def assert_configured() -> None:
    """
    Checks the required variables before starting.

    This used to be a `_require()` at import time, which killed the process
    with ValueError before main() ran. Now the check is explicit and
    happens inside main(), after the channel with the supervisor comes up.
    """
    if not SERVER_URL:
        raise SystemExit(
            "\n  Variavel obrigatoria nao definida: EXECUTOR_SERVER_URL\n"
            "\n  O enrollment a grava no .env:\n"
            "    python -m executor enroll --executor-id=<ID> --otp=<OTP> \\\n"
            "        --server=<URL do host dos executores>\n"
            "\n  O comando pronto, com o endereco da sua instalacao, sai da tela de\n"
            "  matricula do executor.\n"
            f"\n  (.env esperado em {_env_path})\n"
        )
    if not EXECUTOR_ID:
        # This is the message the user sees when the executor cannot
        # start. It must say what to DO, not only what is missing — and both
        # paths below work in every environment where the executor runs.
        raise SystemExit(
            "\n  Variavel obrigatoria nao definida: EXECUTOR_ID\n"
            "\n  Enrollment (funciona em qualquer ambiente):\n"
            "    python -m executor enroll --executor-id=<ID> --otp=<OTP> \\\n"
            "        --server=" + SERVER_URL + "\n"
            "\n  Em Docker, o EXECUTOR_ID tambem precisa estar no .env montado\n"
            "  no container (env_file: em docker-compose.executor.yml).\n"
            "\n  No app desktop, o formulario de vinculo faz isso pela interface.\n"
            f"\n  (.env esperado em {_env_path})\n"
        )


def assert_enrolled() -> None:
    """
    Checks that the executor has been enrolled before starting.
    Called by executor/main.py to fail fast with a clear message.
    """
    _cleanup_renewal_orphans()
    cert_path = Path(EXECUTOR_CERT_PATH)
    key_path  = Path(EXECUTOR_KEY_PATH)
    if not cert_path.exists() or not key_path.exists():
        raise SystemExit(
            "\n  Executor nao enrolado.\n"
            "  Rode: python -m executor enroll --otp=<OTP> --server=" + SERVER_URL + "\n"
            f"  (cert.pem esperado em {cert_path})\n"
        )

# In the Docker image the version written at build applies, over the .env (see
# executor/versao.py); outside it, EXECUTOR_VERSION — the desktop app sets it.
EXECUTOR_VERSION:            str = versao_do_executor()
_versao_no_env = (os.getenv("EXECUTOR_VERSION") or "").strip()
# The 1.0.0 is the one from the .env.example every old installation has: not a choice.
if _versao_no_env and _versao_no_env not in (EXECUTOR_VERSION, "1.0.0"):
    avisar(
        "EXECUTOR_VERSION=%s ignorada: vale a versao gravada na imagem (%s).",
        _versao_no_env, EXECUTOR_VERSION,
    )
# Minimum 1 because zero does not fail, it works wrong: an executor with no worker, a queue
# that never accepts, a job that times out immediately (see executor/_ambiente.py::ler_int).
# Maximums are defensive: absurd values (256 workers, a 100k queue) bring down
# the host before the operator notices the typo. The desktop app's Settings
# screen mirrors the defaults and ranges of these three in desktop/src/shared/limites.ts
# — the test there reads THESE lines and fails if the two sides diverge.
MAX_CONCURRENT:           int = ler_int("EXECUTOR_MAX_CONCURRENT", 4, minimo=1, maximo=256)
MAX_QUEUE_SIZE:           int = ler_int("EXECUTOR_MAX_QUEUE_SIZE", 50, minimo=1, maximo=10_000)
JOB_TIMEOUT:              int = ler_int("EXECUTOR_JOB_TIMEOUT", 3600, minimo=1)
# 15s, and not 60s: the ceiling exists against a thundering herd in a long outage, but with
# 60s a server deploy (Traefik returning 404/502 for a few seconds)
# kept the executor off the panel for up to a minute AFTER everything was back —
# time during which dispatch routes to another executor or answers "nenhum executor
# disponivel" (no executor available). The 50-100% jitter already spreads the fleet enough.
RECONNECT_MAX_DELAY:      int = ler_int("EXECUTOR_RECONNECT_MAX_DELAY", 15, minimo=1, maximo=3600)
NONCE_CACHE_TTL:          int = ler_int("NONCE_CACHE_TTL", 600, minimo=1)

# Fixed workspace for GeoSync (optional — if not set, auto-detected from the server)
WORKSPACE_ID:       str | None = os.getenv("EXECUTOR_WORKSPACE_ID") or None


def _parse_host_aliases(raw: str) -> dict[str, str]:
    """
    Converts EXECUTOR_HOST_ALIASES to a dict {hostname_interno: host_externo_com_porta}.
    Format: "db=localhost:5433,redis=localhost:6379"
    """
    aliases: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" in part:
            internal, external = part.split("=", 1)
            aliases[internal.strip()] = external.strip()
    return aliases


HOST_ALIASES: dict[str, str] = _parse_host_aliases(os.getenv("EXECUTOR_HOST_ALIASES", ""))

# Base directory where the executor saves artifacts generated by output nodes.
# Electron sets EXECUTOR_ARTIFACTS_DIR pointing to the folder chosen by the user.
ARTIFACTS_DIR: str = os.getenv(
    "EXECUTOR_ARTIFACTS_DIR",
    str(Path.home() / "AtlansExecutor" / "artifacts"),
)

# ── Logging ────────────────────────────────────────────────────────────────────
# LOG_LEVEL, LOG_COLOR, LOG_FILE_AGENT and LOG_FILE_WORKFLOW do not live here: what
# reads them, directly from the environment, is configure_logging() in executor/logging_setup.py
# — at configuration time, not at import, so as not to depend on import order.


def _default_log_dir() -> str:
    """`<pai de ARTIFACTS_DIR>/logs`, following the ~/AtlansExecutor convention.

    In Docker, EXECUTOR_ARTIFACTS_DIR=/data/artifacts becomes /data/logs — inside
    the volume that is already persistent. If the parent is the filesystem root
    (ARTIFACTS_DIR misconfigured), falls back to home so as not to try writing to /.
    """
    pai = Path(ARTIFACTS_DIR).parent
    if pai == pai.parent:  # reached the root — not a place to write logs
        return str(Path.home() / "AtlansExecutor" / "logs")
    return str(pai / "logs")


LOG_DIR: str = os.getenv("EXECUTOR_LOG_DIR") or _default_log_dir()

# ── Live panel / channel with the supervisor ─────────────────────────────────
# EXECUTOR_DASHBOARD is read directly from the environment by the panel gate
# (`should_enable_from_process` in executor/dashboard/__init__.py):
# auto  — turns on the rich panel if the terminal is interactive and `rich` exists
# on    — forces the rich panel (useful for those who know what they are doing)
# off   — neither of the two; keeps the line-by-line log on the console
# json  — NDJSON channel on stdout, for a supervisor (the desktop app).
#         Never inferred: emitting JSON on the stdout of something expecting human logs
#         would break the consumer silently. See executor/dashboard/json_runtime.py
#         for the event format and the list of commands accepted on stdin.
DASHBOARD_INTERVAL: float = ler_float("EXECUTOR_DASHBOARD_INTERVAL", 1.0, minimo=0.25)

# ── GeoSync — sync of local folders with the Workspace Drive ──────────────────
# Comma-separated folders. Empty = sync disabled.
SYNC_DIRS: str = os.getenv("EXECUTOR_SYNC_DIRS", "")
# The defaults below apply when the line is missing from .env. The .env.example — the seed
# of every new installation — writes bidirectional and 10s on purpose; the desktop app
# writes the mode the screen shows and always 10s (desktop/src/shared/geosync.ts,
# with a test against these lines).
SYNC_INTERVAL: int = ler_int("EXECUTOR_SYNC_INTERVAL", 30, minimo=1)  # segundos
# upload | download | bidirectional | catalog
#
# `upload` is the safe default: nothing that happens in the Drive deletes or overwrites
# a local file (see the mode gate in sync/manager.py::_process_drive_event).
#
# `catalog` is for personal data (LGPD): the executor registers the dataset in the Drive —
# name, type, size, CRS, bbox, feature count — and the CONTENT never leaves
# this machine. The files can only be read by workflows that run on this
# same executor; download through the platform does not exist.
SYNC_MODE: str = os.getenv("EXECUTOR_SYNC_MODE", "upload")
SYNC_CONFLICT_STRATEGY: str = os.getenv("EXECUTOR_SYNC_CONFLICT_STRATEGY", "remote-wins")  # local-wins | remote-wins | keep-both
SYNC_TRIGGERS: str = os.getenv("EXECUTOR_SYNC_TRIGGERS", "")
