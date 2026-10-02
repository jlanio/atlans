"""Redação recursiva de uma definition de workflow antes de ela SAIR do servidor.

A definition salva carrega, em `nodes[].properties` (ou `parameters`, o formato
do corpo da validação), tudo o que o editor gravou: `connectionString` legado
cifrado com Fernet, `headers.Authorization` escrito à mão, DSN com senha em
`url`. O `_sem_segredos` da factory só olha o primeiro nível e só serve ao log;
quem devolve a definition inteira a um cliente (o servidor MCP, versões,
exportação) precisa descer por dict/list, e precisa da MESMA lista de chaves do
lint — uma terceira lista divergiria em silêncio.

Três funções, todas puras e sem mutar a entrada:

- `redigir_definition`: chave sensível → "<REDACTED>", toda string folha passa
  por `scrub_text` (Bearer, PAT, DSN...) e toda string que é JSON de um dict é
  redigida por dentro e re-serializada — na definition INTEIRA, porque é a
  definition inteira que se entrega. É a versão que se ENTREGA.
- `compactar_definition`: tira o que só interessa ao canvas (posição,
  viewport). Reduz o que um agente lê sem mudar semântica.
- `definition_contem_segredo`: caminhos onde há segredo LITERAL preenchido —
  a borda que recusa a entrada precisa dizer ONDE, não só que há. Recusa
  também o MARCADOR `<REDACTED>` em qualquer string: ele só existe numa
  definition que saiu redigida daqui, e gravá-lo de volta apagaria, em
  silêncio, o valor que a redação escondeu (a chave de uma URL, um token num
  texto). É o que fecha o ciclo ler → editar → gravar sem destruir nada.

Teto de profundidade em todas: uma estrutura patológica não vira recursão
infinita. O que fica além do teto é tratado como opaco — o redator não entrega
o que não conseguiu inspecionar, e a checagem acusa o caminho.
"""
from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from typing import Any, Iterator, Mapping

from app.core.utils.logger import _REDACTED, scrub_text
# `_CABECALHOS_SECRETOS` é privado do lint, mas é a fonte da verdade sobre quais
# cabeçalhos carregam credencial. Importar em vez de copiar mantém redação e
# lint em passo: um cabeçalho novo no lint passa a ser redigido aqui sem
# ninguém lembrar de mexer em dois lugares.
from flow.utils.definition_lint import (
    _CABECALHOS_SECRETOS,
    _PROFUNDIDADE_MAX,
    _como_dict,
    _preenchido,
    _residuo_literal,
    CHAVES_SECRETAS,
)

# Chaves que, em qualquer nível de `properties`/`parameters`, nunca saem em
# claro. União das duas listas do lint — nunca uma terceira.
CHAVES_REDIGIDAS: frozenset = CHAVES_SECRETAS | _CABECALHOS_SECRETOS

# Os dois nomes do mesmo saco de parâmetros: `properties` na definition salva,
# `parameters` no corpo da validação (mesma tolerância do simulate_runner).
_CONTAINERS_DE_PARAMETROS = ("properties", "parameters")

# O que só o canvas usa. `viewport` fica no topo; os demais em cada nó.
_CHAVES_DE_CANVAS_NO_NO = ("position", "measured", "selected", "dragging")
_CHAVES_DE_CANVAS_NO_TOPO = ("viewport",)

