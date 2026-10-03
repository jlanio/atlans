"""Recursive redaction of a workflow definition before it LEAVES the server.

The saved definition carries, in `nodes[].properties` (or `parameters`, the
format of the validation body), everything the editor stored: a legacy
Fernet-encrypted `connectionString`, a hand-written `headers.Authorization`, a
DSN with a password in `url`. The factory's `_without_secrets` only looks at the
first level and only serves the log; whoever returns the whole definition to a
client (the MCP server, versions, export) needs to descend through dict/list,
and needs the SAME key list as the lint — a third list would diverge silently.

Three functions, all pure and none mutating the input:

- `redact_definition`: sensitive key → "<REDACTED>", every leaf string goes
  through `scrub_text` (Bearer, PAT, DSN...) and every string that is the JSON
  of a dict is redacted inside and re-serialized — across the WHOLE definition,
  because the whole definition is what gets delivered. It is the version that
  gets DELIVERED.
- `compact_definition`: removes what only matters to the canvas (position,
  viewport). Reduces what an agent reads without changing semantics.
- `definition_contains_secret`: paths where there is a filled-in LITERAL
  secret — the edge that refuses the input has to say WHERE, not just that
  there is one. It also refuses the `<REDACTED>` MARKER in any string: it only
  exists in a definition that left here redacted, and storing it back would
  silently erase the value the redaction hid (the key in a URL, a token in a
  text). That is what closes the read → edit → save cycle without destroying
  anything.

A depth ceiling on all of them: a pathological structure does not become
infinite recursion. Whatever lies beyond the ceiling is treated as opaque — the
redactor does not deliver what it could not inspect, and the check flags the
path.
"""
from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from typing import Any, Iterator, Mapping

from app.core.utils.logger import _REDACTED, scrub_text
# `_SECRET_HEADERS` is private to the lint, but it is the source of truth on
# which headers carry a credential. Importing instead of copying keeps redaction
# and lint in step: a new header in the lint starts being redacted here without
# anyone remembering to touch two places.
from flow.utils.definition_lint import (
    _SECRET_HEADERS,
    _MAX_DEPTH,
    _as_dict,
    _is_filled,
    _literal_residue,
    SECRET_KEYS,
)

# Keys that, at any level of `properties`/`parameters`, never go out in the
# clear. Union of the lint's two lists — never a third one.
REDACTED_KEYS: frozenset = SECRET_KEYS | _SECRET_HEADERS

# The two names of the same parameter bag: `properties` in the saved definition,
# `parameters` in the validation body (same tolerance as simulate_runner).
_PARAMETER_CONTAINERS = ("properties", "parameters")

# What only the canvas uses. `viewport` sits at the top; the rest on each node.
_NODE_CANVAS_KEYS = ("position", "measured", "selected", "dragging")
_TOP_LEVEL_CANVAS_KEYS = ("viewport",)

# `scheme://usuario:senha@host` — the same shape as the logger's DSN pattern,  # pragma: allowlist secret
# here only to DETECT (redaction is left to `scrub_text`). It runs over the
# literal residue of the string: `postgresql://{{ $Cred.user }}:{{ $Cred.senha }}@h`
# has neither user nor password stored.
# Ceilings and optional user for the same reason as the logger: linear cost and
# `redis://:senha@host` (password without user) also counts as a credential.
_URL_WITH_CREDENTIAL = re.compile(r"(?i)\b[a-z][a-z0-9+.\-]{0,31}://[^/\s:@]*:[^\s/]{1,256}@")
# The key of GeoServer's authkey module stored in the URL query — on the WFS
# node it lives in Credentials (`geoserver_authkey`), never in `url`. It only
# counts in the `url` of a node that USES that credential (see
# `_authkey_nodes`): in an HttpRequest, or in a text, `authkey` is just a
# word — and the edge used to refuse a whole definition because of it. Delivery
# redacts `authkey=` in ANY string (`scrub_text`); what keeps the redacted read
# from being saved over the key in an HttpRequest is the refusal of the
# `<REDACTED>` marker, below.
_URL_WITH_AUTHKEY = re.compile(r"(?i)[?&]authkey=[^&#\s]{4,}")
# Jinja blocks and quoted literals inside them: `{{ x | default('hunter2') }}`
# under a sensitive key stores a secret that `_is_filled` does not see (it strips
# the whole block). DELIVERY needs to see it; the edge keeps the lint's rule.
_JINJA_BLOCKS_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
_QUOTED_LITERAL_RE = re.compile(r"""(['"]).+?\1""", re.S)
# Where a node's `url` lives in the definition: `properties`/`parameters` (the
# two bags) and `data.properties` (what the editor stores).
_URL_DE_NO_RE = re.compile(r"^nodes\[(\d+)\]\.(?:properties|parameters|data\.properties)\.url$")


