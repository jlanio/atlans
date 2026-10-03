# tests/unit/test_fundos_do_mapa.py
"""
Basemaps belong to the installation, and the code only ships the streets.

Before, the satellite and hybrid of the image map (Carta) were Google imagery, hard-coded,
for every installation. Now the URL of each named basemap comes from MAPA_*_URL: the
server injects it into the Carta (image map) node on dispatch (the executor does not have the
configuration), and without it only the streets (OpenStreetMap) work.

  CONFIG     MAPA_* on the server, with template validation; without hybrid, the satellite
  INJECTION  the dispatch puts the installation's basemap into each Carta node
  CARTA      the node uses the injected one, the executor's environment or OSM — or explains
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.fundos_do_mapa import NO_BASEMAP, inject_basemaps
from flow.utils.carta import RUAS_PADRAO, configured_basemap, server_injected

RAIZ = Path(__file__).resolve().parents[2]
SAT = {"url": "https://sat.example.org/{z}/{x}/{y}.jpg", "credito": "© Sat"}


# ── CONFIG ───────────────────────────────────────────────────────────────────

def _basemaps_for_env(ambiente: dict[str, str]) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("MAPA_")}
    env.update(ambiente)
    r = subprocess.run(
        [sys.executable, "-c", "import app.core.config as c; print(sorted(c.MAPA_FUNDOS.items()))"],
        cwd=RAIZ, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout.strip()


def test_without_config_the_server_has_no_basemap():
    assert _basemaps_for_env({}) == "[]"


def test_server_reads_basemaps_and_ignores_non_templates():
    saida = _basemaps_for_env({
        "MAPA_SATELITE_URL": " https://sat.example.org/{z}/{x}/{y}.jpg ", "MAPA_SATELITE_CREDITO": "© Sat",
        "MAPA_HIBRIDO_URL": "https://hib.example.org/tiles",  # without {z}/{x}/{y}
        "MAPA_RUAS_URL": "file:///etc/{z}/{x}/{y}",
    })
    # The invalid hybrid is ignored, and hybrid falls back to satellite, as on the web.
    sat = "{'url': 'https://sat.example.org/{z}/{x}/{y}.jpg', 'credito': '© Sat'}"
    assert saida == f"[('hibrido', {sat}), ('satelite', {sat})]"


def test_own_hybrid_beats_the_satellite():
    saida = _basemaps_for_env({
        "MAPA_SATELITE_URL": "https://sat.example.org/{z}/{x}/{y}.jpg",
        "MAPA_HIBRIDO_URL": "https://hib.example.org/{z}/{x}/{y}.jpg",
    })
    assert "('hibrido', {'url': 'https://hib.example.org/{z}/{x}/{y}.jpg'" in saida


# ── INJECTION ────────────────────────────────────────────────────────────────

def _definition(*nos):
    return {"nodes": list(nos), "edges": []}


def test_dispatch_puts_the_installation_basemap_in_the_map_node():
    original = _definition(
        {"id": "c1", "name": "CartaImagem", "properties": {"fundo": "satelite"}},
        {"id": "c2", "name": "CartaImagem", "data": {"properties": {"fundo": "hibrido"}}},
        {"id": "w1", "name": "WFS", "properties": {"fundo": "satelite"}},
    )

    enriched = inject_basemaps(original, {"satelite": SAT})

    assert enriched["nodes"][0]["properties"]["fundo_da_instalacao"] == SAT
    # Basemap without configuration: the URL goes empty — the executor knows the server
    # answered, and decides.
    assert enriched["nodes"][1]["data"]["properties"]["fundo_da_instalacao"] == NO_BASEMAP
    # Only the Carta node; and the original definition stays intact (it is the one stored in the database).
    assert "fundo_da_instalacao" not in enriched["nodes"][2]["properties"]
    assert "fundo_da_instalacao" not in original["nodes"][0]["properties"]


FORGED = {"url": "https://outro.example.org/{z}/{x}/{y}.png"}


def test_handwritten_workflow_basemap_does_not_pass_as_installation_basemap():
    original = _definition({"id": "c1", "name": "CartaImagem", "properties": {
        "fundo": "satelite", "fundo_da_instalacao": FORGED,
    }})
    assert inject_basemaps(original, {})["nodes"][0]["properties"]["fundo_da_instalacao"] == NO_BASEMAP


def test_forged_disappears_from_both_property_forms():
    """Review finding: with `properties` AND `data.properties` on the same node, the
    injection wrote only to the second — and the executor reads the first."""
    original = _definition({
        "id": "c1", "name": "CartaImagem",
        "properties": {"fundo": "satelite", "fundo_da_instalacao": FORGED},
        "data": {"properties": {"fundo": "satelite", "fundo_da_instalacao": FORGED}},
    })
    no = inject_basemaps(original, {"satelite": SAT})["nodes"][0]
    assert no["properties"]["fundo_da_instalacao"] == SAT
    assert no["data"]["properties"]["fundo_da_instalacao"] == SAT


async def test_dispatch_injects_at_root_and_in_sub_workflows(monkeypatch):
    """The envelope that goes out to the executor, not just the function: removing the injection
    from `_serializar_payload` must break this test."""
    import json
    from types import SimpleNamespace

    from app.core import config
    from app.services import workflow_execution_service as servico

    monkeypatch.setattr(config, "MAPA_FUNDOS", {"satelite": SAT})
    carta = {"id": "c1", "name": "CartaImagem", "properties": {"fundo": "satelite", "fundo_da_instalacao": FORGED}}
    wf = SimpleNamespace(id_hash="wf-1", workspace_id="ws-1", pinned_outputs=None, pin_metadata=None)

    corpo = await servico._serializar_payload(
        wf, _definition(dict(carta)), "job-1", None, False,
        pre_resolved={}, disabled_nodes=None,
        subworkflow_definitions={"sub-1": _definition({**carta, "id": "c2", "properties": {"fundo": "hibrido"}})},
    )
    envelope = json.loads(corpo)
    raiz = envelope["workflow_definition"]["nodes"][0]["properties"]
    sub = envelope["subworkflow_definitions"]["sub-1"]["nodes"][0]["properties"]
    assert raiz["fundo_da_instalacao"] == SAT
    assert sub["fundo_da_instalacao"] == NO_BASEMAP


def test_without_map_node_the_definition_comes_back_unchanged():
    original = _definition({"id": "w1", "name": "WFS", "properties": {}})
    assert inject_basemaps(original, {"satelite": SAT}) is original


# ── CARTA ────────────────────────────────────────────────────────────────────

def test_map_uses_the_injected_basemap():
    assert configured_basemap("satelite", SAT, ambiente={}) == (SAT["url"], "© Sat")


def test_without_injection_the_executor_environment_applies():
    ambiente = {"MAPA_SATELITE_URL": "https://exec.example.org/{z}/{x}/{y}.png", "MAPA_SATELITE_CREDITO": "© Exec"}
    assert configured_basemap("satelite", {}, ambiente=ambiente) == ("https://exec.example.org/{z}/{x}/{y}.png", "© Exec")


def test_streets_fall_back_to_openstreetmap_and_satellite_to_nothing():
    assert configured_basemap("ruas", {}, ambiente={}) == RUAS_PADRAO
    assert configured_basemap("satelite", {}, ambiente={}) is None
    assert configured_basemap("hibrido", None, ambiente={}) is None


def test_on_executor_hybrid_also_falls_back_to_satellite():
    ambiente = {"MAPA_SATELITE_URL": "https://exec.example.org/{z}/{x}/{y}.png", "MAPA_SATELITE_CREDITO": "© Exec"}
    assert configured_basemap("hibrido", {}, ambiente=ambiente) == ("https://exec.example.org/{z}/{x}/{y}.png", "© Exec")


def test_executor_knows_whether_the_server_sent_the_basemap():
    assert server_injected(NO_BASEMAP)
    assert server_injected(SAT)
    # The field's default: a server older than this version sends nothing.
    assert not server_injected({})
    assert not server_injected(None)


def test_invalid_template_says_which_variable_to_check():
    with pytest.raises(ValueError, match="MAPA_SATELITE_URL"):
        configured_basemap("satelite", {}, ambiente={"MAPA_SATELITE_URL": "https://sat.example.org/tiles"})


async def test_map_without_configured_satellite_explains_what_to_do(monkeypatch):
    from flow.nodes.outputs.carta_imagem import CartaImagem

    monkeypatch.delenv("MAPA_SATELITE_URL", raising=False)
    no = CartaImagem(node_id="c1", parameters={"fundo": "satelite", "fundo_da_instalacao": NO_BASEMAP})
    with pytest.raises(ValueError, match="nao esta configurado nesta instalacao .MAPA_SATELITE_URL no servidor."):
        await no.execute({"output": None})


async def test_new_executor_with_old_server_says_what_happened(monkeypatch):
    """Review finding: the executors pick up `main` before the server
    deploy. Without the injection (old server) and without MAPA_* on the executor, the
    message says so, and not that the installation does not have the basemap."""
    from flow.nodes.outputs.carta_imagem import CartaImagem

    monkeypatch.delenv("MAPA_HIBRIDO_URL", raising=False)
    monkeypatch.delenv("MAPA_SATELITE_URL", raising=False)
    no = CartaImagem(node_id="c1", parameters={"fundo": "hibrido"})
    with pytest.raises(ValueError, match="servidor nao mandou o fundo 'hibrido'.*MAPA_HIBRIDO_URL ou MAPA_SATELITE_URL"):
        await no.execute({"output": None})