# `scheme://usuario:senha@host` — o mesmo desenho do padrão de DSN do logger,  # pragma: allowlist secret
# aqui só para DETECTAR (a redação fica com o `scrub_text`). Corre sobre o
# resíduo literal da string: `postgresql://{{ $Cred.user }}:{{ $Cred.senha }}@h`
# não tem usuário nem senha gravados.
# Tetos e usuario opcional pelo mesmo motivo do logger: custo linear e
# `redis://:senha@host` (senha sem usuario) tambem conta como credencial.
_URL_COM_CREDENCIAL = re.compile(r"(?i)\b[a-z][a-z0-9+.\-]{0,31}://[^/\s:@]*:[^\s/]{1,256}@")
# A chave do módulo authkey do GeoServer gravada na query da URL — no nó WFS
# ela mora em Credenciais (`geoserver_authkey`), nunca na `url`. Só vale na
# `url` de um nó que USA essa credencial (ver `_nos_com_authkey`): num
# HttpRequest, ou num texto, `authkey` é só uma palavra — e a borda recusava
# uma definição inteira por ela. A entrega redige `authkey=` em QUALQUER
# string (`scrub_text`); o que impede a leitura redigida de ser gravada por
# cima da chave num HttpRequest é a recusa do marcador `<REDACTED>`, abaixo.
_URL_COM_AUTHKEY = re.compile(r"(?i)[?&]authkey=[^&#\s]{4,}")
# Blocos Jinja e literais entre aspas dentro deles: `{{ x | default('hunter2') }}`
# sob uma chave sensível grava um segredo que `_preenchido` não vê (ele tira o
# bloco inteiro). A ENTREGA precisa vê-lo; a borda segue com a regra do lint.
_BLOCOS_JINJA_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
_LITERAL_ENTRE_ASPAS_RE = re.compile(r"""(['"]).+?\1""", re.S)
# Onde a `url` de um nó mora na definition: `properties`/`parameters` (os dois
# sacos) e `data.properties` (o que o editor grava).
_URL_DE_NO_RE = re.compile(r"^nodes\[(\d+)\]\.(?:properties|parameters|data\.properties)\.url$")


def _e_chave_redigida(chave: Any) -> bool:
    return str(chave).lower() in CHAVES_REDIGIDAS


@lru_cache(maxsize=1)
def _nos_com_authkey() -> frozenset:
    """Os nós cujo `credential_id` aceita `geoserver_authkey` — só na `url`
    deles uma `?authkey=` gravada é a chave fora do lugar. Lido do registro
    (a fonte do que cada nó aceita); sem registro, o nó WFS."""
    try:
        from flow.registry import NODE_REGISTRY

        nos = set()
        for nome, cls in NODE_REGISTRY.items():
            for prop in cls.description().get("properties") or []:
                if prop.get("name") == "credential_id" and "geoserver_authkey" in (prop.get("credential_types") or ()):
                    nos.add(nome)
    except Exception:  # registro indisponível ou descriptor quebrado
        nos = set()
    return frozenset(nos) or frozenset({"WFS"})


def _nome_do_no(node: Mapping[str, Any]) -> str:
    dados = node.get("data")
    return str(node.get("name") or (dados.get("name") if isinstance(dados, Mapping) else "") or "")


def _indices_com_authkey(definition: Mapping[str, Any]) -> frozenset:
    """Os índices, em `nodes`, dos nós em que `?authkey=` na `url` é segredo."""
    com_authkey = _nos_com_authkey()
    return frozenset(i for i, node in _nos_de(definition) if _nome_do_no(node) in com_authkey)


def _nos_de(definition: Mapping[str, Any]) -> Iterator[tuple[int, dict]]:
    """Índice e nó, só dos nós que são dict — o resto fica intacto onde está."""
    nodes = definition.get("nodes")
    if not isinstance(nodes, list):
        return
    for i, node in enumerate(nodes):
        if isinstance(node, dict):
            yield i, node


# ── redigir ──────────────────────────────────────────────────────────────────

def _so_referencias(valor: Any, profundidade: int = 0) -> bool:
    """Sob uma chave sensível, não há NADA literal aqui dentro?

    Vazio (`{}`, `""`, None) ou só referências a valores de runtime
    (`{{ inputs.pw }}`, `$Cred.token`, `Bearer {{ tok }}`) — sem literal entre
    aspas dentro das expressões. Um mapping ignora a chave `type` (seletor,
    como em `_preenchido`); número ou booleano é literal (`"password": 1234`).
    """
    if profundidade > _PROFUNDIDADE_MAX:
        return False
    if valor is None:
        return True
    if isinstance(valor, str):
        if _preenchido(valor):
            return False
        return not any(_LITERAL_ENTRE_ASPAS_RE.search(bloco) for bloco in _BLOCOS_JINJA_RE.findall(valor))
    if isinstance(valor, dict):
        return all(
            _so_referencias(item, profundidade + 1)
            for chave, item in valor.items() if str(chave).lower() != "type"
        )
    if isinstance(valor, list):
        return all(_so_referencias(item, profundidade + 1) for item in valor)
    return False


