# app/mcp/catalogo.py
"""
O catálogo de nós em dois tamanhos: o índice que cabe no contexto e a ficha completa.

O `description()` de todos os nós registrados soma perto de 80 KB de JSON.
Entregar isso numa chamada consome o orçamento de contexto de quem está do
outro lado antes de a conversa começar — e nove décimos daquilo é detalhe de
propriedade que só interessa depois de escolhido o nó. Daí a divisão:

- `indice_compacto` responde "que nós existem, e para quê" em ~10 KB: nome,
  tipo, a primeira frase da descrição e se o nó pede credencial;
- `descrever(brief=True)` responde "como configuro este nó" com as propriedades
  essenciais;
- `descrever(brief=False)` entrega a ficha inteira mais as dicas que não estão
  em nenhum campo — que as saídas deste nó dependem do que o usuário declarar,
  que tal propriedade espera um nome de coluna.

Tudo é derivado do registro de nós em tempo de chamada. Nenhuma lista copiada:
um nó novo aparece aqui no mesmo deploy em que aparece no editor, e um nó
desabilitado some dos dois.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Iterable, Mapping

# A primeira frase de uma descrição longa ainda pode ser longa; o índice
# inteiro é lido de uma vez, então o corte vale mais que a frase completa
# (quem quiser o texto todo chama `describe_node`).
_MAX_ONE_LINE = 160

# Piso para aceitar um segmento como frase. O ponto que fecha uma frase e o
# ponto de uma abreviação ("Ex.", "etc.", "p. ex.", "Obs.") são o mesmo
# caractere, e cortar no primeiro deixaria o índice cheio de linhas "Ex" e
# "etc" — que não dizem nada sobre o nó. Abaixo deste tamanho o segmento é
# JUNTADO ao seguinte, nunca descartado: perder o resto da frase é pior do que
# uma linha um pouco mais longa. O valor fica abaixo de qualquer frase real
# curta ("Recorta camadas", "Ordena as linhas") e acima das abreviações que
# aparecem nas descrições.
_MIN_ONE_LINE = 8

# Abreviações que fecham com ponto no MEIO da frase e escapam do piso acima
# ("Junta SHP, GeoJSON, etc. Aceita ZIP." tem 33 caracteres antes do ponto).
# Lista curta e explícita de propósito: o que não estiver aqui simplesmente
# corta como sempre cortou — errar para o lado de uma linha mais curta é
# preferível a adivinhar gramática.
_ABREVIACOES = frozenset({"ex", "etc", "p", "pag", "obs", "cf", "fig", "aprox", "vs", "ref"})


def _texto_de_descricao(desc: Any) -> str:
    """A descrição, venha ela como texto, dict ou `NodeDefinition`."""
    if isinstance(desc, str):
        return desc
    if isinstance(desc, Mapping):
        return str(desc.get("description") or "")
    return str(getattr(desc, "description", None) or "")


def one_line(desc: Any) -> str:
    """A primeira frase da descrição, sem o ponto final.

    O corte é no primeiro PARÁGRAFO, e não na primeira quebra de linha: muitas
    descrições do catálogo são escritas em texto corrido e quebram no meio da
    frase, mas quase todas separam a explicação longa por uma linha em branco.

    Dentro do parágrafo, a frase termina no primeiro ponto seguido de ESPAÇO —
    exigir o espaço é o que protege os decimais, que o catálogo usa o tempo todo
    ("buffer de 0.5 m"). Sobra a abreviação, que traz o espaço junto: um segmento
    curto demais para ser frase ("Ex.", "p. ex.") ou terminado numa abreviação
    conhecida ("…, etc.") é juntado ao seguinte, em vez de cortar a descrição no
    meio e deixar a linha do índice sem dizer para que o nó serve.
    """
    paragrafo = _texto_de_descricao(desc).split("\n\n")[0]
    texto = " ".join(paragrafo.split())
    if not texto:
        return ""
    partes = texto.split(". ")
    frase = partes[0]
    for seguinte in partes[1:]:
        if not _fim_de_frase(frase):
            frase = f"{frase}. {seguinte}"
            continue
        break
    frase = frase.rstrip(".")
    if len(frase) > _MAX_ONE_LINE:
        frase = frase[: _MAX_ONE_LINE - 1].rstrip() + "…"
    return frase


def _fim_de_frase(trecho: str) -> bool:
    """O ponto depois deste trecho fecha mesmo uma frase?

    Duas recusas: o trecho é curto demais para ser frase (é uma abreviação
    inteira, "Ex.") ou termina numa abreviação conhecida ("…, etc.").
    """
    sem_ponto = trecho.rstrip(".")
    if len(sem_ponto) < _MIN_ONE_LINE:
        return False
    palavras = sem_ponto.split()
    ultima = _normalizar(palavras[-1]).strip(",;:()[]") if palavras else ""
    return ultima not in _ABREVIACOES


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acento — busca por "área" acha "area" e vice-versa."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold()


def _campos_de_busca(d: Any) -> str:
    return " ".join(
        str(valor or "")
        for valor in (
            getattr(d, "name", None),
            getattr(d, "alias", None),
            getattr(d, "type", None),
            _texto_de_descricao(d),
        )
    )


def indice_compacto(
    defs: Iterable[Any], *, query: str | None = None, tipo: str | None = None
) -> list[dict]:
    """O índice filtrado, ordenado por nome.

    O filtro por `query` corre sobre nome, apelido, tipo e descrição: quem
    procura "postgres" não sabe se o nó se chama `DatabaseQuery`.
    """
    alvo = _normalizar(query) if query else None
    itens: list[dict] = []
    for d in defs:
        if tipo and str(getattr(d, "type", "") or "") != tipo:
            continue
        if alvo and alvo not in _normalizar(_campos_de_busca(d)):
            continue
        itens.append(
            {
                "name": getattr(d, "name", None),
                "type": getattr(d, "type", None),
                "one_line": one_line(d),
                "requires_credential": bool(getattr(d, "requires_credential", False)),
            }
        )
    return sorted(itens, key=lambda i: str(i["name"] or ""))


def tipos_do_catalogo(defs: Iterable[Any]) -> list[dict]:
    """`[{type, count}]` — o mapa que diz por onde filtrar antes de listar tudo."""
    contagem: dict[str, int] = {}
    for d in defs:
        chave = str(getattr(d, "type", "") or "sem_tipo")
        contagem[chave] = contagem.get(chave, 0) + 1
    return [{"type": tipo, "count": n} for tipo, n in sorted(contagem.items())]


def _propriedade_essencial(p: Any) -> dict:
    """O mínimo para configurar a propriedade — sem rótulo, ajuda nem visibilidade."""
    item: dict[str, Any] = {"name": getattr(p, "name", None), "type": getattr(p, "type", None)}
    # `required` não existe no catálogo de hoje; é lido por getattr para que um
    # dia em que passe a existir a informação apareça sem mexer aqui.
    if getattr(p, "required", None):
        item["required"] = True
    default = getattr(p, "default", None)
    if default is not None:
        item["default"] = default
    opcoes = getattr(p, "options", None)
    if opcoes:
        item["options"] = [
            {"value": getattr(o, "value", None), "label": getattr(o, "label", None)}
            for o in opcoes
        ]
    tipos_de_credencial = getattr(p, "credential_types", None)
    if tipos_de_credencial:
        item["credential_types"] = list(tipos_de_credencial)
    return item


def _dicas(d: Any) -> list[str]:
    """O que a ficha não diz por campo e faz a diferença na hora de montar o nó."""
    dicas: list[str] = []
    if getattr(d, "dynamic_inputs", False):
        dicas.append(
            "As entradas deste nó são as que você declarar na propriedade `ports`; "
            "as arestas que chegam usam esses nomes em `to_key`."
        )
    if getattr(d, "outputs_from_ports", False):
        dicas.append(
            "As saídas deste nó são as que você declarar na propriedade `ports`; "
            "cada porta é um ponto de saída próprio, nomeado em `from_key`."
        )
    if getattr(d, "dynamic_output", False):
        dicas.append(
            "As saídas deste nó vêm da propriedade `output_vars`, e não dos "
            "`outputs` do catálogo."
        )
    for p in getattr(d, "properties", None) or []:
        porta = getattr(p, "suggest_columns", None)
        if not porta:
            continue
        origem = "de qualquer entrada" if porta == "*" else f"que chega pela porta `{porta}`"
        dicas.append(
            f"A propriedade `{getattr(p, 'name', '')}` espera o NOME DE UMA COLUNA do dado {origem}."
        )
    if getattr(d, "requires_credential", False):
        dicas.append(
            "Este nó exige credencial: passe o identificador de `list_credentials`, "
            "nunca a string de conexão ou o token em si."
        )
    tipo_de_fonte = getattr(d, "source_kind", None)
    if tipo_de_fonte:
        dicas.append(
            f"Este nó lê uma FONTE EXTERNA ({tipo_de_fonte}): não invente `url`/`typeName`. "
            f"Consulte `search_sources(kind=\"{tipo_de_fonte}\")` e cole o `node_snippet` de "
            "`describe_source`; fonte fora do catálogo → `probe_source` e `register_source`."
        )
    return dicas


def descrever(d: Any, *, brief: bool) -> dict:
    """A ficha do nó — essencial ou completa, sempre com as dicas no fim."""
    if not brief:
        # `model_dump` do próprio `NodeDefinition`: a ficha completa é o que o
        # editor consome, e copiá-la campo a campo aqui criaria uma segunda
        # definição do que é um nó, fadada a ficar para trás.
        ficha = d.model_dump(exclude_none=True) if hasattr(d, "model_dump") else dict(d)
        ficha["hints"] = _dicas(d)
        return ficha

    return {
        "name": getattr(d, "name", None),
        "type": getattr(d, "type", None),
        "description": _texto_de_descricao(d) or None,
        "properties": [_propriedade_essencial(p) for p in getattr(d, "properties", None) or []],
        "inputs": [
            {"name": getattr(p, "name", None), "description": getattr(p, "description", None)}
            for p in getattr(d, "inputs", None) or []
        ],
        "outputs": [
            {
                "name": getattr(c, "name", None),
                "type": getattr(c, "type", None),
                "description": getattr(c, "description", None),
            }
            for c in getattr(d, "outputs", None) or []
        ],
        "requires_credential": bool(getattr(d, "requires_credential", False)),
        "hints": _dicas(d),
    }
