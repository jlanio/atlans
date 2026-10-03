# flow/utils/identidade.py
"""
How the executor introduces itself to third-party servers (tiles, Nominatim).

OpenStreetMap's usage policies ask for a User-Agent that identifies the
application and, preferably, a contact. A value fixed in code (the site of one
installation, or a name every installation repeats) would make all of them answer
as one — and an abuse block on one would catch the others. Here it carries the
site of the installation the executor belongs to, with no configuration: the same
address the executor already uses to talk to the server.

Standard library only: the module runs in the executor and in the API.
"""
from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from urllib.parse import urlsplit

PRODUTO = "Atlans"
_PREFIXO_DO_HOST_DOS_EXECUTORES = "agents."


def site_da_instalacao(ambiente: Mapping[str, str] | None = None) -> str:
    """The site of this executor's installation; empty if there is none.

    EXECUTOR_PUBLIC_SERVER_URL, when defined; otherwise the executors' host
    (EXECUTOR_SERVER_URL) without the conventional `agents.` (the same path as
    executor/_ca_bootstrap.py), in http(s).
    """
    ambiente = os.environ if ambiente is None else ambiente
    publico = (ambiente.get("EXECUTOR_PUBLIC_SERVER_URL") or "").strip()
    url = publico or (ambiente.get("EXECUTOR_SERVER_URL") or "").strip()
    if not url:
        return ""
    if url.startswith("wss://"):
        url = "https://" + url[len("wss://"):]
    elif url.startswith("ws://"):
        url = "http://" + url[len("ws://"):]
    try:
        partes = urlsplit(url)
        host, porta = (partes.hostname or "").lower(), partes.port
    except ValueError:
        return ""
    if partes.scheme not in ("http", "https") or not host:
        return ""
    if not publico and host.startswith(_PREFIXO_DO_HOST_DOS_EXECUTORES):
        host = host[len(_PREFIXO_DO_HOST_DOS_EXECUTORES):]
    if _interno(host):
        return ""
    if ":" in host:  # IPv6 goes in brackets in the URL
        host = f"[{host}]"
    return f"{partes.scheme}://{host}" + (f":{porta}" if porta else "")


def _interno(host: str) -> bool:
    """An address that is no use as a contact and would only tell third parties what
    the installation's network looks like: a private, loopback or reserved IP, and
    a name without a dot (`localhost`, `api`)."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    return not ip.is_global


def user_agent(componente: str, ambiente: Mapping[str, str] | None = None) -> str:
    """`Atlans/<componente> (+<site da instalação>)` (component, installation site), or without the site if there is none."""
    site = site_da_instalacao(ambiente)
    return f"{PRODUTO}/{componente} (+{site})" if site else f"{PRODUTO}/{componente}"
