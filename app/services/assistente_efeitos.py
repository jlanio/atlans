# app/services/assistente_efeitos.py
"""Which nodes of a definition act OUTSIDE the assistant's own sandbox.

The assistant creates and runs its own workflows without a click: that is what
makes the Home's answer reach the globe. That freedom was written for graphs
that read, transform and end in a `DataOutput` — whose only trace is an
artifact of the run itself. A definition the model authors can also carry nodes
that send, write or publish somewhere, and the model's prompt is fed text the
platform does not control (WFS layer metadata, Drive file names, other members'
workflow descriptions). Whatever acts outside therefore needs the person's
click, even in a workflow the assistant created.

"Acts outside" here means:
- an output node that leaves a trace beyond the run's own artifact (the
  flow-side `TEM_EFEITO_COLATERAL`, minus `DataOutput`): Drive files, a
  database, S3, the portal, e-mail, webhooks;
- `HttpRequest` with ANY method — a GET carries data in its query string too;
- `SubWorkflow`: it runs another workflow, possibly one of the person's;
- a trigger that fires on its own (schedule, webhook, file, geofence): the
  workflow would then run later with no click at all;
- any node that uses a stored credential (`credential_id`): it acts with the
  person's secrets.

The registry lookup fails CLOSED: a node type the registry does not know is
treated as acting, because there is no way to tell it is harmless.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Output nodes whose only trace is the run's own artifact.
_SAIDAS_DO_PROPRIO_RUN = frozenset({"DataOutput"})

# Nodes that act outside whatever their parameters say.
_SEMPRE_AGEM = frozenset({"HttpRequest", "SubWorkflow"})

# Triggers that make the workflow run later without anyone clicking.
_DISPAROS_AUTONOMOS = frozenset({"ScheduleTrigger", "WebhookTrigger", "FileTrigger", "GeofenceTrigger"})


def _tipo(no: Mapping[str, Any]) -> str:
    """The node type in either canvas format (`name` at the top or in `data`)."""
    dados = no.get("data") if isinstance(no.get("data"), Mapping) else {}
    return str(no.get("name") or dados.get("name") or no.get("type") or "")


def _propriedades(no: Mapping[str, Any]) -> Mapping[str, Any]:
    props = no.get("properties")
    if isinstance(props, Mapping):
        return props
    dados = no.get("data") if isinstance(no.get("data"), Mapping) else {}
    props = dados.get("properties")
    return props if isinstance(props, Mapping) else {}


def _rotulo(no: Mapping[str, Any], tipo: str) -> str:
    ident = no.get("id")
    return f"{tipo} ({ident})" if ident not in (None, "") else tipo


def _classe_age(tipo: str) -> bool:
    """Does the registered class declare an effect? Unknown type → yes."""
    from flow.registry import NODE_REGISTRY

    cls = NODE_REGISTRY.get(tipo)
    if cls is None:
        return True
    return bool(getattr(cls, "TEM_EFEITO_COLATERAL", False))


def nos_que_agem(definicao: Any) -> list[str]:
    """Labels (`Tipo (id)`) of the nodes that act outside, in definition order.

    Empty list = the graph only reads and transforms, and may go without a click.
    A definition that is not an object with a node list returns empty: there is
    nothing to run (the tool itself refuses it further on)."""
    if not isinstance(definicao, Mapping):
        return []
    nos = definicao.get("nodes")
    if not isinstance(nos, list):
        return []
    agem: list[str] = []
    for no in nos:
        if not isinstance(no, Mapping):
            continue
        tipo = _tipo(no)
        if tipo in _SAIDAS_DO_PROPRIO_RUN and not _propriedades(no).get("credential_id"):
            continue
        if (
            tipo in _SEMPRE_AGEM
            or tipo in _DISPAROS_AUTONOMOS
            or _propriedades(no).get("credential_id")
            or _classe_age(tipo)
        ):
            agem.append(_rotulo(no, tipo))
    return agem
