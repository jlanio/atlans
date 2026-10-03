# executor/sync/scanner.py
"""
DatasetScanner — agrupa arquivos locais em datasets espaciais.
Trata Shapefile como pacote logico (shp+dbf+shx+prj+cpg).
"""
import hashlib
import logging
import time
from pathlib import Path

from executor.sync.paths import TRASH_DIR_NAME

logger = logging.getLogger("executor.sync")

# Shapefile component extensions
_SHP_EXTENSIONS = {".shp", ".dbf", ".shx", ".prj", ".cpg", ".sbn", ".sbx", ".fbn", ".fbx", ".ain", ".aih", ".ixs", ".mxs", ".atx", ".qpj"}
_SHP_REQUIRED = {".shp", ".dbf", ".shx"}

# Extensoes suportadas para sync (arquivos unicos)
_SINGLE_FILE_EXTENSIONS = {
    ".geojson", ".json", ".gpkg", ".kml", ".kmz",
    ".tiff", ".tif", ".csv", ".xlsx",
    ".zip", ".gml", ".fgb", ".parquet",
}

# Everything the sync recognizes
SUPPORTED_EXTENSIONS = _SINGLE_FILE_EXTENSIONS | _SHP_EXTENSIONS

# Arquivos/pastas ignorados
_IGNORE_NAMES = {".atlans-sync.json", ".DS_Store", "Thumbs.db", "__pycache__", ".git", TRASH_DIR_NAME}


class Dataset:
    """Represents a spatial dataset (may be 1 file or a Shapefile bundle)."""

    def __init__(self, name: str, dataset_type: str):
        self.name = name
        self.type = dataset_type  # "shapefile" | "geojson" | "gpkg" | "csv" | "tiff" | etc
        self.files: dict[str, FileInfo] = {}  # filename → FileInfo
        self.is_complete = True

    def add_file(self, file_info: "FileInfo"):
        self.files[file_info.filename] = file_info

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files.values())

    @property
    def primary_path(self) -> Path | None:
        """Returns the path of the main file (e.g. .shp for Shapefile, .geojson for GeoJSON)."""
        if self.type == "shapefile":
            for f in self.files.values():
                if f.path.suffix.lower() == ".shp":
                    return f.path
        elif self.files:
            return next(iter(self.files.values())).path
        return None

    def file_hashes(self) -> dict[str, str]:
        return {name: f.md5 for name, f in self.files.items()}


class FileInfo:
    """Information about an individual file."""

    def __init__(self, path: Path):
        st = path.stat()  # um stat so: o segundo era I/O puro em vao
        self.path = path
        self.filename = path.name
        self.extension = path.suffix.lower()
        self.size = st.st_size
        self.mtime = st.st_mtime
        # When this stat was taken. It is what makes the (size, mtime) pair a
        # reliable WITNESS of "unchanged" — see `_trustworthy_witness`.
        self.stat_at = time.time()
        self._md5: str | None = None

    @property
    def md5(self) -> str:
        if self._md5 is None:
            self._md5 = _compute_md5(self.path)
        return self._md5

    def seed_md5(self, valor: str) -> None:
        """Adopts the MD5 the manifest already held for this file.

        Only called when (size, mtime) match the manifest — that is, when the
        diff has already concluded the file didn't change. Without this,
        `_dataset_md5()` further on would reread from disk what we just
        decided not to reread.
        """
        self._md5 = valor

    def to_dict(self) -> dict:
        return {
            "md5": self.md5,
            "size": self.size,
            "mtime": self.mtime,
            "stat_at": self.stat_at,
        }


