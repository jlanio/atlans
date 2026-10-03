# flow/utils/definition_lint.py
"""Static lint of a workflow definition, BEFORE the simulator.

The simulator (`WorkflowExecutor.simulate_runner`) requires a constructed
executor, and the constructor blows up on a nonexistent node name and on a cycle
(500 on /validate), while other defects pass silently: an invalid alias falls
back to `name`, an orphan edge is ignored, an invented property is dropped, a
duplicate id overwrites the previous node. An agent that builds the definition
through the API needs to HEAR all of that at once, with a stable code per
problem — not one exception at a time.

Pure by design: only stdlib, flow.core.* and flow.utils.*. It does not import
the registry or the factory (the caller passes the names and the descriptors),
so it runs without geopandas loaded and without a database session.

The checks are CUMULATIVE: each step continues after an error, so the report
comes out whole. `RelatorioLint.fatal` says whether it is worth trying to
construct the executor afterwards (which would bring the constructor down).

Everything here runs synchronously on the server's event loop, over text the
client controls: every string scan is LINEAR (see `_partes_jinja`) and the
reference heuristics (alias, `inputs.x`) ignore strings above
`_TAMANHO_MAX_TEXTO` — the secret check never skips.
"""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Collection, Iterable, Iterator, Mapping, Optional

from flow.core.aliases import RESERVED_ALIASES, alias_declarado
from flow.core.graph import WorkflowGraph
from flow.utils.parameter_validation import _CHAVES_DE_PLATAFORMA
from flow.utils.workflow_contract import _parse_ports

# Codes that would bring down the WorkflowExecutor constructor. `construction_error`
# does not originate here: it is the code the caller uses when, even with a clean
# lint, construction blew up — the vocabulary lives in one place. `unknown_node`
# only brings down the constructor if the node is in the execution order (the
# NodeManager only instantiates those); the graph step downgrades the rest (see
# `Diagnostico.fatal`). `invalid_credential_id` is fatal by contract, not by
# construction: an id that is not a UUID never reaches the database, and a client
# that only looks at the HTTP status (the skill's `validar.py`) must keep failing
# as it did with the 403.
FATAIS = frozenset({
    "unknown_node", "duplicate_node_id", "cycle", "construction_error", "invalid_credential_id",
})

# Copy of `_PROPRIEDADES_SECRETAS` (flow/factory.py), in lowercase: the keys
# that should only reach the node through server injection. The factory is not
# imported because it pulls in the whole registry; tests/unit/test_definition_lint.py
# ensures the two lists stay the same.
CHAVES_SECRETAS = frozenset({
    "http_auth", "s3_auth", "connectionstring", "token", "password", "senha",
    "secret", "api_key", "apikey", "authorization", "private_key",
    "awssecretaccesskey",
})

# HTTP headers that carry a credential when written by hand in `headers`.
# Superset of `_CABECALHOS_DE_CREDENCIAL` (flow/nodes/action/http_request.py),
# the list the node drops when following a 3xx to another origin — what the node
# considers a credential in transit the lint considers a stored credential.
# `cookie` and `proxy-authorization` carry a session and a proxy credential as
# literally as `Authorization`; without them `headers.Cookie` went out in plain
# text in the definition and in the redaction (which imports this list).
# `x-api-key` only exists here: it is a stored key, not a header to drop on a
# redirect. tests/unit/test_definition_lint.py watches over the inclusion.
_CABECALHOS_SECRETOS = frozenset({
    "authorization", "x-api-key", "cookie", "proxy-authorization",
})

# What remains of a value after removing the expressions and that is NOT a secret:
# only the authentication scheme ("Bearer {{ $Cred.token }}" → "Bearer").
_ESQUEMAS_DE_AUTENTICACAO = frozenset({"bearer", "basic", "token", "apikey", "api-key"})

# A `$Alias` or `$Alias.campo.sub` reference — the same pattern as
# flow/utils/expression_service.py (`_ALIAS_PATTERN`), repeated here so as not
# to pull jinja2 into a pure module. `[^\W\d]` is "letter or _" in Unicode.
_ALIAS_REF = re.compile(r"\$[^\W\d]\w*(?:\.[^\W\d]\w*)*")

# `inputs.nome` / `inputs["nome"]` inside a Jinja block. The lookbehind avoids
# `nodes.inputs.x`; `$` is still allowed before it (`{{ $inputs.x }}` renders).
_INPUTS_EM_JINJA = re.compile(
    r"(?<![\w.])inputs\s*(?:\.\s*([^\W\d]\w*)|\[\s*(['\"])([^'\"\]]+)\2\s*\])"
)