def _redigir_valor(valor: Any, profundidade: int) -> Any:
    """Desce por dict/list trocando chave sensível e passando cada string folha
    pelo `scrub_text`. String que é JSON de um dict conta como estrutura, não
    como folha: entra na descida e volta serializada. Além do teto, a subárvore
    inteira vira marcador: se não dá para olhar dentro, não se entrega."""
    if profundidade > _PROFUNDIDADE_MAX:
        return _REDACTED
    if isinstance(valor, str):
        # O editor grava dict SERIALIZADO em mais propriedades que `headers`
        # (`body`, `config`, `options`): uma string JSON é estrutura, não
        # texto, e o `scrub_text` sozinho não conhece `x-api-key` nem
        # `connectionString` dentro dela. Parseia, redige por chave e
        # re-serializa; o que não for JSON de dict segue pelo `scrub_text`.
        aninhado = _como_dict(valor)
        if aninhado is None:
            return scrub_text(valor)
        return json.dumps(_redigir_valor(aninhado, profundidade + 1), ensure_ascii=False)
    if isinstance(valor, dict):
        saida = {}
        for chave, item in valor.items():
            # Chave sensível sem NADA literal dentro (`http_auth: {}`, o padrão
            # que o nó WFS declara; `password: ""`; `token: "{{ inputs.tok }}"`)
            # não esconde nada — e sai como entrou, para a definition lida
            # voltar a ser gravável: um `"<REDACTED>"` no lugar é um segredo
            # "preenchido" que a borda recusa na volta. Qualquer literal, mesmo
            # escondido numa expressão, some inteiro.
            if _e_chave_redigida(chave) and not _so_referencias(item, profundidade + 1):
                saida[chave] = _REDACTED
            else:
                saida[chave] = _redigir_valor(item, profundidade + 1)
        return saida
    if isinstance(valor, list):
        return [_redigir_valor(item, profundidade + 1) for item in valor]
    return valor


def _sem_os_sacos(definition: Mapping[str, Any]) -> tuple:
    """Separa a definition em (resto, sacos), sem tocar na entrada.

    `sacos` traz `nodes[].properties`/`parameters` indexados por `(índice do
    nó, nome do contêiner)`; `resto` é a definition com esses dois fora.

    A descida tem teto de profundidade, e o teto é a única razão de os dois
    sacos receberem tratamento próprio: uma propriedade aninhada é conteúdo de
    quem edita e pode ser funda, e gastar os três primeiros níveis só para
    chegar de `{}` até `nodes[i].properties` encurtaria o orçamento de
    exatamente o lugar que mais precisa dele. Assim cada saco é percorrido com
    a profundidade contada a partir dele, e o resto a partir da raiz.

    A separação é por cópia RASA (o dict do topo, a lista de nós e os nós que
    perdem um contêiner): a entrada continua intacta e uma definition grande
    não paga uma cópia profunda só para ser inspecionada.
    """
    resto = dict(definition)
    sacos: dict = {}
    nodes = resto.get("nodes")
    if not isinstance(nodes, list):
        return resto, sacos

    novos = list(nodes)
    for i, node in enumerate(novos):
        if not isinstance(node, dict):
            continue
        presentes = [c for c in _CONTAINERS_DE_PARAMETROS if c in node]
        if not presentes:
            continue
        copia = dict(node)
        for container in presentes:
            sacos[(i, container)] = copia.pop(container)
        novos[i] = copia
    resto["nodes"] = novos
    return resto, sacos


