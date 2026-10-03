# executor/_env_utils.py
"""
Idempotent manipulation of executor/.env.

Shared between `executor.enrollment` (persists EXECUTOR_ID after enroll)
and the desktop app (writes config without destroying custom envs).

Algorithm:
  - Reads lines with splitlines (preserves comments, order, blank lines).
  - Finds the first line with `KEY=...` (ignoring comments and indentation).
  - If it exists with the same value: no-op.
  - If it exists with a different value: updates in place (same position).
  - If it does not exist: appends at the end.
  - If the file does not exist: creates it with a minimal header.

IO errors are logged as WARNING — never raised — so as not to block
critical flows (e.g.: enrollment has already persisted the cert).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _sem_export(linha: str) -> str:
    """Strips the `export ` prefix from a .env line, if present.

    A single place on purpose: when only `read_env_var` tolerated `export KEY=`,
    `remove_env_var` failed to match the same line that read reported — the
    migration of a legacy variable (enrollment.py) became a silent no-op, and a
    line `export KEY=antigo` coexisted with a `KEY=novo` appended later,
    with read returning the old one (first occurrence wins).
    """
    despido = linha.lstrip()
    if despido.startswith("export "):
        return despido[len("export "):].lstrip()
    return despido


def default_env_path() -> Path:
    """Default path of executor/.env, honoring EXECUTOR_ENV_PATH if set."""
    from_env = os.getenv("EXECUTOR_ENV_PATH")
    if from_env:
        return Path(from_env)
    # Goes up one level from this file (executor/) and uses .env in the same dir
    return Path(__file__).parent / ".env"


def persist_env_var(
    key: str,
    value: str,
    env_path: Path | str | None = None,
    file_header: str | None = None,
) -> None:
    """
    Idempotent. Updates/adds an environment variable in `env_path`.

    Args:
        key:        name of the env var (e.g.: "EXECUTOR_ID")
        value:      value (string; will be written as `KEY=value` literally)
        env_path:   path of the .env. If None, uses `default_env_path()`.
        file_header: optional header for the file if it is created from scratch
                    (e.g.: "# Gerado por executor enroll\n"). Ignored if it already exists.
    """
    env_path = Path(env_path) if env_path else default_env_path()
    target_line = f"{key}={value}"

    try:
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                # Ignora linhas comentadas e linhas com chaves diferentes
                if line.lstrip().startswith("#") or not line.strip():
                    continue
                # Same normalization as read/remove: without it, an
                # `export KEY=antigo` was not recognized and persist APPENDED
                # `KEY=novo`, leaving both lines — with read returning the
                # first one, that is, the old one.
                stripped = _sem_export(line)
                if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                    # Preserve the `export ` that was on the line: in a .env that is
                    # `source`d — the reason someone writes `export` —,
                    # swapping it for the bare form would stop the variable from
                    # reaching child processes.
                    prefixo = "export " if line.lstrip().startswith("export ") else ""
                    nova = f"{prefixo}{target_line}"
                    if line == nova:
                        return  # already the same
                    lines[i] = nova
                    break
            else:
                lines.append(target_line)
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            header = file_header or "# Gerado automaticamente.\n"
            env_path.write_text(f"{header}{target_line}\n", encoding="utf-8")
        logger.info("%s persistido em %s", key, env_path)
    except OSError as exc:
        logger.warning(
            "Nao foi possivel persistir %s em %s: %s. Adicione manualmente: %s",
            key, env_path, exc, target_line,
        )


def remove_env_var(key: str, env_path: Path | str | None = None) -> bool:
    """
    Removes the `KEY=...` line from the .env, if it exists. Returns True if it removed something.
    Useful for cleaning up legacy envs (EXECUTOR_API_KEY, EXECUTOR_PRIVATE_KEY_PATH pointing
    to an old path, etc.) during migration.
    """
    env_path = Path(env_path) if env_path else default_env_path()
    if not env_path.exists():
        return False

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
        kept = []
        removed = False
        for line in lines:
            stripped = _sem_export(line)
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                removed = True
                continue
            kept.append(line)
        if removed:
            env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            logger.info("%s removido de %s", key, env_path)
        return removed
    except OSError as exc:
        logger.warning("Nao foi possivel remover %s de %s: %s", key, env_path, exc)
        return False


def normalize_server_url_to_ws(server_url: str) -> str:
    """
    Normalizes the server URL to the WebSocket scheme (`wss://` or `ws://`).

    The executor opens a WebSocket connection — writing `https://` into EXECUTOR_SERVER_URL
    breaks the connect with `scheme isn't ws or wss` from the `websockets` lib.
    Accepts https/http/wss/ws as input; always returns wss/ws.

    Functions that receive `--server=URL` from the operator must call this before
    persisting to .env. The call sites that do HTTP (POST /enroll, etc.)
    must use `_ws_to_http` for the reverse direction.
    """
    s = server_url.strip()
    if s.startswith("https://"):
        return "wss://" + s[len("https://"):]
    if s.startswith("http://"):
        return "ws://" + s[len("http://"):]
    # Already wss/ws, or another scheme — return unchanged.
    return s


def seed_env_from_example(
    env_path: Path | str | None = None,
    example_path: Path | str | None = None,
) -> bool:
    """
    Seeds `env_path` with the content of `example_path` when it has not been
    configured yet.

    Idempotent: if `env_path` already has non-empty content (lines with `KEY=valor`
    outside comments), no-op. If it does not exist or is empty/comments only,
    copies the example. It is the single point of enroll — manual, from the quickstart or
    from the desktop app — to guarantee that every critical variable (EXECUTOR_SERVER_URL,
    LOG_LEVEL, etc.) has a value from the first boot.

    Returns:
        True if the file was seeded in this call, False if it was already OK.
    """
    env_path = Path(env_path) if env_path else default_env_path()
    if example_path is None:
        # The example lives next to the CODE, not next to the `.env`.
        #
        # The default used to be `env_path.parent / ".env.example"`, which only
        # works when the `.env` lives inside the package. With EXECUTOR_ENV_PATH
        # pointing elsewhere — `%APPDATA%\AtlasExecutor\config\.env` in the
        # desktop app — the example did not exist there and the seed became a silent
        # no-op: the `.env` was born without EXECUTOR_SYNC_* or LOG_*,
        # exactly the scenario the docstring above says it wants to avoid.
        example_path = Path(__file__).parent / ".env.example"
    else:
        example_path = Path(example_path)

    if not example_path.exists():
        logger.debug(".env.example nao encontrado em %s — pulando seed.", example_path)
        return False

    # Consider the .env "already configured" if it has at least one non-comment line
    # with `KEY=...`. Avoids overwriting a file customized by the operator.
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.lstrip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    return False  # already has config — preserve it
        except OSError as exc:
            logger.warning("Falha ao ler %s para verificar seed: %s", env_path, exc)
            return False

    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(
            example_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        logger.info(".env semeado a partir de %s", example_path.name)
        return True
    except OSError as exc:
        logger.warning(
            "Nao foi possivel semear %s a partir de %s: %s",
            env_path, example_path, exc,
        )
        return False


def read_env_var(key: str, env_path: Path | str | None = None) -> str | None:
    """Reads the current value of an env var from the file (without applying it to os.environ)."""
    env_path = Path(env_path) if env_path else default_env_path()
    if not env_path.exists():
        return None

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#") or not stripped:
                continue
            stripped = _sem_export(stripped)
            if stripped.startswith(f"{key}="):
                return stripped[len(key) + 1:]
            if stripped.startswith(f"{key} ="):
                return stripped[len(key) + 2:].lstrip()
        return None
    except OSError:
        return None
