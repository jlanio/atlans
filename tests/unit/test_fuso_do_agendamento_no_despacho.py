# tests/unit/test_fuso_do_agendamento_no_despacho.py
"""
O fuso padrão dos agendamentos vai no ScheduleTrigger despachado.

O `default` do campo `timezone` do nó é lido do ambiente de quem importa o nó:
no servidor, AGENDAMENTO_FUSO_PADRAO; no executor, que não tem a variável,
UTC. Num gatilho sem fuso explícito, o servidor agendava num fuso e o executor
repetia outro na saída do nó (`info.timezone`). O servidor passa a preencher o
fuso ao despachar, como faz com os fundos de mapa.
"""
from __future__ import annotations

from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.services import workflow_execution_service
from app.services.fuso_do_agendamento import injetar_fuso_do_agendamento


def _definicao(**props):
    return {
        "nodes": [
            {"id": "t", "name": "ScheduleTrigger", "properties": dict(props), "data": {"properties": dict(props)}},
            {"id": "h", "name": "HttpRequest", "properties": {"url": "https://example.org"}},
        ],
        "edges": [],
    }


def test_sem_fuso_o_despacho_poe_o_da_instalacao_nas_duas_formas():
    original = _definicao(cron="0 9 * * *")
    enriched = injetar_fuso_do_agendamento(original)
    gatilho = enriched["nodes"][0]
    assert gatilho["properties"]["timezone"] == FUSO_PADRAO_DO_AGENDAMENTO
    assert gatilho["data"]["properties"]["timezone"] == FUSO_PADRAO_DO_AGENDAMENTO
    # Cópia: a definição salva não muda; o outro nó não é tocado.
    assert "timezone" not in original["nodes"][0]["properties"]
    assert enriched["nodes"][1] == original["nodes"][1]


def test_fuso_vazio_conta_como_ausente_e_explicito_fica():
    enriched = injetar_fuso_do_agendamento(_definicao(cron="0 9 * * *", timezone="  "))
    assert enriched["nodes"][0]["properties"]["timezone"] == FUSO_PADRAO_DO_AGENDAMENTO
    enriched = injetar_fuso_do_agendamento(_definicao(cron="0 9 * * *", timezone="Europe/Lisbon"))
    assert enriched["nodes"][0]["properties"]["timezone"] == "Europe/Lisbon"
    assert injetar_fuso_do_agendamento(_definicao(cron="0 9 * * *"), fuso="Pacific/Auckland")["nodes"][0]["properties"]["timezone"] == "Pacific/Auckland"


def test_sem_gatilho_a_definicao_volta_igual_e_e_o_mesmo_objeto():
    definicao = {"nodes": [{"id": "h", "name": "HttpRequest", "properties": {}}], "edges": []}
    assert injetar_fuso_do_agendamento(definicao) is definicao
    assert injetar_fuso_do_agendamento({}) == {}


def test_o_despacho_passa_pela_injecao():
    # O mesmo lugar em que os fundos de mapa entram: o envelope que vai ao executor.
    fonte = open(workflow_execution_service.__file__, encoding="utf-8").read()
    assert "injetar_fuso_do_agendamento(enriched)" in fonte
    assert "injetar_fuso_do_agendamento(sub)" in fonte
