# flow/nodes/contrato.py
"""O contrato do description() de um nó — vocabulários fechados e validação.

O campo `type` acumulava três papéis com vocabulários misturados e nenhum
deles validado: a CATEGORIA do nó, o TIPO DE CAMPO de saída e o TIPO DE
PROPRIEDADE (widget do formulário). Um typo em qualquer um passava mudo pela
importação e virava defeito visual longe da causa — nó sem ícone, campo sem
editor, porta sem tipo.

Aqui os três vocabulários viram conjuntos fechados, e `validar_description`
roda na importação (via `register_node`): nó malformado morre no CI com a
frase apontando o campo, não na tela.
"""
from typing import Any

# Categoria do nó — decide a paleta, o ícone e o agrupamento no editor.
CATEGORIAS = frozenset({"trigger", "action", "spatial", "datasource", "output", "control"})

# Tipo do DADO que sai por um campo de `outputs` (não é widget de UI).
TIPOS_DE_CAMPO = frozenset({"geodataframe", "string", "number", "boolean", "object", "list", "any"})

# Tipo de uma propriedade — o WIDGET do formulário do editor. `integer` não é
# sinônimo de `number`: o form arredonda e usa step=1 (numeric-field.tsx).
TIPOS_DE_PROPRIEDADE = frozenset({
    "string", "number", "integer", "boolean", "object", "select", "chips",
    "credential", "keyvalue", "code", "ports", "drive", "artifact", "sql",
})

# Todas as chaves que um description() pode ter. Chave fora do conjunto é
# quase sempre typo (`output` por `outputs`) — e um typo aqui não quebra nada
# na hora: o campo só deixa de existir para o editor e para o validate.
CHAVES_DO_DESCRIPTION = frozenset({
    "name", "alias", "description", "type", "properties", "outputs", "inputs",
    "dynamic_inputs", "dynamic_output", "outputs_from_ports", "branches",
    "requires_credential", "source_kind",
})

CHAVES_DE_PROPRIEDADE = frozenset({
    "name", "label", "type", "default", "description", "credential_types",
    "drive_extensions", "options", "visibleWhen", "suggest_columns",
    "required", "placeholder",
})


# Nomes que já existiram no catálogo e para onde foram. A renomeação de 27/07
# (commit ff11c196, "app em dev, sem shim") não migrou os fluxos salvos: um
# fluxo com `DriveTrigger` falhava todo dia na partida com "Node 'DriveTrigger'
# não encontrado". Quem lê isto: o `python -m app.cli migrar-nos` (que reescreve
# as definições salvas) e as mensagens de nó desconhecido do lint e da factory,
# que passam a dizer para onde o nó foi em vez de só que ele não existe.
# Renomear um nó daqui em diante = uma entrada nova aqui, no mesmo commit.
NOMES_ANTIGOS: dict[str, str] = {
    "DriveTrigger": "DataInput",
    "ArtifactOutput": "DataOutput",
}


# Nós que saíram do catálogo sem substituto, e por quê. O executor constrói
# todos os nós antes do run — inclusive os de um ramo que não vai rodar —, então
# um fluxo salvo com um deles para de rodar inteiro: a mensagem tem de dizer que
# o nó saiu, e não sugerir erro de digitação.
NOS_REMOVIDOS: dict[str, str] = {
    "Cluster": (
        "dependia do scikit-learn, que nenhuma instalação do executor traz, e "
        "falhava em todo run"
    ),
}


def dica_de_no_desconhecido(nome: str) -> str:
    """Complemento da mensagem de nó desconhecido (renomeado ou removido);
    vazio se o nome nunca existiu."""
    novo = NOMES_ANTIGOS.get(nome)
    if novo:
        return (
            f" Este nó foi renomeado para '{novo}': troque-o no editor, ou peça ao "
            "administrador para rodar `python -m app.cli migrar-nos --aplicar`."
        )
    motivo = NOS_REMOVIDOS.get(nome)
    if motivo:
        return f" Este nó saiu do catálogo ({motivo}): tire-o do fluxo no editor."
    return ""


def _erro(nome: str, msg: str) -> ValueError:
    return ValueError(f"description() de '{nome}': {msg}")


