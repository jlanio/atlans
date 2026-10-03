# app/core/storage.py
"""
MinIO/S3 storage backend for the Drive and Artifacts.
All file operations go through this module.
"""
import asyncio
import hashlib
import os
from urllib.parse import urlsplit
from app.core.utils.logger import get_logger

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config as BotoConfig

logger = get_logger(__name__)

_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
# External endpoint for pre-signed URLs (reachable by executors/browsers outside Docker)
# If not set, uses the same internal endpoint
_EXTERNAL_ENDPOINT = os.getenv("MINIO_EXTERNAL_ENDPOINT", _ENDPOINT)

_BUCKET = os.getenv("MINIO_BUCKET", "atlans-drive")
_PRESIGN_EXPIRY = int(os.getenv("MINIO_PRESIGN_EXPIRY", "3600"))

# Hosts that only resolve from inside Docker (or from the machine itself): a
# pre-signed URL generated with them is useless to a browser, remote executor or MCP.
_HOSTS_LOCAIS = frozenset({"localhost", "127.0.0.1", "::1", "minio"})


def endpoint_externo_e_local() -> bool:
    """True if `MINIO_EXTERNAL_ENDPOINT` cannot generate URLs reachable outside Docker.

    The compose default is `http://localhost:9000` — it works in dev and breaks
    silently in production: the Drive, the artifacts and the MCP hand out links
    that only open on the server machine. Boot warns (does not fail: in dev it is
    expected). Empty also counts as local — with no endpoint there is no usable URL.
    """
    valor = (_EXTERNAL_ENDPOINT or "").strip()
    if not valor:
        return True
    # `urlsplit("minio:9000")` would read "minio" as the scheme; without "://" the host comes after "//".
    if "://" not in valor:
        valor = "//" + valor
    try:
        host = urlsplit(valor).hostname  # already lowercase and without the IPv6 brackets
    except ValueError:
        # An address that does not even parse (malformed IPv6, for example): no
        # pre-signed URL will work, so the warning stands — and boot does not fail over it.
        return True
    return not host or host in _HOSTS_LOCAIS


def endpoint_externo() -> str:
    """Effective value of `MINIO_EXTERNAL_ENDPOINT` (falls back to the internal one when absent).

    Exists for those who only need to SHOW the endpoint — the boot warning in
    `app/main.py` — without reaching into this module's private `_EXTERNAL_ENDPOINT`.
    """
    return _EXTERNAL_ENDPOINT


# Singleton: cliente interno (operacoes server-side)
_client = None
# Cliente externo (gera pre-signed URLs acessiveis por browsers e executores)
_external_client = None


def _require_credentials() -> tuple[str, str]:
    """Read the MinIO credentials at the time of use. Fails closed if absent
    so as not to fall back to a publicly known default value (.env.example) and
    open the administrative bucket. Lazy so as not to break the import in test
    environments that do not touch storage."""
    access_key = os.getenv("MINIO_ROOT_USER")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD")
    if not access_key or not secret_key:
        raise RuntimeError(
            "MINIO_ROOT_USER e MINIO_ROOT_PASSWORD sao obrigatorias. "
            "Defina-as no ambiente antes de subir o servico."
        )
    return access_key, secret_key


