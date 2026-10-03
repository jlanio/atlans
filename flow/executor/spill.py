# flow/executor/spill.py
"""Spill-to-disk for large intermediate outputs (GeoDataFrames > threshold)."""
import os
import uuid
import threading
from typing import Any, Dict
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_SPILL_THRESHOLD_MB = int(os.getenv("SPILL_THRESHOLD_MB", "50"))
_SPILL_BASE_DIR = "/tmp/atlans_spill"

# In-memory cache to avoid re-reading parquet when multiple children
# consume the same spilled output. Thread-safe via lock.
_spill_lock = threading.Lock()
_spill_cache: Dict[str, Any] = {}


def _estimate_gdf_size_mb(gdf) -> float:
    """Estimates a GeoDataFrame's memory usage in MB (shallow — fast)."""
    try:
        return gdf.memory_usage(deep=False).sum() / (1024 * 1024)
    except Exception:
        return 0.0


def _spill_to_disk(task_id: str, node_id: str, outputs: dict) -> dict:
    """Saves large GeoDataFrames to Parquet on disk, replacing them with a reference."""
    if _SPILL_THRESHOLD_MB <= 0 or not task_id:
        return outputs
    import geopandas as gpd

    spill_dir = os.path.join(_SPILL_BASE_DIR, task_id)
    modified = dict(outputs)
    for key, value in outputs.items():
        if not isinstance(value, gpd.GeoDataFrame):
            continue
        size_mb = _estimate_gdf_size_mb(value)
        if size_mb < _SPILL_THRESHOLD_MB:
            continue
        try:
            os.makedirs(spill_dir, exist_ok=True)
            path = os.path.join(spill_dir, f"{node_id}_{key}_{uuid.uuid4().hex[:8]}.parquet")
            value.to_parquet(path, index=False)
            modified[key] = {"__spilled__": True, "__spill_path__": path, "__spill_key__": key}
            logger.info(
                "Spill-to-disk: nó %s, key '%s' (%.1f MB) salvo em %s",
                node_id, key, size_mb, path,
            )
        except Exception as exc:
            logger.warning("Falha no spill-to-disk para nó %s: %s — mantendo em memória.", node_id, exc)
    return modified


def _load_from_disk(outputs: dict) -> dict:
    """Restores GeoDataFrames from spilled references, with an in-memory cache."""
    restored = dict(outputs)
    for key, value in outputs.items():
        if not isinstance(value, dict) or not value.get("__spilled__"):
            continue
        path = value.get("__spill_path__", "")

        # Checks the cache before reading from disk
        with _spill_lock:
            cached = _spill_cache.get(path)
        if cached is not None:
            restored[key] = cached
            logger.debug("Spill cache hit: %s", path)
            continue

        try:
            import geopandas as gpd
            gdf = gpd.read_parquet(path)
            with _spill_lock:
                _spill_cache[path] = gdf
            restored[key] = gdf
            logger.debug("Spill restaurado do disco: %s", path)
        except Exception as exc:
            # Do NOT leave the sentinel reference ({'__spilled__': True, ...}) in
            # `restored`: without this the consuming node would receive the control
            # dict as if it were data and fail in an obscure way (or worse, treat it
            # as a GeoDataFrame). Fails loudly, with the real cause.
            logger.error("Falha ao restaurar spill de %s: %s", path, exc)
            raise RuntimeError(
                f"Falha ao restaurar dados derramados em disco ({path}): {exc}"
            ) from exc
    return restored


def _cleanup_spill(task_id: str, is_nested: bool = False) -> None:
    """Removes a run's spill directory and clears the corresponding cache.

    `is_nested=True` makes the call a no-op: the directory is indexed by
    task_id, which sub-workflows SHARE with the parent (the task_id is propagated
    so that output nodes have scope). Without this guard, the end of the
    sub-workflow deleted the spills the parent was still going to consume — and the
    parent failed to reread its own output. Cleanup is always the responsibility
    of the root executor, which finishes last.
    """
    if not task_id or is_nested:
        return
    import shutil
    spill_dir = os.path.join(_SPILL_BASE_DIR, task_id)

    # Clears the in-memory cache for this task
    with _spill_lock:
        keys_to_remove = [k for k in _spill_cache if k.startswith(spill_dir)]
        for k in keys_to_remove:
            del _spill_cache[k]

    try:
        if os.path.isdir(spill_dir):
            shutil.rmtree(spill_dir, ignore_errors=True)
            logger.debug("Spill cleanup: %s removido.", spill_dir)
    except Exception as exc:
        logger.warning("Falha ao limpar spill dir %s: %s", spill_dir, exc)


def _delete_spill_files(outputs: dict) -> None:
    """Removes the spill files referenced in `outputs` and clears the corresponding cache."""
    for value in outputs.values():
        if isinstance(value, dict) and value.get("__spilled__"):
            path = value.get("__spill_path__", "")
            with _spill_lock:
                _spill_cache.pop(path, None)
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                pass
