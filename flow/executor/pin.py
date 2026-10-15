# flow/executor/pin.py
"""Pin-cache management: upload/download/delete of artifacts in MinIO."""
import hashlib
import os
import json
import re
import unicodedata
from typing import Dict, Any, Optional
from flow.utils.geo_helpers import gdf_para_geojson
from flow.utils.json_saida import json_default
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_PIN_PRESIGN_TIMEOUT = int(os.getenv("PIN_PRESIGN_TIMEOUT", "15"))
_PIN_UPLOAD_TIMEOUT  = int(os.getenv("PIN_UPLOAD_TIMEOUT",  "120"))
_PIN_RETRY_COUNT     = int(os.getenv("PIN_UPLOAD_MAX_RETRIES", "2"))
_PIN_RETRY_MAX_DELAY = int(os.getenv("PIN_UPLOAD_RETRY_MAX_DELAY", "30"))

# ── One object per DataFrame ─────────────────────────────────────────────────
#
# The FIRST DataFrame of the output stays where it always was (`__pin_s3_key__`,
# `__pin_format__`, `__pin_geo_key__`, `__pin_filename__`), so the refs already in
# `workflows.pinned_outputs` keep being read as before. Each further DataFrame
# (RemoveDuplicates' `removed`, FilterByGeometryType's `lines`/`polygons`/`other`,
# FileTrigger's `file_b`) gets an object of its own, listed in `__pin_frames__` as
# `{output_key: {"format": …, "filename": …}}`. It used to go into `__pin_extra__`
# as the raw object; the WebSocket serializer turned it into the text
# "<DataFrame RxC>" on the way to the server, and the pinned run delivered that text
# where the layer should be.
#
# The entry holds only the NAME. The folder is the one of `__pin_s3_key__`, which
# the server derives (`run_result_consumer._safe_pin_ref`), so each layer adds a
# short name to `pinned_outputs` rather than a whole key — and the server rebuilds
# the name from (node, output) instead of trusting the one written here.
PIN_FRAME_FORMATS = ("parquet", "geojson", "pandas-json")

# Ceiling on extra layers per node, applied here and by the server (which drops the
# whole pin above it). A legitimate node with dozens of DataFrame outputs is already
# unusual; the ceiling keeps a buggy or compromised executor from turning one ref
# into thousands of key derivations in the consumer and into a `pinned_outputs`
# that travels in every dispatch of the workflow.
PIN_MAX_FRAMES = 64

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")

# What the WebSocket serializer (`executor/connection.py::_json_default`) made of
# a DataFrame that went into `__pin_extra__` raw — every DataFrame after the
# first, before `__pin_frames__` existed.
_LAYER_AS_TEXT = re.compile(r"<DataFrame \d+x\d+>")


