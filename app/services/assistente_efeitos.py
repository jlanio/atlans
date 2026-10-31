# app/services/assistente_efeitos.py
"""Which nodes of a definition act OUTSIDE the assistant's own sandbox.

The assistant creates and runs its own workflows without a click: that is what
makes the Home's answer reach the globe. That freedom was written for graphs
that read, transform and end in a run artifact. A definition the model authors
can also carry nodes that send, write or publish somewhere, and the model's
prompt is fed text the platform does not control (WFS layer metadata, Drive
file names, other members' workflow descriptions). Whatever acts outside
therefore needs the person's click, even in a workflow the assistant created.

"Acts outside" here means:
- writing anywhere but the run's own artifact: the shared Drive (including
  `DataOutput` with `context=drive`, which can overwrite a file other workflows
  read), a database, S3, the portal, e-mail, webhooks;
- `HttpRequest` with ANY method — a GET carries data in its query string too;
- `SubWorkflow`: it runs another workflow, possibly one of the person's;
- a node that reads a URL built from an expression (`{{ ... }}`): the data of
  the run can leave in the query string, like an HttpRequest GET;
- a node that uses a stored credential (`credential_id`) — except the
  download token of the artifact nodes, which only protects the download;
- when CREATING or CHANGING a workflow, a trigger that fires on its own
  (schedule, webhook, file, geofence): the workflow would then run later with
  no click at all. Running a workflow does not create its schedule.

A node type is judged by an explicit list, not by the flow-side retry flag
(`TEM_EFEITO_COLATERAL` answers "can a retry repeat a write", a different
question). The registry lookup still fails CLOSED: a node type the registry
does not know, or a registered one with the retry flag that is in neither list
below, is treated as acting. A definition that cannot be read (a JSON string
that does not parse, a `nodes` that is not a list) acts too — the tool parses
strings itself, so judging only dicts let a string through.

URL-reading nodes with a LITERAL URL are not judged here: whether that URL is
already in the catalog is a database question (`urls_lidas`), answered by the
caller.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

# Write somewhere outside the run's own artifact, whatever their parameters say.
_ESCREVEM_FORA = frozenset({
    "SaveFile", "SaveGeoJSON", "SaveToGeoParquet", "SaveToPostGIS", "SaveToPostgres",
    "SaveToS3", "SaveToShapefile", "SendEmail", "SendWebhook", "PublishMap",
})

# Produce only the run's artifact (DataOutput: unless its destination is the Drive).
_SO_O_ARTEFATO_DO_RUN = frozenset({"DataOutput", "CartaImagem"})

# Act outside whatever their parameters say.
_SEMPRE_AGEM = frozenset({"HttpRequest", "SubWorkflow"})

# Triggers that make the workflow run later without anyone clicking.
_DISPAROS_AUTONOMOS = frozenset({"ScheduleTrigger", "WebhookTrigger", "FileTrigger", "GeofenceTrigger"})

# Read a URL given in their parameters.
_LEEM_URL = frozenset({"WFS", "DataInput"})

ILEGIVEL = "definition (ilegível)"


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


def _tem_expressao(valor: Any) -> bool:
    return isinstance(valor, str) and ("{{" in valor or "{%" in valor)


def _desconhecido_ou_com_escrita(tipo: str) -> bool:
    """Fail closed: unknown to the registry, or flagged as writing and not
    classified above (a node added later is born acting)."""
    from flow.registry import NODE_REGISTRY

    cls = NODE_REGISTRY.get(tipo)
    if cls is None:
        return True
    return bool(getattr(cls, "TEM_EFEITO_COLATERAL", False)) and tipo not in _SO_O_ARTEFATO_DO_RUN


def _como_definicao(definicao: Any) -> Mapping[str, Any] | None | str:
    """The definition as a dict; None when absent; ILEGIVEL when present but unreadable."""
    if definicao is None:
        return None
    if isinstance(definicao, str):
        try:
            definicao = json.loads(definicao)
        except (TypeError, ValueError):
            return ILEGIVEL
    if not isinstance(definicao, Mapping):
        return ILEGIVEL
    nos = definicao.get("nodes")
    if nos is not None and not isinstance(nos, list):
        return ILEGIVEL
    return definicao


def _nos(definicao: Mapping[str, Any]):
    for no in definicao.get("nodes") or []:
        if isinstance(no, Mapping):
            yield no


def nos_que_agem(definicao: Any, *, disparos: bool = True) -> list[str]:
    """Labels (`Tipo (id)`) of the nodes that act outside, in definition order.

    `disparos=False` when judging a RUN: a trigger node creates nothing then.
    Empty list = the graph only reads and transforms (literal URLs aside, see
    `urls_lidas`). A definition that is present but unreadable returns
    `[ILEGIVEL]`.
    """
    lida = _como_definicao(definicao)
    if lida is None:
        return []
    if lida == ILEGIVEL:
        return [ILEGIVEL]
    agem: list[str] = []
    for no in _nos(lida):
        tipo = _tipo(no)
        props = _propriedades(no)
        if tipo in _SO_O_ARTEFATO_DO_RUN:
            # Their `credential_id` is the download token: not a use of a secret.
            destino = props.get("context")
            if destino not in (None, "", "artifacts"):
                agem.append(_rotulo(no, tipo))
            continue
        if tipo in _DISPAROS_AUTONOMOS:
            if disparos or props.get("credential_id"):
                agem.append(_rotulo(no, tipo))
            continue
        if (
            tipo in _ESCREVEM_FORA
            or tipo in _SEMPRE_AGEM
            or props.get("credential_id")
            or (tipo in _LEEM_URL and _tem_expressao(props.get("url")))
            or _desconhecido_ou_com_escrita(tipo)
        ):
            agem.append(_rotulo(no, tipo))
    return agem


def urls_lidas(definicao: Any) -> list[tuple[str, str]]:
    """(label, URL) of the nodes that read a LITERAL URL — the caller checks
    each against the catalog. URLs with an expression are already in
    `nos_que_agem`."""
    lida = _como_definicao(definicao)
    if lida is None or lida == ILEGIVEL:
        return []
    urls: list[tuple[str, str]] = []
    for no in _nos(lida):
        tipo = _tipo(no)
        if tipo not in _LEEM_URL:
            continue
        props = _propriedades(no)
        if tipo == "DataInput" and props.get("context") not in ("url",):
            continue
        url = props.get("url")
        if isinstance(url, str) and url.strip() and not _tem_expressao(url):
            urls.append((_rotulo(no, tipo), url.strip()))
    return urls