def _is_redacted_key(chave: Any) -> bool:
    return str(chave).lower() in REDACTED_KEYS


@lru_cache(maxsize=1)
def _authkey_nodes() -> frozenset:
    """The nodes whose `credential_id` accepts `geoserver_authkey` — only in
    their `url` is a stored `?authkey=` the key out of place. Read from the
    registry (the source of what each node accepts); without a registry, the
    WFS node."""
    try:
        from flow.registry import NODE_REGISTRY

        nos = set()
        for nome, cls in NODE_REGISTRY.items():
            for prop in cls.description().get("properties") or []:
                if prop.get("name") == "credential_id" and "geoserver_authkey" in (prop.get("credential_types") or ()):
                    nos.add(nome)
    except Exception:  # registry unavailable or broken descriptor
        nos = set()
    return frozenset(nos) or frozenset({"WFS"})


def _node_name(node: Mapping[str, Any]) -> str:
    dados = node.get("data")
    return str(node.get("name") or (dados.get("name") if isinstance(dados, Mapping) else "") or "")


def _authkey_indices(definition: Mapping[str, Any]) -> frozenset:
    """The indices, in `nodes`, of the nodes in which `?authkey=` in `url` is a secret."""
    with_authkey = _authkey_nodes()
    return frozenset(i for i, node in _nodes_of(definition) if _node_name(node) in with_authkey)


def _nodes_of(definition: Mapping[str, Any]) -> Iterator[tuple[int, dict]]:
    """Index and node, only for nodes that are dicts — the rest stays intact where it is."""
    nodes = definition.get("nodes")
    if not isinstance(nodes, list):
        return
    for i, node in enumerate(nodes):
        if isinstance(node, dict):
            yield i, node


# ── redact ──────────────────────────────────────────────────────────────────

def _only_references(valor: Any, profundidade: int = 0) -> bool:
    """Under a sensitive key, is there NOTHING literal in here?

    Empty (`{}`, `""`, None) or only references to runtime values
    (`{{ inputs.pw }}`, `$Cred.token`, `Bearer {{ tok }}`) — with no quoted
    literal inside the expressions. A mapping ignores the `type` key (a
    selector, as in `_is_filled`); a number or boolean is a literal
    (`"password": 1234`).
    """
    if profundidade > _MAX_DEPTH:
        return False
    if valor is None:
        return True
    if isinstance(valor, str):
        if _is_filled(valor):
            return False
        return not any(_QUOTED_LITERAL_RE.search(bloco) for bloco in _JINJA_BLOCKS_RE.findall(valor))
    if isinstance(valor, dict):
        return all(
            _only_references(item, profundidade + 1)
            for chave, item in valor.items() if str(chave).lower() != "type"
        )
    if isinstance(valor, list):
        return all(_only_references(item, profundidade + 1) for item in valor)
    return False


def _redact_value(valor: Any, profundidade: int) -> Any:
    """Descends through dict/list replacing sensitive keys and passing each leaf
    string through `scrub_text`. A string that is the JSON of a dict counts as
    structure, not as a leaf: it enters the descent and comes back serialized.
    Beyond the ceiling, the whole subtree becomes the marker: if you cannot look
    inside, you do not deliver it."""
    if profundidade > _MAX_DEPTH:
        return _REDACTED
    if isinstance(valor, str):
        # The editor stores a SERIALIZED dict in more properties than `headers`
        # (`body`, `config`, `options`): a JSON string is structure, not
        # text, and `scrub_text` alone knows neither `x-api-key` nor
        # `connectionString` inside it. Parses, redacts by key and
        # re-serializes; whatever is not the JSON of a dict goes through `scrub_text`.
        aninhado = _as_dict(valor)
        if aninhado is None:
            return scrub_text(valor)
        return json.dumps(_redact_value(aninhado, profundidade + 1), ensure_ascii=False)
    if isinstance(valor, dict):
        saida = {}
        for chave, item in valor.items():
            # A sensitive key with NOTHING literal inside (`http_auth: {}`, the default
            # the WFS node declares; `password: ""`; `token: "{{ inputs.tok }}"`)
            # hides nothing — and goes out as it came in, so the definition that
            # was read can be saved again: a `"<REDACTED>"` in its place is a
            # "filled-in" secret that the edge refuses on the way back. Any
            # literal, even hidden in an expression, disappears entirely.
            if _is_redacted_key(chave) and not _only_references(item, profundidade + 1):
                saida[chave] = _REDACTED
            else:
                saida[chave] = _redact_value(item, profundidade + 1)
        return saida
    if isinstance(valor, list):
        return [_redact_value(item, profundidade + 1) for item in valor]
    return valor


