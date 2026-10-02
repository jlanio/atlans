# flow/utils/definition_lint.py
"""Lint estático de uma definition de workflow, ANTES do simulador.

O simulador (`WorkflowExecutor.simulate_runner`) exige um executor construído,
e o construtor estoura com nome de nó inexistente e com ciclo (500 no
/validate), enquanto outros defeitos passam em silêncio: alias inválido cai no
`name`, aresta órfã é ignorada, propriedade inventada é descartada, id
duplicado sobrescreve o nó anterior. Um agente que monta a definição por API
precisa OUVIR isso tudo de uma vez, com código estável por problema — não uma
exceção por vez.

Puro por desenho: só stdlib, flow.core.* e flow.utils.*. Não importa o
registry nem a factory (o chamador passa os nomes e os descriptors), então
roda sem geopandas carregado e sem sessão de banco.

Os checks são CUMULATIVOS: cada passo continua depois de um erro, para o
relatório sair inteiro. `RelatorioLint.fatal` diz se vale a pena tentar
construir o executor depois (o que derrubaria o construtor).

Tudo aqui roda síncrono no event loop do servidor, sobre texto que o cliente
controla: toda varredura de string é LINEAR (ver `_partes_jinja`) e as
heurísticas de referência (alias, `inputs.x`) ignoram strings acima de
`_TAMANHO_MAX_TEXTO` — a checagem de segredo nunca ignora.
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

# Códigos que derrubariam o construtor do WorkflowExecutor. `construction_error`
# não nasce aqui: é o código que o chamador usa quando, mesmo com o lint limpo,
# a construção estourou — o vocabulário fica num lugar só. `unknown_node` só
# derruba o construtor se o nó entra na ordem de execução (o NodeManager só
# instancia esses); o passo do grafo rebaixa os demais (ver `Diagnostico.fatal`).
# `invalid_credential_id` é fatal por contrato, não por construção: um id que
# não é UUID nunca chega ao banco, e o cliente que só olha o status HTTP (o
# `validar.py` da skill) precisa continuar reprovando como reprovava com o 403.
FATAIS = frozenset({
    "unknown_node", "duplicate_node_id", "cycle", "construction_error", "invalid_credential_id",
})

# Cópia de `_PROPRIEDADES_SECRETAS` (flow/factory.py), em minúsculas: as chaves
# que só deveriam chegar ao nó por injeção do servidor. Não se importa a factory
# porque ela puxa o registry inteiro; tests/unit/test_definition_lint.py garante
# que as duas listas continuam iguais.
CHAVES_SECRETAS = frozenset({
    "http_auth", "s3_auth", "connectionstring", "token", "password", "senha",
    "secret", "api_key", "apikey", "authorization", "private_key",
    "awssecretaccesskey",
})

# Cabeçalhos HTTP que carregam credencial quando escritos à mão em `headers`.
# Superconjunto de `_CABECALHOS_DE_CREDENCIAL` (flow/nodes/action/http_request.py),
# a lista que o nó derruba ao seguir um 3xx para outra origem — o que o nó
# considera credencial em trânsito o lint considera credencial gravada.
# `cookie` e `proxy-authorization` carregam sessão e credencial de proxy tão
# literalmente quanto `Authorization`; sem eles `headers.Cookie` saía em claro
# na definition e na redação (que importa esta lista). `x-api-key` só existe
# aqui: é chave gravada, não cabeçalho a derrubar num redirecionamento.
# tests/unit/test_definition_lint.py vigia a inclusão.
_CABECALHOS_SECRETOS = frozenset({
    "authorization", "x-api-key", "cookie", "proxy-authorization",
})

# O que sobra de um valor depois de tirar as expressões e que NÃO é segredo:
# só o esquema de autenticação ("Bearer {{ $Cred.token }}" → "Bearer").
_ESQUEMAS_DE_AUTENTICACAO = frozenset({"bearer", "basic", "token", "apikey", "api-key"})

# Referência `$Alias` ou `$Alias.campo.sub` — o mesmo padrão de
# flow/utils/expression_service.py (`_ALIAS_PATTERN`), repetido aqui para não
# puxar o jinja2 num módulo puro. `[^\W\d]` é "letra ou _" em Unicode.
_ALIAS_REF = re.compile(r"\$[^\W\d]\w*(?:\.[^\W\d]\w*)*")

# `inputs.nome` / `inputs["nome"]` dentro de um bloco Jinja. O lookbehind evita
# `nodes.inputs.x`; `$` continua permitido antes (`{{ $inputs.x }}` renderiza).
_INPUTS_EM_JINJA = re.compile(
    r"(?<![\w.])inputs\s*(?:\.\s*([^\W\d]\w*)|\[\s*(['\"])([^'\"\]]+)\2\s*\])"
)

# Teto por string para as heurísticas de referência (alias, inputs). Um
# parâmetro de formulário não chega perto; um payload hostil chega, e o
# relatório não precisa de nada que esteja dentro de 16 mil caracteres de texto.
_TAMANHO_MAX_TEXTO = 16_000

# Teto da descida por dict/list — estrutura patológica não vira recursão infinita.
_PROFUNDIDADE_MAX = 32

# Teto do total de texto que o índice de referências a alias percorre (soma
# das strings da definição): ~1 s de CPU no pior caso, e é só para um aviso.
_ORCAMENTO_INDICE = 2_000_000


@dataclass
class Diagnostico:
    code: str
    severity: str
    message: str
    node_id: Optional[str] = None
    edge: Optional[dict] = None
    # Derrubaria o construtor do executor? Fora do `as_dict()`: é decisão
    # interna do servidor (422 antes de simular), não parte do contrato.
    fatal: bool = False

    def as_dict(self) -> dict:
        """Sempre as cinco chaves: quem consome (MCP, script) não precisa
        tratar campo ausente como caso especial."""
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
        """Algum erro derrubaria o construtor do executor?"""
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
    """Alterna texto comum e bloco Jinja: [fora, dentro, fora, ..., fora].

    Tokenizador LINEAR com `str.find`: acha a próxima abertura (`{{` ou `{%`)
    e, a partir dela, o fechamento correspondente; sem fechamento, o resto da
    string é texto comum. Substitui `re.split` com `(\\{\\{.*?\\}\\}|...)`, que
    era quadrático numa string de `{{` repetidos sem `}}` — 40 KB custavam 6 s
    de CPU síncrona no event loop, 100 KB custavam 40 s.

    A próxima ocorrência de cada abertura é lembrada e só recalculada quando
    `pos` a ultrapassa: sem isso, um texto com milhares de `{{` e nenhum `{%`
    faria o find de `{%` varrer o resto da string a cada bloco.
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
    """A string tem algum bloco Jinja ou referência `$Alias`? Então o valor
    final só existe em runtime, e o lint não pode julgar o texto cru."""
    return len(_partes_jinja(texto)) > 1 or _ALIAS_REF.search(texto) is not None