def redigir_definition(definition: Mapping[str, Any]) -> dict:
    """Cópia da definition com os segredos redigidos em QUALQUER chave, em
    qualquer nível — não só dentro de `nodes[].properties` e
    `nodes[].parameters`.

    Quem recebe a definition recebe a definition inteira: um saco de
    configuração no topo, um `nodes[].data` gravado pelo editor ou um `config`
    fora dos dois contêineres conhecidos sairiam verbatim se a descida
    começasse nos contêineres — sem sequer passar pelo `scrub_text`. Por isso
    a descida começa na RAIZ, e os dois sacos entram por fora só para não
    gastar o orçamento de profundidade deles com os níveis da definition.

    O que não é segredo continua saindo como entrou (edges, ids, números,
    nó que não é dict, definition sem `nodes`).
    """
    resto, sacos = _sem_os_sacos(definition)
    redigida = _redigir_valor(resto, 0)
    for (i, container), valor in sacos.items():
        redigida["nodes"][i][container] = _redigir_valor(valor, 0)
    return redigida


# ── compactar ────────────────────────────────────────────────────────────────

def compactar_definition(definition: Mapping[str, Any]) -> dict:
    """Cópia da definition sem o que só serve ao canvas: `viewport` no topo e
    `position`/`measured`/`selected`/`dragging` em cada nó. Não redige — é
    tamanho, não segurança; combine com `redigir_definition` para entregar."""
    saida = copy.deepcopy(dict(definition))
    for chave in _CHAVES_DE_CANVAS_NO_TOPO:
        saida.pop(chave, None)
    for _, node in _nos_de(saida):
        for chave in _CHAVES_DE_CANVAS_NO_NO:
            node.pop(chave, None)
    return saida


# ── detectar ─────────────────────────────────────────────────────────────────

def _url_com_credencial_literal(texto: str, *, authkey: bool = False) -> bool:
    """A string grava `user:senha@` — ou, com `authkey`, `?authkey=` —
    LITERALMENTE? Expressões e `$Alias` são tirados antes: credencial que só
    existe em runtime não é segredo salvo."""
    residuo = _residuo_literal(texto)
    if _URL_COM_CREDENCIAL.search(residuo) is not None:
        return True
    return authkey and _URL_COM_AUTHKEY.search(residuo) is not None


def _e_url_de_no_com_authkey(caminho: str, indices: frozenset) -> bool:
    m = _URL_DE_NO_RE.match(caminho)
    return m is not None and int(m.group(1)) in indices


def _caminhos_com_segredo(valor: Any, caminho: str, profundidade: int,
                          encontrados: list, com_authkey: frozenset = frozenset()) -> None:
    if profundidade > _PROFUNDIDADE_MAX:
        # Opaco: não dá para afirmar que está limpo, então acusa.
        encontrados.append(caminho)
        return
    if isinstance(valor, str):
        # Mesma regra do redator: string que é JSON de dict é estrutura, e o
        # caminho acusado desce para dentro dela
        # (`nodes[0].properties.config.token`) em vez de parar na propriedade.
        aninhado = _como_dict(valor)
        if aninhado is not None:
            _caminhos_com_segredo(aninhado, caminho, profundidade + 1, encontrados, com_authkey)
        elif _REDACTED in valor or _url_com_credencial_literal(valor, authkey=_e_url_de_no_com_authkey(caminho, com_authkey)):
            # O marcador é nosso: só chega aqui numa definition que saiu
            # redigida e voltou — gravá-lo apagaria o valor escondido.
            encontrados.append(caminho)
        return
    if isinstance(valor, dict):
        for chave, item in valor.items():
            # Na raiz o caminho ainda é vazio: `params_schema.token`, e não
            # `.params_schema.token`.
            sub = f"{caminho}.{chave}" if caminho else str(chave)
            if _e_chave_redigida(chave):
                if _preenchido(item):
                    encontrados.append(sub)
                continue
            _caminhos_com_segredo(item, sub, profundidade + 1, encontrados, com_authkey)
        return
    if isinstance(valor, list):
        for i, item in enumerate(valor):
            _caminhos_com_segredo(item, f"{caminho}[{i}]", profundidade + 1, encontrados, com_authkey)