# Per-string ceiling for the reference heuristics (alias, inputs). A form
# parameter does not come close; a hostile payload does, and the report
# needs nothing that lies inside 16 thousand characters of text.
_TAMANHO_MAX_TEXTO = 16_000

# Ceiling on the descent through dict/list — a pathological structure does not become infinite recursion.
_PROFUNDIDADE_MAX = 32

# Ceiling on the total text the alias reference index goes through (sum of
# the definition's strings): ~1 s of CPU in the worst case, and it is only for a warning.
_ORCAMENTO_INDICE = 2_000_000


@dataclass
class Diagnostico:
    code: str
    severity: str
    message: str
    node_id: Optional[str] = None
    edge: Optional[dict] = None
    # Would it bring down the executor constructor? Outside `as_dict()`: it is an
    # internal server decision (422 before simulating), not part of the contract.
    fatal: bool = False

    def as_dict(self) -> dict:
        """Always the five keys: consumers (MCP, script) do not need to
        handle a missing field as a special case."""
        return {
            "code": self.code,
            "severity": self.severity,
            "node_id": self.node_id,
            "edge": self.edge,
            "message": self.message,
        }


@dataclass
class RelatorioLint:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    execution_order: list = field(default_factory=list)
    suggested_params_schema: dict = field(default_factory=dict)

    @property
    def fatal(self) -> bool:
        """Would any error bring down the executor constructor?"""
        return any(d.fatal for d in self.errors)

    def erro(self, code: str, message: str, *, node_id: Optional[str] = None,
             edge: Optional[dict] = None) -> Diagnostico:
        d = Diagnostico(code, "error", message, node_id=node_id, edge=edge, fatal=code in FATAIS)
        self.errors.append(d)
        return d

    def aviso(self, code: str, message: str, *, node_id: Optional[str] = None,
              edge: Optional[dict] = None) -> Diagnostico:
        d = Diagnostico(code, "warning", message, node_id=node_id, edge=edge)
        self.warnings.append(d)
        return d


# ── Helpers ──────────────────────────────────────────────────────────────────

def _partes_jinja(texto: str) -> list:
    """Alternates plain text and Jinja block: [outside, inside, outside, ..., outside].

    LINEAR tokenizer with `str.find`: finds the next opening (`{{` or `{%`)
    and, from there, the matching closing; with no closing, the rest of the
    string is plain text. Replaces `re.split` with `(\\{\\{.*?\\}\\}|...)`, which
    was quadratic on a string of repeated `{{` without `}}` — 40 KB cost 6 s
    of synchronous CPU on the event loop, 100 KB cost 40 s.

    The next occurrence of each opening is remembered and only recomputed when
    `pos` passes it: without that, a text with thousands of `{{` and no `{%`
    would make the find for `{%` scan the rest of the string at every block.
    """
    partes: list = []
    pos = 0
    proxima = {"{{": texto.find("{{"), "{%": texto.find("{%")}
    while True:
        for abertura in ("{{", "{%"):
            if -1 < proxima[abertura] < pos:
                proxima[abertura] = texto.find(abertura, pos)
        candidatos = [i for i in proxima.values() if i != -1]
        if not candidatos:
            partes.append(texto[pos:])
            return partes
        inicio = min(candidatos)
        fechamento = "}}" if texto.startswith("{{", inicio) else "%}"
        fim = texto.find(fechamento, inicio + 2)
        if fim == -1:
            partes.append(texto[pos:])
            return partes
        partes.append(texto[pos:inicio])
        partes.append(texto[inicio:fim + 2])
        pos = fim + 2


def _blocos_jinja(texto: str) -> list:
    partes = _partes_jinja(texto)
    return [partes[i] for i in range(1, len(partes), 2)]


def _tem_template(texto: str) -> bool:
    """Does the string have any Jinja block or `$Alias` reference? Then the final
    value only exists at runtime, and the lint cannot judge the raw text."""
    return len(_partes_jinja(texto)) > 1 or _ALIAS_REF.search(texto) is not None


