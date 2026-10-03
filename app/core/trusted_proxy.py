# app/core/trusted_proxy.py
"""
Trust in the reverse proxy (Traefik) and resolution of the client's real IP.

Two problems solved here:

1. **Identity headers injected by the proxy.** `X-Forwarded-Tls-Client-Cert-Info`
   carries the executor's mTLS identity. Traefik only *overwrites* it when there
   is a client cert; a client without a cert would have its own header passed
   through intact. The strip happens in Traefik (`strip-executor-cert-header@file`),
   and the second layer is here: we only accept this header if the TCP connection
   came from a proxy listed in `TRUSTED_PROXIES`.

2. **The client's real IP** (rate limit key, enrollment audit trail, executor
   telemetry). Behind the proxy, `request.client.host` is always Traefik's IP —
   every limit became a single global bucket for the whole platform.
   `get_client_ip` reads `X-Forwarded-For` (XFF) when (and only when) the peer
   is a trusted proxy.

The production path is client -> Cloudflare -> Traefik -> API, and that changes
HOW the XFF has to be read:

- Cloudflare does not replace the XFF the client sent: it APPENDS the client's
  real IP to its end. The first element of the header is what the client
  wrote — forgeable. "Take the first IP" behind Cloudflare returned whatever
  the attacker wanted, a new identity per request.
- Traefik trusts the Cloudflare ranges (`forwardedHeaders.trustedIPs` in
  docker-compose.yml): it passes the XFF through as it came and appends its
  peer's IP (the Cloudflare edge). Coming from a peer outside those ranges
  (direct access to the origin, or AGENTS_HOST, which sits outside the CDN), it
  DISCARDS the received XFF and rewrites it with only the peer's IP.
- The API therefore sees `<what the client wrote>, <real IP>, <Cloudflare edge>`
  behind Cloudflare, and `<real IP>` without it. In both cases the RIGHT side is
  the trustworthy one: each element on the right was written by a hop we
  trust. That is why `get_client_ip` walks the header from right to left,
  skips the known proxies (`TRUSTED_PROXIES` plus `EDGE_PROXIES`) and returns
  the first IP left over.
- `CF-Connecting-IP` is NOT used: Cloudflare sets it, but whoever reaches the
  origin directly writes whatever they want in it, and Traefik only sanitizes
  the `X-Forwarded-*` headers — never the `CF-*` ones. Without a trusted origin
  for the header, it is worth as much as the first element of the XFF.

Variables (comma-separated IPs and CIDRs, e.g. `172.16.0.0/12,10.0.0.0/8`):

- `TRUSTED_PROXIES`: proxies that talk DIRECTLY to the API (the Traefik network).
  It is what authorizes the mTLS cert header and reading the XFF. Empty disables
  both checks — useful in dev, where the API is accessed directly without a proxy.
- `EDGE_PROXIES`: EDGE proxies that append the client to the XFF (Cloudflare).
  They are skipped in the right -> left walk and nothing more: they do NOT vouch
  for the mTLS cert header (`is_trusted_proxy` only looks at `TRUSTED_PROXIES` —
  Cloudflare is never the API's TCP peer, and the cert only makes sense coming
  from Traefik). Variable ABSENT = Cloudflare's published ranges
  (`CLOUDFLARE_RANGES`); `EDGE_PROXIES=` (empty) turns it off.
"""
import ipaddress
import os

from app.core.utils.logger import get_logger

logger = get_logger(__name__)

# Ranges published by Cloudflare at https://www.cloudflare.com/ips/
# (https://www.cloudflare.com/ips-v4 and https://www.cloudflare.com/ips-v6),
# copied on 2026-09-13. The IPv4 ones are the same as `forwardedHeaders.trustedIPs`
# in docker-compose.yml — when Cloudflare changes the list, update both.
CLOUDFLARE_RANGES = (
    "173.245.48.0/20,103.21.244.0/22,103.22.200.0/22,103.31.4.0/22,"
    "141.101.64.0/18,108.162.192.0/18,190.93.240.0/20,188.114.96.0/20,"
    "197.234.240.0/22,198.41.128.0/17,162.158.0.0/15,104.16.0.0/13,"
    "104.24.0.0/14,172.64.0.0/13,131.0.72.0/22,"
    "2400:cb00::/32,2606:4700::/32,2803:f800::/32,2405:b500::/32,"
    "2405:8100::/32,2a06:98c0::/29,2c0f:f248::/32"
)


