# app/core/trusted_proxy.py
"""
Confianca no proxy reverso (Traefik) e resolucao do IP real do cliente.

Dois problemas resolvidos aqui:

1. **Headers de identidade injetados pelo proxy.** `X-Forwarded-Tls-Client-Cert-Info`
   carrega a identidade mTLS do executor. O Traefik so o *sobrescreve* quando ha
   client cert; um cliente sem cert teria o header proprio repassado intacto.
   O strip acontece no Traefik (`strip-executor-cert-header@file`), e aqui fica a
   segunda camada: so aceitamos esse header se a conexao TCP veio de um proxy
   listado em `TRUSTED_PROXIES`.

2. **IP real do cliente** (chave de rate limit, trilha de auditoria do
   enrollment, telemetria do executor). Atras do proxy, `request.client.host` e
   sempre o IP do Traefik — todos os limites viravam um unico balde global para
   a plataforma inteira. `get_client_ip` le `X-Forwarded-For` (XFF) quando (e
   somente quando) o peer e um proxy confiavel.

O caminho em producao e cliente -> Cloudflare -> Traefik -> API, e isso muda
COMO o XFF tem de ser lido:

- A Cloudflare nao substitui o XFF que o cliente mandou: ela ANEXA o IP real
  do cliente ao fim dele. O primeiro elemento do header e o que o cliente
  escreveu — forjavel. "Pegar o primeiro IP" atras da Cloudflare devolvia o
  que o atacante quisesse, uma identidade nova por request.
- O Traefik confia nas faixas da Cloudflare (`forwardedHeaders.trustedIPs` no
  docker-compose.yml): repassa o XFF como veio e anexa o IP do seu peer (o
  edge da Cloudflare). Vindo de um peer fora dessas faixas (acesso direto ao
  origin, ou o AGENTS_HOST, que fica fora do CDN), ele DESCARTA o XFF recebido
  e o reescreve so com o IP do peer.
- A API ve, portanto, `<o que o cliente escreveu>, <IP real>, <edge Cloudflare>`
  atras da Cloudflare, e `<IP real>` sem ela. Nos dois casos o lado DIREITO e
  o confiavel: cada elemento a direita foi escrito por um salto em que
  confiamos. Por isso `get_client_ip` caminha o header da direita para a
  esquerda, pula os proxies conhecidos (`TRUSTED_PROXIES` mais `EDGE_PROXIES`)
  e devolve o primeiro IP que sobra.
- `CF-Connecting-IP` NAO e usado: a Cloudflare o define, mas quem chega direto
  ao origin escreve nele o que quiser, e o Traefik so saneia os
  `X-Forwarded-*` — nunca os `CF-*`. Sem uma origem confiavel para o header,
  ele vale tanto quanto o primeiro elemento do XFF.

Variaveis (IPs e CIDRs separados por virgula, ex: `172.16.0.0/12,10.0.0.0/8`):

- `TRUSTED_PROXIES`: proxies que falam DIRETAMENTE com a API (rede do Traefik).
  E o que autoriza o header de cert mTLS e a leitura do XFF. Vazio desativa
  ambas as checagens — util em dev, onde a API e acessada direto sem proxy.
- `EDGE_PROXIES`: proxies de BORDA que anexam o cliente ao XFF (Cloudflare).
  Sao pulados na caminhada direita -> esquerda e nada mais: NAO avalizam o
  header de cert mTLS (`is_trusted_proxy` olha so `TRUSTED_PROXIES` — a
  Cloudflare nunca e o peer TCP da API, e o cert so faz sentido vindo do
  Traefik). Variavel AUSENTE = faixas publicadas da Cloudflare
  (`CLOUDFLARE_RANGES`); `EDGE_PROXIES=` (vazia) desliga.
"""
import ipaddress
import os

from app.core.utils.logger import get_logger

logger = get_logger(__name__)

# Faixas publicadas pela Cloudflare em https://www.cloudflare.com/ips/
# (https://www.cloudflare.com/ips-v4 e https://www.cloudflare.com/ips-v6),
# copia de 2026-09-13. As IPv4 sao as mesmas de `forwardedHeaders.trustedIPs`
# no docker-compose.yml — quando a Cloudflare mudar a lista, atualize os dois.
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
    Converte `raw` (IPs/CIDRs separados por virgula) em redes.

    `var` e o nome da variavel de ambiente, so para a mensagem de log. Entradas
    invalidas sao ignoradas com log de erro em vez de levantar: uma faixa mal
    digitada nao pode derrubar o import do modulo — e a API — na subida.
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

# Variavel AUSENTE (None) e diferente de VAZIA (""): sem ela vale a lista da
# Cloudflare; `EDGE_PROXIES=` explicito significa "nenhum proxy de borda".
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
    """True se o peer TCP e um proxy confiavel (ou se a checagem esta desativada)."""
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
    IP real do cliente (rate limit, auditoria de enrollment, telemetria).

    - `TRUSTED_PROXIES` vazio, ou peer fora dele: devolve o peer e IGNORA o
      `X-Forwarded-For` — senao o proprio cliente forjaria o header e trocaria
      de "identidade" a cada request, anulando rate limit e auditoria.
    - Senao, caminha o XFF da DIREITA para a esquerda: pula os saltos da nossa
      infra (`TRUSTED_PROXIES`, contiguos a direita), depois NO MAXIMO UM salto
      de borda (`EDGE_PROXIES` — o edge da Cloudflare que falou com o Traefik)
      e devolve o elemento seguinte, seja ele qual for. Esse e o IP que a
      Cloudflare anexou: o do cliente que se conectou a ela.
    - UM salto de borda, e nao todos: um Cloudflare Worker que chama a
      instalacao chega a Cloudflare com o IP de saida dos Workers (que esta
      nas faixas dela) e manda o XFF que quiser. Pulando todos os saltos da
      Cloudflare, o valor escrito pelo Worker virava a identidade — um balde
      de rate limit novo por request. Com um salto so, todo trafego de Worker
      cai no IP de saida dos Workers.
    - Se todos os elementos sao proxies conhecidos, devolve o mais a esquerda
      (deterministico; so acontece com trafego dos proprios proxies).
    - Elementos vazios ou que nao sao IP (`unknown`, `ip:porta`, lixo, IPv6
      com zona `fe80::1%eth0`) sao pulados — so IPs validos sao devolvidos,
      na forma canonica (`2001:DB8::9` -> `2001:db8::9`), para o mesmo
      cliente cair sempre no mesmo balde. Se nenhum elemento e valido,
      devolve o peer.
    - Sem XFF: peer. Sem peer: "unknown".
    """
    if forwarded_for and TRUSTED_PROXIES and is_trusted_proxy(client_host):
        saltos = []  # IPs validos, da direita para a esquerda
        for hop in reversed(forwarded_for.split(",")):
            try:
                addr = ipaddress.ip_address(hop.strip())
            except ValueError:
                continue  # vazio ou nao-IP: pula
            if getattr(addr, "scope_id", None):
                continue  # `fe80::1%zona`: a zona e texto livre e sem limite de tamanho
            saltos.append(addr)
        i = 0
        while i < len(saltos) and _in_any(saltos[i], TRUSTED_PROXIES):
            i += 1  # nossa infra, anexada a direita
        if i < len(saltos) and _in_any(saltos[i], EDGE_PROXIES):
            i += 1  # um edge da Cloudflare, o que falou com o Traefik
        if i < len(saltos):
            return str(saltos[i])
        if saltos:
            return str(saltos[-1])  # so proxies conhecidos: o mais a esquerda
    return client_host or "unknown"