def _slug(texto: str, limite: int) -> str:
    """`texto` reduced to `[A-Za-z0-9_-]`: accents dropped (NFKD), the rest becomes `_`."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return _UNSAFE_NAME_CHARS.sub("_", texto).strip("_")[:limite]


def pin_frame_filename(node_id: Any, output_key: Any, fmt: str) -> str:
    """Object name of a pinned DataFrame that is not the node's first one.

    This is the contract with the server, which derives the same name on its own
    and never takes the one the executor reports. Refs already stored keep
    working if it changes (they carry the name), but an executor and a server on
    different versions would disagree: the server would store a name nobody
    uploaded, and every pinned run would miss it and run the node again.

    - Only `[A-Za-z0-9_-]` before the extension, so the server's sanitization
      (`_sanitize_filename`) and the presign guard leave it untouched.
    - The hash of (node, output) keeps two outputs apart when their names reduce
      to the same text ('área' and 'area', 'a b' and 'a_b'), and keeps the name
      from ever matching the first layer's `{node_id}_pin.{fmt}`: the stem ends
      in hex digits, never in `_pin`.
    - The readable parts are cut so the stem stays below the server's
      160-character ceiling (`_MAX_STEM_LEN`).
    """
    no, saida = str(node_id), str(output_key)
    digest = hashlib.sha256(f"{no}\x00{saida}".encode("utf-8", "surrogatepass")).hexdigest()[:12]
    return f"{_slug(no, 60) or 'no'}_pin_{_slug(saida, 60) or 'saida'}_{digest}.{fmt}"


def pin_frame_s3_key(main_s3_key: Any, filename: Any) -> Optional[str]:
    """Key of an extra layer: the folder of `__pin_s3_key__` plus the layer's name.

    The executor downloads with it and the server deletes with it (unpin, move,
    purge), so both reach the same object. None when the name is not a plain file
    name: a separator or a `..` would leave the run's folder.
    """
    if not isinstance(main_s3_key, str) or "/" not in main_s3_key:
        return None
    if (not isinstance(filename, str) or not filename or ".." in filename
            or "/" in filename or "\\" in filename):
        return None
    return f"{main_s3_key.rsplit('/', 1)[0]}/{filename}"


def _serialize_frame(df: Any) -> "tuple[bytes | str, str, str]":
    """(content, format, content_type) of a DataFrame, in a form `_read_frame`
    reads back: Parquet, else GeoJSON for a GeoDataFrame and pandas' own JSON
    ("pandas-json", the `split` orientation) for a plain table.

    Parquet goes out as the path of a temporary file, which `upload_pin_to_minio`
    reads and removes. A plain table used to fall back to `df.to_json()` labelled
    as GeoJSON, which no read could open: a mixed-type column ([12.5, "sem dado"])
    or repeated column names were enough for Parquet to fail, and the pinned node
    then ran again on every run, uploading the pin again each time. `split` keeps
    each value with its own type and accepts repeated column names; what has no
    JSON form becomes text (`default_handler=str`), so it does not fail.
    """
    import geopandas as gpd

    try:
        import tempfile as _tempfile
        _tmp = _tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        _tmp.close()
        try:
            df.to_parquet(_tmp.name, index=False)
        except Exception:
            os.unlink(_tmp.name)
            raise
        return _tmp.name, "parquet", "application/octet-stream"
    except (ImportError, Exception) as exc:
        logger.debug("Falha ao serializar pin como parquet, usando o plano B: %s", exc)
    if isinstance(df, gpd.GeoDataFrame):
        # Through the single helper (datetime becomes text in a copy — the raw
        # `to_json` failed on a datetime column, taking down the pin).
        return gdf_para_geojson(df, nat_as_null=True).encode("utf-8"), "geojson", "application/geo+json"
    texto = df.to_json(orient="split", default_handler=str, date_format="iso")
    return texto.encode("utf-8"), "pandas-json", "application/json"


def _remove_temporary(*contents: Any) -> None:
    """Removes the temporary Parquet files among `contents` (the str ones)."""
    for content in contents:
        if isinstance(content, str):
            try:
                os.unlink(content)
            except OSError:
                pass


def _json_value(key: Any, value: Any) -> Any:
    """A non-DataFrame output already in the form the server will store.

    The ref travels as JSON (WebSocket, then `pinned_outputs`). A value `json`
    does not know used to stay raw in the ref, and the serializer on the way
    turned it into text without anything here noticing — which is how a second
    DataFrame became "<DataFrame RxC>". Converting HERE, by the same rules, keeps
    what the server stored for dates and numpy numbers, makes the ref this
    executor builds the one the next run receives, and leaves a warning when
    the pinned run is going to see text where the node produced an object.
    """
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        pass
    as_text: set = set()
    try:
        convertido = json.loads(json.dumps(value, default=lambda obj: json_default(obj, como_texto=as_text)))
    except (TypeError, ValueError):
        # A structure that contains itself: not even the default gets out of it.
        as_text.add(type(value).__name__)
        convertido = str(value)
    if as_text:
        # One line per output — a list of ten thousand geometries is one warning.
        logger.warning(
            "Pin: a saída '%s' tem valor sem forma JSON (%s); o run fixado verá texto.",
            key, ", ".join(sorted(as_text)),
        )
    return convertido


def upload_pin_artifact(node_id: str, outputs: Dict[str, Any], workspace_id: str, task_id: str) -> Dict[str, Any]:
    """Serializes outputs and uploads them to MinIO as a pin cache artifact.

    One object per DataFrame: the first where it always was, the others in
    `__pin_frames__` (see the block above `PIN_FRAME_FORMATS`).
    """
    import geopandas as gpd
    import pandas as pd

    has_geo = any(isinstance(v, (gpd.GeoDataFrame, pd.DataFrame)) for v in outputs.values())

    ws_id = workspace_id or "default"
    task_id = task_id or "no-task"
    more_frames: Dict[Any, Any] = {}

    if has_geo:
        geo_key = None
        geo_val = None
        extra = {}
        for k, v in outputs.items():
            if isinstance(v, (gpd.GeoDataFrame, pd.DataFrame)):
                if geo_key is None:
                    geo_key = k
                    geo_val = v
                else:
                    more_frames[k] = v
            else:
                extra[k] = _json_value(k, v)

        if len(more_frames) > PIN_MAX_FRAMES:
            # Before uploading anything: the server would drop this pin, and each run
            # would upload every layer again for nothing.
            raise ValueError(
                f"saída com {len(more_frames) + 1} DataFrames; o pin guarda no máximo "
                f"{PIN_MAX_FRAMES + 1}."
            )
        # Every layer serialized BEFORE any upload: a layer that cannot be
        # written must not leave the ones already uploaded behind, with no ref
        # pointing at them, on every run that retries.
        content, fmt, content_type = _serialize_frame(geo_val)
        serialized: list = []
        try:
            for k, frame in more_frames.items():
                serialized.append((k, *_serialize_frame(frame)))
        except Exception:
            _remove_temporary(content, *(item[1] for item in serialized))
            raise
        filename = f"{node_id}_pin.{fmt}"
    else:
        content = json.dumps(outputs, default=str).encode("utf-8")
        filename = f"{node_id}_pin.json"
        fmt = "json"
        content_type = "application/json"
        geo_key = None
        extra = {}

    s3_key = f"pin-cache/{ws_id}/{task_id}/{filename}"
    if not has_geo:
        upload_pin_to_minio(content, s3_key, content_type)
        return {
            "__pin_s3_key__": s3_key, "__pin_format__": fmt,
            "__pin_geo_key__": None, "__pin_filename__": filename,
        }

    # A failed layer upload raises and the node is left unpinned (core logs "Auto-pin
    # falhou"): a ref missing a layer would deliver the output without it.
    frames: Dict[str, Dict[str, str]] = {}
    pendentes = [content, *(item[1] for item in serialized)]
    try:
        upload_pin_to_minio(content, s3_key, content_type)
        pendentes.pop(0)
        for k, frame_content, frame_fmt, frame_type in serialized:
            frame_name = pin_frame_filename(node_id, k, frame_fmt)
            upload_pin_to_minio(frame_content, pin_frame_s3_key(s3_key, frame_name), frame_type)
            pendentes.pop(0)
            frames[str(k)] = {"format": frame_fmt, "filename": frame_name}
    except Exception:
        _remove_temporary(*pendentes)
        raise

    return {
        "__pin_s3_key__": s3_key,
        "__pin_format__": fmt,
        "__pin_geo_key__": geo_key,
        "__pin_filename__": filename,
        # Always present, even empty: it is what tells this ref from one written
        # before one object per layer (see `download_pin_artifact`).
        "__pin_frames__": frames,
        **({"__pin_extra__": extra} if extra else {}),
        # The order the node produced: rebuilt from objects and values, the
        # outputs came back first layer first, and a Merge "last" or an edge
        # with only `to_key` (the first value) picked another output.
        "__pin_order__": [str(k) for k in outputs],
    }


def upload_pin_to_minio(content: "bytes | str", s3_key: str, content_type: str) -> None:
    """Upload to MinIO via pre-signed URL. content may be bytes or the path of a
    temporary file (in which case the file is read and removed)."""
    import httpx
    from flow.utils.executor_http import get_agent_http_config
    from flow.utils.http_retry import retry_sync

    base_url, headers, verify = get_agent_http_config()

    if isinstance(content, str):
        _tmp_path = content
        with open(_tmp_path, "rb") as _f:
            content = _f.read()
        os.unlink(_tmp_path)

    def _do_upload() -> None:
        # Re-obtains the pre-signed URL on every attempt: the previous URL may have
        # expired between retries (presign has a short TTL).
        resp = httpx.post(
            f"{base_url}/drive/executor-presign-upload",
            json={"s3_key": s3_key, "content_type": content_type},
            headers=headers, verify=verify, follow_redirects=True, timeout=_PIN_PRESIGN_TIMEOUT,
        )
        resp.raise_for_status()
        upload_url = resp.json()["upload_url"]
        put_resp = httpx.put(
            upload_url,
            content=content,
            headers={"Content-Type": content_type},
            timeout=_PIN_UPLOAD_TIMEOUT, verify=verify,
        )
        put_resp.raise_for_status()

    # Best-effort upload: retries any failure (network, storage, 5xx), since
    # almost every pin upload failure is transient and the cost of retrying
    # is low compared to losing the pin cache.
    retry_sync(
        _do_upload,
        max_attempts=_PIN_RETRY_COUNT + 1,
        max_delay=_PIN_RETRY_MAX_DELAY,
        retryable_exc=(Exception,),
        label=f"Upload pin {s3_key}",
    )
    logger.info("Pin cache enviado ao MinIO via pre-signed URL: %s", s3_key)


def _download_from_minio(s3_key: str) -> Optional[bytes]:
    """The object's bytes via pre-signed URL; None when it could not be downloaded."""
    try:
        import httpx
        from flow.utils.executor_http import get_agent_http_config
        base_url, headers, verify = get_agent_http_config()
        resp = httpx.post(
            f"{base_url}/drive/executor-presign-download",
            json={"s3_key": s3_key},
            headers=headers, verify=verify, follow_redirects=True, timeout=_PIN_PRESIGN_TIMEOUT,
        )
        resp.raise_for_status()
        download_url = resp.json().get("download_url")
        if download_url:
            dl = httpx.get(download_url, follow_redirects=True, timeout=_PIN_UPLOAD_TIMEOUT, verify=verify)
            dl.raise_for_status()
            return dl.content
    except Exception as exc:
        logger.warning("Download de pin via pre-signed URL falhou: %s — %s", s3_key, exc)
    return None