def _without_bags(definition: Mapping[str, Any]) -> tuple:
    """Splits the definition into (rest, bags), without touching the input.

    `bags` holds `nodes[].properties`/`parameters` indexed by `(node index,
    container name)`; `resto` is the definition with those two removed.

    The descent has a depth ceiling, and the ceiling is the only reason the two
    bags get their own treatment: a nested property is the editor's content and
    can be deep, and spending the first three levels just to get from `{}` to
    `nodes[i].properties` would shorten the budget of exactly the place that
    needs it most. So each bag is walked with depth counted from itself, and
    the rest from the root.

    The split is by SHALLOW copy (the top-level dict, the node list and the
    nodes that lose a container): the input stays intact and a large definition
    does not pay for a deep copy just to be inspected.
    """
    resto = dict(definition)
    bags: dict = {}
    nodes = resto.get("nodes")
    if not isinstance(nodes, list):
        return resto, bags

    novos = list(nodes)
    for i, node in enumerate(novos):
        if not isinstance(node, dict):
            continue
        presentes = [c for c in _PARAMETER_CONTAINERS if c in node]
        if not presentes:
            continue
        copia = dict(node)
        for container in presentes:
            bags[(i, container)] = copia.pop(container)
        novos[i] = copia
    resto["nodes"] = novos
    return resto, bags


def redact_definition(definition: Mapping[str, Any]) -> dict:
    """Copy of the definition with secrets redacted under ANY key, at any
    level — not only inside `nodes[].properties` and
    `nodes[].parameters`.

    Whoever receives the definition receives the whole definition: a
    configuration bag at the top, a `nodes[].data` stored by the editor or a
    `config` outside the two known containers would go out verbatim if the
    descent started at the containers — without even going through
    `scrub_text`. That is why the descent starts at the ROOT, and the two bags
    come in from outside only so as not to spend their depth budget on the
    definition's levels.

    What is not a secret still goes out as it came in (edges, ids, numbers,
    a node that is not a dict, a definition without `nodes`).
    """
    resto, bags = _without_bags(definition)
    redigida = _redact_value(resto, 0)
    for (i, container), valor in bags.items():
        redigida["nodes"][i][container] = _redact_value(valor, 0)
    return redigida


# ── compactar ────────────────────────────────────────────────────────────────

def compact_definition(definition: Mapping[str, Any]) -> dict:
    """Copy of the definition without what only serves the canvas: `viewport` at
    the top and `position`/`measured`/`selected`/`dragging` on each node. Does
    not redact — this is about size, not security; combine with
    `redact_definition` to deliver."""
    saida = copy.deepcopy(dict(definition))
    for chave in _TOP_LEVEL_CANVAS_KEYS:
        saida.pop(chave, None)
    for _, node in _nodes_of(saida):
        for chave in _NODE_CANVAS_KEYS:
            node.pop(chave, None)
    return saida


# ── detectar ─────────────────────────────────────────────────────────────────

def _url_with_literal_credential(texto: str, *, authkey: bool = False) -> bool:
    """Does the string store `user:senha@` — or, with `authkey`, `?authkey=` —
    LITERALLY? Expressions and `$Alias` are stripped first: a credential that
    only exists at runtime is not a saved secret."""
    residue = _literal_residue(texto)
    if _URL_WITH_CREDENTIAL.search(residue) is not None:
        return True
    return authkey and _URL_WITH_AUTHKEY.search(residue) is not None


def _is_authkey_node_url(caminho: str, indices: frozenset) -> bool:
    m = _URL_DE_NO_RE.match(caminho)
    return m is not None and int(m.group(1)) in indices


