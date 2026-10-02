# app/core/storage.py
"""
MinIO/S3 storage backend para o Drive e Artifacts.
Todas as operacoes de arquivo passam por este modulo.
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
# Endpoint externo para pre-signed URLs (acessivel por executores/browsers fora do Docker)
# Se nao definido, usa o mesmo endpoint interno
_EXTERNAL_ENDPOINT = os.getenv("MINIO_EXTERNAL_ENDPOINT", _ENDPOINT)

_BUCKET = os.getenv("MINIO_BUCKET", "atlans-drive")
_PRESIGN_EXPIRY = int(os.getenv("MINIO_PRESIGN_EXPIRY", "3600"))

# Hosts que so resolvem de dentro do Docker (ou da propria maquina): uma URL
# pre-assinada gerada com eles e inutil para browser, executor remoto ou MCP.
_HOSTS_LOCAIS = frozenset({"localhost", "127.0.0.1", "::1", "minio"})


def endpoint_externo_e_local() -> bool:
    """True se `MINIO_EXTERNAL_ENDPOINT` nao serve para gerar URLs alcancaveis fora do Docker.

    O default do compose e `http://localhost:9000` — funciona no dev e quebra em
    silencio em producao: o Drive, os artefatos e o MCP entregam links que so
    abrem na maquina do servidor. O boot avisa (nao derruba: em dev e o esperado).
    Vazio tambem conta como local — sem endpoint nao ha URL que preste.
    """
    valor = (_EXTERNAL_ENDPOINT or "").strip()
    if not valor:
        return True
    # `urlsplit("minio:9000")` leria "minio" como scheme; sem "://" o host vem depois de "//".
    if "://" not in valor:
        valor = "//" + valor
    try:
        host = urlsplit(valor).hostname  # ja vem minusculo e sem os colchetes de IPv6
    except ValueError:
        # Endereco que nem parseia (IPv6 malformado, por exemplo): nenhuma URL
        # pre-assinada vai prestar, entao o aviso vale — e o boot nao cai por isso.
        return True
    return not host or host in _HOSTS_LOCAIS


def endpoint_externo() -> str:
    """Valor efetivo de `MINIO_EXTERNAL_ENDPOINT` (cai no interno quando ausente).

    Existe para quem so precisa MOSTRAR o endpoint — o aviso de boot em
    `app/main.py` — sem alcancar o `_EXTERNAL_ENDPOINT` privado deste modulo.
    """
    return _EXTERNAL_ENDPOINT


# Singleton: cliente interno (operacoes server-side)
_client = None
# Cliente externo (gera pre-signed URLs acessiveis por browsers e executores)
_external_client = None


def _require_credentials() -> tuple[str, str]:
    """Le as credenciais do MinIO no momento do uso. Falha fechado se ausentes
    para nao cair em valor default conhecido publicamente (.env.example) e
    abrir o bucket administrativo. Lazy para nao quebrar import em ambientes
    de teste que nao tocam o storage."""
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
    """Cliente com endpoint externo para gerar pre-signed URLs acessiveis fora do Docker."""
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
    """Cria o bucket se nao existir. Chamar no startup."""
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
    """Upload direto de bytes para o MinIO. Retorna o MD5 do conteudo."""
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
    """Download do conteudo completo de um objeto."""
    client = _get_client()
    resp = client.get_object(Bucket=_BUCKET, Key=key)
    return resp["Body"].read()


def delete(key: str) -> bool:
    """Remove um objeto do MinIO. Best-effort: nunca levanta, retorna False em falha.

    Use `delete_strict` quando a falha for relevante (ex: rollback de delete
    no DB se o objeto nao for removido do S3). Esta variant existe para call
    sites onde a falha pode ser ignorada (ex: cleanup periodico que tenta
    de novo na proxima iteracao).
    """
    client = _get_client()
    try:
        client.delete_object(Bucket=_BUCKET, Key=key)
        return True
    except Exception as exc:
        logger.warning("Falha ao deletar '%s': %s", key, exc)
        return False


def delete_strict(key: str, allow_missing: bool = True) -> None:
    """Remove um objeto do MinIO levantando excecao em falha.

    Atomicidade: usar antes de DELETE no DB. Se levantar, o caller NAO deve
    apagar o registro — assim o objeto fica retornavel via cleanup periodico
    na proxima rodada.

    Args:
        key: chave do objeto no bucket.
        allow_missing: se True (default), tratar `NoSuchKey`/404 como sucesso
            (idempotente — alguem ja deletou). Se False, levanta tambem em 404.

    Raises:
        ClientError: qualquer erro do S3 que nao seja "not found" (se
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
    """Itera sobre objetos do bucket com `prefix`. Generator paginado.

    Yields dicts com `key`, `size`, `last_modified`. Usado pela reconciliacao
    para comparar DB vs estado real do MinIO. Cuidado com memoria: nunca
    materializa a lista inteira.
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
    """Itera sobre multipart uploads incompletos com `prefix`. Generator.

    Multipart abandonado consome disco no MinIO sem aparecer no DB nem em
    list_objects. Detectar idade > N horas e abortar para liberar bytes.

    Yields dicts com `key`, `upload_id`, `initiated`.
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
    """Retorna metadados do objeto (size, md5) ou None se nao existir."""
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
    """Gera URL pre-assinada para upload (PUT) — usa endpoint externo (browsers e executores)."""
    client = _get_external_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": _BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def presigned_get(key: str, expires: int = _PRESIGN_EXPIRY, filename: str | None = None) -> str:
    """Gera URL pre-assinada para download direto (GET). Usa endpoint externo."""
    client = _get_external_client()
    params = {"Bucket": _BUCKET, "Key": key}
    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    return client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires,
    )


# ── Wrappers async ────────────────────────────────────────────────────────────
# boto3 é síncrono: chamado direto num handler/coroutine, cada round-trip de rede
# BLOQUEIA o event loop do worker (congelando todas as outras requisições dele).
# Em contexto async, use SEMPRE estas variantes (rodam a chamada em thread).

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