def _read_frame(content: bytes, fmt: str) -> Any:
    """A pinned DataFrame rebuilt from its object (`fmt` in `PIN_FRAME_FORMATS`)."""
    import io as _io

    if fmt == "parquet":
        try:
            import geopandas as gpd
            return gpd.read_parquet(_io.BytesIO(content))
        except Exception as exc:
            logger.debug("Falha ao ler pin como GeoDataFrame, tentando pandas: %s", exc)
            import geopandas as gpd
            import pandas as pd
            df = pd.read_parquet(_io.BytesIO(content))
            # An empty GeoDataFrame with no geometry column (a Switch's empty
            # bucket) has no geo metadata to come back with: in the run it was a
            # GeoDataFrame, and a node that tells the two apart would differ.
            if df.empty and len(df.columns) == 0:
                return gpd.GeoDataFrame()
            return df
    if fmt == "pandas-json":
        import pandas as pd
        return pd.read_json(
            _io.StringIO(content.decode("utf-8")), orient="split", dtype=False, convert_dates=False,
        )
    # `driver="GeoJSON"` does NOT restrict the driver when reading with pyogrio;
    # `read_geodataframe` rejects VRT content based on the content itself.
    from flow.utils.leitura_geo import read_geodataframe
    return read_geodataframe(_io.BytesIO(content))