class DatasetScanner:
    """Escaneia uma pasta e agrupa arquivos em datasets espaciais."""

    def __init__(self, sync_dir: str, ignore_filter=None):
        self.sync_dir = Path(sync_dir)
        self._ignore = ignore_filter

    def scan(self) -> dict[str, Dataset]:
        """Returns a name → Dataset dict with all the datasets found."""
        datasets: dict[str, Dataset] = {}
        shp_groups: dict[str, list[FileInfo]] = {}  # stem → arquivos

        for file_path in self.sync_dir.iterdir():
            # Symlinks NEVER enter the sync. The upload has no `safe_join` like the
            # download does, so a link planted in the folder (e.g.
            # 'pontos.csv' → /opt/atlans/executor/certs/client.key) would publish
            # an outside file to the workspace Drive — the validator doesn't even
            # open .csv/.xlsx and the shapefile bundle is zipped without any
            # content check. This closes PATH ESCAPE, not content provenance: a
            # hardlink is still invisible here (is_symlink() is False) and no
            # path check would catch it — whoever can link can already copy the
            # same bytes into the folder.
            if file_path.is_symlink():
                logger.warning("Symlink '%s' ignorado pelo sync (aponta para fora do controle da pasta).",
                               file_path.name)
                continue
            if not file_path.is_file():
                continue
            if file_path.name in _IGNORE_NAMES or file_path.name.startswith("."):
                continue
            if self._ignore and self._ignore.should_ignore(file_path):
                continue

            ext = file_path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            # QGIS (and the like) creates and removes temp files all the time: the file
            # may vanish between iterdir() and the FileInfo's stat(). That is
            # normal, not a sync error — skip instead of killing the whole scan.
            try:
                info = FileInfo(file_path)
            except OSError as exc:
                logger.debug("Arquivo '%s' indisponivel durante o scan (%s) — ignorado.", file_path.name, exc)
                continue

            if ext in _SHP_EXTENSIONS:
                # Groups by stem (name without extension)
                stem = file_path.stem.lower()
                shp_groups.setdefault(stem, []).append(info)
            elif ext in _SINGLE_FILE_EXTENSIONS:
                # Single-file dataset
                ds_name = file_path.stem.lower()
                ds_type = ext.lstrip(".")
                if ds_type in ("tiff", "tif"):
                    ds_type = "raster"
                elif ds_type in ("csv", "xlsx"):
                    ds_type = "tabular"
                ds = Dataset(ds_name, ds_type)
                ds.add_file(info)
                datasets[ds_name] = ds

        # Processes Shapefile groups
        for stem, files in shp_groups.items():
            ds = Dataset(stem, "shapefile")
            extensions_found = set()
            for f in files:
                ds.add_file(f)
                extensions_found.add(f.extension)

            # Verifica completude (minimo: .shp + .dbf + .shx)
            ds.is_complete = _SHP_REQUIRED.issubset(extensions_found)
            if not ds.is_complete:
                missing = _SHP_REQUIRED - extensions_found
                logger.warning("Shapefile '%s' incompleto — faltam: %s", stem, missing)

            datasets[stem] = ds

        return datasets

    def diff(self, current: dict[str, Dataset], manifest_datasets: dict,
             force_hash: bool = False) -> tuple[list, list, list]:
        """
        Compares the current state with the manifest.
        Returns (new, modified, removed) as lists of dataset names.

        For datasets present on BOTH sides, the verdict comes from (size,
        mtime) — which the manifest already held and `scan()` just read in
        `stat()`. Before, the diff asked for the MD5 of everything every cycle
        (30s by default): in a field folder with rasters, the disk stayed at
        100% read permanently without ANY file having changed.

        `force_hash=True` ignores the shortcut and rehashes everything — it is
        the safety net against a rewrite that preserves mtime (copy with
        `-p`), used at boot and hourly by the cycle.
        """
        new_datasets = []
        modified_datasets = []
        removed_datasets = []

        current_names = set(current.keys())
        manifest_names = set(manifest_datasets.keys())

        # Novos
        for name in current_names - manifest_names:
            ds = current[name]
            if ds.type == "shapefile" and not ds.is_complete:
                continue  # Doesn't sync an incomplete shapefile
            new_datasets.append(name)

        # Removidos
        for name in manifest_names - current_names:
            removed_datasets.append(name)

        # Modificados
        for name in current_names & manifest_names:
            ds = current[name]
            manifest_ds = manifest_datasets[name]
            manifest_files = manifest_ds.get("files", {})

            if not force_hash and _metadata_unchanged(ds, manifest_files):
                continue  # atalho barato: nem abriu o arquivo

            # Here the hash is mandatory: (size, mtime) diverged and it is what
            # separates a real edit from a `touch` — without this confirmation,
            # opening the file in QGIS would be enough to re-send everything.
            current_hashes = _current_hashes(ds)
            if current_hashes is None:
                continue
            manifest_hashes = {fname: info.get("md5") for fname, info in manifest_files.items()}

            if current_hashes != manifest_hashes:
                modified_datasets.append(name)
            else:
                _renew_witness(ds, manifest_files)

        return new_datasets, modified_datasets, removed_datasets


# Worst mtime granularity seen in the field: FAT32/exFAT on USB sticks and
# external HDDs record the modification time in 2-second steps.
_MTIME_GRANULARITY_S = 2.0


