# app/services/nos_renomeados.py
"""Reescreve as definições salvas que ainda usam nomes antigos de nós.

A renomeação de 27/07 (`DriveTrigger` → `DataInput`, `ArtifactOutput` →
`DataOutput`, commit ff11c196) foi feita "sem shim" e não migrou os fluxos
salvos. Em 25/09 dois estavam quebrados: o TESTE_BPA, agendado, falhando todo
dia na partida com "Node 'DriveTrigger' não encontrado", e o Geoserver.

Não é uma revisão do Alembic de propósito: a F3 fixou uma revisão única (ver
tests/unit/test_base_zero.py) e reabrir a cadeia é decisão do dono. É um
comando idempotente do CLI — simula por padrão, grava com `--aplicar`:

    docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos
    docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos --aplicar

O mapa de nomes mora em `flow.nodes.contrato.NOMES_ANTIGOS`, junto das
mensagens que o citam.
"""
from __future__ import annotations

import copy
import re

from flow.core.aliases import resolve_alias
from flow.nodes.contrato import NOMES_ANTIGOS

# Saídas que mudaram de nome junto com o nó. Só o `DataInput` mudou uma: o
# `drive_file_id` do metadata do `DriveTrigger` virou `file_id`. O `DataOutput`
# manteve as quatro saídas do `ArtifactOutput`.
_SAIDAS_RENOMEADAS = {"DriveTrigger": {"drive_file_id": "file_id"}}


def _propriedades_novas(antigo: str, props: dict) -> dict:
    """O que muda nas propriedades além do nome.

    `ArtifactOutput` era público quando NÃO tinha credencial e protegido quando
    tinha. No `DataOutput` o padrão é `isPublic=True` e a credencial só vale com
    `isPublic=False` — renomear sem gravar isso tornaria PÚBLICO o download de
    um artefato que era protegido. `destination` virou `context` (mesmos
    valores). `DriveTrigger` lia do Drive: `context='drive'` explícito, para não
    depender do default do `DataInput`.
    """
    props = dict(props)
    if antigo == "ArtifactOutput":
        if "destination" in props:
            destino = props.pop("destination")
            props.setdefault("context", destino)
        if props.get("credential_id"):
            props["isPublic"] = False
    elif antigo == "DriveTrigger":
        props.setdefault("context", "drive")
    return props


def _padrao_de_saida(alias: str, antiga: str) -> re.Pattern:
    """`Alias.metadata.<antiga>` numa expressão, nas formas que o Jinja aceita:
    `$Alias...`/`{{ Alias... }}`, com `.metadata` ou `['metadata']`, e a chave
    como atributo, `['<antiga>']` ou `.get('<antiga>')`. O lookbehind impede
    casar o alias como sufixo de outro nome (`MeuDriveTrigger`) ou como
    atributo (`x.DriveTrigger`). O que escapa daqui (via `named.`, `nodes[...]`,
    entrada mapeada, código Python) sai em `sobras_para_revisar`."""
    a, k = re.escape(alias), re.escape(antiga)
    return re.compile(
        rf"(?<![\w.])(?P<base>\$?{a}(?:\.metadata|\[(?P<q1>['\"])metadata(?P=q1)\]))"
        rf"(?:\.{k}\b|\[(?P<q2>['\"]){k}(?P=q2)\]|(?P<get>\.get\(\s*)(?P<q3>['\"]){k}(?P=q3))"
    )


def _trocar_chave(m: re.Match, nova: str) -> str:
    base = m.group("base")
    if m.group("q2"):
        return f"{base}[{m.group('q2')}{nova}{m.group('q2')}]"
    if m.group("get"):
        return f"{base}{m.group('get')}{m.group('q3')}{nova}{m.group('q3')}"
    return f"{base}.{nova}"


def _reescrever_saidas(valor, padroes: list[tuple[re.Pattern, str, str]]):
    """Aplica as trocas de saída em toda string de `valor` (dicts e listas
    inclusive). Devolve (novo valor, {(antiga, nova) aplicadas})."""
    if isinstance(valor, str):
        feitas = set()
        for padrao, antiga, nova in padroes:
            valor, n = padrao.subn(lambda m, nova=nova: _trocar_chave(m, nova), valor)
            if n:
                feitas.add((antiga, nova))
        return valor, feitas
    if isinstance(valor, (dict, list)):
        feitas = set()
        itens = valor.items() if isinstance(valor, dict) else enumerate(valor)
        novo = {} if isinstance(valor, dict) else [None] * len(valor)
        for chave, item in itens:
            novo[chave], f = _reescrever_saidas(item, padroes)
            feitas |= f
        return novo, feitas
    return valor, set()