def _residuo_literal(texto: str) -> str:
    """What remains of a string without the Jinja blocks, the `$Alias` references
    and the whitespace: what was written LITERALLY in the definition."""
    partes = _partes_jinja(texto)
    fora = "".join(partes[i] for i in range(0, len(partes), 2))
    # Joins with a SPACE, not with nothing. Gluing the pieces together, two lines of
    # free text became a single string — the body of an e-mail ending in a
    # URL and starting the next line with an e-mail address produced a
    # "host:usuario@dominio" that nobody ever wrote, matched the
    # URL-with-credential pattern, and got the message accused of storing a
    # password. The asymmetry gave the bug away: the SAME URL with a path at the
    # end passed, because the slash broke the match.
    #
    # The space does not affect what the function exists to measure — whether
    # literal text was left, and whether that text is only an authentication
    # scheme: a real DSN has no space inside.
    return " ".join(_ALIAS_REF.sub("", fora).split())


def _params_de(node: Mapping[str, Any]) -> dict:
    """`parameters` is the format of the validation body; `properties` that of the
    saved definition — same tolerance as simulate_runner."""
    params = node.get("parameters") or node.get("properties") or {}
    return params if isinstance(params, dict) else {}


def _strings(valor: Any, profundidade: int = 0) -> Iterator[str]:
    """All the string values of a structure, descending through dict/list."""
    if profundidade > _PROFUNDIDADE_MAX:
        return
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, Mapping):
        for item in valor.values():
            yield from _strings(item, profundidade + 1)
    elif isinstance(valor, (list, tuple)):
        for item in valor:
            yield from _strings(item, profundidade + 1)


def _preenchido(valor: Any, profundidade: int = 0) -> bool:
    """Is there a LITERAL secret in here?

    String: strips Jinja blocks and `$Alias` references; what remains only counts
    if it is not empty nor just an authentication scheme — "Bearer {{
    $Cred.token }}" and "Bearer $Cred.token" store nothing, "Bearer abc123"
    does. Mapping: counts if ANY leaf counts, ignoring the `type` key
    (it is a selector — `{"type": "http_bearer"}` is a form without a token, not
    a secret). No size ceiling: this is the check that is never skipped.
    """
    if valor is None or profundidade > _PROFUNDIDADE_MAX:
        return False
    if isinstance(valor, str):
        residuo = _residuo_literal(valor)
        return bool(residuo) and residuo.lower() not in _ESQUEMAS_DE_AUTENTICACAO
    if isinstance(valor, Mapping):
        return any(
            _preenchido(item, profundidade + 1)
            for chave, item in valor.items()
            if str(chave).lower() != "type"
        )
    if isinstance(valor, (list, tuple)):
        return any(_preenchido(item, profundidade + 1) for item in valor)
    return True


def _como_dict(valor: Any) -> Optional[dict]:
    """`headers` arrives as a dict or as JSON serialized by the editor."""
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (ValueError, TypeError):
            return None
    return valor if isinstance(valor, dict) else None


class _IndiceDeReferencias:
    """Names the definition uses as node aliases, collected ONCE.

    Outside a Jinja block only `$Alias` counts. Inside, besides `$Alias`,
    `named.Alias`, `named['Alias']` and a bare `Alias` as a name also count
    (`{{ Alias.x }}`, `{{ Alias }}`, `{{ Alias['x'] }}`, `{{ Alias | tojson }}`,
    `{% for r in Alias %}`) — the lookbehind excludes `inputs.Alias` and
    `named.Alias`, which are not the alias itself.

    The previous version compiled two regexes PER duplicated alias group and
    re-tokenized ALL strings for each group: N nodes with repeated names
    cost O(N²) tokenizations (100 nodes with 16 KB each = 24 s of synchronous
    CPU on the event loop). Here each string is tokenized once, the lookup by
    alias is a set lookup, and the total indexed text has a ceiling
    (`_ORCAMENTO_INDICE`): it is a WARNING heuristic, and the lint runs
    synchronously in the handler — a body of tens of MB cannot cost tens of seconds.
    """

    def __init__(self, textos: Iterable[str]):
        self.nomes: set = set()
        self.truncado = False
        orcamento = _ORCAMENTO_INDICE
        for texto in textos:
            orcamento -= len(texto)
            if orcamento < 0:
                self.truncado = True
                break
            for m in _REF_EM_QUALQUER_LUGAR.finditer(texto):
                self.nomes.add(m.group(1) or m.group(3))
            # One call per string, not per block: the line break between the
            # blocks is not `[\w.$]`, so the lookbehind still holds.
            self.nomes.update(_NOME_EM_JINJA.findall("\n".join(_blocos_jinja(texto))))

    def referencia(self, alias: str) -> bool:
        return alias in self.nomes