def _trustworthy_witness(gravado: dict) -> bool:
    """Can the recorded (size, mtime) pair WITNESS that the file didn't change?

    It can only if, at the moment it was collected, the file's mtime was
    already "closed". On a coarse-mtime FS (FAT32/exFAT: 2s), a write made
    right AFTER our stat falls into the SAME mtime bucket — and since the DBF
    record has a fixed width, editing a shapefile attribute in QGIS rewrites
    only the .dbf without changing its size. Result: identical size and mtime
    for every component, the shortcut concludes "unchanged" and the user's
    file NEVER gets uploaded (the hourly full scan was the only net).

    Two ways out:
      * mtime with a fractional part → the FS has sub-second resolution and
        the collision window is milliseconds; it doesn't exist in practice;
      * otherwise, the stat is required to have been taken at least one
        granularity AFTER the mtime — then any later write necessarily falls
        into a different bucket and the shortcut is safe again.

    An entry without `stat_at` (manifest written before this field) has no
    way to prove anything: it rehashes once and `_renew_witness`
    re-anchors it.
    """
    mtime = gravado["mtime"]
    if mtime % 1:
        return True
    stat_at = gravado.get("stat_at")
    if stat_at is None:
        return False
    return (stat_at - mtime) >= _MTIME_GRANULARITY_S


def _metadata_unchanged(ds: Dataset, manifest_files: dict) -> bool:
    """Do the (size, mtime) of ALL files match the manifest?

    All-or-nothing on purpose: seeding the MD5 of some files and hashing the
    rest would produce a half-stale combined hash, which would end up written
    to the manifest as if it were the current state of the disk.
    """
    if set(ds.files) != set(manifest_files):
        return False

    for fname, finfo in ds.files.items():
        gravado = manifest_files[fname]
        if not isinstance(gravado, dict):
            return False
        stored_md5 = gravado.get("md5")
        # An old manifest (or an entry written without stat) has nothing to
        # compare with — falls back to the hash.
        if not stored_md5 or gravado.get("size") is None or gravado.get("mtime") is None:
            return False
        if finfo.size != gravado["size"] or finfo.mtime != gravado["mtime"]:
            return False
        if not _trustworthy_witness(gravado):
            return False

    for fname, finfo in ds.files.items():
        finfo.seed_md5(manifest_files[fname]["md5"])
    return True


def _renew_witness(ds: Dataset, manifest_files: dict) -> None:
    """Re-anchors (size, mtime, stat_at) after the HASH confirms the content
    is the same.

    Without this, a `touch` — or an entry written by an old version, without
    `stat_at`, or collected too early on a USB stick — doomed the dataset to
    be rehashed every cycle: nothing changes, nothing is sent and, therefore,
    nobody rewrites the manifest entry. Here the mutation is on the
    manifest's live dict; the end-of-cycle flush persists it. If it is lost,
    the only cost is one more hash on the next cycle.
    """
    for fname, finfo in ds.files.items():
        gravado = manifest_files.get(fname)
        if isinstance(gravado, dict):
            gravado["size"] = finfo.size
            gravado["mtime"] = finfo.mtime
            gravado["stat_at"] = finfo.stat_at


def manifest_entry(path: Path, md5: str) -> dict:
    """'files' entry for a file that WE just wrote (download).

    Goes through `FileInfo` so the witness format (size/mtime/stat_at) has a
    single home: built by hand at each download point, forgetting `stat_at`
    was enough to get the dataset rehashed every cycle.
    """
    info = FileInfo(path)
    info.seed_md5(md5)
    return info.to_dict()


def _current_hashes(ds: Dataset) -> dict[str, str] | None:
    """MD5 of all the dataset's files, or None if any could not be read.

    `scan()` already handles the temp file that vanishes between `iterdir` and
    `stat`; here the window is much larger, because the hash OPENS every file
    — and in the hourly full scan that is the whole folder. A single file
    that vanished (QGIS/ArcGIS create and remove temp files all the time) or
    that was locked killed the cycle with OSError, and with it change
    detection for the whole folder. Without being able to read, there is no
    safe verdict to give: the dataset is left for the next cycle, when the
    scan will see the folder as it ended up.
    """
    try:
        return ds.file_hashes()
    except OSError as exc:
        logger.info("Dataset '%s' nao pode ser lido agora (%s) — veredito adiado "
                    "para o proximo ciclo.", ds.name, exc)
        return None


# MD5 read chunk. 8 KB paid for one read call every 8 KB of raster; the
# uploader already read in 1 MB.
_CHUNK = 1024 * 1024


def _compute_md5(path: Path) -> str:
    """Computes a file's MD5."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
