# app/services/fuso_do_agendamento.py
"""
The default time zone of schedules in the dispatched ScheduleTrigger node.

The `default` of the node's `timezone` field is read from the environment of WHOEVER
IMPORTS the node (`flow/utils/fuso.py`): on the server, `AGENDAMENTO_FUSO_PADRAO`; on
the executor, which does not have that variable, UTC. The server schedules by its own,
and the executor only echoes the parameters in the node's output (`info.timezone`) —
and the two diverged on a trigger without an explicit time zone. As it does with the
map basemaps (`fundos_do_mapa.py`), the server fills in the time zone when dispatching: a
ScheduleTrigger without `timezone` (or with it empty) goes out with the installation's
default time zone, in both forms of properties (`properties`, the one the executor
reads, and `data.properties`, the canvas's). An explicit time zone in the workflow stays.
"""
from __future__ import annotations

import copy

from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.services.fundos_do_mapa import _property_dicts

SCHEDULE_NODE = "ScheduleTrigger"


def injetar_fuso_do_agendamento(definition: dict, fuso: str | None = None) -> dict:
    """The definition with the installation time zone in each ScheduleTrigger without one (a copy, if it changes)."""
    nos = definition.get("nodes") if isinstance(definition, dict) else None
    if not nos or not any(isinstance(n, dict) and n.get("name") == SCHEDULE_NODE for n in nos):
        return definition
    fuso = fuso or FUSO_PADRAO_DO_AGENDAMENTO
    enriched = copy.deepcopy(definition)
    for no in enriched["nodes"]:
        if not isinstance(no, dict) or no.get("name") != SCHEDULE_NODE:
            continue
        for props in _property_dicts(no):
            if not str(props.get("timezone") or "").strip():
                props["timezone"] = fuso
    return enriched