# Campos de um parâmetro do `params_schema` que gravam VALOR; os demais o
# descrevem (tipo, rótulo, `required`). Um parâmetro chamado `token` ou
# `password` é o caso normal — o valor chega na execução, pelo `inputs` —, e o
# próprio lint sugere `{"token": {"type": "string", "required": true}}`:
# varrer o schema como se fosse definition recusava a sugestão (`required:
# true` é literal "preenchido" sob uma chave sensível).
_CAMPOS_DE_VALOR_DO_PARAMETRO = ("default", "enum", "examples", "const", "value")


def params_schema_contem_segredo(schema: Any) -> list[str]:
    """Caminhos (`params_schema.token.default`) onde o `params_schema` grava
    segredo literal: o valor de um parâmetro de nome sensível, ou, em
    qualquer campo, uma URL com senha ou o marcador `<REDACTED>`. Um
    parâmetro só declarado (`{"type": "string", "required": true}`) não grava
    nada. Um schema que não é objeto também não: a validação de forma o
    recusa adiante."""
    if not isinstance(schema, Mapping):
        return []
    encontrados: list = []
    for nome, spec in schema.items():
        base = f"params_schema.{nome}"
        if not isinstance(spec, Mapping):
            # Forma curta `{"token": "valor"}`: o valor é o próprio parâmetro.
            _caminhos_com_segredo({nome: spec}, "params_schema", 0, encontrados)
            continue
        for campo, valor in spec.items():
            caminho = f"{base}.{campo}"
            if campo in _CAMPOS_DE_VALOR_DO_PARAMETRO and _e_chave_redigida(nome):
                if _preenchido(valor):
                    encontrados.append(caminho)
            elif campo in _CAMPOS_DE_VALOR_DO_PARAMETRO or isinstance(valor, str):
                _caminhos_com_segredo(valor, caminho, 0, encontrados)
    return encontrados


def definition_contem_segredo(definition: Mapping[str, Any]) -> list[str]:
    """Caminhos (`nodes[2].properties.connectionString`,
    `nodes[0].properties.headers.Authorization`, `nodes[1].properties.url`)
    onde há segredo LITERAL preenchido.

    "Preenchido" é a regra `_preenchido` do lint: string não vazia depois de
    tirar `{{ … }}`/`{% … %}` e `$Alias`, e que não seja só um esquema de
    autenticação ("Bearer {{ inputs.tok }}" não grava nada); dict/list contam
    se alguma folha contar. Uma URL conta quando grava `user:senha@` — e, na
    `url` de um nó que usa a credencial `geoserver_authkey`, quando grava
    `?authkey=`. Qualquer string com o marcador `<REDACTED>` conta: é uma
    leitura redigida voltando, e gravá-la apagaria o valor escondido. String
    que é JSON de um dict (o editor grava assim em `headers`, `body`, `config`)
    é lida como estrutura, e o caminho acusado desce para dentro dela. Lista
    vazia = nada a recusar.

    A varredura cobre a definition INTEIRA, e não só os dois sacos de
    parâmetros: a detecção não pode ser mais estreita que a redação, senão a
    borda aceita o que a entrega depois apaga — e passa a existir um lugar
    (`nodes[].data`, um saco no topo) onde o segredo entra sem ninguém avisar.
    Os sacos entram por fora só pelo orçamento de profundidade, como em
    `redigir_definition`; por isso os caminhos deles vêm depois."""
    encontrados: list = []
    com_authkey = _indices_com_authkey(definition)
    resto, sacos = _sem_os_sacos(definition)
    _caminhos_com_segredo(resto, "", 0, encontrados, com_authkey)
    for (i, container), valor in sacos.items():
        _caminhos_com_segredo(valor, f"nodes[{i}].{container}", 0, encontrados, com_authkey)
    return encontrados
