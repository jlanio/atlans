# tests/unit/test_fuso_do_agendamento_no_despacho.py
"""
The default schedule time zone goes into the dispatched ScheduleTrigger.

The `default` of the node's `timezone` field is read from the environment of whoever imports the node:
on the server, AGENDAMENTO_FUSO_PADRAO; on the executor, which does not have the variable,
UTC. On a trigger with no explicit time zone, the server scheduled in one time zone and the
executor repeated another in the node's output (`info.timezone`). The server now fills in the
time zone on dispatch, as it does with the basemaps.
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
    # A copy: the saved definition does not change; the other node is not touched.
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
    # The same place the basemaps go in: the envelope that goes to the executor.
    fonte = open(workflow_execution_service.__file__, encoding="utf-8").read()
    assert "injetar_fuso_do_agendamento(enriched)" in fonte
    assert "injetar_fuso_do_agendamento(sub)" in fonte