# `$Alias`, `named.Alias` (group 1) and `named['Alias']` (group 3) — the same
# `(?!\w)` as before: `$Ab` does not reference `A`.
_REF_EM_QUALQUER_LUGAR = re.compile(
    r"(?:\$|named\.)([^\W\d]\w*)(?!\w)"
    r"|named\[\s*(['\"])(.*?)\2\s*\]"
)
# Nome solto dentro de bloco Jinja (`{{ A }}`, `{{ A['x'] }}`, `{% for r in A %}`).
_NOME_EM_JINJA = re.compile(r"(?<![\w.$])([^\W\d]\w*)(?!\w)")


def _inputs_referenciados(texto: str) -> list:
    """Names of `inputs.<nome>` that a trigger parameter consumes.

    Only inside a Jinja block: a bare `$inputs.x` in the text is NOT rendered
    by the executor (`rendering._tem_expressao` only triggers `$X` when X is a
    node alias), so suggesting a parameter from it would promise what the
    run does not deliver. `{{ $inputs.x }}` inside the block still counts.
    """
    nomes: list = []
    for bloco in _blocos_jinja(texto):
        nomes.extend(m.group(1) or m.group(3) for m in _INPUTS_EM_JINJA.finditer(bloco))
    return nomes


# ── Lint ─────────────────────────────────────────────────────────────────────

