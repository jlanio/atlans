"""
Executor version — the one the executors panel shows.

Order of precedence, in `versao_do_executor()`:

1. the one written into the Docker image at build time (`ARQUIVO_DA_IMAGEM`,
   OUTSIDE the code tree: a checkout never has it, so the desktop and the CLI
   do not inherit it). It beats the environment on purpose: old installations
   have `EXECUTOR_VERSION=1.0.0` in `executor/.env`, seeded from `.env.example`,
   and that is why every Docker executor showed up as "v1.0.0";
2. `EXECUTOR_VERSION` from the environment — the desktop app sets it to its own version;
3. "1.0.0".

At build time, `python -m executor.versao <pasta> <destino>` writes the product
version — the desktop app's, `desktop/package.json`; the release passes the tag's
in `EXECUTOR_BASE` — plus the commit: `2.15.0+3f02f44`. The commit comes from the
checkout itself (the Dockerfile copies `.git/HEAD`, `packed-refs` and `refs` into
the folder; .dockerignore lets only that in) or from `EXECUTOR_COMMIT`, which wins.
Without either (build from a tarball), only the product version comes out.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Mapping

ARQUIVO_DA_IMAGEM = Path("/usr/local/share/atlans-executor/VERSAO")
# The server discards versions longer than this (`_EXECUTOR_VERSION_MAX` in
# app/api/routers/executor_ws/protocolo.py) and the panel would show none at all.
MAX_LENGTH = 20
DEFAULT_VERSION = "1.0.0"
_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")   # SHA-1 or SHA-256


def _acceptable(versao: str) -> bool:
    return 0 < len(versao) <= MAX_LENGTH and versao.isprintable()


def versao_do_executor(
    ambiente: Mapping[str, str] | None = None, arquivo: Path | None = None
) -> str:
    """The version the executor declares in the handshake and at enroll (see the order above).

    Tolerant: an unreadable, oversized or garbage file is ignored —
    this runs on import of `executor.config`, and an error here would keep the
    executor from starting.

    `EXECUTOR_VERSION` goes through the same yardstick as the file: enroll validates
    the length (`executor_version`, up to 20 characters) and would reject with 422 a
    long `<versão>+<commit>` from a local build. If too long, the commit is
    shortened as in the build (`compor`); if it cannot be fixed, the default stays.
    """
    ambiente = os.environ if ambiente is None else ambiente
    arquivo = ARQUIVO_DA_IMAGEM if arquivo is None else arquivo
    try:
        gravada = arquivo.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        gravada = ""
    if _acceptable(gravada):
        return gravada
    from_env = (ambiente.get("EXECUTOR_VERSION") or "").strip()
    if _acceptable(from_env):
        return from_env
    if from_env:
        base, _, commit = from_env.partition("+")
        shortened = compor(base, commit or None)
        if shortened:
            return shortened
    return DEFAULT_VERSION


def commit_do_git(pasta: Path) -> str | None:
    """HEAD SHA from the copies of `.git/HEAD`, `.git/packed-refs` and the
    contents of `.git/refs` (`heads/`, `tags/`...) in a single folder — the layout
    that the Dockerfile's `COPY` produces. None if it cannot be determined."""
    try:
        head = (pasta / "HEAD").read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None
    if _SHA.match(head):                               # HEAD destacado
        return head
    if not head.startswith("ref: refs/"):
        return None
    ref = head[len("ref: "):]
    if ".." in ref.split("/"):
        return None
    try:
        # The loose ref beats the packed one: `git pull` only updates the loose one.
        solta = (pasta / ref[len("refs/"):]).read_text(encoding="utf-8").strip()
        if _SHA.match(solta):
            return solta
    except (OSError, ValueError):
        pass
    try:
        for linha in (pasta / "packed-refs").read_text(encoding="utf-8").splitlines():
            partes = linha.split()
            if len(partes) == 2 and partes[1] == ref and _SHA.match(partes[0]):
                return partes[0]
    except (OSError, ValueError):
        pass
    return None


def compor(product_version: str, commit: str | None) -> str:
    """`<versão>+<commit curto>` within the server's limit.

    The hash is shortened (7 → 4 characters) first; if not even the product
    version fits, only the commit remains, which is what identifies the code.
    """
    base = product_version.strip()
    curto = "".join(c for c in (commit or "").strip() if c.isalnum())[:7]
    if base:
        for tamanho in range(len(curto), 3, -1):
            candidate = f"{base}+{curto[:tamanho]}"
            if _acceptable(candidate):
                return candidate
        if _acceptable(base):
            return base
    return curto if _acceptable(curto) else ""


def gravar(
    pasta: Path, destino: Path, *, commit: str | None = None, base: str | None = None,
) -> str | None:
    """Image build: writes the version to `destino` and returns it.

    Never breaks the build: with no acceptable version, it warns and writes
    nothing — the executor falls back to EXECUTOR_VERSION, as before.
    """
    if not base:
        try:
            base = json.loads((pasta / "package.json").read_text(encoding="utf-8"))["version"]
        except (OSError, ValueError, KeyError, TypeError):
            base = ""
    # The release tag is `executor/v1.2.3`; the panel already prepends the "v".
    base = re.sub(r"^[vV](?=\d)", "", str(base).strip())
    versao = compor(base, commit or commit_do_git(pasta))
    if not versao:
        print(f"aviso: sem versão aceitável para o executor (base {base!r}); nada gravado.", file=sys.stderr)
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(versao, encoding="utf-8")
    return versao


if __name__ == "__main__":
    print(gravar(
        Path(sys.argv[1]), Path(sys.argv[2]),
        commit=os.environ.get("EXECUTOR_COMMIT") or None,
        base=os.environ.get("EXECUTOR_BASE") or None,
    ))