def _get_client():
    global _client
    if _client is None:
        access_key, secret_key = _require_credentials()
        _client = boto3.client(
            "s3",
            endpoint_url=_ENDPOINT,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return _client


def _get_external_client():
    """Client with the external endpoint to generate pre-signed URLs reachable outside Docker."""
    global _external_client
    if _external_client is None:
        access_key, secret_key = _require_credentials()
        _external_client = boto3.client(
            "s3",
            endpoint_url=_EXTERNAL_ENDPOINT,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return _external_client


def ensure_bucket():
    """Create the bucket if it does not exist. Call at startup."""
    client = _get_client()
    try:
        client.head_bucket(Bucket=_BUCKET)
        logger.info("MinIO bucket '%s' encontrado.", _BUCKET)
    except ClientError:
        try:
            client.create_bucket(Bucket=_BUCKET)
            logger.info("MinIO bucket '%s' criado.", _BUCKET)
        except Exception as exc:
            logger.error("Falha ao criar bucket '%s': %s", _BUCKET, exc)
            raise


def upload(key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes directly to MinIO. Returns the MD5 of the content."""
    client = _get_client()
    md5 = hashlib.md5(content).hexdigest()
    client.put_object(
        Bucket=_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    return md5


def download(key: str) -> bytes:
    """Download the full content of an object."""
    client = _get_client()
    resp = client.get_object(Bucket=_BUCKET, Key=key)
    return resp["Body"].read()


def delete(key: str) -> bool:
    """Remove an object from MinIO. Best-effort: never raises, returns False on failure.

    Use `delete_strict` when the failure matters (e.g. rolling back a delete
    in the DB if the object is not removed from S3). This variant exists for call
    sites where the failure can be ignored (e.g. a periodic cleanup that tries
    again on the next iteration).
    """
    client = _get_client()
    try:
        client.delete_object(Bucket=_BUCKET, Key=key)
        return True
    except Exception as exc:
        logger.warning("Falha ao deletar '%s': %s", key, exc)
        return False


def delete_strict(key: str, allow_missing: bool = True) -> None:
    """Remove an object from MinIO, raising an exception on failure.

    Atomicity: use before the DELETE in the DB. If it raises, the caller must NOT
    delete the record — that way the object remains retrievable via the periodic
    cleanup on the next round.

    Args:
        key: the object's key in the bucket.
        allow_missing: if True (default), treat `NoSuchKey`/404 as success
            (idempotent — someone already deleted it). If False, also raises on 404.

    Raises:
        ClientError: any S3 error other than "not found" (if
            `allow_missing=True`).
    """
    client = _get_client()
    try:
        client.delete_object(Bucket=_BUCKET, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if allow_missing and code in ("NoSuchKey", "NoSuchBucket", "404"):
            logger.debug("delete_strict: objeto '%s' ja nao existia (idempotente).", key)
            return
        logger.warning("delete_strict falhou para '%s' (code=%s).", key, code)
        raise


def list_objects(prefix: str = "", max_keys_per_page: int = 1000):
    """Iterate over the bucket's objects with `prefix`. Paginated generator.

    Yields dicts with `key`, `size`, `last_modified`. Used by reconciliation
    to compare the DB vs the actual MinIO state. Mind the memory: it never
    materializes the whole list.
    """
    client = _get_client()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=_BUCKET, Prefix=prefix, PaginationConfig={"PageSize": max_keys_per_page}):
        for obj in page.get("Contents", []) or []:
            yield {
                "key": obj["Key"],
                "size": obj.get("Size", 0),
                "last_modified": obj.get("LastModified"),
            }


def list_incomplete_multipart_uploads(prefix: str = ""):
    """Iterate over incomplete multipart uploads with `prefix`. Generator.

    Abandoned multipart uploads consume disk in MinIO without showing up in the DB
    or in list_objects. Detect age > N hours and abort to free bytes.

    Yields dicts with `key`, `upload_id`, `initiated`.
    """
    client = _get_client()
    paginator = client.get_paginator("list_multipart_uploads")
    for page in paginator.paginate(Bucket=_BUCKET, Prefix=prefix):
        for upload in page.get("Uploads", []) or []:
            yield {
                "key": upload["Key"],
                "upload_id": upload["UploadId"],
                "initiated": upload.get("Initiated"),
            }


def abort_multipart_upload(key: str, upload_id: str) -> bool:
    """Aborta um multipart upload incompleto. Retorna True em sucesso."""
    client = _get_client()
    try:
        client.abort_multipart_upload(Bucket=_BUCKET, Key=key, UploadId=upload_id)
        return True
    except Exception as exc:
        logger.warning("Falha ao abortar multipart '%s' (uploadId=%s): %s", key, upload_id, exc)
        return False


def head(key: str) -> dict | None:
    """Return the object's metadata (size, md5) or None if it does not exist."""
    client = _get_client()
    try:
        resp = client.head_object(Bucket=_BUCKET, Key=key)
        return {
            "size": resp["ContentLength"],
            "etag": resp["ETag"].strip('"'),
            "content_type": resp.get("ContentType"),
        }
    except ClientError as exc:
        logger.debug("Objeto S3 '%s' não encontrado: %s", key, exc)
        return None


def presigned_put(key: str, content_type: str = "application/octet-stream", expires: int = _PRESIGN_EXPIRY) -> str:
    """Generate a pre-signed URL for upload (PUT) — uses the external endpoint (browsers and executors)."""
    client = _get_external_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": _BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def presigned_get(key: str, expires: int = _PRESIGN_EXPIRY, filename: str | None = None) -> str:
    """Generate a pre-signed URL for direct download (GET). Uses the external endpoint."""
    client = _get_external_client()
    params = {"Bucket": _BUCKET, "Key": key}
    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    return client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires,
    )


# ── Async wrappers ────────────────────────────────────────────────────────────
# boto3 is synchronous: called directly in a handler/coroutine, each network round
# trip BLOCKS the worker's event loop (freezing all its other requests).
# In an async context, ALWAYS use these variants (they run the call in a thread).

async def upload_async(key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
    return await asyncio.to_thread(upload, key, content, content_type)


async def head_async(key: str) -> dict | None:
    return await asyncio.to_thread(head, key)


async def delete_async(key: str) -> bool:
    return await asyncio.to_thread(delete, key)


async def delete_strict_async(key: str, allow_missing: bool = True) -> None:
    return await asyncio.to_thread(delete_strict, key, allow_missing=allow_missing)


async def presigned_put_async(key: str, content_type: str = "application/octet-stream", expires: int = _PRESIGN_EXPIRY) -> str:
    return await asyncio.to_thread(presigned_put, key, content_type=content_type, expires=expires)


async def presigned_get_async(key: str, expires: int = _PRESIGN_EXPIRY, filename: str | None = None) -> str:
    return await asyncio.to_thread(presigned_get, key, expires=expires, filename=filename)


async def list_incomplete_multipart_uploads_async(prefix: str = "") -> list:
    return await asyncio.to_thread(lambda: list(list_incomplete_multipart_uploads(prefix)))


async def abort_multipart_upload_async(key: str, upload_id: str) -> bool:
    return await asyncio.to_thread(abort_multipart_upload, key, upload_id)