def _residuo_literal(texto: str) -> str:
    """O que resta de uma string sem os blocos Jinja, as referências `$Alias`
    e os espaços: o que foi gravado LITERALMENTE na definição."""
    partes = _partes_jinja(texto)
    fora = "".join(partes[i] for i in range(0, len(partes), 2))
    # Junta com ESPAÇO, não com nada. Colando os pedaços, duas linhas de um
    # texto livre viravam uma string só — o corpo de um e-mail que termine numa
    # URL e comece a linha seguinte com um endereço de e-mail produzia um
    # "host:usuario@dominio" que nunca foi escrito por ninguém, casava com o
    # padrão de URL-com-credencial, e fazia a mensagem ser acusada de guardar
    # senha. A assimetria denunciava o erro: a MESMA URL com caminho no fim
    # passava, porque a barra quebrava o casamento.
    #
    # O espaço não afeta o que a função existe para medir — se sobrou texto
    # literal, e se esse texto é só um esquema de autenticação: um DSN de
    # verdade não tem espaço dentro.
    return " ".join(_ALIAS_REF.sub("", fora).split())


def _params_de(node: Mapping[str, Any]) -> dict:
    """`parameters` é o formato do corpo da validação; `properties` o da
    definition salva — mesma tolerância do simulate_runner."""
    params = node.get("parameters") or node.get("properties") or {}
    return params if isinstance(params, dict) else {}


