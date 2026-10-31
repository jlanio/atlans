# tests/unit/test_ip_fixo_do_traefik.py
"""Traefik's fixed IP: the only origin of the executors' mTLS identity header.

The compose default was TRUSTED_PROXIES=172.16.0.0/12 — every container on the
Docker networks, the web and MinIO included, could present
X-Forwarded-Tls-Client-Cert-Info to the API (it still needed a valid serial).
Now Traefik gets a fixed address (TRAEFIK_IP) and the header is accepted only
from it (MTLS_PROXIES). TRUSTED_PROXIES itself stays wide on purpose: the web
container's /terra proxy forwards the client's X-Forwarded-For and has to stay
trusted for that.

`make bootstrap` picks the address; its functions are EXECUTED here, cut out of
the script between the markers — a copy would stay green with the script broken.
"""
import re
import subprocess
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
BOOTSTRAP = (RAIZ / "scripts" / "bootstrap.sh").read_text(encoding="utf-8")
COMPOSE = yaml.safe_load((RAIZ / "docker-compose.yml").read_text(encoding="utf-8"))


def _functions() -> str:
    trecho = re.search(r"# >>> faixas_ipv4.*?\n(.*?)# <<< faixas_ipv4", BOOTSTRAP, re.S)
    assert trecho, "o bootstrap.sh perdeu os marcadores das funções de faixas IPv4"
    return trecho.group(1)


def _bash(chamada: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + _functions() + "\n" + chamada],
        capture_output=True, text=True, timeout=30,
    )


@pytest.mark.parametrize("faixa, esperado", [
    ("172.29.0.0/16", "172.29.255.254"),
    ("172.18.0.0/16", "172.18.255.254"),
    ("10.20.30.0/24", "10.20.30.254"),
    ("192.168.0.0/20", "192.168.15.254"),
    ("172.29.7.9/16", "172.29.255.254"),     # host bits in the range: the network counts
])
def test_traefik_gets_the_last_address_of_the_range(faixa, esperado):
    r = _bash(f'last_usable "{faixa}"')
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == esperado
    # And it is inside the range, as the bootstrap later checks.
    assert _bash(f'cidr_contains "{faixa}" "{esperado}/32"').returncode == 0


@pytest.mark.parametrize("faixa", ["172.29.0.0", "172.29.0.0/31", "172.29.0.0/x"])
def test_no_address_for_a_range_that_has_no_room(faixa):
    assert _bash(f'last_usable "{faixa}"').returncode != 0


def test_the_bootstrap_only_pins_it_on_a_new_proxy_net():
    """Docker refuses a fixed IP on a network created without a declared range,
    as an old proxy-net may be: Traefik would not start on the next up."""
    bloco = BOOTSTRAP[BOOTSTRAP.index('TRAEFIK_IP_ENV="$(env_get TRAEFIK_IP)"'):]
    condicao = bloco[: bloco.index("then")]
    assert '[ -z "$TRAEFIK_IP_ENV" ]' in condicao
    assert '[ -z "$PROXY_SUBNET_ATUAL" ]' in condicao
    assert "upsert_env .env TRAEFIK_IP" in bloco


def test_traefik_takes_the_fixed_ip_on_proxy_net():
    redes = COMPOSE["services"]["traefik"]["networks"]
    assert redes == {"proxy-net": {"ipv4_address": "${TRAEFIK_IP:-}"}}


def test_the_cert_header_comes_from_traefik_alone_when_it_is_pinned():
    env = COMPOSE["x-api-env"]
    # TRAEFIK_IP first; without it (older installations), TRUSTED_PROXIES as before.
    assert env["MTLS_PROXIES"] == "${MTLS_PROXIES:-${TRAEFIK_IP:-${TRUSTED_PROXIES:-172.16.0.0/12}}}"
    # The XFF trust stays wide: the web container's /terra proxy needs it.
    assert env["TRUSTED_PROXIES"] == "${TRUSTED_PROXIES:-172.16.0.0/12}"


def test_the_dev_api_does_not_trust_production_traefik_ip():
    """traefik-dev has no fixed IP: with TRAEFIK_IP in the .env (bootstrap), a
    dev API trusting only it would refuse the local executor."""
    env = COMPOSE["services"]["api"]["environment"]
    assert "TRAEFIK_IP" not in env["MTLS_PROXIES"]
    assert "ipv4_address" not in str(COMPOSE["services"]["traefik-dev"]["networks"])
