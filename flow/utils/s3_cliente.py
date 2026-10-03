# flow/utils/s3_cliente.py
"""boto3 client built from the fields of the vault's `s3` credential.

One implementation for both sides: the SaveToS3 node (on the executor, with the
`s3_auth` the server injects from the chosen credential) and the credential's
connection test (in the API). Before, each one built the session its own way: the
node with keys typed into the definition — the secret in plain text in the database,
in the version history and in the MCP read — and without `endpoint_url`, so MinIO
and S3-compatible services were left out; the test with the credential's fields.

The field names are the catalog's (`app/core/credentials/schemas.py`):
`access_key_id`, `secret_access_key`, `region`, `bucket`, `endpoint_url`.
An empty field is not passed to boto3: without keys, its default chain applies
(environment variables, `~/.aws/credentials`, IAM role).
"""
from typing import Any, Mapping


def _as_text(valor: Any) -> str | None:
    texto = str(valor).strip() if valor not in (None, "") else ""
    return texto or None


def s3_client(
    auth: Mapping[str, Any] | None = None,
    *,
    region: str | None = None,
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
):
    """`boto3.client("s3")` with the credential's keys, region and endpoint.

    An explicit `region` wins over the credential's. Explicit
    `access_key_id`/`secret_access_key` only apply when the credential has no keys —
    they exist for the node's old fields (see SaveToS3), never to override the vault.
    """
    import boto3

    auth = auth or {}
    chave = _as_text(auth.get("access_key_id"))
    segredo = _as_text(auth.get("secret_access_key"))
    if not chave and not segredo:
        chave, segredo = _as_text(access_key_id), _as_text(secret_access_key)

    kwargs: dict[str, Any] = {}
    regiao = _as_text(region) or _as_text(auth.get("region"))
    if regiao:
        kwargs["region_name"] = regiao
    if chave:
        kwargs["aws_access_key_id"] = chave
    if segredo:
        kwargs["aws_secret_access_key"] = segredo
    endpoint = _as_text(auth.get("endpoint_url"))
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    # One session per call, not the module's default session: it is not
    # thread-safe, and the node's upload runs in `asyncio.to_thread`.
    return boto3.session.Session().client("s3", **kwargs)
