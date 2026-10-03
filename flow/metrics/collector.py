# flow/metrics/collector.py
"""
ResourceTracker — collects CPU and memory via psutil.
MetricsCollector — aggregates metrics per node and per run.
"""
import math
import os
import sys
import threading
import time
import logging
from typing import Any

logger = logging.getLogger("flow.metrics")


def _bbox_finito(gdf) -> list[float] | None:
    """The GeoDataFrame's bounding box, or None when it is not representable.

    An EMPTY GeoDataFrame has `total_bounds == [nan, nan, nan, nan]`, and
    `round(float('nan'), 6)` returns nan without raising — so the try/except
    protected nothing. That nan traveled in the stats up to `WorkflowRun.node_stats`,
    which is JSONB: NaN does not exist in JSON and Postgres rejects the INSERT. The
    whole run's result went to run_dead_letter and the status got stuck at 'running',
    even though the workflow had finished — it happened whenever a spatial
    filter returned no features at all.
    """
    try:
        b = gdf.total_bounds
        valores = [float(b[i]) for i in range(4)]
    except Exception as exc:
        logger.debug("Falha ao calcular bbox: %s", exc)
        return None

    if not all(math.isfinite(v) for v in valores):
        return None
    return [round(v, 6) for v in valores]


class ResourceTracker:
    """Collects CPU and memory samples of the current process."""

    def __init__(self):
        import psutil

        self._samples: list[dict] = []
        # The (shared) run_tracker is sampled at the end of EACH node, and end_node
        # now runs in `asyncio.to_thread` — several nodes of the same batch
        # sample concurrently. Without the lock, `_samples.append` collided with
        # the iteration in `summary()` ("list changed size during iteration") and
        # the psutil.Process was touched from two threads. Each tracker has its own.
        self._lock = threading.Lock()
        self._proc = psutil.Process(os.getpid())
        # Inicializa medicao de CPU (primeiro chamado retorna 0)
        self._proc.cpu_percent()

    def sample(self):
        """Captures one CPU and memory sample."""
        try:
            # Everything under the lock: the shared psutil.Process keeps state between
            # `cpu_percent()` calls, so two concurrent `sample()` calls on the
            # run_tracker have to be serialized (the syscalls are fast).
            with self._lock:
                self._samples.append({
                    "cpu_pct": self._proc.cpu_percent(),
                    "mem_mb": self._proc.memory_info().rss / (1024 * 1024),
                    "ts": time.time(),
                })
        except Exception as exc:
            logger.debug("Falha ao capturar amostra de CPU/memória: %s", exc)

    def summary(self) -> dict:
        """Retorna resumo de CPU e memoria."""
        with self._lock:
            if not self._samples:
                return {}
            cpus = [s["cpu_pct"] for s in self._samples]
            mems = [s["mem_mb"] for s in self._samples]
        return {
            "cpu_avg_pct": round(sum(cpus) / len(cpus), 2),
            "cpu_peak_pct": round(max(cpus), 2),
            "mem_avg_mb": round(sum(mems) / len(mems), 2),
            "mem_peak_mb": round(max(mems), 2),
            "samples": len(cpus),
        }


def estimate_size(obj: Any) -> int:
    """Estimates the size in bytes of an object.

    PERF: uses memory_usage(deep=False) for GeoDataFrames — avoids iterating
    over every value of every column. Estimate ~10x faster, ~80% accuracy.
    """
    import pandas as pd

    # GeoDataFrame is a subclass of DataFrame: the same branch covers both.
    if isinstance(obj, pd.DataFrame):
        return int(obj.memory_usage(deep=False).sum())
    if isinstance(obj, (dict, list, str, bytes)):
        try:
            return sys.getsizeof(obj)
        except Exception:
            pass
    return 0


def extract_spatial_metrics(obj: Any) -> dict:
    """Extrai metricas espaciais de um GeoDataFrame."""
    try:
        import geopandas as gpd
        if not isinstance(obj, gpd.GeoDataFrame) or obj.empty:
            return {}

        geom_types = obj.geometry.geom_type.value_counts().to_dict()

        total_vertices = 0
        try:
            for g in obj.geometry:
                if g is None:
                    continue
                if hasattr(g, "geoms"):
                    for sub in g.geoms:
                        if hasattr(sub, "exterior"):
                            total_vertices += len(sub.exterior.coords)
                        elif hasattr(sub, "coords"):
                            total_vertices += len(sub.coords)
                elif hasattr(g, "exterior"):
                    total_vertices += len(g.exterior.coords)
                elif hasattr(g, "coords"):
                    total_vertices += len(g.coords)
        except Exception as exc:
            logger.debug("Falha ao contar vértices de geometrias: %s", exc)

        crs_str = None
        if obj.crs:
            try:
                epsg = obj.crs.to_epsg()
                crs_str = f"EPSG:{epsg}" if epsg else str(obj.crs)
            except Exception:
                crs_str = str(obj.crs)

        bbox = _bbox_finito(obj)

        return {
            "geometry_types": geom_types,
            "crs": crs_str,
            "bbox": bbox,
            "feature_count": len(obj),
            "vertex_count": total_vertices,
        }
    except Exception as exc:
        logger.debug("Falha ao extrair métricas espaciais: %s", exc)
        return {}