def _parse_networks(raw: str, var: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """
    Convert `raw` (comma-separated IPs/CIDRs) into networks.

    `var` is the environment variable's name, only for the log message. Invalid
    entries are ignored with an error log instead of raising: a mistyped range
    must not break the module import — and the API — at startup.
    """
    nets = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            logger.error("%s: entrada invalida ignorada: %r", var, part)
    return nets


TRUSTED_PROXIES = _parse_networks(os.getenv("TRUSTED_PROXIES", ""), "TRUSTED_PROXIES")

# An ABSENT variable (None) is different from an EMPTY one (""): without it the
# Cloudflare list applies; an explicit `EDGE_PROXIES=` means "no edge proxy".
_edge_raw = os.getenv("EDGE_PROXIES")
EDGE_PROXIES = _parse_networks(
    CLOUDFLARE_RANGES if _edge_raw is None else _edge_raw, "EDGE_PROXIES"
)

if not TRUSTED_PROXIES:
    logger.warning(
        "TRUSTED_PROXIES vazio — headers de cert mTLS serao aceitos de qualquer "
        "origem e o rate limit usara o IP do peer direto. Configure em producao "
        "com a rede do Traefik (ex: 172.16.0.0/12)."
    )

if _edge_raw is None:
    _edge_mode = "faixas publicadas da Cloudflare (default)"
elif EDGE_PROXIES:
    _edge_mode = f"{len(EDGE_PROXIES)} faixa(s) configurada(s)"
else:
    _edge_mode = "desligado (nenhum proxy de borda)"
logger.info("EDGE_PROXIES: %s", _edge_mode)


def _in_any(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    return any(addr in net for net in nets)


def is_trusted_proxy(client_host: str | None) -> bool:
    """True if the TCP peer is a trusted proxy (or if the check is disabled)."""
    if not TRUSTED_PROXIES:
        return True  # checagem desativada — dev/local
    if not client_host:
        return False
    try:
        addr = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    return _in_any(addr, TRUSTED_PROXIES)


def get_client_ip(client_host: str | None, forwarded_for: str | None) -> str:
    """
    The client's real IP (rate limit, enrollment audit, telemetry).

    - `TRUSTED_PROXIES` empty, or peer outside it: returns the peer and IGNORES
      `X-Forwarded-For` — otherwise the client itself would forge the header and
      change "identity" on every request, defeating rate limit and audit.
    - Otherwise, walks the XFF from RIGHT to left: skips our infrastructure's
      hops (`TRUSTED_PROXIES`, contiguous on the right), then AT MOST ONE edge
      hop (`EDGE_PROXIES` — the Cloudflare edge that talked to Traefik) and
      returns the next element, whatever it is. That is the IP Cloudflare
      appended: that of the client that connected to it.
    - ONE edge hop, and not all of them: a Cloudflare Worker calling the
      installation reaches Cloudflare with the Workers' egress IP (which is
      within its ranges) and sends whatever XFF it wants. Skipping all the
      Cloudflare hops, the value written by the Worker became the identity — a
      new rate limit bucket per request. With a single hop, all Worker traffic
      lands on the Workers' egress IP.
    - If all elements are known proxies, returns the leftmost one
      (deterministic; only happens with traffic from the proxies themselves).
    - Empty or non-IP elements (`unknown`, `ip:port`, garbage, IPv6
      with a zone `fe80::1%eth0`) are skipped — only valid IPs are returned,
      in canonical form (`2001:DB8::9` -> `2001:db8::9`), so the same
      client always lands in the same bucket. If no element is valid,
      returns the peer.
    - No XFF: peer. No peer: "unknown".
    """
    if forwarded_for and TRUSTED_PROXIES and is_trusted_proxy(client_host):
        saltos = []  # valid IPs, from right to left
        for hop in reversed(forwarded_for.split(",")):
            try:
                addr = ipaddress.ip_address(hop.strip())
            except ValueError:
                continue  # empty or non-IP: skip
            if getattr(addr, "scope_id", None):
                continue  # `fe80::1%zone`: the zone is free text with no length limit
            saltos.append(addr)
        i = 0
        while i < len(saltos) and _in_any(saltos[i], TRUSTED_PROXIES):
            i += 1  # nossa infra, anexada a direita
        if i < len(saltos) and _in_any(saltos[i], EDGE_PROXIES):
            i += 1  # a Cloudflare edge, the one that talked to Traefik
        if i < len(saltos):
            return str(saltos[i])
        if saltos:
            return str(saltos[-1])  # so proxies conhecidos: o mais a esquerda
    return client_host or "unknown"
