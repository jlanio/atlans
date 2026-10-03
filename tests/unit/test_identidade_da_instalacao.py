# tests/unit/test_identidade_da_instalacao.py
"""
The executor presents itself to third parties with YOUR installation's site.

Before, the Carta sent `Atlans/carta (+https://atlans.example.org)` on every tile
request, from any installation, and the Geocode sent `atlas-studio-geocode/1.0` (the
product's old name, with no contact), the same in all of them. OSM's policy asks for
a User-Agent that identifies the application: with a single value, an abuse block
on one installation would hit the others. And the Geocode only talked to the
public Nominatim; now NOMINATIM_URL points to a self-hosted one.
"""
from __future__ import annotations

import sys
import types

import pandas as pd
import pytest

from flow.nodes.action import geocode
from flow.utils.identidade import site_da_instalacao, user_agent


@pytest.mark.parametrize("ambiente, site", [
    # The quickstart convention: the executors' host with `agents.`.
    ({"EXECUTOR_SERVER_URL": "wss://agents.atlans.example.org"}, "https://atlans.example.org"),
    ({"EXECUTOR_SERVER_URL": "wss://Agents.Atlans.Example.org:8443/"}, "https://atlans.example.org:8443"),
    # Without the convention, the host as it came.
    ({"EXECUTOR_SERVER_URL": "wss://executores.example.org"}, "https://executores.example.org"),
    # The explicit override wins, and does not lose an `agents.` that is genuine.
    ({"EXECUTOR_SERVER_URL": "wss://agents.x.org", "EXECUTOR_PUBLIC_SERVER_URL": "https://agents.y.org"},
     "https://agents.y.org"),
    ({}, ""),
    ({"EXECUTOR_SERVER_URL": "ftp://x.org"}, ""),
    ({"EXECUTOR_SERVER_URL": "wss://[::1"}, ""),
    # Public address by IP: valid as a contact; IPv6 in square brackets.
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
    "ws://api:8000",           # container name, no domain
])
def test_endereco_interno_nao_vai_para_terceiros(servidor):
    """Review finding: `ws://10.0.0.5:8000` became
    `Atlans/carta (+http://10.0.0.5:8000)` — the installation's internal network in
    the User-Agent of every tile request, without serving as a contact."""
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
    """The fake geopy: records how the Nominatim was constructed."""
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
    """Review finding: the web app saves the defaults into the node. With an empty
    default, an executor older than this version called Nominatim with an empty
    User-Agent, and geopy refuses it (ConfigurationError)."""
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
