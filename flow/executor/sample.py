# flow/executor/sample.py
"""Data sample of a node's outputs, for the editor's Entradas/Saídas panels.

The editor never had the data: the panels showed key and column names only, and
to see a value the person had to save the result somewhere and open it outside.
With `data_preview` on (runs started from the editor, see
docs/specs/node-data-panels.md), each node that completes sends this sample in a
`sample` event of its own.

Pure and bounded on purpose:
- no I/O, so it is tested in isolation and runs in a thread;
- the first `max_rows` rows only (`head`), never a scan of the whole frame;
  geometries are summarized (type, vertex count, a short WKT), never serialized;
- the result is MEASURED serialized against `budget_bytes` and cut until it
  fits, so the event stays under the protocol ceiling
  (flow/utils/publisher/reducao.py) without the reduction having to drop it;
- every string goes through the pattern redaction of the log (Bearer, Basic,
  DSN with a password, `token=`, `authkey=`, PATs, AWS keys, PEM blocks —
  flow/utils/redacao_log.py) and through the live-secret redaction; columns or
  keys with a sensitive name have their WHOLE value replaced, even a list or a
  dict.

The live-secret redaction alone is not enough: `segredos_vivos.in_use` only
covers the instant a node uses a credential (the WFS fetch), and the sample is
built after the node returns, when that list is usually empty again.
"""
import json
import math
import re
from datetime import date, datetime, time as dtime
from decimal import Decimal
from typing import Any

from flow.utils.redacao_log import scrub_text
from flow.utils.segredos_vivos import redact_text

SAMPLE_VERSION = 1

MAX_ROWS = 20
MAX_COLS = 40
MAX_CELL = 120
WKT_CHARS = 80
# Leaves room under the 64 KB event ceiling for the event's own fields.
BUDGET_BYTES = 48_000

JSON_MAX_DEPTH = 4
JSON_MAX_ITEMS = 20

# Keys that are not data for the panel: the artifact and response envelopes.
SKIPPED_KEYS = frozenset({"__artifact__", "__response__"})

_SENSITIVE = re.compile(
    r"pass(word|wd)?|secret|token|api[_-]?key|authorization|senha|cookie|credential|private[_-]?key",
    re.IGNORECASE,
)
_MASK = "***"


def _redact(texto: str) -> str:
    return scrub_text(redact_text(texto))


def _cut(texto: str, limite: int) -> str:
    # Sliced before the redaction: `str()` of a cell can be huge, and the patterns
    # only need a margin past the limit to see a secret that starts inside it.
    texto = _redact(texto[: limite * 4])
    return texto if len(texto) <= limite else texto[:limite] + "…"


def _is_sensitive(name: Any) -> bool:
    return isinstance(name, str) and bool(_SENSITIVE.search(name))


# ── Tables ───────────────────────────────────────────────────────────────────

def _geometry_column(df) -> "str | None":
    try:
        geom = getattr(df, "geometry", None)
        name = getattr(geom, "name", None)
        return name if name in df.columns else None
    except Exception:
        return None


def _column_type(serie, is_geometry: bool) -> str:
    import pandas as pd
    if is_geometry:
        tipos = {g.geom_type for g in serie.dropna().head(MAX_ROWS) if g is not None and not g.is_empty}
        if len(tipos) == 1:
            return f"geometry:{tipos.pop()}"
        return "geometry:mixed" if tipos else "geometry"
    dtype = serie.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "bool"
    if pd.api.types.is_integer_dtype(dtype):
        return "int"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if pd.api.types.is_string_dtype(dtype):
        # object columns land here too: decided by the values actually present.
        valores = serie.dropna().head(MAX_ROWS)
        if len(valores) and all(isinstance(v, str) for v in valores):
            return "str"
        return "object" if len(valores) else "str"
    return "object"


def _geometry_cell(geom) -> "dict | None":
    if geom is None:
        return None
    try:
        if geom.is_empty:
            return {"type": geom.geom_type, "vertices": 0, "wkt": f"{geom.geom_type.upper()} EMPTY"}
        import shapely
        vertices = int(shapely.get_num_coordinates(geom))
        if vertices > WKT_FULL_MAX_VERTICES:
            # `to_wkt` has no ceiling: it writes the whole geometry (tens of MB for
            # a boundary with a million vertices) only for 80 characters to be
            # kept. Only the first coordinates are written here.
            return {"type": geom.geom_type, "vertices": vertices, "wkt": _wkt_prefix(geom)}
        wkt = shapely.to_wkt(geom, rounding_precision=5, trim=True)
        return {"type": geom.geom_type, "vertices": vertices,
                "wkt": wkt if len(wkt) <= WKT_CHARS else wkt[:WKT_CHARS] + "…"}
    except Exception:
        return {"type": getattr(geom, "geom_type", "Geometry"), "vertices": None, "wkt": None}


