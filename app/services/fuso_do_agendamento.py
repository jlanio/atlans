# app/services/fuso_do_agendamento.py
"""
O fuso padrão dos agendamentos no nó ScheduleTrigger despachado.

O `default` do campo `timezone` do nó é lido do ambiente de QUEM IMPORTA o nó
(`flow/utils/fuso.py`): no servidor, `AGENDAMENTO_FUSO_PADRAO`; no executor,
que não tem essa variável, UTC. O servidor agenda pelo dele, e o executor só
repete os parâmetros na saída do nó (`info.timezone`) — e os dois divergiam
num gatilho sem fuso explícito. Como faz com os fundos de mapa
(`fundos_do_mapa.py`), o servidor preenche o fuso ao despachar: um
ScheduleTrigger sem `timezone` (ou com ele vazio) sai com o fuso padrão da
instalação, nas duas formas de propriedades (`properties`, a que o executor
lê, e `data.properties`, a do canvas). Um fuso explícito no workflow fica.
"""
from __future__ import annotations

import copy

from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.services.fundos_do_mapa import _propriedades

NO_DO_AGENDAMENTO = "ScheduleTrigger"


def injetar_fuso_do_agendamento(definition: dict, fuso: str | None = None) -> dict:
    """A definição com o fuso da instalação em cada ScheduleTrigger sem fuso (cópia, se mudar)."""
    nos = definition.get("nodes") if isinstance(definition, dict) else None
    if not nos or not any(isinstance(n, dict) and n.get("name") == NO_DO_AGENDAMENTO for n in nos):
        return definition
    fuso = fuso or FUSO_PADRAO_DO_AGENDAMENTO
    enriched = copy.deepcopy(definition)
    for no in enriched["nodes"]:
        if not isinstance(no, dict) or no.get("name") != NO_DO_AGENDAMENTO:
            continue
        for props in _propriedades(no):
            if not str(props.get("timezone") or "").strip():
                props["timezone"] = fuso
    return enriched