def migrar_definicao(definicao) -> tuple[object, list[tuple[str, str, str]]]:
    """Devolve (definição reescrita, trocas [(node_id, antigo, novo)]).

    Sem troca, devolve o MESMO objeto (quem chama não regrava nada). O nome pode
    estar no topo do nó (o formato salvo pelo editor) ou em `data.name`.

    Os OUTROS nós citam este pelo alias (`$DriveTrigger.metadata.original_name`).
    Sem alias customizado válido — o caso comum: o editor grava o rótulo do
    catálogo, "Drive de arquivos", que tem espaço — o alias é o próprio `name`,
    e trocar o nome quebraria essas expressões: `{{ }}` com "undefined" e o
    `$Alias` pior, seguindo como TEXTO até o nó. Por isso o nome antigo fica
    fixado como alias (o título do nó no editor passa a mostrá-lo). E a saída
    que mudou de nome (`metadata.drive_file_id` → `metadata.file_id`) é
    reescrita nas expressões que apontam para o nó migrado.
    """
    if not isinstance(definicao, dict) or not isinstance(definicao.get("nodes"), list):
        return definicao, []
    trocas: list[tuple[str, str, str]] = []
    padroes: list[tuple[re.Pattern, str, str]] = []
    nova = copy.deepcopy(definicao)

    def _niveis(no):
        dados = no.get("data")
        return [no] + ([dados] if isinstance(dados, dict) else [])

    for no in nova["nodes"]:
        if not isinstance(no, dict):
            continue
        antigo = next((n["name"] for n in _niveis(no) if n.get("name") in NOMES_ANTIGOS), None)
        if antigo is None:
            continue
        novo = NOMES_ANTIGOS[antigo]
        for nivel in _niveis(no):
            if nivel.get("name") == antigo:
                alias = resolve_alias(nivel)
                if alias == antigo:
                    nivel["alias"] = antigo
                for antiga, nova_saida in _SAIDAS_RENOMEADAS.get(antigo, {}).items():
                    padroes.append((_padrao_de_saida(alias, antiga), antiga, nova_saida))
                nivel["name"] = novo
            if isinstance(nivel.get("properties"), dict):
                nivel["properties"] = _propriedades_novas(antigo, nivel["properties"])
        trocas.append((str(no.get("id")), antigo, novo))
    if not trocas:
        return definicao, []
    for no in nova["nodes"] if padroes else ():
        if not isinstance(no, dict):
            continue
        for nivel in _niveis(no):
            if not isinstance(nivel.get("properties"), dict):
                continue
            nivel["properties"], feitas = _reescrever_saidas(nivel["properties"], padroes)
            for antiga, nova_saida in sorted(feitas):
                trocas.append((str(no.get("id")), f"metadata.{antiga}", f"metadata.{nova_saida}"))
    return nova, trocas


def _textos(valor):
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for item in valor.values():
            yield from _textos(item)
    elif isinstance(valor, list):
        for item in valor:
            yield from _textos(item)


def sobras_para_revisar(definicao) -> list[str]:
    """Ids dos nós que ainda citam uma saída renomeada depois da migração —
    formas que a reescrita não alcança com segurança (`named.X`, `nodes['id']`,
    entrada mapeada, código Python). Quem roda o comando revisa à mão."""
    if not isinstance(definicao, dict) or not isinstance(definicao.get("nodes"), list):
        return []
    antigas = {antiga for saidas in _SAIDAS_RENOMEADAS.values() for antiga in saidas}
    ids = []
    for no in definicao["nodes"]:
        if not isinstance(no, dict):
            continue
        niveis = [no] + ([no["data"]] if isinstance(no.get("data"), dict) else [])
        if any(
            antiga in texto
            for nivel in niveis for texto in _textos(nivel.get("properties"))
            for antiga in antigas
        ):
            ids.append(str(no.get("id")))
    return ids


async def migrar_nos(db, *, aplicar: bool) -> list[dict]:
    """Varre workflows e versões salvas. Devolve uma linha por definição que
    muda (ou mudaria, sem `aplicar`).

    As versões entram porque restaurar uma versão antiga traria o nome antigo
    de volta — e o fluxo quebraria de novo, sem ninguém entender por quê.
    """
    from sqlalchemy import String, cast, or_, select

    from app.models.workflow import Workflow
    from app.models.workflow_version import WorkflowVersion

    relatorio: list[dict] = []
    for modelo, rotulo in ((Workflow, "workflow"), (WorkflowVersion, "versao")):
        # Filtro barato no banco (texto do JSON); a decisão fina é do Python.
        texto = cast(modelo.definition, String)
        filtro = or_(*[texto.like(f'%"{nome}"%') for nome in NOMES_ANTIGOS])
        linhas = (await db.execute(select(modelo).where(filtro))).scalars().all()
        for linha in linhas:
            nova, trocas = migrar_definicao(linha.definition)
            if not trocas:
                continue
            relatorio.append({
                "tipo": rotulo,
                "workflow": getattr(linha, "workflow_hash", None) or linha.id_hash,
                "nome": getattr(linha, "name", None),
                "versao": getattr(linha, "version_number", None),
                "trocas": trocas,
                "revisar": sobras_para_revisar(nova),
            })
            if aplicar:
                linha.definition = nova
    if aplicar and relatorio:
        await db.commit()
    return relatorio


async def nomes_antigos_desabilitados(db) -> list[str]:
    """Nomes antigos que o admin deixou desabilitados.

    O mapa `disabled_nodes` é por nome, e este comando NÃO transfere a marca
    para o nó novo: desabilitar o `DataOutput` hoje pararia também os fluxos que
    o usam desde 27/07. Quem decide é o admin — o comando só avisa que, depois
    da migração, os fluxos com o nó antigo voltam a rodar.
    """
    from app.services.disabled_nodes_service import list_disabled

    desabilitados = await list_disabled(db)
    return sorted(nome for nome in NOMES_ANTIGOS if nome in desabilitados)
