# tests/unit/test_identidade_da_instalacao.py
"""
O executor se apresenta a terceiros com o site da SUA instalação.

Antes, a Carta mandava `Atlans/carta (+https://atlans.example.org)` em todo pedido de
tile, de qualquer instalação, e o Geocode mandava `atlas-studio-geocode/1.0` (o
nome antigo do produto, sem contato), igual em todas. A política do OSM pede um
User-Agent que identifique a aplicação: com um valor só, um bloqueio por abuso
de uma instalação pegaria as outras. E o Geocode só falava com o Nominatim
público; agora NOMINATIM_URL aponta para um próprio.
"""
from __future__ import annotations

import sys
import types

import pandas as pd
import pytest

from flow.nodes.action import geocode
from flow.utils.identidade import site_da_instalacao, user_agent


@pytest.mark.parametrize("ambiente, site", [
    # A convenção do quickstart: o host dos executores com `agents.`.
    ({"EXECUTOR_SERVER_URL": "wss://agents.atlans.example.org"}, "https://atlans.example.org"),
    ({"EXECUTOR_SERVER_URL": "wss://Agents.Atlans.Example.org:8443/"}, "https://atlans.example.org:8443"),
    # Sem a convenção, o host como veio.
    ({"EXECUTOR_SERVER_URL": "wss://executores.example.org"}, "https://executores.example.org"),
    # O override explícito vence, e não perde um `agents.` que seja de verdade.
    ({"EXECUTOR_SERVER_URL": "wss://agents.x.org", "EXECUTOR_PUBLIC_SERVER_URL": "https://agents.y.org"},
     "https://agents.y.org"),
    ({}, ""),
    ({"EXECUTOR_SERVER_URL": "ftp://x.org"}, ""),
    ({"EXECUTOR_SERVER_URL": "wss://[::1"}, ""),
    # Endereço público por IP: vale como contato; o IPv6, entre colchetes.
    ({"EXECUTOR_SERVER_URL": "wss://8.8.8.8:8443"}, "https://8.8.8.8:8443"),
    ({"EXECUTOR_SERVER_URL": "wss://[2001:4860::5]:8443"}, "https://[2001:4860::5]:8443"),
])
def test_o_site_da_instalacao(ambiente, site):
    assert site_da_instalacao(ambiente) == site


@pytest.mark.parametrize("servidor", [
    "ws://localhost:8000",
    "ws://10.0.0.5:8000",
    "wss://192.168.1.20",
    "ws://127.0.0.1:8000",
    "wss://[fd00::5]:8443",
    "ws://api:8000",           # nome de container, sem domínio
])
def test_endereco_interno_nao_vai_para_terceiros(servidor):
    """Achado da revisão: `ws://10.0.0.5:8000` virava
    `Atlans/carta (+http://10.0.0.5:8000)` — a rede interna da instalação no
    User-Agent de todo pedido de tile, sem servir de contato."""
    assert site_da_instalacao({"EXECUTOR_SERVER_URL": servidor}) == ""
    assert user_agent("carta", {"EXECUTOR_SERVER_URL": servidor}) == "Atlans/carta"


def test_o_user_agent_leva_o_site_ou_so_o_produto():
    assert user_agent("carta", {"EXECUTOR_SERVER_URL": "wss://agents.atlans.example.org"}) == \
        "Atlans/carta (+https://atlans.example.org)"
    assert user_agent("geocode", {}) == "Atlans/geocode"


@pytest.mark.parametrize("valor, esperado", [
    ("", {}),
    ("https://nominatim.example.org/", {"domain": "nominatim.example.org", "scheme": "https"}),
    ("http://geo.interno:8080/nominatim", {"domain": "geo.interno:8080/nominatim", "scheme": "http"}),
])
def test_o_servidor_do_nominatim(valor, esperado):
    assert geocode._servidor_nominatim({"NOMINATIM_URL": valor}) == esperado


def test_nominatim_url_que_nao_e_url_explica():
    with pytest.raises(ValueError, match="NOMINATIM_URL"):
        geocode._servidor_nominatim({"NOMINATIM_URL": "nominatim.example.org"})


@pytest.fixture
def geopy_falso(monkeypatch):
    """O geopy de mentira: registra como o Nominatim foi construído."""
    construidos: list[dict] = []

    class Nominatim:
        def __init__(self, **kw):
            construidos.append(kw)

        def geocode(self, endereco):
            return types.SimpleNamespace(latitude=-10.0, longitude=-50.0)

    geocoders = types.ModuleType("geopy.geocoders")
    geocoders.Nominatim = Nominatim
    limitador = types.ModuleType("geopy.extra.rate_limiter")
    limitador.RateLimiter = lambda f, **kw: f
    monkeypatch.setitem(sys.modules, "geopy.geocoders", geocoders)
    monkeypatch.setitem(sys.modules, "geopy.extra.rate_limiter", limitador)
    return construidos


async def test_o_geocode_se_apresenta_com_o_site_da_instalacao(geopy_falso, monkeypatch):
    monkeypatch.setenv("EXECUTOR_SERVER_URL", "wss://agents.atlans.example.org")
    monkeypatch.delenv("EXECUTOR_PUBLIC_SERVER_URL", raising=False)
    monkeypatch.setenv("NOMINATIM_URL", "https://nominatim.example.org")
    no = geocode.GeocodeNode(node_id="g1", parameters={"delay_seconds": 1.1})

    saida = await no.execute({"output": pd.DataFrame({"address": ["Rua A, 1"]})})

    assert geopy_falso == [{
        "user_agent": "Atlans/geocode (+https://atlans.example.org)",
        "domain": "nominatim.example.org", "scheme": "https",
    }]
    assert bool(saida["output"]["geocoded"].iloc[0])


def test_o_catalogo_mantem_o_padrao_antigo_do_campo():
    """Achado da revisão: o web grava os padrões no nó. Com o padrão vazio, um
    executor anterior a esta versão chamava o Nominatim com User-Agent vazio,
    e o geopy recusa (ConfigurationError)."""
    campos = {c["name"]: c for c in geocode.GeocodeNode.description()["properties"]}
    assert campos["user_agent"]["default"] == geocode.USER_AGENT_ANTIGO == "atlas-studio-geocode/1.0"


@pytest.mark.parametrize("valor", ["", "  ", "atlas-studio-geocode/1.0", " atlas-studio-geocode/1.0 "])
async def test_vazio_e_o_padrao_antigo_viram_o_da_instalacao(geopy_falso, monkeypatch, valor):
    monkeypatch.setenv("EXECUTOR_SERVER_URL", "wss://agents.atlans.example.org")
    monkeypatch.delenv("EXECUTOR_PUBLIC_SERVER_URL", raising=False)
    monkeypatch.delenv("NOMINATIM_URL", raising=False)
    no = geocode.GeocodeNode(node_id="g1", parameters={"user_agent": valor})

    await no.execute({"output": pd.DataFrame({"address": ["Rua A, 1"]})})

    assert geopy_falso == [{"user_agent": "Atlans/geocode (+https://atlans.example.org)"}]


async def test_o_user_agent_do_no_vence(geopy_falso, monkeypatch):
    monkeypatch.delenv("NOMINATIM_URL", raising=False)
    no = geocode.GeocodeNode(node_id="g1", parameters={"user_agent": "MeuApp/2.0 (eu@example.org)"})

    await no.execute({"output": pd.DataFrame({"address": ["Rua A, 1"]})})

    assert geopy_falso == [{"user_agent": "MeuApp/2.0 (eu@example.org)"}]