# Above this, the WKT is not written whole (see `_wkt_prefix`).
WKT_FULL_MAX_VERTICES = 64

# How many "(" open each type's coordinate list in WKT.
_WKT_DEPTH = {"LineString": 1, "LinearRing": 1, "MultiPoint": 1,
              "Polygon": 2, "MultiLineString": 2, "MultiPolygon": 3}


def _num(v: float) -> str:
    texto = f"{v:.5f}".rstrip("0").rstrip(".")
    return "0" if texto in ("", "-0") else texto


def _wkt_prefix(geom) -> str:
    """The start of the WKT of a large geometry, cut at `WKT_CHARS` and ended
    with "…", without writing the rest. A GeometryCollection (no single
    coordinate list) gives only its type.
    """
    import shapely
    profundidade = _WKT_DEPTH.get(geom.geom_type)
    if profundidade is None:
        return f"{geom.geom_type.upper()} (…"
    coords = shapely.get_coordinates(geom)[:WKT_CHARS // 4]
    pares = ", ".join(f"{_num(x)} {_num(y)}" for x, y in coords)
    return f"{geom.geom_type.upper()} {'(' * profundidade}{pares}"[:WKT_CHARS] + "…"


def _cell(valor: Any, max_cell: int) -> Any:
    if valor is None:
        return None
    # NaN, NaT, pd.NA → null. `pd.isna` of a list/array is an array, not a bool:
    # only a scalar answer counts.
    try:
        import pandas as pd
        if pd.isna(valor) is True:
            return None
    except (TypeError, ValueError):
        pass
    # numpy scalars → Python (bool before int: numpy.bool_ is not an int subclass).
    if hasattr(valor, "item") and not isinstance(valor, (str, bytes)) and getattr(valor, "ndim", 1) == 0:
        try:
            valor = valor.item()
        except Exception:
            pass
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return None if math.isnan(valor) or math.isinf(valor) else valor
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date, dtime)):
        return valor.isoformat()
    if hasattr(valor, "isoformat"):  # pandas.Timestamp
        try:
            return valor.isoformat()
        except Exception:
            pass
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return f"<bytes {len(valor)}>"
    return _cut(str(valor), max_cell)


def _table_sample(df, max_rows: int, max_cols: int, max_cell: int) -> dict:
    geometria = _geometry_column(df)
    colunas = [c for c in df.columns if c != geometria]
    cols_cut = len(colunas) > max_cols
    colunas = colunas[:max_cols]
    if geometria is not None:
        colunas.append(geometria)

    head = df.head(max_rows)
    columns = []
    for c in colunas:
        is_geom = c == geometria
        entrada = {"name": str(c), "type": _column_type(head[c], is_geom)}
        if is_geom:
            entrada["geometry"] = True
        columns.append(entrada)

    sensiveis = {i for i, c in enumerate(colunas) if c != geometria and _is_sensitive(str(c))}
    cells_cut = False
    rows = []
    for registro in head[colunas].itertuples(index=False, name=None):
        linha = []
        for i, valor in enumerate(registro):
            if colunas[i] == geometria:
                linha.append(_geometry_cell(valor))
            elif i in sensiveis:
                linha.append(None if valor is None else _MASK)
            else:
                cel = _cell(valor, max_cell)
                if isinstance(cel, str) and cel.endswith("…") and len(cel) == max_cell + 1:
                    cells_cut = True
                linha.append(cel)
        rows.append(linha)

    sample: dict = {
        "kind": "table",
        "rows_total": int(len(df)),
        "columns": columns,
        "rows": rows,
        "truncated": {"rows": len(df) > len(rows), "columns": cols_cut, "cells": cells_cut},
    }
    crs = getattr(df, "crs", None) if geometria is not None else None
    if crs is not None:
        try:
            sample["crs"] = crs.to_string()
        except Exception:
            sample["crs"] = str(crs)
    return sample


# ── Everything else ──────────────────────────────────────────────────────────