def download_pin_artifact(pinned: Dict[str, Any]) -> Dict[str, Any]:
    """Downloads a pin artifact from MinIO and rebuilds the original outputs.

    Returns {} when ANY of the pin's objects is missing — the first layer's or an
    extra one's. The executor treats {} as a broken pin: the node runs and
    auto-pin rewrites it (`core._resolve_pin_data`). Delivering only the layers
    that arrived would leave the edge out of the missing one with nothing, and the
    target would fail far from the cause, with this node shown as served from cache.
    """
    s3_key = pinned.get("__pin_s3_key__")
    fmt = pinned.get("__pin_format__", "json")
    geo_key = pinned.get("__pin_geo_key__")
    extra = pinned.get("__pin_extra__", {})
    # Refs written before `__pin_frames__` existed have no such key and are read
    # exactly as before: the first layer plus `__pin_extra__`.
    frames = pinned.get("__pin_frames__") or {}

    if not s3_key:
        return pinned

    # A pin written before one object per layer holds the text "<DataFrame RxC>"
    # where its second layer should be, and the pinned run delivered that text.
    # Its first object exists, so nothing else would ever call it broken: {}
    # makes the node run and auto-pin rewrite it, with every layer. Only such a
    # ref: one written since carries `__pin_frames__`, even empty.
    if "__pin_frames__" not in pinned and isinstance(extra, dict) and any(
        isinstance(v, str) and _LAYER_AS_TEXT.fullmatch(v) for v in extra.values()
    ):
        logger.warning("Pin com camada gravada como texto em %s: o nó roda e o pin é regravado.", s3_key)
        return {}

    # Each layer's key and format checked before any download.
    if not isinstance(frames, dict):
        logger.warning("Pin com camadas ilegíveis em %s.", s3_key)
        return {}
    frame_objects = []
    for output_key, frame in frames.items():
        frame_fmt = frame.get("format") if isinstance(frame, dict) else None
        frame_key = pin_frame_s3_key(s3_key, frame.get("filename")) if isinstance(frame, dict) else None
        if frame_fmt not in PIN_FRAME_FORMATS or frame_key is None:
            logger.warning("Pin com camada ilegível (%r) em %s.", output_key, s3_key)
            return {}
        frame_objects.append((output_key, frame_key, frame_fmt))

    content = _download_from_minio(s3_key)
    if content is None:
        logger.warning("Não foi possível baixar artefato de pin: %s", s3_key)
        return {}

    outputs = {}

    if fmt in PIN_FRAME_FORMATS:
        outputs[geo_key or "output"] = _read_frame(content, fmt)
    else:
        outputs = json.loads(content.decode("utf-8"))

    for output_key, frame_key, frame_fmt in frame_objects:
        frame_content = _download_from_minio(frame_key)
        if frame_content is None:
            logger.warning("Não foi possível baixar a camada '%s' do pin: %s", output_key, frame_key)
            return {}
        outputs[output_key] = _read_frame(frame_content, frame_fmt)

    if extra:
        outputs.update(extra)

    ordem = pinned.get("__pin_order__")
    if isinstance(ordem, list):
        outputs = {
            **{k: outputs[k] for k in ordem if isinstance(k, str) and k in outputs},
            **{k: v for k, v in outputs.items() if k not in ordem},
        }

    return outputs
