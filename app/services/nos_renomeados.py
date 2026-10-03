# app/services/nos_renomeados.py
"""Rewrites saved definitions that still use old node names.

The 07-27 rename (`DriveTrigger` → `DataInput`, `ArtifactOutput` →
`DataOutput`, commit ff11c196) was done "without a shim" and did not migrate the saved
workflows. On 09-25 two were broken: TESTE_BPA, scheduled, failing every
day at startup with "Node 'DriveTrigger' não encontrado" (not found), and Geoserver.

It is deliberately not an Alembic revision: F3 pinned a single revision (see
tests/unit/test_base_zero.py) and reopening the chain is the owner's decision. It is an
idempotent CLI command — dry run by default, writes with `--aplicar`:

    docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos
    docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos --aplicar

The name map lives in `flow.nodes.contrato.NOMES_ANTIGOS`, next to the
messages that cite it.
"""
from __future__ import annotations

import copy
import re

from flow.core.aliases import resolve_alias
from flow.nodes.contrato import NOMES_ANTIGOS

# Outputs that were renamed along with the node. Only `DataInput` changed one:
# `DriveTrigger`'s metadata `drive_file_id` became `file_id`. `DataOutput`
# kept the four outputs of `ArtifactOutput`.
_SAIDAS_RENOMEADAS = {"DriveTrigger": {"drive_file_id": "file_id"}}


def _propriedades_novas(antigo: str, props: dict) -> dict:
    """What changes in the properties besides the name.

    `ArtifactOutput` was public when it had NO credential and protected when
    it had one. In `DataOutput` the default is `isPublic=True` and the credential only
    applies with `isPublic=False` — renaming without writing that would make the download
    of an artifact that was protected PUBLIC. `destination` became `context` (same
    values). `DriveTrigger` read from Drive: explicit `context='drive'`, so as not to
    depend on `DataInput`'s default.
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
    """`Alias.metadata.<antiga>` in an expression, in the forms Jinja accepts:
    `$Alias...`/`{{ Alias... }}`, with `.metadata` or `['metadata']`, and the key
    as an attribute, `['<antiga>']` or `.get('<antiga>')`. The lookbehind prevents
    matching the alias as a suffix of another name (`MeuDriveTrigger`) or as an
    attribute (`x.DriveTrigger`). What escapes this (via `named.`, `nodes[...]`,
    mapped input, Python code) comes out in `sobras_para_revisar`."""
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
    """Applies the output renames to every string in `valor` (dicts and lists
    included). Returns (new value, {(old, new) applied})."""
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
    """Returns (rewritten definition, changes [(node_id, old, new)]).

    With no change, returns the SAME object (the caller rewrites nothing). The name can
    be at the top of the node (the format the editor saves) or in `data.name`.

    The OTHER nodes cite this one by alias (`$DriveTrigger.metadata.original_name`).
    Without a valid custom alias — the common case: the editor saves the catalog
    label, "Drive de arquivos", which has a space — the alias is the `name` itself,
    and changing the name would break those expressions: `{{ }}` with "undefined" and
    `$Alias` worse, passing through as TEXT to the node. That is why the old name is
    pinned as the alias (the node's title in the editor starts showing it). And the output
    that was renamed (`metadata.drive_file_id` → `metadata.file_id`) is
    rewritten in the expressions that point to the migrated node.
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
    """Ids of the nodes that still cite a renamed output after the migration —
    forms the rewrite cannot reach safely (`named.X`, `nodes['id']`,
    mapped input, Python code). Whoever runs the command reviews them by hand."""
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
    """Scans workflows and saved versions. Returns one line per definition that
    changes (or would change, without `aplicar`).

    Versions are included because restoring an old version would bring the old name
    back — and the workflow would break again, with nobody understanding why.
    """
    from sqlalchemy import String, cast, or_, select

    from app.models.workflow import Workflow
    from app.models.workflow_version import WorkflowVersion

    relatorio: list[dict] = []
    for modelo, rotulo in ((Workflow, "workflow"), (WorkflowVersion, "versao")):
        # Cheap filter in the database (JSON text); the fine decision is Python's.
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
    """Old names the admin left disabled.

    The `disabled_nodes` map is by name, and this command does NOT transfer the mark
    to the new node: disabling `DataOutput` today would also stop the workflows that
    have used it since 07-27. The admin decides — the command only warns that, after
    the migration, the workflows with the old node run again.
    """
    from app.services.disabled_nodes_service import list_disabled

    desabilitados = await list_disabled(db)
    return sorted(nome for nome in NOMES_ANTIGOS if nome in desabilitados)