def lint_definition(
    nodes: list,
    edges: list,
    *,
    registry_names: Collection[str],
    reserved_aliases: Collection[str] = RESERVED_ALIASES,
    descriptors: Optional[Mapping[str, dict]] = None,
) -> RelatorioLint:
    """Static diagnostics of `nodes` + `edges`.

    `registry_names`: valid node names (keys of NODE_REGISTRY).
    `descriptors`: `{name: cls.description()}` — optional; without it the property
    checks (undeclared / missing required / invalid JSON / empty fallback)
    do not run.
    """
    rel = RelatorioLint()
    nodes = [n for n in (nodes or []) if isinstance(n, Mapping)]
    # Only edges with both ends: the router's Pydantic already guarantees this, and
    # a malformed entry here is not a workflow diagnostic, it is payload garbage.
    edges = [
        e for e in (edges or [])
        if isinstance(e, Mapping) and "source" in e and "target" in e
    ]

    def alias_efetivo(node: Mapping[str, Any], name: str) -> str:
        # `resolve_alias` honoring the received `reserved_aliases` (and tolerant of a
        # node without `name`, which `unknown_node` already reports).
        custom = alias_declarado(node)
        if custom and custom.isidentifier() and custom not in reserved_aliases:
            return custom
        return name

    # 1. Duplicate ids. The executor builds `{id: nó}` and the last one wins.
    node_defs: dict = {}
    for node in nodes:
        node_defs.setdefault(str(node.get("id") or ""), node)
    for nid, vezes in Counter(str(n.get("id") or "") for n in nodes).items():
        if vezes > 1:
            rel.erro(
                "duplicate_node_id",
                f"id '{nid}' aparece {vezes} vezes; o executor sobrescreveria em silêncio.",
                node_id=nid,
            )

    # 2. Per node: name, alias, secrets, credential_id and properties.
    for node in nodes:
        nid = str(node.get("id") or "")
        name = str(node.get("name") or "")
        params = _params_de(node)

        if name not in registry_names:
            # The prefix is the factory's message (flow/factory.py), verbatim: it is the
            # text the validation's consumer already looks for.
            from flow.nodes.contrato import dica_de_no_desconhecido
            dica = dica_de_no_desconhecido(name)
            rel.erro(
                "unknown_node",
                f"Node '{name}' não encontrado para instância (id={nid})."
                + (dica or " Confira o nome exato no catálogo (GET /nodes)."),
                node_id=nid,
            )

        custom = alias_declarado(node)
        if custom and not custom.isidentifier():
            rel.erro(
                "invalid_alias",
                f"alias '{custom}' de '{name}' (id={nid}) não é um identificador "
                "(letras, dígitos e '_', sem começar por dígito): hoje o executor o "
                f"descarta em silêncio e registra o nó como '{name}' — `${custom}` e "
                f"`{{{{ {custom}.x }}}}` não renderizariam.",
                node_id=nid,
            )
        elif custom in reserved_aliases:
            rel.erro(
                "reserved_alias",
                f"alias '{custom}' de '{name}' (id={nid}) é reservado (colide com uma "
                f"chave fixa do contexto Jinja: {sorted(reserved_aliases)}): hoje o "
                f"executor o descarta em silêncio e registra o nó como '{name}'.",
                node_id=nid,
            )

        # Secret stored in the definition. Never echo the value: the diagnostic goes
        # to logs and to the client, and the problem is precisely the leak.
        def acusar_segredo(chave: str) -> None:
            rel.erro(
                "secret_in_definition",
                f"propriedade '{chave}' preenchida em '{name}' (id={nid}): segredo "
                "nunca vai na definição — use credential_id; o servidor injeta o "
                "valor na execução.",
                node_id=nid,
            )

        for chave, valor in params.items():
            if str(chave).lower() in CHAVES_SECRETAS and _preenchido(valor):
                acusar_segredo(str(chave))
        cabecalhos = _como_dict(params.get("headers"))
        if cabecalhos:
            for chave, valor in cabecalhos.items():
                if str(chave).lower() in _CABECALHOS_SECRETOS and _preenchido(valor):
                    acusar_segredo(f"headers.{chave}")

        cid = params.get("credential_id")
        if cid not in (None, ""):
            try:
                uuid.UUID(str(cid))
            except ValueError:
                rel.erro(
                    "invalid_credential_id",
                    f"credential_id '{str(cid)[:60]}' de '{name}' (id={nid}) não é um "
                    "UUID: credenciais são referenciadas pelo id_hash "
                    "(GET /credentials), não pelo nome.",
                    node_id=nid,
                )

        desc = descriptors.get(name) if descriptors else None
        if desc:
            props = [
                p for p in (desc.get("properties") or [])
                if isinstance(p, dict) and p.get("name")
            ]
            declaradas = {p["name"] for p in props}
            # Only the PRESENCE of the key is checked, never the value's type: a
            # parameter can be a Jinja expression that only becomes an integer in the run.
            nao_declaradas = [
                k for k in params
                if k not in declaradas and k not in _CHAVES_DE_PLATAFORMA
            ]
            if nao_declaradas:
                rel.aviso(
                    "undeclared_property",
                    f"propriedade(s) {nao_declaradas} de '{name}' (id={nid}) não "
                    "existem no descriptor do nó e seriam descartadas em silêncio "
                    f"na execução. Declaradas: {sorted(declaradas)}.",
                    node_id=nid,
                )
            faltando = [
                p["name"] for p in props
                if p.get("default") is None and p["name"] not in params
            ]
            if faltando:
                rel.aviso(
                    "missing_required_parameter",
                    f"parâmetro(s) obrigatório(s) {faltando} de '{name}' (id={nid}) "
                    "ausente(s): a execução falharia antes de rodar o nó.",
                    node_id=nid,
                )
            # The exception to the "never the type" rule: an `object` property stored as
            # text. The run decodes it in validate() (`_coerce_structured`) and
            # fails with this same sentence if it is not JSON of a dict/list — an
            # unreadable Switch `rules` passed silently through here and
            # `schema_declarado` hid it (only the fallback in the schema). Text with
            # a template is left out: `{"limite": {{ inputs.n }}}` only becomes valid JSON in the run.
            for prop in props:
                if prop.get("type") != "object":
                    continue
                valor = params.get(prop["name"])
                if not isinstance(valor, str) or not valor.strip() or _tem_template(valor):
                    continue
                try:
                    decodificado = json.loads(valor)
                except ValueError:
                    decodificado = None
                if not isinstance(decodificado, (dict, list)):
                    rel.erro(
                        "invalid_json_property",
                        f"propriedade '{prop['name']}' de '{name}' (id={nid}) deve ser "
                        "um objeto (dict) ou JSON válido: o run falharia na validação "
                        "de parâmetros antes de executar o nó.",
                        node_id=nid,
                    )
            # Switch: a present and empty `fallback_output` does not fall to the default —
            # the run reads `parameters.get("fallback_output", "output_0")` and emits
            # the port '' literally, which no edge can name.
            # It is an error, not a warning: no edge names the port '' (an empty
            # `from_key` means "no key"), so the wiring from it is dead and the
            # edge diagnostic does not see it — the report would say `ok`.
            if "fallback_output" in declaradas and params.get("fallback_output", None) == "":
                rel.erro(
                    "empty_fallback_output",
                    f"fallback_output vazio em '{name}' (id={nid}): o run emitiria a "
                    "porta '', que nenhuma aresta consegue nomear; use um nome (o "
                    "default só vale com a chave ausente).",
                    node_id=nid,
                )

    # 3. Duplicate alias. Two nodes under the same alias: `named[alias]` keeps only
    # the last one that ran. With an explicit alias it is an error (the user asked
    # for a name and it does not point where they think). Derived from `name` (two
    # "Buffer" without an alias) it is normal and only becomes a warning if some
    # expression actually references that name.
    grupos: dict = {}
    for nid, node in node_defs.items():
        grupos.setdefault(alias_efetivo(node, str(node.get("name") or "")), []).append(node)
    indice: Optional[_IndiceDeReferencias] = None
    for alias, membros in grupos.items():
        if len(membros) < 2 or not alias:
            continue
        ids = [str(m.get("id") or "") for m in membros]
        explicito = any(alias_efetivo(m, "") == alias for m in membros)
        if explicito:
            rel.erro(
                "duplicate_alias",
                f"alias '{alias}' usado por {len(membros)} nós ({ids}): "
                f"`{{{{ ${alias}.x }}}}` apontaria só para o último a rodar; os demais "
                "ficariam inacessíveis por alias.",
                node_id=ids[0],
            )
            continue
        if indice is None:
            indice = _IndiceDeReferencias(
                s for node in nodes for s in _strings(node) if len(s) <= _TAMANHO_MAX_TEXTO
            )
        if indice.referencia(alias):
            rel.aviso(
                "duplicate_alias",
                f"{len(membros)} nós '{alias}' sem alias próprio ({ids}) e a definição "
                f"referencia '{alias}' como alias: a referência resolve para o último "
                "que rodou. Dê um alias distinto a cada um.",
                node_id=ids[0],
            )

    # 4. Graph: orphan edge, cycle, nodes left out of the run.
    graph = WorkflowGraph(node_defs, edges, filter_isolated=True)
    for edge in graph.orphan_edges:
        src, tgt = edge.get("source"), edge.get("target")
        pontas = [
            f"{papel} '{ponta}'"
            for papel, ponta in (("source", src), ("target", tgt))
            if ponta not in node_defs
        ]
        rel.aviso(
            "orphan_edge",
            f"aresta '{src}' -> '{tgt}': {' e '.join(pontas)} não existe entre os nós; "
            "o executor a ignora em silêncio.",
            edge={"source": src, "target": tgt},
        )
    try:
        order = graph.compute_order()
    except ValueError as exc:
        rel.erro("cycle", str(exc))
        order = []
    else:
        for nid, node in node_defs.items():
            if nid in order:
                continue
            name = str(node.get("name") or "")
            # `.get`, not `[]`: incoming/outgoing are defaultdicts and index
            # access would create the key.
            if not graph.incoming.get(nid) and not graph.outgoing.get(nid):
                msg = f"nó '{name}' (id={nid}) isolado: sem arestas, fica fora da simulação e do run."
            else:
                msg = (
                    f"nó '{name}' (id={nid}) sem caminho a partir de um trigger: "
                    "fica fora da simulação e do run."
                )
            rel.aviso("unreachable_node", msg, node_id=nid)
        # The NodeManager only instantiates the nodes in the execution order: a
        # nonexistent name outside it (isolated, outside the trigger's cone) is still
        # an error, but does not bring down the constructor. With a cycle there is
        # no order — and `cycle` is already fatal.
        na_ordem = set(order)
        for d in rel.errors:
            if d.code == "unknown_node" and d.node_id not in na_ordem:
                d.fatal = False
    rel.execution_order = list(order)

    # 5. Run parameters the workflow expects. `{{ inputs.X }}` is only a user
    # parameter in a trigger node (core.py: in the others, `inputs` are the
    # edges). The SubWorkflowInput's `ports` are the input contract.
    sugeridos: dict = {}
    for node in nodes:
        params = _params_de(node)
        nomes: list = []
        if node.get("type") == "trigger":
            for texto in _strings(params):
                if len(texto) <= _TAMANHO_MAX_TEXTO:
                    nomes.extend(_inputs_referenciados(texto))
        if node.get("name") == "SubWorkflowInput":
            nomes.extend(_parse_ports(params.get("ports")))
        for nome in nomes:
            sugeridos.setdefault(nome, {"type": "string", "required": True})
    rel.suggested_params_schema = sugeridos

    return rel
