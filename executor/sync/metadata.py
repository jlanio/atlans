# executor/sync/metadata.py
"""
MetadataExtractor — extracts spatial metadata from datasets.
Uses geopandas for vectors and rasterio for rasters.
"""
import logging
from pathlib import Path
from typing import Any

from executor.utils import classify_dataset_type

logger = logging.getLogger("executor.sync")


def extract_metadata(primary_path: Path, dataset_type: str) -> dict[str, Any]:
    """
    Extracts spatial metadata from a dataset.
    Returns a dict with data_type, geometry_type, crs, feature_count, bbox, columns.
    """
    result: dict[str, Any] = {
        "data_type": classify_dataset_type(dataset_type),
        "file_size": primary_path.stat().st_size,
    }

    if result["data_type"] == "vector":
        result.update(_extract_vector(primary_path))
    elif result["data_type"] == "raster":
        result.update(_extract_raster(primary_path))
    elif result["data_type"] == "tabular":
        result.update(_extract_tabular(primary_path))

    return result


def _extract_vector(path: Path) -> dict:
    try:
        import geopandas as gpd
        gdf_sample = gpd.read_file(path)

        geom_type = None
        if not gdf_sample.empty and gdf_sample.geometry is not None:
            geom_type = gdf_sample.geometry.geom_type.mode().iloc[0] if len(gdf_sample) > 0 else None

        bbox = None
        if not gdf_sample.empty:
            b = gdf_sample.total_bounds  # [minx, miny, maxx, maxy]
            bbox = [round(float(b[0]), 6), round(float(b[1]), 6),
                    round(float(b[2]), 6), round(float(b[3]), 6)]

        crs_str = None
        if gdf_sample.crs:
            crs_str = str(gdf_sample.crs)
            # Tenta extrair EPSG
            try:
                epsg = gdf_sample.crs.to_epsg()
                if epsg:
                    crs_str = f"EPSG:{epsg}"
            except Exception as exc:
                logger.debug("Falha ao converter CRS para EPSG: %s", exc)

        columns = [c for c in gdf_sample.columns if c != "geometry"]

        return {
            "geometry_type": geom_type,
            "crs": crs_str,
            "feature_count": len(gdf_sample),
            "bbox": bbox,
            "columns": columns,
        }
    except Exception as e:
        logger.warning("Falha ao extrair metadados vetoriais de '%s': %s", path, e)
        return {}


def _extract_raster(path: Path) -> dict:
    try:
        import rasterio
        with rasterio.open(path) as src:
            crs_str = None
            if src.crs:
                try:
                    crs_str = f"EPSG:{src.crs.to_epsg()}" if src.crs.to_epsg() else str(src.crs)
                except Exception:
                    crs_str = str(src.crs)

            b = src.bounds
            return {
                "crs": crs_str,
                "bbox": [round(b.left, 6), round(b.bottom, 6), round(b.right, 6), round(b.top, 6)],
                "width": src.width,
                "height": src.height,
                "bands": src.count,
                "dtype": str(src.dtypes[0]) if src.dtypes else None,
            }
    except ImportError:
        logger.debug("rasterio nao instalado — metadados raster indisponiveis.")
        return {}
    except Exception as e:
        logger.warning("Falha ao extrair metadados raster de '%s': %s", path, e)
        return {}


def _extract_tabular(path: Path) -> dict:
    try:
        import pandas as pd
        ext = path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(path, nrows=0)
        elif ext == ".xlsx":
            df = pd.read_excel(path, nrows=0)
        else:
            return {}

        # Conta linhas (rapido com wc approach)
        row_count = None
        if ext == ".csv":
            with open(path, "r") as f:
                row_count = sum(1 for _ in f) - 1  # -1 header

        return {
            "columns": list(df.columns),
            "feature_count": row_count,
        }
    except Exception as e:
        logger.warning("Falha ao extrair metadados tabulares de '%s': %s", path, e)
        return {}