def _strings(valor: Any, profundidade: int = 0) -> Iterator[str]:
    """Todos os valores string de uma estrutura, descendo por dict/list."""
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
    """Há um segredo LITERAL aqui dentro?

    String: tira blocos Jinja e referências `$Alias`; o que sobra só conta se
    não for vazio nem apenas um esquema de autenticação — "Bearer {{
    $Cred.token }}" e "Bearer $Cred.token" não gravam nada, "Bearer abc123"
    grava. Mapping: conta se ALGUMA folha contar, ignorando a chave `type`
    (é seletor — `{"type": "http_bearer"}` é um formulário sem token, não um
    segredo). Sem teto de tamanho: esta é a checagem que nunca se pula.
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
    """`headers` chega como dict ou como JSON serializado pelo editor."""
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (ValueError, TypeError):
            return None
    return valor if isinstance(valor, dict) else None


class _IndiceDeReferencias:
    """Nomes que a definição usa como alias de nó, coletados UMA vez.

    Fora de bloco Jinja só `$Alias` conta. Dentro, além de `$Alias`, vale
    `named.Alias`, `named['Alias']` e `Alias` solto como nome (`{{ Alias.x }}`,
    `{{ Alias }}`, `{{ Alias['x'] }}`, `{{ Alias | tojson }}`, `{% for r in
    Alias %}`) — o lookbehind exclui `inputs.Alias` e `named.Alias`, que não
    são o alias em si.

    A versão anterior compilava dois regex POR grupo de alias duplicado e
    re-tokenizava TODAS as strings a cada grupo: N nós com nomes repetidos
    custavam O(N²) tokenizações (100 nós com 16 KB cada = 24 s de CPU síncrona
    no event loop). Aqui cada string é tokenizada uma vez, a consulta por
    alias é uma busca em conjunto, e o total de texto indexado tem teto
    (`_ORCAMENTO_INDICE`): é heurística de AVISO, e o lint roda síncrono no
    handler — um corpo de dezenas de MB não pode custar dezenas de segundos.
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
            # Uma chamada por string, não por bloco: a quebra de linha entre os
            # blocos não é `[\w.$]`, então o lookbehind continua valendo.
            self.nomes.update(_NOME_EM_JINJA.findall("\n".join(_blocos_jinja(texto))))

    def referencia(self, alias: str) -> bool:
        return alias in self.nomes


# `$Alias`, `named.Alias` (grupo 1) e `named['Alias']` (grupo 3) — o mesmo
# `(?!\w)` de antes: `$Ab` não referencia `A`.
_REF_EM_QUALQUER_LUGAR = re.compile(
    r"(?:\$|named\.)([^\W\d]\w*)(?!\w)"
    r"|named\[\s*(['\"])(.*?)\2\s*\]"
)
# Nome solto dentro de bloco Jinja (`{{ A }}`, `{{ A['x'] }}`, `{% for r in A %}`).
_NOME_EM_JINJA = re.compile(r"(?<![\w.$])([^\W\d]\w*)(?!\w)")


