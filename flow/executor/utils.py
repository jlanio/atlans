# flow/executor/utils.py
"""Helpers for inspecting and debugging outputs."""
from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _count_gdf_features(data: dict) -> "int | None":
    """Counts the total features in the GeoDataFrames present in an outputs/inputs dict."""
    try:
        import geopandas as gpd
        total = sum(len(v) for v in data.values() if isinstance(v, gpd.GeoDataFrame))
        return total if total > 0 else None
    except Exception as exc:
        logger.debug("Falha ao contar features: %s", exc)
        return None


# Ceiling per output. A wide table (census, raw sensor data) goes past a thousand
# columns; the list goes into node_stats, which is persisted as JSON and returned
# in observability. What matters is feeding column name suggestions, and
# nobody picks among a thousand — truncating here avoids bloating every run's record.
#
# Public because the UI warns that the list was cut when it arrives at the limit.
MAX_COLUMNS = 200


def _geometry_column(valor) -> "str | None":
    """Name of the ACTIVE geometry column, when there is one.

    Ask the GeoDataFrame instead of guessing by name: the geopandas
    default is "geometry", but the database nodes use "geom", and an attribute
    called "geom" in a plain DataFrame is no geometry at all.
    """
    nome = getattr(valor, "_geometry_column_name", None)
    return str(nome) if nome else None


def _output_columns(data: dict) -> "dict | None":
    """ATTRIBUTE columns of each tabular output of a node.

    Exists so the editor stops requiring guesswork: whoever configures a Join or
    a filter needs to know which columns arrive there, and the only way was to
    run it and look at the result. Recorded per execution, it covers ANY node —
    including PythonScript, whose output no static analysis can predict.

    The geometry column is left OUT. The list feeds fields that ask for an
    attribute column name, and geometry is useless for all of them: in the Join,
    bringing it from B collides with A's and the node fails; in the filter,
    comparing geometry with a value also fails. Suggesting what always goes wrong
    is worse than not suggesting.

    Returns None when there is nothing tabular: `node_stats` is per node and per
    run, and an extra key in each of them is paid for in bytes in the database.
    """
    try:
        import pandas as pd

        found = {}
        for chave, valor in (data or {}).items():
            if not isinstance(valor, pd.DataFrame):
                continue
            geometria = _geometry_column(valor)
            nomes = [str(c) for c in valor.columns if str(c) != geometria]
            # Truncate without inventing an item in the list: the cut marker that used
            # to be here ("… (+312)") went along with the columns, and the UI renders
            # EACH item as a clickable suggestion — you could insert the marker as if
            # it were a column name. Whoever displays it infers the cut from the size.
            found[str(chave)] = nomes[:MAX_COLUMNS]
        return found or None
    except Exception as exc:
        logger.debug("Falha ao listar colunas das saidas: %s", exc)
        return None


def _build_debug_summary(data: dict, with_bounds: bool = True) -> dict:
    """Builds a readable summary of inputs/outputs for automatic debug events.

    `with_bounds=False` omits the GeoDataFrame's `total_bounds`: it scans ALL
    geometries (O(n) — 13.6 ms on a GDF of 300k features) and that only pays off
    in the debug event, which is opt-in via `debug_mode`. The per-node log path
    (`_LazySummary`) passes False.
    """
    import json
    resumo: dict = {}
    for key, value in data.items():
        try:
            # GeoDataFrame has total_bounds and crs; a plain DataFrame does not.
            # Tells the two apart so as not to fall into the generic except.
            if hasattr(value, "total_bounds") and hasattr(value, "crs"):
                colunas = list(value.columns)
                crs = str(value.crs) if value.crs else "N/A"
                resumo[key] = (
                    f"GeoDataFrame | {len(value)} registros | "
                    f"CRS: {crs} | colunas: {colunas}"
                )
                if with_bounds:
                    resumo[key] += f" | bounds: {value.total_bounds.tolist()}"
            elif hasattr(value, "to_json") and hasattr(value, "columns"):
                resumo[key] = (
                    f"DataFrame | {len(value)} registros | "
                    f"colunas: {list(value.columns)}"
                )
            elif isinstance(value, dict):
                resumo[key] = f"dict | {len(value)} chaves: {list(value.keys())}"
            elif isinstance(value, list):
                resumo[key] = f"list | {len(value)} itens"
            elif isinstance(value, (str, bytes)):
                # Slice BEFORE serializing. `json.dumps` of a 20 MB body
                # (http_request returns the raw response) materialized the whole
                # 20 MB only to discard everything but 300 chars — measured:
                # 20 MB of peak memory to produce 313 characters.
                trecho = value[:300]
                if isinstance(trecho, bytes):
                    trecho = trecho.decode("utf-8", "replace")
                resumo[key] = trecho + ("…" if len(value) > 300 else "")
            else:
                val_str = json.dumps(value, default=str)
                resumo[key] = val_str[:300] + ("…" if len(val_str) > 300 else "")
        except Exception as e:
            resumo[key] = f"[Erro ao inspecionar]: {e}"
    return resumo
