"""
IP validation at CONNECT time for libraries that do their own HTTP (owslib).

`validate_url_ssrf` checks the URL the user typed, but owslib then resolves the
name again and follows redirects on its own: a name that resolves to a public
address for the check and to 169.254.169.254 a moment later (DNS rebinding), or
a public server answering `302 Location: http://10.0.0.5/`, still reached the
internal network. HttpRequest and the download pin the resolved IP; owslib has
no hook for that.

This module wraps urllib3's `create_connection` — the single place where
`requests` (and therefore owslib) opens a socket — so that, on a thread marked
with `conexoes_validadas()`, every connection, redirects included, resolves the
name, refuses internal addresses and connects to the address it validated.
Threads that are not marked go straight to the original function.
"""
from __future__ import annotations

import contextlib
import ipaddress
import socket
import threading
import urllib.request
from urllib.parse import urlparse

_estado = threading.local()
_instalado = False
_trava = threading.Lock()


def _hosts_de_proxy() -> set[str]:
    """Proxies the operator configured: the connection goes to them, not to the
    target, so their (often private) address is not the user's choice."""
    hosts: set[str] = set()
    for endereco in urllib.request.getproxies().values():
        with contextlib.suppress(Exception):
            alvo = endereco if "://" in endereco else f"http://{endereco}"
            host = urlparse(alvo).hostname
            if host:
                hosts.add(host.lower())
    return hosts


def _instalar() -> None:
    global _instalado
    with _trava:
        if _instalado:
            return
        import urllib3.util.connection as conexao

        from flow.utils.geo_helpers import _dangerous_address

        original = conexao.create_connection

        def create_connection(address, *args, **kwargs):
            if not getattr(_estado, "ativo", False):
                return original(address, *args, **kwargs)
            host, porta = address
            nome = (host or "").strip("[]").lower()
            if nome in _hosts_de_proxy():
                return original(address, *args, **kwargs)
            infos = socket.getaddrinfo(nome, porta, type=socket.SOCK_STREAM)
            enderecos: list[str] = []
            for info in infos:
                ip = str(info[4][0]).split("%")[0]
                if _dangerous_address(ipaddress.ip_address(ip)):
                    raise ValueError(
                        "Requisições para endereços internos/privados não são "
                        f"permitidas ({nome} → {ip})."
                    )
                enderecos.append(ip)
            ultimo: OSError | None = None
            for ip in dict.fromkeys(enderecos):
                try:
                    # Connects to the address just validated; TLS still checks
                    # the certificate against the original name (urllib3 passes
                    # server_hostname separately).
                    return original((ip, porta), *args, **kwargs)
                except OSError as exc:
                    ultimo = exc
            raise ultimo or OSError(f"Não foi possível conectar a {nome}.")

        conexao.create_connection = create_connection
        _instalado = True


@contextlib.contextmanager
def conexoes_validadas():
    """Validates every connection the CURRENT thread opens while the block lasts."""
    _instalar()
    anterior = getattr(_estado, "ativo", False)
    _estado.ativo = True
    try:
        yield
    finally:
        _estado.ativo = anterior
