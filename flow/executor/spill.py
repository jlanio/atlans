# flow/executor/spill.py
"""Spill-to-disk para outputs intermediários grandes (GeoDataFrames > threshold)."""
import os
import uuid
import threading
from typing import Any, Dict
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_SPILL_THRESHOLD_MB = int(os.getenv("SPILL_THRESHOLD_MB", "50"))
_SPILL_BASE_DIR = "/tmp/atlans_spill"

# Cache em memória para evitar re-leitura de parquet quando múltiplos filhos
# consomem o mesmo output spilled. Thread-safe via lock.
_spill_lock = threading.Lock()
_spill_cache: Dict[str, Any] = {}


def _estimate_gdf_size_mb(gdf) -> float:
    """Estima o uso de memória de um GeoDataFrame em MB (shallow — rápido)."""
    try:
        return gdf.memory_usage(deep=False).sum() / (1024 * 1024)
    except Exception:
        return 0.0


def _spill_to_disk(task_id: str, node_id: str, outputs: dict) -> dict:
    """Salva GeoDataFrames grandes em Parquet no disco, substituindo por referência."""
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
    """Restaura GeoDataFrames de referências spilled, com cache em memória."""
    restored = dict(outputs)
    for key, value in outputs.items():
        if not isinstance(value, dict) or not value.get("__spilled__"):
            continue
        path = value.get("__spill_path__", "")

        # Verifica cache antes de ler do disco
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
            # NAO deixar a referencia sentinela ({'__spilled__': True, ...}) em
            # `restored`: sem isto o no consumidor receberia o dict de controle
            # como se fosse dado e falharia de forma obscura (ou pior, o trataria
            # como GeoDataFrame). Falha alto, com a causa real.
            logger.error("Falha ao restaurar spill de %s: %s", path, exc)
            raise RuntimeError(
                f"Falha ao restaurar dados derramados em disco ({path}): {exc}"
            ) from exc
    return restored


def _cleanup_spill(task_id: str, is_nested: bool = False) -> None:
    """Remove diretório de spill de uma execução e limpa cache correspondente.

    `is_nested=True` torna a chamada um no-op: o diretório é indexado por
    task_id, que sub-workflows COMPARTILHAM com o pai (o task_id é propagado
    para que os nodes de saída tenham escopo). Sem essa guarda, o fim do
    sub-fluxo apagava os spills que o pai ainda ia consumir — e o pai falhava
    ao reler o próprio output. A limpeza é sempre responsabilidade do executor
    raiz, que termina por último.
    """
    if not task_id or is_nested:
        return
    import shutil
    spill_dir = os.path.join(_SPILL_BASE_DIR, task_id)

    # Limpa cache em memória para este task
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
    """Remove os arquivos de spill referenciados em `outputs` e limpa o cache correspondente."""
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