def _inputs_referenciados(texto: str) -> list:
    """Nomes de `inputs.<nome>` que um parâmetro de trigger consome.

    Só dentro de bloco Jinja: `$inputs.x` solto no texto NÃO é renderizado
    pelo executor (`rendering._tem_expressao` só dispara `$X` quando X é alias
    de nó), então sugerir um parâmetro a partir dele seria prometer o que o
    run não entrega. `{{ $inputs.x }}` dentro do bloco continua valendo.
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
    """Diagnósticos estáticos de `nodes` + `edges`.

    `registry_names`: nomes de nó válidos (chaves do NODE_REGISTRY).
    `descriptors`: `{name: cls.description()}` — opcional; sem ele os checks de
    propriedade (não declarada / obrigatória ausente / JSON inválido /
    fallback vazio) não rodam.
    """
    rel = RelatorioLint()
    nodes = [n for n in (nodes or []) if isinstance(n, Mapping)]
    # Só arestas com as duas pontas: o Pydantic do router já garante isso, e
    # uma entrada malformada aqui não é diagnóstico do fluxo, é lixo de payload.
    edges = [
        e for e in (edges or [])
        if isinstance(e, Mapping) and "source" in e and "target" in e
    ]

    def alias_efetivo(node: Mapping[str, Any], name: str) -> str:
        # `resolve_alias` honrando o `reserved_aliases` recebido (e tolerante a
        # nó sem `name`, que `unknown_node` já acusa).
        custom = alias_declarado(node)
        if custom and custom.isidentifier() and custom not in reserved_aliases:
            return custom
        return name

    # 1. Ids duplicados. O executor monta `{id: nó}` e o último vence.
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

    # 2. Por nó: nome, alias, segredos, credential_id e propriedades.
    for node in nodes:
        nid = str(node.get("id") or "")
        name = str(node.get("name") or "")
        params = _params_de(node)

        if name not in registry_names:
            # O prefixo é a mensagem da factory (flow/factory.py), à letra: é o
            # texto que o consumidor da validação já procura.
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

        # Segredo gravado na definição. Nunca ecoar o valor: o diagnóstico vai
        # para logs e para o cliente, e o problema é justamente o vazamento.
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
            # Só a PRESENÇA da chave é checada, nunca o tipo do valor: um
            # parâmetro pode ser expressão Jinja que só vira inteiro no run.
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
            # A exceção à regra "nunca o tipo": propriedade `object` gravada como
            # texto. O run a decodifica em validate() (`_coerce_structured`) e
            # falha com esta mesma frase se não for JSON de dict/list — `rules`
            # ilegível do Switch passava mudo por aqui e `schema_declarado` o
            # escondia (só o fallback no schema). Texto com template fica de
            # fora: `{"limite": {{ inputs.n }}}` só vira JSON válido no run.
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
            # Switch: `fallback_output` presente e vazio não cai no default — o
            # run lê `parameters.get("fallback_output", "output_0")` e emite a
            # porta '' literalmente, que nenhuma aresta consegue nomear.
            # É erro, não aviso: nenhuma aresta nomeia a porta '' (`from_key`
            # vazio é "sem chave"), então a fiação a partir dela está morta e o
            # diagnóstico de aresta não a enxerga — o relatório diria `ok`.
            if "fallback_output" in declaradas and params.get("fallback_output", None) == "":
                rel.erro(
                    "empty_fallback_output",
                    f"fallback_output vazio em '{name}' (id={nid}): o run emitiria a "
                    "porta '', que nenhuma aresta consegue nomear; use um nome (o "
                    "default só vale com a chave ausente).",
                    node_id=nid,
                )

    # 3. Alias duplicado. Dois nós sob o mesmo alias: `named[alias]` guarda só o
    # último que rodou. Com alias explícito é erro (o usuário pediu um nome e ele
    # não aponta para onde acha). Derivado do `name` (dois "Buffer" sem alias) é
    # normal e só vira aviso se alguma expressão de fato referencia esse nome.
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

    # 4. Grafo: aresta órfã, ciclo, nós que ficam de fora do run.
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
            # `.get`, não `[]`: incoming/outgoing são defaultdict e o acesso
            # por índice criaria a chave.
            if not graph.incoming.get(nid) and not graph.outgoing.get(nid):
                msg = f"nó '{name}' (id={nid}) isolado: sem arestas, fica fora da simulação e do run."
            else:
                msg = (
                    f"nó '{name}' (id={nid}) sem caminho a partir de um trigger: "
                    "fica fora da simulação e do run."
                )
            rel.aviso("unreachable_node", msg, node_id=nid)
        # O NodeManager só instancia os nós da ordem de execução: um nome
        # inexistente fora dela (isolado, fora do cone do trigger) continua
        # erro, mas não derruba o construtor. Com ciclo não há ordem — e
        # `cycle` já é fatal.
        na_ordem = set(order)
        for d in rel.errors:
            if d.code == "unknown_node" and d.node_id not in na_ordem:
                d.fatal = False
    rel.execution_order = list(order)

    # 5. Parâmetros de execução que o fluxo espera. `{{ inputs.X }}` só é
    # parâmetro do usuário em nó trigger (core.py: nos demais, `inputs` são as
    # arestas). As `ports` do SubWorkflowInput são o contrato de entrada.
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
