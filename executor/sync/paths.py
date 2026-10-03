# executor/sync/paths.py
"""
Safe path resolution inside the sync directory.

The file name used as a download destination comes from the server
(`WorkspaceFile.original_name`, originally typed by a user at upload).
Treating that value as a trusted path allowed escaping sync_dir with `../`,
with an absolute path (`/etc/x.geojson`, `C:\\Windows\\x.geojson`) or
through a symlink planted inside the folder — turning into arbitrary file
write/removal on the executor host.

The server also sanitizes at ingestion, but the executor must NOT rely on it:
it trusts the server for *what to execute*, not for *where to write*.
"""
import logging
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from executor.utils import ocultar_no_windows

logger = logging.getLogger("executor.sync")

# Local sync trash. A deletion in Drive must not become an `unlink()` on the
# technician's disk: there is no OS trash on that path, no recovery re-download
# and a shapefile loses .shp/.dbf/.shx all at once. We move things here instead
# of deleting them. It lives INSIDE sync_dir so the move is a rename on the
# same volume (atomic and cheap), and the scanner/watcher explicitly ignore
# this name so the trash doesn't become a re-upload loop.
TRASH_DIR_NAME = ".atlans-trash"

# Since the trash lives inside sync_dir, it eats the same quota on the field
# laptop and is invisible to the technician (dot name on Linux/macOS and hidden
# attribute on Windows — see `move_dataset_to_trash`; ignored by scanner and
# watcher). Without a purge, a folder with normal turnover — a daily raster
# replaced in Drive — fills the disk in weeks, and the only symptom would be
# manifest.py's 'Erro ao salvar manifesto' (error saving manifest).
TRASH_RETENTION_DAYS = 14
TRASH_WARN_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB acumulados → avisa o painel

# Discard folder label: the manifest key becomes a directory name, and the
# manifest is a file on disk that may have been edited by hand.
_TRASH_LABEL_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class UnsafePathError(ValueError):
    """File name tried to escape the sync directory."""


def safe_join(base: Path, name: str) -> Path:
    """
    Returns `base/name` ensuring the result stays INSIDE `base`.

    Raises UnsafePathError if `name` contains directory components, is
    absolute, or if the resolved path escapes the base (including via symlink).
    """
    if not name or name in (".", ".."):
        raise UnsafePathError(f"Nome de arquivo invalido: {name!r}")

    # Any path separator is refused — the sync is flat by design.
    normalized = name.replace("\\", "/")
    if "/" in normalized:
        raise UnsafePathError(f"Nome de arquivo contem separador de caminho: {name!r}")

    candidate = base / normalized
    try:
        base_resolved = base.resolve()
        # strict=False: the destination file doesn't exist yet on download.
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise UnsafePathError(f"Falha ao resolver caminho para {name!r}: {exc}") from exc

    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise UnsafePathError(
            f"Caminho {name!r} escapa do diretorio de sync ({resolved} fora de {base_resolved})."
        )
    return resolved


def safe_join_or_none(base: Path, name: str, *, context: str = "") -> Path | None:
    """Variant that logs and returns None instead of raising — for sync loops."""
    try:
        return safe_join(base, name)
    except UnsafePathError as exc:
        logger.error(
            "Caminho rejeitado%s: %s",
            f" ({context})" if context else "", exc,
        )
        return None


def is_inside(base: Path, path: Path) -> bool:
    """
    Confirms that `path`, ALREADY RESOLVED (symlinks followed), is inside `base`.

    Used for UPLOAD containment: the download always went through `safe_join`,
    but the upload had no containment at all — a symlink planted in the sync
    folder (`ln -s /opt/atlans/executor/certs/client.key pontos.csv`) published
    an outside file to the workspace Drive. Requires the file to exist
    (strict=True): we only upload what we can actually resolve.

    SCOPE: this is PATH containment, not content provenance. A hardlink still
    gets through (`resolve()` doesn't undo it and `is_symlink()` is False), and
    no containment is possible against it — whoever can create the hardlink
    can already copy the file into the folder, which would publish exactly the
    same bytes. What we guarantee is that the executor only reads bytes from
    inside sync_dir.
    """
    try:
        resolved = path.resolve(strict=True)
        base_resolved = base.resolve()
    except OSError:
        return False
    return resolved == base_resolved or base_resolved in resolved.parents


def _trash_label(ds_name: str) -> str:
    label = _TRASH_LABEL_UNSAFE.sub("_", ds_name).strip("._")
    return (label or "dataset")[:60]


def move_dataset_to_trash(sync_dir: Path, ds_name: str, files: Iterable[Path]) -> list[Path]:
    """
    Moves the files of ONE dataset to `<sync_dir>/.atlans-trash/<ds>_<stamp>/`,
    preserving the original names. Returns the list of those that could NOT be
    moved (empty = complete discard).

    The discard is per DATASET, not per file, because a shapefile is only
    usable if .shp/.dbf/.shx share the same stem — and "a shapefile loses
    .shp/.dbf/.shx all at once" was precisely the trash's reason to exist.
    Stamping each file individually broke the bundle in two ways: the stamp
    has one-second granularity (a loop over components of hundreds of MB
    crosses the boundary) and the anti-collision counter was independent per
    file. One subfolder per discard solves stem, collision, and also gives the
    age-based purge a natural unit.
    """
    alvos = [p for p in files]
    if not alvos:
        return []

    trash = sync_dir / TRASH_DIR_NAME
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    label = _trash_label(ds_name)
    try:
        trash.mkdir(parents=True, exist_ok=True)
        # On Windows the dot in the name doesn't hide the folder; without the hidden
        # attribute the trash would show up among the user's data. Reapplied on
        # every discard because mkdir(exist_ok=True) doesn't report whether the
        # folder already existed, and hiding an already hidden folder is a no-op.
        ocultar_no_windows(trash)
        dest_dir = trash / f"{label}_{stamp}"
        counter = 1
        while dest_dir.exists():
            dest_dir = trash / f"{label}_{stamp}_{counter}"
            counter += 1
        dest_dir.mkdir()
    except OSError as exc:
        logger.error("Falha ao criar a pasta de lixeira de '%s': %s", ds_name, exc)
        return alvos

    falhos: list[Path] = []
    for path in alvos:
        try:
            path.replace(dest_dir / path.name)
        except OSError as exc:
            logger.error("Falha ao mover '%s' para a lixeira: %s", path.name, exc)
            falhos.append(path)
    return falhos


def _size_of(path: Path) -> int:
    if path.is_dir():
        total = 0
        for sub in path.rglob("*"):
            try:
                if sub.is_file():
                    total += sub.stat().st_size
            except OSError:
                continue
        return total
    try:
        return path.stat().st_size
    except OSError:
        return 0


def purge_trash(sync_dir: Path, max_age_days: int = TRASH_RETENTION_DAYS) -> tuple[int, int]:
    """
    Removes discards older than `max_age_days` days. Synchronous (disk I/O):
    the caller runs it in a thread. Returns (descartes_removidos, bytes_restantes).
    """
    trash = sync_dir / TRASH_DIR_NAME
    if not trash.is_dir():
        return 0, 0

    limite = time.time() - max_age_days * 86400
    removidos = 0
    restantes = 0
    for item in trash.iterdir():
        try:
            if item.stat().st_mtime < limite:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                removidos += 1
                continue
            restantes += _size_of(item)
        except OSError as exc:
            logger.debug("Lixeira: '%s' nao pode ser inspecionado (%s).", item.name, exc)
    return removidos, restantes
