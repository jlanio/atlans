# flow/utils/executor_http.py
"""
Utilitario compartilhado para configurar requisicoes HTTP executor -> servidor.

Apos a migracao para mTLS, as chamadas dos flow nodes (publish_map, send_email,
response_node, change_detector) sao autenticadas pelo cert mTLS persistido no
diretorio EXECUTOR_CERT_DIR (criado durante o enrollment). Sem fallback para
X-Api-Key.

Retorna (base_url, headers, verify) onde:
  - base_url: URL HTTP do servidor
  - headers:  dict vazio (sem auth via header — mTLS resolve a identidade no TLS)
  - verify:   SSLContext com cert + chave + CA pinada do executor
              ou False em localhost (sem TLS).
"""
import logging
import os
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "host.docker.internal"})


def is_local_server(url: str) -> bool:
    """Detecta se a URL aponta para servidor local (dev/Docker).

    SEG: compara o HOSTNAME exato. Substring match (`"localhost" in url`)
    tratava `wss://localhost.evil.tld` — ou qualquer URL com "localhost" na
    query string — como local, desligando TLS e mTLS por completo
    (`verify=False` / `ssl_ctx=None`). Unica implementacao: o executor a
    reexporta de `executor.utils`.
    """
    try:
        host = urlparse(url).hostname
    except ValueError:
        return False
    return (host or "").lower() in _LOCAL_HOSTS


def get_agent_http_config(
    server_url: str | None = None,
) -> tuple[str, dict, "str | bool | object"]:
    """
    Retorna (base_url, headers, verify) prontos para uso com httpx.

    - Converte wss:// -> https:// e ws:// -> http://
    - Em localhost: verify=False (sem TLS local).
    - Em prod: verify=SSLContext com cert mTLS (autenticacao via cert).
    """
    if server_url is None:
        # Sem padrao, como executor/config.py:SERVER_URL: um padrao mandaria o
        # upload para uma instalacao que ninguem escolheu. Antes era
        # 'wss://localhost', que quebrava em silencio (Connection refused no
        # presign upload); agora a falha diz o que fazer.
        server_url = os.getenv("EXECUTOR_SERVER_URL", "").strip()
        if not server_url:
            raise RuntimeError(
                "EXECUTOR_SERVER_URL nao definida: o executor nao sabe com que "
                "servidor falar. O enrollment (`python -m executor enroll "
                "--server=...`) grava o valor no .env."
            )

    base_url = server_url.replace("wss://", "https://").replace("ws://", "http://")
    # Identidade vem do cert mTLS — nao precisamos mais de headers de auth.
    headers: dict = {}

    if is_local_server(base_url):
        verify: "str | bool | object" = False
    else:
        try:
            # Implementacao canonica vive em executor.utils — import lazy para
            # nao ler EXECUTOR_CERT_DIR em chamadas locais (verify=False).
            from executor.utils import build_mtls_ssl_context
            verify = build_mtls_ssl_context()
        except Exception as exc:
            # Diagnostico explicito: silenciar aqui leva a "CERTIFICATE_VERIFY_FAILED"
            # mais tarde sem pista do motivo real (path errado, formato de chave, etc).
            _logger.warning(
                "Falha ao montar SSLContext mTLS de EXECUTOR_CERT_DIR=%s — fallback "
                "para verify=True (provavel SSL: CERTIFICATE_VERIFY_FAILED contra "
                "a CA interna). Erro: %s: %s",
                os.getenv("EXECUTOR_CERT_DIR", "./certs"),
                type(exc).__name__, exc,
            )
            verify = True

    return base_url, headers, verify


def slugify(text: str) -> str:
    """Slug seguro para nome de arquivo/chave S3, em minúsculas.

    Variante minúscula de flow.utils.geo_helpers.slugify_label (implementação
    única). Mantida para os callers que dependem do lower-case (data_output,
    publish_map, send_email → chaves S3)."""
    from flow.utils.geo_helpers import slugify_label
    return slugify_label(text).lower()
