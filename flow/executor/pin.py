# flow/executor/pin.py
"""Gerenciamento de pin-cache: upload/download/delete de artefatos no MinIO."""
import os
import json
from typing import Dict, Any
from flow.utils.geo_helpers import gdf_para_geojson
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_PIN_PRESIGN_TIMEOUT = int(os.getenv("PIN_PRESIGN_TIMEOUT", "15"))
_PIN_UPLOAD_TIMEOUT  = int(os.getenv("PIN_UPLOAD_TIMEOUT",  "120"))
_PIN_RETRY_COUNT     = int(os.getenv("PIN_UPLOAD_MAX_RETRIES", "2"))
_PIN_RETRY_MAX_DELAY = int(os.getenv("PIN_UPLOAD_RETRY_MAX_DELAY", "30"))


def upload_pin_artifact(node_id: str, outputs: Dict[str, Any], workspace_id: str, task_id: str) -> Dict[str, Any]:
    """Serializa outputs e faz upload ao MinIO como artefato de pin cache."""
    import geopandas as gpd
    import pandas as pd

    has_geo = any(isinstance(v, (gpd.GeoDataFrame, pd.DataFrame)) for v in outputs.values())

    ws_id = workspace_id or "default"
    task_id = task_id or "no-task"

    if has_geo:
        geo_key = None
        geo_val = None
        extra = {}
        for k, v in outputs.items():
            if isinstance(v, (gpd.GeoDataFrame, pd.DataFrame)) and geo_key is None:
                geo_key = k
                geo_val = v
            else:
                try:
                    json.dumps(v, default=str)
                    extra[k] = v
                except (TypeError, ValueError):
                    extra[k] = str(v)

        try:
            import tempfile as _tempfile
            _tmp = _tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
            _tmp.close()
            try:
                geo_val.to_parquet(_tmp.name, index=False)
                content = _tmp.name
            except Exception:
                os.unlink(_tmp.name)
                raise
            filename = f"{node_id}_pin.parquet"
            fmt = "parquet"
            content_type = "application/octet-stream"
        except (ImportError, Exception) as exc:
            logger.debug("Falha ao serializar pin como parquet, usando fallback GeoJSON: %s", exc)
            # GeoDataFrame pelo helper unico (datetime vira texto numa copia —
            # o `to_json` cru falhava com coluna datetime, derrubando o pin
            # junto com o Parquet). DataFrame puro segue no `to_json` do pandas.
            geojson_str = gdf_para_geojson(geo_val, nat_como_nulo=True) if isinstance(geo_val, gpd.GeoDataFrame) else geo_val.to_json()
            content = geojson_str.encode("utf-8")
            filename = f"{node_id}_pin.geojson"
            fmt = "geojson"
            content_type = "application/geo+json"
    else:
        content = json.dumps(outputs, default=str).encode("utf-8")
        filename = f"{node_id}_pin.json"
        fmt = "json"
        content_type = "application/json"
        geo_key = None
        extra = {}

    s3_key = f"pin-cache/{ws_id}/{task_id}/{filename}"
    upload_pin_to_minio(content, s3_key, content_type)

    ref: Dict[str, Any] = {
        "__pin_s3_key__": s3_key,
        "__pin_format__": fmt,
        "__pin_geo_key__": geo_key,
        "__pin_filename__": filename,
    }
    if extra:
        ref["__pin_extra__"] = extra
    return ref


def upload_pin_to_minio(content: "bytes | str", s3_key: str, content_type: str) -> None:
    """Upload ao MinIO via pre-signed URL. content pode ser bytes ou path de
    arquivo temporário (nesse caso o arquivo é lido e removido)."""
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
        # Re-obtem a pre-signed URL a cada tentativa: a URL anterior pode ter
        # expirado entre retries (presign tem TTL curto).
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

    # Upload best-effort: retenta qualquer falha (rede, storage, 5xx), pois
    # quase toda falha de upload de pin é transitória e o custo de re-tentar
    # e baixo comparado a perder o pin cache.
    retry_sync(
        _do_upload,
        max_attempts=_PIN_RETRY_COUNT + 1,
        max_delay=_PIN_RETRY_MAX_DELAY,
        retryable_exc=(Exception,),
        label=f"Upload pin {s3_key}",
    )
    logger.info("Pin cache enviado ao MinIO via pre-signed URL: %s", s3_key)


def download_pin_artifact(pinned: Dict[str, Any]) -> Dict[str, Any]:
    """Baixa artefato de pin do MinIO e reconstrói os outputs originais."""
    s3_key = pinned.get("__pin_s3_key__")
    fmt = pinned.get("__pin_format__", "json")
    geo_key = pinned.get("__pin_geo_key__")
    extra = pinned.get("__pin_extra__", {})

    if not s3_key:
        return pinned

    content = None
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
            content = dl.content
    except Exception as exc:
        logger.warning("Download de pin via pre-signed URL falhou: %s — %s", s3_key, exc)

    if content is None:
        logger.warning("Não foi possível baixar artefato de pin: %s", s3_key)
        return {}

    import io as _io
    outputs = {}

    if fmt == "parquet":
        try:
            import geopandas as gpd
            gdf = gpd.read_parquet(_io.BytesIO(content))
            outputs[geo_key or "output"] = gdf
        except Exception as exc:
            logger.debug("Falha ao ler pin como GeoDataFrame, tentando pandas: %s", exc)
            import pandas as pd
            df = pd.read_parquet(_io.BytesIO(content))
            outputs[geo_key or "output"] = df
    elif fmt == "geojson":
        # `driver="GeoJSON"` NAO restringe o driver na leitura com pyogrio; o
        # `ler_geodataframe` recusa conteudo VRT pelo proprio conteudo.
        from flow.utils.leitura_geo import ler_geodataframe
        gdf = ler_geodataframe(_io.BytesIO(content))
        outputs[geo_key or "output"] = gdf
    else:
        outputs = json.loads(content.decode("utf-8"))

    if extra:
        outputs.update(extra)

    return outputs