def _extract_lightweight_metrics(gdf) -> dict:
    """Fast O(1) spatial metrics: crs, bbox, feature_count. No vertex_count."""
    result: dict = {"feature_count": len(gdf)}
    try:
        if gdf.crs:
            epsg = gdf.crs.to_epsg()
            result["crs"] = f"EPSG:{epsg}" if epsg else str(gdf.crs)
    except Exception:
        pass
    bbox = _bbox_finito(gdf)
    if bbox is not None:
        result["bbox"] = bbox
    return result


class NodeMetrics:
    """Metrics collected for an individual node."""

    def __init__(self, node_id: str, node_name: str, node_type: str):
        self.node_id = node_id
        self.node_name = node_name
        self.node_type = node_type
        self.started_at: float = 0
        self.duration_ms: float = 0
        self.status: str = "pending"
        self.error: str | None = None

        self.cpu_avg_pct: float = 0
        self.mem_peak_mb: float = 0
        self.input_bytes: int = 0
        self.output_bytes: int = 0
        self.input_features: int | None = None
        self.output_features: int | None = None
        self.spatial: dict = {}

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "cpu_avg_pct": self.cpu_avg_pct,
            "mem_peak_mb": self.mem_peak_mb,
            "input_bytes": self.input_bytes,
            "output_bytes": self.output_bytes,
            "input_features": self.input_features,
            "output_features": self.output_features,
            "spatial": self.spatial if self.spatial else None,
        }


class MetricsCollector:
    """Aggregates the metrics of all nodes of a run."""

    def __init__(self):
        self.run_tracker = ResourceTracker()
        self.node_metrics: dict[str, NodeMetrics] = {}
        self._node_trackers: dict[str, ResourceTracker] = {}

    def start_node(self, node_id: str, node_name: str, node_type: str):
        nm = NodeMetrics(node_id, node_name, node_type)
        nm.started_at = time.time()
        self.node_metrics[node_id] = nm
        tracker = ResourceTracker()
        tracker.sample()
        self._node_trackers[node_id] = tracker

    def end_node(self, node_id: str, inputs: dict, outputs: Any, status: str,
                 duration_ms: float, error: str | None = None,
                 debug_mode: bool = False):
        nm = self.node_metrics.get(node_id)
        if not nm:
            return

        nm.duration_ms = duration_ms
        nm.status = status
        nm.error = error

        # Node resources
        tracker = self._node_trackers.get(node_id)
        if tracker:
            tracker.sample()
            summary = tracker.summary()
            nm.cpu_avg_pct = summary.get("cpu_avg_pct", 0)
            nm.mem_peak_mb = summary.get("mem_peak_mb", 0)

        # Run sample
        self.run_tracker.sample()

        # PERF: single pass over inputs — bytes + features in one iteration
        import geopandas as gpd

        for v in inputs.values():
            nm.input_bytes += estimate_size(v)
            if isinstance(v, gpd.GeoDataFrame):
                nm.input_features = (nm.input_features or 0) + len(v)

        # PERF: single pass over outputs — bytes + features + spatial in one iteration
        if outputs is not None:
            out_items = outputs.values() if isinstance(outputs, dict) else [outputs]
            for v in out_items:
                nm.output_bytes += estimate_size(v)
                if isinstance(v, gpd.GeoDataFrame):
                    nm.output_features = (nm.output_features or 0) + len(v)
                    nm.spatial = extract_spatial_metrics(v) if debug_mode else _extract_lightweight_metrics(v)

    def build_metrics(self) -> dict:
        """Builds the complete __metrics__ dict to include in the stats."""
        run_summary = self.run_tracker.summary()
        nodes_data = {}
        operation_types: dict[str, int] = {}
        total_input = 0
        total_output = 0
        total_features = 0
        nodes_failed = 0
        all_crs: set[str] = set()
        all_geom_types: dict[str, int] = {}

        for nid, nm in self.node_metrics.items():
            nodes_data[nid] = nm.to_dict()
            total_input += nm.input_bytes
            total_output += nm.output_bytes
            total_features += (nm.output_features or 0)
            if nm.status == "failed":
                nodes_failed += 1

            # Operation types
            op = nm.node_name
            operation_types[op] = operation_types.get(op, 0) + 1

            # Spatial aggregation
            if nm.spatial:
                if nm.spatial.get("crs"):
                    all_crs.add(nm.spatial["crs"])
                for gt, count in nm.spatial.get("geometry_types", {}).items():
                    all_geom_types[gt] = all_geom_types.get(gt, 0) + count

        return {
            "run": {
                **run_summary,
                "input_bytes": total_input,
                "output_bytes": total_output,
                "nodes_executed": len(self.node_metrics),
                "nodes_failed": nodes_failed,
                "operation_types": operation_types,
                "total_features": total_features,
            },
            "nodes": nodes_data,
            "spatial_summary": {
                "crs_used": list(all_crs),
                "geometry_types": all_geom_types,
            } if all_crs or all_geom_types else None,
        }