def validar_description(desc: Any) -> None:
    """Valida um description() completo. Levanta ValueError com a causa exata.

    Roda na importação do módulo do nó (register_node), então o custo é pago
    uma vez por processo — e um nó malformado nunca chega ao registry.
    """
    if not isinstance(desc, dict):
        raise ValueError(f"description() deve devolver dict, não {type(desc).__name__}.")

    nome = desc.get("name")
    if not isinstance(nome, str) or not nome or " " in nome:
        raise ValueError(f"description() sem 'name' válido (sem espaços): {nome!r}.")

    estranhas = set(desc) - CHAVES_DO_DESCRIPTION
    if estranhas:
        raise _erro(nome, f"chaves desconhecidas {sorted(estranhas)} — typo? "
                          f"Aceitas: {sorted(CHAVES_DO_DESCRIPTION)}.")

    categoria = desc.get("type")
    if categoria not in CATEGORIAS:
        raise _erro(nome, f"'type' (categoria) inválido: {categoria!r}. "
                          f"Aceitos: {sorted(CATEGORIAS)}.")

    props = desc.get("properties")
    if not isinstance(props, list):
        raise _erro(nome, "'properties' deve ser uma lista (mesmo vazia).")
    for p in props:
        if not isinstance(p, dict) or not p.get("name"):
            raise _erro(nome, f"propriedade sem 'name': {p!r}.")
        estranhas = set(p) - CHAVES_DE_PROPRIEDADE
        if estranhas:
            raise _erro(nome, f"propriedade '{p['name']}' com chaves desconhecidas "
                              f"{sorted(estranhas)}.")
        tipo = p.get("type")
        if tipo not in TIPOS_DE_PROPRIEDADE:
            raise _erro(nome, f"propriedade '{p['name']}' com type inválido: {tipo!r}. "
                              f"Aceitos: {sorted(TIPOS_DE_PROPRIEDADE)}.")
        if tipo == "select" and not p.get("options"):
            raise _erro(nome, f"propriedade '{p['name']}' é select sem 'options'.")
        if tipo == "credential" and not p.get("credential_types"):
            raise _erro(nome, f"propriedade '{p['name']}' é credential sem 'credential_types'.")
        if p.get("required") is not None and not isinstance(p["required"], bool):
            raise _erro(nome, f"propriedade '{p['name']}': 'required' deve ser bool.")
        if p.get("placeholder") is not None and not isinstance(p["placeholder"], str):
            raise _erro(nome, f"propriedade '{p['name']}': 'placeholder' deve ser string.")

    saidas = desc.get("outputs")
    if saidas is not None:
        if not isinstance(saidas, list):
            raise _erro(nome, "'outputs' deve ser uma lista de campos.")
        for c in saidas:
            if not isinstance(c, dict) or not c.get("name"):
                raise _erro(nome, f"campo de saída sem 'name': {c!r}.")
            tipo = c.get("type")
            if tipo not in TIPOS_DE_CAMPO:
                raise _erro(nome, f"campo de saída '{c['name']}' com type inválido: {tipo!r}. "
                                  f"Aceitos: {sorted(TIPOS_DE_CAMPO)}.")
            estranhas = set(c) - {"name", "type", "description", "port"}
            if estranhas:
                raise _erro(nome, f"campo de saída '{c['name']}' com chaves desconhecidas "
                                  f"{sorted(estranhas)}.")

    entradas = desc.get("inputs")
    if entradas is not None:
        if not isinstance(entradas, list):
            raise _erro(nome, "'inputs' deve ser uma lista de portas.")
        for p in entradas:
            if not isinstance(p, dict) or not p.get("name"):
                raise _erro(nome, f"porta de entrada sem 'name': {p!r}.")
            tipo = p.get("type")
            if tipo is not None and tipo not in TIPOS_DE_CAMPO:
                raise _erro(nome, f"porta de entrada '{p['name']}' com type inválido: {tipo!r}. "
                                  f"Aceitos: {sorted(TIPOS_DE_CAMPO)}.")
            estranhas = set(p) - {"name", "type", "description"}
            if estranhas:
                raise _erro(nome, f"porta de entrada '{p['name']}' com chaves desconhecidas "
                                  f"{sorted(estranhas)}.")

    for flag in ("dynamic_inputs", "dynamic_output", "outputs_from_ports",
                 "branches", "requires_credential"):
        valor = desc.get(flag)
        if valor is not None and not isinstance(valor, bool):
            raise _erro(nome, f"'{flag}' deve ser bool, não {type(valor).__name__}.")
