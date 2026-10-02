# flow/utils/identidade.py
"""
Como o executor se apresenta a servidores de terceiros (tiles, Nominatim).

As políticas de uso do OpenStreetMap pedem um User-Agent que identifique a
aplicação e, de preferência, um contato. Um valor fixo no código (o site de uma
instalação, ou um nome que toda instalação repete) faria todas responderem por
uma só — e um bloqueio por abuso de uma pegaria as outras. Aqui ele leva o site
da instalação a que o executor pertence, sem configuração: o mesmo endereço que
o executor já usa para falar com o servidor.

Só a biblioteca padrão: o módulo roda no executor e na API.
"""
from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from urllib.parse import urlsplit

PRODUTO = "Atlans"
_PREFIXO_DO_HOST_DOS_EXECUTORES = "agents."


def site_da_instalacao(ambiente: Mapping[str, str] | None = None) -> str:
    """O site da instalação deste executor; vazio se não houver.

    EXECUTOR_PUBLIC_SERVER_URL, quando definido; senão o host dos executores
    (EXECUTOR_SERVER_URL) sem o `agents.` da convenção (o mesmo caminho do
    executor/_ca_bootstrap.py), em http(s).
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
    if ":" in host:  # IPv6 vai entre colchetes na URL
        host = f"[{host}]"
    return f"{partes.scheme}://{host}" + (f":{porta}" if porta else "")


def _interno(host: str) -> bool:
    """Um endereço que não serve de contato e só contaria a terceiros como é a
    rede da instalação: IP privado, de loopback ou reservado, e nome sem ponto
    (`localhost`, `api`)."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    return not ip.is_global


def user_agent(componente: str, ambiente: Mapping[str, str] | None = None) -> str:
    """`Atlans/<componente> (+<site da instalação>)`, ou sem o site se não houver."""
    site = site_da_instalacao(ambiente)
    return f"{PRODUTO}/{componente} (+{site})" if site else f"{PRODUTO}/{componente}"
