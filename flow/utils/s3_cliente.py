# flow/utils/s3_cliente.py
"""Cliente boto3 a partir dos campos da credencial `s3` do cofre.

Uma implementação para os dois lados: o nó SaveToS3 (no executor, com o
`s3_auth` que o servidor injeta a partir da credencial escolhida) e o teste de
conexão da credencial (na API). Antes cada um montava a sessão à sua maneira: o
nó com chaves digitadas na definition — o segredo em texto puro no banco, no
histórico de versões e na leitura do MCP — e sem `endpoint_url`, então MinIO e
S3-compatíveis ficavam de fora; o teste com os campos da credencial.

Os nomes dos campos são os do catálogo (`app/core/credentials/schemas.py`):
`access_key_id`, `secret_access_key`, `region`, `bucket`, `endpoint_url`.
Campo vazio não vai ao boto3: sem chaves, vale a cadeia padrão dele (variáveis
de ambiente, `~/.aws/credentials`, IAM role).
"""
from typing import Any, Mapping


def _texto(valor: Any) -> str | None:
    texto = str(valor).strip() if valor not in (None, "") else ""
    return texto or None


def cliente_s3(
    auth: Mapping[str, Any] | None = None,
    *,
    region: str | None = None,
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
):
    """`boto3.client("s3")` com as chaves, a região e o endpoint da credencial.

    `region` explícita vence a da credencial. `access_key_id`/`secret_access_key`
    explícitos só valem quando a credencial não traz chaves — existem para os
    campos antigos do nó (ver SaveToS3), nunca para sobrepor o cofre.
    """
    import boto3

    auth = auth or {}
    chave = _texto(auth.get("access_key_id"))
    segredo = _texto(auth.get("secret_access_key"))
    if not chave and not segredo:
        chave, segredo = _texto(access_key_id), _texto(secret_access_key)

    kwargs: dict[str, Any] = {}
    regiao = _texto(region) or _texto(auth.get("region"))
    if regiao:
        kwargs["region_name"] = regiao
    if chave:
        kwargs["aws_access_key_id"] = chave
    if segredo:
        kwargs["aws_secret_access_key"] = segredo
    endpoint = _texto(auth.get("endpoint_url"))
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    # Uma sessão por chamada, e não a sessão padrão do módulo: ela não é segura
    # entre threads, e o upload do nó roda em `asyncio.to_thread`.
    return boto3.session.Session().client("s3", **kwargs)
