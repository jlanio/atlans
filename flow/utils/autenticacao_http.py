# flow/utils/autenticacao_http.py
"""HTTP authentication and origin rules shared by the nodes that make requests.

They lived inside `flow/nodes/action/http_request.py` while HttpRequest was the
only node that sent a credential and followed redirects. DataInput's URL origin
does both too, and a second copy would let the two drift apart exactly where a
divergence leaks a secret (which header carries a credential, what counts as the
same origin). HttpRequest keeps importing them under its old private names.
"""
import base64
from typing import Any, Dict
from urllib.parse import urlparse

# Headers that carry a credential and must not cross a change of origin.
# It's the same list curl and requests drop when following a 3xx.
CREDENTIAL_HEADERS = frozenset({'authorization', 'cookie', 'proxy-authorization'})

_DEFAULT_PORTS = {'http': 80, 'https': 443}


def same_origin(a: str, b: str) -> bool:
    """Compares origin in the RFC 6454 sense: scheme, host and effective port."""
    def origem(u: str):
        p = urlparse(u)
        esquema = (p.scheme or '').lower()
        return (esquema, (p.hostname or '').lower(), p.port or _DEFAULT_PORTS.get(esquema))
    return origem(a) == origem(b)


def circuit_key(url: str) -> str:
    """The circuit-breaker key of an address: `http:` plus its host and port.

    Never the `user:password@` a URL may carry: the key is printed in the
    "temporarily unavailable" error stored with the run, and in the breaker's
    logs. The host is case-insensitive, so `Portal.gov.br` and `portal.gov.br`
    share one circuit.
    """
    try:
        netloc = urlparse(url).netloc
    except ValueError:  # an unbalanced `[`: the request fails on its own
        return 'http:(URL inválida)'
    return f"http:{netloc.rpartition('@')[2].lower() or '(sem host)'}"


def without_credentials(headers: Dict[str, str]) -> Dict[str, str]:
    """Copy of the headers without the ones that carry a secret."""
    return {k: v for k, v in headers.items() if k.lower() not in CREDENTIAL_HEADERS}


def apply_auth(headers: Dict[str, str], auth: Any) -> Dict[str, str]:
    """Builds the `Authorization` header from the resolved credential.

    The credential wins over an `Authorization` written by hand in the headers:
    whoever selected a credential expressed the stronger intent, and the
    opposite would let a header forgotten in the form silently drop the secret
    the user just chose.
    """
    if not isinstance(auth, dict):
        return headers

    tipo = auth.get('type')
    if not tipo:
        return headers
    if tipo not in ('http_bearer', 'http_basic'):
        # The resolver injects `http_auth` for WFS credentials too; one of
        # them chosen here would be ignored and the request would go out ANONYMOUS.
        raise ValueError(
            f"A credencial escolhida (tipo '{tipo}') não serve para requisição HTTP: "
            "use uma do tipo HTTP Bearer ou HTTP Basic."
        )

    # HTTP headers are case-insensitive, but dictionaries are not:
    # writing to `Authorization` left a hand-typed `authorization` standing
    # beside it, and the node sent TWO authentication headers — it's up to the
    # server to decide which one counts, and neither outcome is what the user asked for.
    for existente in [k for k in headers if k.lower() == 'authorization']:
        headers.pop(existente)

    if tipo == 'http_bearer':
        token = str(auth.get('token') or '').strip()
        if not token:
            raise ValueError(
                "A credencial Bearer selecionada não tem token preenchido."
            )
        headers['Authorization'] = f'Bearer {token}'
    elif tipo == 'http_basic':
        usuario = str(auth.get('username') or '')
        senha   = str(auth.get('password') or '')
        if not usuario:
            raise ValueError(
                "A credencial Basic selecionada não tem usuário preenchido."
            )
        par = base64.b64encode(f'{usuario}:{senha}'.encode('utf-8')).decode('ascii')
        headers['Authorization'] = f'Basic {par}'

    return headers


def exigir_credencial_resolvida(parametros: Dict[str, Any]) -> None:
    """Refuses to go out anonymous when the chosen credential was not resolved.

    The server REMOVES `credential_id` from the properties when injecting the
    resolved credential (see credential_resolver.inject_credentials). Arriving
    at the node with the id STILL present and without `http_auth` means the
    resolution didn't happen — credential deleted, outside the scope of whoever
    triggered it, or orphaned. Going ahead would send the request without
    authentication, and the error the user sees (a 401, or worse, a public
    version of the data) would be far from the cause.
    """
    if parametros.get('credential_id') and not parametros.get('http_auth'):
        raise ValueError(
            "A credencial escolhida para este nó não pôde ser resolvida — ela pode "
            "ter sido apagada, não estar acessível a quem disparou a execução, ou ser "
            "de um tipo que este nó não usa (Bearer ou Basic). "
            "A requisição NÃO foi enviada, para não sair sem autenticação."
        )
