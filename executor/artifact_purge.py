# executor/artifact_purge.py
"""
Removal of local artifacts on the server's order (retention).

Artifacts marked with `keepLocal` live only on the executor's disk — the
server keeps only the catalog. When retention expires, the one that has to delete the
file is this machine, because the server has no access to it.

## Threat model

The order arrives over the network, in a `control` that `connection.py` only accepts with
a valid Ed25519 signature from the server. Even so, the path of each file is
treated as HOSTILE input:

  - the path is built from the LOCAL root (`artifacts_root()`), never from a
    received value;
  - the result is confined to that root with `resolve()` + `is_relative_to`;
  - `..`, absolute paths and drive letters are refused before anything
    else.

Without this, `local_path = "../../../../Windows/System32/config/SAM"` would turn
retention cleanup into an arbitrary file deleter — and a compromised server,
or any path-derivation bug on its side, would become data loss
on the customer's machine.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("executor.artifact_purge")


def _seguro(bruto: str) -> bool:
    """Rejects what should not even reach path resolution."""
    if not bruto or not isinstance(bruto, str):
        return False
    normalizado = bruto.replace("\\", "/")
    if normalizado.startswith("/"):
        return False                      # absoluto POSIX
    if len(bruto) >= 2 and bruto[1] == ":":
        return False                      # 'C:\...' — absoluto Windows
    if ".." in normalizado.split("/"):
        return False                      # travessia explicita
    return True


def _sob_a_raiz(local_path: str, raiz: Path) -> Path | None:
    """Resolves `local_path` under an ALREADY resolved root, or None if it escapes it."""
    if not _seguro(local_path):
        return None

    alvo = (raiz / local_path).resolve()
    # Second barrier, after resolve(): covers a symlink pointing outside,
    # which the textual check above does not catch.
    if not alvo.is_relative_to(raiz):
        return None
    return alvo


def _limpar_diretorios_vazios(caminho: Path, raiz: Path) -> None:
    """Walks up removing directories that became empty, without going past the root.

    Without this, `artifacts/` accumulates an empty `<workspace>/<run>/` tree per
    execution, forever.
    """
    pai = caminho.parent
    while pai != raiz and pai.is_relative_to(raiz):
        try:
            pai.rmdir()          # only removes it if it is empty
        except OSError:
            return
        pai = pai.parent


def purgar(itens: list) -> int:
    """Deletes the requested artifacts. Returns how many were removed.

    Never raises: a cleanup failure must not bring down the connection with the
    server nor interrupt jobs in progress.
    """
    from flow.utils.artifact_helpers import artifacts_root

    if not isinstance(itens, list):
        return 0

    raiz = Path(artifacts_root()).resolve()
    removidos = 0

    for item in itens:
        if not isinstance(item, dict):
            continue
        local_path = item.get("local_path") or ""
        id_hash = item.get("id_hash") or "?"

        # The root is resolved ONCE for the whole batch: `purgar` runs in the WebSocket
        # receive loop, and a retention order with hundreds of
        # artifacts paid one `resolve()` of the root per item — a repeated syscall
        # holding up the loop that also delivers the jobs.
        alvo = _sob_a_raiz(local_path, raiz)
        if alvo is None:
            # LOUD refusal: if this happens, either the server has a path-derivation
            # bug, or someone is trying something.
            logger.error(
                "Ordem de remocao RECUSADA para o artefato %s: caminho %r sai do "
                "diretorio de artefatos.", id_hash, local_path,
            )
            continue

        try:
            if alvo.is_file():
                os.unlink(alvo)
                removidos += 1
                _limpar_diretorios_vazios(alvo, raiz)
            # A missing file is not an error: it was already deleted by hand, or the
            # previous order arrived and the server did not record the confirmation.
        except OSError as exc:
            logger.warning("Falha ao remover o artefato local %s (%s): %s", id_hash, alvo, exc)

    return removidos