def _paths_with_secret(valor: Any, caminho: str, profundidade: int,
                          encontrados: list, with_authkey: frozenset = frozenset()) -> None:
    if profundidade > _MAX_DEPTH:
        # Opaque: we cannot assert it is clean, so flag it.
        encontrados.append(caminho)
        return
    if isinstance(valor, str):
        # Same rule as the redactor: a string that is the JSON of a dict is structure,
        # and the flagged path descends into it
        # (`nodes[0].properties.config.token`) instead of stopping at the property.
        aninhado = _as_dict(valor)
        if aninhado is not None:
            _paths_with_secret(aninhado, caminho, profundidade + 1, encontrados, with_authkey)
        elif _REDACTED in valor or _url_with_literal_credential(valor, authkey=_is_authkey_node_url(caminho, with_authkey)):
            # The marker is ours: it only gets here in a definition that left
            # redacted and came back — saving it would erase the hidden value.
            encontrados.append(caminho)
        return
    if isinstance(valor, dict):
        for chave, item in valor.items():
            # At the root the path is still empty: `params_schema.token`, not
            # `.params_schema.token`.
            sub = f"{caminho}.{chave}" if caminho else str(chave)
            if _is_redacted_key(chave):
                if _is_filled(item):
                    encontrados.append(sub)
                continue
            _paths_with_secret(item, sub, profundidade + 1, encontrados, with_authkey)
        return
    if isinstance(valor, list):
        for i, item in enumerate(valor):
            _paths_with_secret(item, f"{caminho}[{i}]", profundidade + 1, encontrados, with_authkey)


# Fields of a `params_schema` parameter that store a VALUE; the others
# describe it (type, label, `required`). A parameter named `token` or
# `password` is the normal case — the value arrives at execution, through
# `inputs` —, and the lint itself suggests `{"token": {"type": "string", "required": true}}`:
# scanning the schema as if it were a definition used to refuse the suggestion
# (`required: true` is a "filled-in" literal under a sensitive key).
_PARAMETER_VALUE_FIELDS = ("default", "enum", "examples", "const", "value")


def params_schema_contains_secret(schema: Any) -> list[str]:
    """Paths (`params_schema.token.default`) where the `params_schema` stores a
    literal secret: the value of a parameter with a sensitive name, or, in
    any field, a URL with a password or the `<REDACTED>` marker. A parameter
    that is only declared (`{"type": "string", "required": true}`) stores
    nothing. Neither does a schema that is not an object: shape validation
    refuses it further on."""
    if not isinstance(schema, Mapping):
        return []
    encontrados: list = []
    for nome, spec in schema.items():
        base = f"params_schema.{nome}"
        if not isinstance(spec, Mapping):
            # Short form `{"token": "valor"}`: the value is the parameter itself.
            _paths_with_secret({nome: spec}, "params_schema", 0, encontrados)
            continue
        for campo, valor in spec.items():
            caminho = f"{base}.{campo}"
            if campo in _PARAMETER_VALUE_FIELDS and _is_redacted_key(nome):
                if _is_filled(valor):
                    encontrados.append(caminho)
            elif campo in _PARAMETER_VALUE_FIELDS or isinstance(valor, str):
                _paths_with_secret(valor, caminho, 0, encontrados)
    return encontrados


def definition_contains_secret(definition: Mapping[str, Any]) -> list[str]:
    """Paths (`nodes[2].properties.connectionString`,
    `nodes[0].properties.headers.Authorization`, `nodes[1].properties.url`)
    where there is a filled-in LITERAL secret.

    "Filled-in" is the lint's `_is_filled` rule: a non-empty string after
    stripping `{{ … }}`/`{% … %}` and `$Alias`, and that is not just an
    authentication scheme ("Bearer {{ inputs.tok }}" stores nothing); dict/list
    count if any leaf counts. A URL counts when it stores `user:senha@` — and,
    in the `url` of a node that uses the `geoserver_authkey` credential, when
    it stores `?authkey=`. Any string with the `<REDACTED>` marker counts: it
    is a redacted read coming back, and saving it would erase the hidden
    value. A string that is the JSON of a dict (the editor stores it that way
    in `headers`, `body`, `config`) is read as structure, and the flagged path
    descends into it. Empty list = nothing to refuse.

    The scan covers the WHOLE definition, not only the two parameter bags:
    detection cannot be narrower than redaction, otherwise the edge accepts
    what delivery later erases — and there comes to be a place
    (`nodes[].data`, a bag at the top) where the secret gets in without anyone
    noticing. The bags come in from outside only for the depth budget, as in
    `redact_definition`; that is why their paths come after."""
    encontrados: list = []
    with_authkey = _authkey_indices(definition)
    resto, bags = _without_bags(definition)
    _paths_with_secret(resto, "", 0, encontrados, with_authkey)
    for (i, container), valor in bags.items():
        _paths_with_secret(valor, f"nodes[{i}].{container}", 0, encontrados, with_authkey)
    return encontrados
