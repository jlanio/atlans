# tests/unit/test_fundos_do_mapa.py
"""
Os fundos de mapa são da instalação, e o código só traz as ruas.

Antes, o satélite e o híbrido da Carta eram a imagem do Google, fixa no código,
para toda instalação. Agora a URL de cada fundo com nome vem de MAPA_*_URL: o
servidor a injeta no nó Carta ao despachar (o executor não tem a
configuração), e sem ela só as ruas (OpenStreetMap) funcionam.

  CONFIG     MAPA_* no servidor, com validação do template; sem híbrido, o satélite
  INJEÇÃO    o despacho põe o fundo da instalação em cada nó Carta
  CARTA      o nó usa o injetado, o ambiente do executor ou o OSM — ou explica
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.fundos_do_mapa import SEM_FUNDO, injetar_fundos_de_mapa
from flow.utils.carta import RUAS_PADRAO, fundo_configurado, servidor_injetou

RAIZ = Path(__file__).resolve().parents[2]
SAT = {"url": "https://sat.example.org/{z}/{x}/{y}.jpg", "credito": "© Sat"}


# ── CONFIG ───────────────────────────────────────────────────────────────────

def _mapa_fundos(ambiente: dict[str, str]) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("MAPA_")}
    env.update(ambiente)
    r = subprocess.run(
        [sys.executable, "-c", "import app.core.config as c; print(sorted(c.MAPA_FUNDOS.items()))"],
        cwd=RAIZ, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout.strip()


def test_sem_configuracao_o_servidor_nao_tem_fundo_nenhum():
    assert _mapa_fundos({}) == "[]"


def test_o_servidor_le_os_fundos_e_ignora_o_que_nao_e_template():
    saida = _mapa_fundos({
        "MAPA_SATELITE_URL": " https://sat.example.org/{z}/{x}/{y}.jpg ", "MAPA_SATELITE_CREDITO": "© Sat",
        "MAPA_HIBRIDO_URL": "https://hib.example.org/tiles",  # sem {z}/{x}/{y}
        "MAPA_RUAS_URL": "file:///etc/{z}/{x}/{y}",
    })
    # O híbrido inválido é ignorado, e o híbrido cai no satélite, como no web.
    sat = "{'url': 'https://sat.example.org/{z}/{x}/{y}.jpg', 'credito': '© Sat'}"
    assert saida == f"[('hibrido', {sat}), ('satelite', {sat})]"


def test_o_hibrido_proprio_vence_o_satelite():
    saida = _mapa_fundos({
        "MAPA_SATELITE_URL": "https://sat.example.org/{z}/{x}/{y}.jpg",
        "MAPA_HIBRIDO_URL": "https://hib.example.org/{z}/{x}/{y}.jpg",
    })
    assert "('hibrido', {'url': 'https://hib.example.org/{z}/{x}/{y}.jpg'" in saida


# ── INJEÇÃO ──────────────────────────────────────────────────────────────────

def _definicao(*nos):
    return {"nodes": list(nos), "edges": []}


def test_o_despacho_poe_o_fundo_da_instalacao_no_no_carta():
    original = _definicao(
        {"id": "c1", "name": "CartaImagem", "properties": {"fundo": "satelite"}},
        {"id": "c2", "name": "CartaImagem", "data": {"properties": {"fundo": "hibrido"}}},
        {"id": "w1", "name": "WFS", "properties": {"fundo": "satelite"}},
    )

    enriquecida = injetar_fundos_de_mapa(original, {"satelite": SAT})

    assert enriquecida["nodes"][0]["properties"]["fundo_da_instalacao"] == SAT
    # Fundo sem configuração: a URL vai vazia — o executor sabe que o servidor
    # respondeu, e decide.
    assert enriquecida["nodes"][1]["data"]["properties"]["fundo_da_instalacao"] == SEM_FUNDO
    # Só o nó Carta; e a definição original fica intacta (é a gravada no banco).
    assert "fundo_da_instalacao" not in enriquecida["nodes"][2]["properties"]
    assert "fundo_da_instalacao" not in original["nodes"][0]["properties"]


FORJADO = {"url": "https://outro.example.org/{z}/{x}/{y}.png"}


def test_um_fundo_escrito_a_mao_no_workflow_nao_passa_por_fundo_da_instalacao():
    original = _definicao({"id": "c1", "name": "CartaImagem", "properties": {
        "fundo": "satelite", "fundo_da_instalacao": FORJADO,
    }})
    assert injetar_fundos_de_mapa(original, {})["nodes"][0]["properties"]["fundo_da_instalacao"] == SEM_FUNDO


def test_o_forjado_some_das_duas_formas_de_propriedades():
    """Achado da revisão: com `properties` E `data.properties` no mesmo nó, a
    injeção escrevia só no segundo — e o executor lê o primeiro."""
    original = _definicao({
        "id": "c1", "name": "CartaImagem",
        "properties": {"fundo": "satelite", "fundo_da_instalacao": FORJADO},
        "data": {"properties": {"fundo": "satelite", "fundo_da_instalacao": FORJADO}},
    })
    no = injetar_fundos_de_mapa(original, {"satelite": SAT})["nodes"][0]
    assert no["properties"]["fundo_da_instalacao"] == SAT
    assert no["data"]["properties"]["fundo_da_instalacao"] == SAT


async def test_o_despacho_injeta_na_raiz_e_nos_sub_fluxos(monkeypatch):
    """O envelope que sai para o executor, e não só a função: tirar a injeção
    de `_serializar_payload` tem de quebrar este teste."""
    import json
    from types import SimpleNamespace

    from app.core import config
    from app.services import workflow_execution_service as servico

    monkeypatch.setattr(config, "MAPA_FUNDOS", {"satelite": SAT})
    carta = {"id": "c1", "name": "CartaImagem", "properties": {"fundo": "satelite", "fundo_da_instalacao": FORJADO}}
    wf = SimpleNamespace(id_hash="wf-1", workspace_id="ws-1", pinned_outputs=None, pin_metadata=None)

    corpo = await servico._serializar_payload(
        wf, _definicao(dict(carta)), "job-1", None, False,
        pre_resolved={}, disabled_nodes=None,
        subworkflow_definitions={"sub-1": _definicao({**carta, "id": "c2", "properties": {"fundo": "hibrido"}})},
    )
    envelope = json.loads(corpo)
    raiz = envelope["workflow_definition"]["nodes"][0]["properties"]
    sub = envelope["subworkflow_definitions"]["sub-1"]["nodes"][0]["properties"]
    assert raiz["fundo_da_instalacao"] == SAT
    assert sub["fundo_da_instalacao"] == SEM_FUNDO


def test_sem_no_carta_a_definicao_volta_a_mesma():
    original = _definicao({"id": "w1", "name": "WFS", "properties": {}})
    assert injetar_fundos_de_mapa(original, {"satelite": SAT}) is original


# ── CARTA ────────────────────────────────────────────────────────────────────

def test_a_carta_usa_o_fundo_injetado():
    assert fundo_configurado("satelite", SAT, ambiente={}) == (SAT["url"], "© Sat")


def test_sem_injecao_vale_o_ambiente_do_executor():
    ambiente = {"MAPA_SATELITE_URL": "https://exec.example.org/{z}/{x}/{y}.png", "MAPA_SATELITE_CREDITO": "© Exec"}
    assert fundo_configurado("satelite", {}, ambiente=ambiente) == ("https://exec.example.org/{z}/{x}/{y}.png", "© Exec")


def test_as_ruas_caem_no_openstreetmap_e_o_satelite_em_nada():
    assert fundo_configurado("ruas", {}, ambiente={}) == RUAS_PADRAO
    assert fundo_configurado("satelite", {}, ambiente={}) is None
    assert fundo_configurado("hibrido", None, ambiente={}) is None


def test_no_executor_o_hibrido_tambem_cai_no_satelite():
    ambiente = {"MAPA_SATELITE_URL": "https://exec.example.org/{z}/{x}/{y}.png", "MAPA_SATELITE_CREDITO": "© Exec"}
    assert fundo_configurado("hibrido", {}, ambiente=ambiente) == ("https://exec.example.org/{z}/{x}/{y}.png", "© Exec")


def test_o_executor_sabe_se_o_servidor_mandou_o_fundo():
    assert servidor_injetou(SEM_FUNDO)
    assert servidor_injetou(SAT)
    # O padrão do campo: o servidor anterior a esta versão não manda nada.
    assert not servidor_injetou({})
    assert not servidor_injetou(None)


def test_um_template_invalido_diz_qual_variavel_conferir():
    with pytest.raises(ValueError, match="MAPA_SATELITE_URL"):
        fundo_configurado("satelite", {}, ambiente={"MAPA_SATELITE_URL": "https://sat.example.org/tiles"})


async def test_a_carta_sem_satelite_configurado_explica_o_que_fazer(monkeypatch):
    from flow.nodes.outputs.carta_imagem import CartaImagem

    monkeypatch.delenv("MAPA_SATELITE_URL", raising=False)
    no = CartaImagem(node_id="c1", parameters={"fundo": "satelite", "fundo_da_instalacao": SEM_FUNDO})
    with pytest.raises(ValueError, match="nao esta configurado nesta instalacao .MAPA_SATELITE_URL no servidor."):
        await no.execute({"output": None})


async def test_executor_novo_com_servidor_antigo_diz_o_que_houve(monkeypatch):
    """Achado da revisão: os executores pegam a `main` antes do deploy do
    servidor. Sem a injeção (servidor antigo) e sem MAPA_* no executor, a
    mensagem diz isso, e não que a instalação não tem o fundo."""
    from flow.nodes.outputs.carta_imagem import CartaImagem

    monkeypatch.delenv("MAPA_HIBRIDO_URL", raising=False)
    monkeypatch.delenv("MAPA_SATELITE_URL", raising=False)
    no = CartaImagem(node_id="c1", parameters={"fundo": "hibrido"})
    with pytest.raises(ValueError, match="servidor nao mandou o fundo 'hibrido'.*MAPA_HIBRIDO_URL ou MAPA_SATELITE_URL"):
        await no.execute({"output": None})