def _json_value(valor: Any, depth: int, max_cell: int) -> "tuple[Any, bool]":
    """(JSON-safe value, whether anything was cut)."""
    try:
        import pandas as pd
        if isinstance(valor, pd.DataFrame):
            return f"<DataFrame {len(valor)}x{len(valor.columns)}>", False
    except Exception:
        pass
    if isinstance(valor, dict):
        if depth >= JSON_MAX_DEPTH:
            return f"<dict {len(valor)} chaves>", True
        out, cut = {}, len(valor) > JSON_MAX_ITEMS
        for i, (k, v) in enumerate(valor.items()):
            if i >= JSON_MAX_ITEMS:
                break
            chave = _cut(str(k), max_cell)
            if _is_sensitive(chave) and v is not None:
                # The whole value, whatever its shape: `{"token": ["abc"]}` or
                # `{"credentials": {"user": …, "pass": …}}` leaked when only
                # scalars were masked.
                out[chave] = _MASK
                continue
            out[chave], c = _json_value(v, depth + 1, max_cell)
            cut = cut or c
        return out, cut
    if isinstance(valor, (list, tuple, set, frozenset)):
        itens = list(valor)
        if depth >= JSON_MAX_DEPTH:
            return f"<list {len(itens)} itens>", True
        out, cut = [], len(itens) > JSON_MAX_ITEMS
        for v in itens[:JSON_MAX_ITEMS]:
            j, c = _json_value(v, depth + 1, max_cell)
            out.append(j)
            cut = cut or c
        return out, cut
    if isinstance(valor, str):
        # Sliced BEFORE anything else: an HttpRequest body can be tens of MB.
        trecho = valor[: max_cell * 4]
        cortado = _cut(trecho, max_cell)
        return cortado, len(valor) > max_cell
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return f"<bytes {len(valor)}>", False
    if hasattr(valor, "geom_type"):
        return _geometry_cell(valor), False
    cel = _cell(valor, max_cell)
    return cel, isinstance(cel, str) and cel.endswith("…")


def _is_table(valor: Any) -> bool:
    try:
        import pandas as pd
        return isinstance(valor, pd.DataFrame)
    except Exception:
        return False


def _is_spilled(valor: Any) -> bool:
    return isinstance(valor, dict) and valor.get("__spilled__") is True


def _size(obj: Any) -> int:
    # ensure_ascii (the default) makes len(str) == bytes, same as reducao.py.
    return len(json.dumps(obj))


# ── Entry point ──────────────────────────────────────────────────────────────

def build_output_sample(
    outputs: Any,
    *,
    max_rows: int = MAX_ROWS,
    max_cols: int = MAX_COLS,
    max_cell: int = MAX_CELL,
    budget_bytes: int = BUDGET_BYTES,
) -> dict:
    """The `output_sample` of a node: `{version, outputs: {key: entry}, skipped}`.

    Never raises: an output that fails to sample becomes
    `{"kind": "omitted", "reason": "error"}`, so one odd value does not take the
    others with it.
    """
    result: dict = {"version": SAMPLE_VERSION, "outputs": {}, "skipped": []}
    if not isinstance(outputs, dict):
        outputs = {"output": outputs}

    tabelas: dict = {}
    for chave, valor in outputs.items():
        chave = str(chave)
        if chave in SKIPPED_KEYS or _is_spilled(valor):
            result["skipped"].append(chave)
            continue
        try:
            if _is_table(valor):
                tabelas[chave] = valor
                result["outputs"][chave] = _table_sample(valor, max_rows, max_cols, max_cell)
            else:
                v, cut = _json_value(valor, 0, max_cell)
                result["outputs"][chave] = {"kind": "json", "value": v, "truncated": cut}
        except Exception:
            result["outputs"][chave] = {"kind": "omitted", "reason": "error"}

    if _size(result) <= budget_bytes:
        return result

    # 1. Fewer rows, every table at once, down to 1.
    rows = max_rows
    while rows > 1 and _size(result) > budget_bytes:
        rows = max(1, rows // 2)
        for chave, df in tabelas.items():
            try:
                result["outputs"][chave] = _table_sample(df, rows, max_cols, max_cell)
            except Exception:
                result["outputs"][chave] = {"kind": "omitted", "reason": "error"}

    # 2. Fewer columns (the geometry is always kept, at the end).
    cols = max_cols
    while cols > 1 and _size(result) > budget_bytes:
        cols = max(1, cols // 2)
        for chave, df in tabelas.items():
            try:
                result["outputs"][chave] = _table_sample(df, rows, cols, max_cell)
            except Exception:
                result["outputs"][chave] = {"kind": "omitted", "reason": "error"}

    # 3. The largest outputs leave whole until it fits.
    while _size(result) > budget_bytes:
        candidatas = [(k, _size(v)) for k, v in result["outputs"].items() if v.get("kind") != "omitted"]
        if not candidatas:
            break
        maior = max(candidatas, key=lambda kv: kv[1])[0]
        result["outputs"][maior] = {"kind": "omitted", "reason": "too_large"}

    return result
