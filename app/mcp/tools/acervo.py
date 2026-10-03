# app/mcp/tools/acervo.py
"""
Collection tools: a workflow's history, its copy, and what it produced.

This is the domain that makes it safe to let an agent edit a production
workflow. Without `restore_workflow_version`, a mistake of its own has no undo;
without `duplicate_workflow`, experimenting requires touching the original.

Three decisions shape the module:

- **None of the services here authorizes anything.** `list_versions`,
  `get_version`, `restore_version` and `duplicate_workflow` know nothing of
  role or workspace — in REST it is the router that blocks. The four
  tools that point at ONE workflow open with the pair
  `carregar_workflow(decifrar=False)` + `exigir_papel`, and it is that pair, not
  the service, that closes the door. What the service checks is something else:
  that the credentials of the saved definition (copy or restored version) are
  within reach of whoever saves (SEG-12).
  `list_artifacts` is the exception, for the same reason as `get_run_artifacts`:
  it does not point at a workflow, so there is no role to check against
  anything. The cut is `escopo.workspace_ids` inside the WHERE, which is
  already the intersection between the user's workspaces and the token's
  reach — equivalent to requiring `viewer`, which is the lowest role there is.
- **The version listing runs its own query.** `list_versions` returns the
  whole definition of each version; in a tool that would be N encrypted blobs
  read from the database only to be discarded. Here only what the question
  needs is selected — the same reason `_count_versions` exists in
  `construcao.py`.
- **No definition leaves here without going through redaction.** A version's
  definition already comes redacted from the service; the one `restore`
  returns does not — it comes back encrypted from the database, and handing it
  over raw would dump `gAAAA…` into the reader's context.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from mcp.server.mcpserver import Context
from sqlalchemy import func, select

from app.core.authorization.workflow_access import exigir_papel
from app.core.exceptions import WorkflowNotFoundError
from app.core.rbac import ROLE_EDITOR, ROLE_VIEWER
from app.core.storage import presigned_get_async
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.core.utils.redacao import compact_definition, redact_definition
from app.crud.workflow_crud import WorkflowCRUD
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow, resolve_workspace
from app.mcp.saida import envelope, sanitize, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.models.workflow_version import WorkflowVersion
from app.services.artifact_service import listar_artefatos
from app.services.workflow_service import WorkflowService
from app.services.workflow_version_service import get_version
from flow.utils.workflow_contract import validate_subworkflow_references_against_db

# Ceiling of the version listing. A heavily edited workflow accumulates hundreds
# of snapshots, and whoever asks "what changed" wants the latest ones.
MAX_VERSIONS = 50

# Ceiling of the artifact listing per response — the same context budget as the
# server's other listings.
MAX_ARTEFATOS = 100

# Validity of the signed URL, the same as the others: the link is a bearer link
# and travels through a conversation that may be recorded.
LINK_VALIDITY_S = 300

# The two slices the artifact listing understands — the same ones the REST route
# validates via `pattern`.
SLICES = ("execution", "publication")

logger = get_logger("app.mcp.tools.acervo")

_READ_ROLE_MESSAGE = "Requer papel 'viewer' ou superior neste workspace."
_WRITE_ROLE_MESSAGE = "Requer papel 'editor' ou superior neste workspace."


def _version_not_found(numero: Any):
    return erro(
        "not_found",
        f"Este workflow não tem a versão {numero}.",
        "use list_workflow_versions(workflow_id) para ver as versões que existem",
    )


# ── Versions ─────────────────────────────────────────────────────────────────


@ferramenta
async def list_workflow_versions(
    ctx: Context, workflow_id: str, limit: int = MAX_VERSIONS, offset: int = 0
) -> dict:
    """A workflow's snapshot history, from newest to oldest.

    Returns only what identifies each version — number, change note and date.
    Each one's definition comes out through
    `get_workflow_version(workflow_id, n)`, one at a time and redacted: dumping
    the content of all of them here would cost more context than any question
    about history justifies.

    A version is born when `update_workflow` changes the set of nodes, and also
    right before a `restore_workflow_version` — the auto-snapshot that makes the
    restore reversible. In other words: using the tools in this domain makes the
    history grow, and that is why `offset` exists. With `has_more: true`, the
    next page is `offset = offset + returned`; without it, the oldest versions
    of a heavily edited workflow would be unreachable through this tool.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")
    teto = max(1, min(int(limit), MAX_VERSIONS))
    salto = max(0, int(offset))

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _READ_ROLE_MESSAGE)
        id_hash = wf.id_hash

        # Its own query, not `list_versions`: that one brings the `definition`
        # column of each row — N encrypted blobs read from the database only
        # to be discarded here. The question is "which versions exist", and
        # the answer fits in three columns.
        linhas = (
            await db.execute(
                select(
                    WorkflowVersion.version_number,
                    WorkflowVersion.change_note,
                    WorkflowVersion.created_at,
                )
                .where(WorkflowVersion.workflow_hash == id_hash)
                .order_by(WorkflowVersion.version_number.desc())
                .limit(teto + 1)
                .offset(salto)
            )
        ).all()

    cortou = len(linhas) > teto
    itens = [
        {"version_number": numero, "created_at": iso(criada)}
        for numero, _, criada in linhas[:teto]
    ]
    # The change note is written by people: it goes down into
    # `untrusted_data`, in the same order as the top-level items.
    notas = [nota for _, nota, _ in linhas[:teto]]

    return envelope(
        {
            "workflow_id": id_hash,
            "items": itens,
            "returned": len(itens),
            "limit": teto,
            "offset": salto,
            "has_more": cortou,
        },
        change_notes=notas or None,
    )


@ferramenta
async def get_workflow_version(ctx: Context, workflow_id: str, version_number: int) -> dict:
    """A version from the history, with the definition REDACTED.

    Redacted without exception: the history stores the encrypted connection
    string, and opening it for the reader would hand the production database
    password to any workspace member. Restoring does not need it — restore
    copies the encrypted blob without opening it.

    The shape of the version remains whole: what is lost is the secret, not
    the nodes.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _READ_ROLE_MESSAGE)
        id_hash = wf.id_hash

        try:
            versao = await get_version(WorkflowCRUD(db), id_hash, int(version_number))
        except WorkflowNotFoundError as exc:
            # The workflow was already loaded above, so here this can only be the
            # VERSION. Without translating it, the error arrives with no hint —
            # and the next question from whoever got the number wrong is always
            # the same.
            raise _version_not_found(version_number) from exc
        except ValueError as exc:
            # A token that does not decrypt. The service reports it instead of
            # returning unreadable text as if it were content, and the tool does
            # not turn that into "not found": the data exists, what failed was
            # opening it.
            raise erro(
                "internal_error",
                "A definition desta versão não pôde ser decifrada.",
                "a chave de criptografia pode ter mudado; procure o administrador",
            ) from exc

        # The object comes DETACHED from the service (`expunge`), on purpose:
        # without that, a restore in the same session would pick up this
        # redacted instance through the identity map and write `<REDACTED>`
        # into the workflow's definition. The price is that nothing can be
        # read by lazy load — everything comes out now, from what the SELECT
        # already brought.
        numero = versao.version_number
        nota = versao.change_note
        criada = versao.created_at
        segura = compact_definition(versao.definition or {})

    return envelope(
        {
            "workflow_id": id_hash,
            "version_number": numero,
            "created_at": iso(criada),
        },
        change_note=nota,
        definition=segura,
    )


@ferramenta
async def restore_workflow_version(
    ctx: Context, workflow_id: str, version_number: int
) -> dict:
    """Returns the workflow to the state of a previous version.

    **It is reversible.** Before restoring, the current state becomes a new
    snapshot in the history, so a wrong restore is undone with another restore
    — the number of the created version comes back in `snapshot_version`.

    The schedule is resynchronized from the restored definition: if the old
    version had a different cron, the schedule becomes that one; if it had no
    schedule trigger, the schedule is removed. That sync is best-effort in the
    core — if it fails, the restore **still holds**, and the response has no
    way to warn about it. Confirm with `get_workflow(workflow_id)` when the
    workflow depends on scheduling.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _WRITE_ROLE_MESSAGE)
        id_hash = wf.id_hash

        antes = await _ultimo_numero_de_versao(db, id_hash)
        try:
            # Through the service, and not through the versions module's
            # `restore_version`: it is the service that checks the version's
            # credentials against whoever restores (SEG-12) — the same guard
            # as REST.
            restaurado = await WorkflowService(db).restore_version(
                id_hash, int(version_number), restored_by=escopo.user_id,
            )
        except WorkflowNotFoundError as exc:
            raise _version_not_found(version_number) from exc

        # `restore_version` writes the version's ENCRYPTED blob into the
        # workflow, without opening it — that is what keeps the credential
        # protected at rest. To LEAVE here, however, it has to go through
        # redaction: handing `gAAAA…` to the caller tells it nothing and
        # still costs context.
        segura = compact_definition(redact_definition(restaurado.definition or {}))
        nome = restaurado.name
        ativo = bool(restaurado.flag_ative)

        # The restore has already committed at this point. The schedule sync
        # that comes after it is best-effort and swallows its own failure —
        # but if what failed was a DATABASE statement, the transaction is left
        # aborted and this next query would raise, turning into an
        # "unexpected error" an operation that SUCCEEDED and is saved. The
        # docstring promises the opposite, so the risk belongs to the query,
        # not to the response.
        try:
            depois = await _ultimo_numero_de_versao(db, id_hash)
            indeterminado = False
        except Exception:  # noqa: BLE001 — any failure here is read-only
            logger.warning(
                "Restauração de %s gravou, mas o número do snapshot não pôde ser lido.",
                id_hash, exc_info=True,
            )
            depois, indeterminado = None, True

    dados = {
        "workflow_id": id_hash,
        "restored_from_version": int(version_number),
        # The auto-snapshot only exists if the number went up; if
        # `create_version` never got to write, saying it exists would send the
        # caller to restore a nonexistent version to undo.
        "snapshot_version": depois if depois and depois != antes else None,
        "is_active": ativo,
    }
    # Conditional insertion, and not `"hint": … if … else None`: the
    # `envelope` drops null keys only inside `untrusted_data`, so a
    # `"hint": None` at the top level would survive. `None` in the field above
    # means "there was no snapshot"; this hint is for the different case —
    # there was one, but its number could not be read —, which without it
    # would be indistinguishable from the first.
    if indeterminado:
        dados["hint"] = (
            "a restauração foi gravada, mas o número do snapshot anterior não pôde ser "
            "lido; use list_workflow_versions(workflow_id) para encontrá-lo"
        )

    return envelope(dados, name=nome, definition=segura)


async def _ultimo_numero_de_versao(db, workflow_hash: str) -> Optional[int]:
    """The workflow's highest `version_number` — as the CRUD computes it to create."""
    resultado = await db.execute(
        select(func.max(WorkflowVersion.version_number)).where(
            WorkflowVersion.workflow_hash == workflow_hash
        )
    )
    valor = resultado.scalar()
    return int(valor) if valor is not None else None


# ── Duplicar ─────────────────────────────────────────────────────────────────


@ferramenta
async def duplicate_workflow(
    ctx: Context, workflow_id: str, name: str | None = None
) -> dict:
    """Creates a copy of the workflow, in the SAME workspace.

    Used to experiment without risking the original: edit the copy, run it,
    and the production workflow stays intact.

    What does **not** come along with the copy, and not by oversight: the pins
    (they point at artifacts of runs this copy never had), the portal state (a
    copy is not born published because the original was) and the version
    history (it describes edits that did not happen here). The schedule comes
    along, but **disabled** — duplicating usually precedes an edit, and being
    born firing on its own would silently double the load.

    Without `name`, the copy gets a derived name ("Cópia de X", i.e. "Copy of
    X").
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _WRITE_ROLE_MESSAGE)
        id_hash = wf.id_hash

        # The same check the REST route does, and that the service does NOT: a
        # referenced SubWorkflow may have been deactivated or removed after the
        # original was saved. Without it, the copy is born broken and only
        # fails at run time, with an error much less clear than the list of
        # references.
        broken = await validate_subworkflow_references_against_db(
            wf.definition or {}, db, workspace_id=wf.workspace_id
        )
        if broken:
            # Explicit `sanitize`: `erro()` only redacts extras that are STRINGS
            # (`erros.py`), and this one is a list. The validator's messages
            # echo the node's `id` and the target's hash — both written by
            # whoever edits the workflow —, so without this a command sentence
            # (or a secret from a legacy definition) would go out verbatim in
            # the error body and in the SDK log. Same treatment that
            # `construcao.py` gives the `report`.
            raise erro(
                "validation",
                "O workflow referencia sub-fluxos que não estão utilizáveis.",
                "corrija as referências no original antes de duplicar",
                errors=sanitize(
                    [{"path": "definition.nodes", "message": m} for m in broken]
                ),
            )

        # Authorship comes from the caller — "who created this" is the first
        # question from whoever finds a duplicated workflow months later. The
        # stamp used to be applied here by hand because the service did not
        # do it; now it does, and the REST route stamps through the same door.
        # A single rule, on both paths.
        copia = await WorkflowService(db).duplicate_workflow(
            id_hash, name, duplicated_by=escopo.user_id,
        )
        await db.commit()

        dados = {
            "id": copia.id_hash,
            "workspace_id": copia.workspace_id,
            "copied_from": id_hash,
            "is_active": bool(copia.flag_ative),
            "created_by_id": copia.created_by_id,
        }
        copy_name = copia.name

    return envelope(dados, name=copy_name)


# ── Workspace artifacts ──────────────────────────────────────────────────────


@ferramenta
async def list_artifacts(
    ctx: Context,
    workspace_id: str | None = None,
    workflow_id: str | None = None,
    run_id: str | None = None,
    fmt: str | None = None,
    search: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """The files that a workspace's runs produced.

    Unlike `get_run_artifacts`, which answers "what did THIS run generate",
    this one answers "what exists in the collection" — with filters by
    workflow, run, format and text, and pagination.

    `kind` slices between `execution` (run output) and `publication` (layers
    published on the portal).

    Each item says whether it can be downloaded (`available`). **An unavailable
    artifact is not an error**: content that stayed on the executor and never
    went up to the cloud appears with `available: false` and the explanation,
    because it exists — what does not exist is the possibility of downloading
    it from here.

    Not every available item comes with a link. `protected: true` marks an
    artifact whose download requires a credential through the application, and
    it comes out with `available: true` and **without** a URL: the presigned URL
    is a bearer link, and signing it would bypass precisely the credential the
    application requires. What is missing there is the right, not the content —
    and each item's `hint` says which of the cases it is.

    Pin-cache artifacts are left out: they are internal engine state, not
    output that anyone asked for.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")
    teto = max(1, min(int(limit), MAX_ARTEFATOS))

    # The REST route refuses a `kind` outside the pair with 422 (`pattern=` in
    # the `Query`); here there is no Pydantic at the edge, and the core's
    # `if/elif` has no `else`: a wrong value — "publications" in the plural,
    # "Execution" capitalized — would become "no filter", returning the ENTIRE
    # collection without saying anything about the slice being ignored. Whoever
    # asked for publications would read runs as publications.
    if kind is not None and kind not in SLICES:
        raise erro(
            "validation",
            f"`kind` aceita {' ou '.join(sorted(SLICES))}, ou nada para não recortar.",
            "use kind='publication' para as camadas do portal e kind='execution' para o resto",
            errors=[{"path": "kind", "message": f"valor não reconhecido: {kind!r}"}],
        )

    async with infra.sessao() as db:
        target_workspace = (
            await resolve_workspace(db, escopo, workspace_id)
            if workspace_id is not None
            else None
        )
        target_workflow = None
        if workflow_id is not None:
            # Resolved here, and not passed raw to the core, for the same two
            # reasons as `list_runs`: so that the tool accepts the workflow's
            # NAME like all the others — which is what `docs/mcp.md` promises
            # in "Input conventions, applying to all of them" —, and so that an
            # id out of reach answers with the usual "not found", instead of
            # an empty list the caller would read as "never produced
            # anything".
            wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
            exigir_papel(papel, ROLE_VIEWER, _READ_ROLE_MESSAGE)
            target_workflow = wf.id_hash

        pagina = await listar_artefatos(
            db,
            sorted(escopo.workspace_ids),
            workspace_id=target_workspace,
            workflow_id=target_workflow,
            run_id=run_id,
            fmt=fmt,
            search=search,
            kind=kind,
            limit=teto,
            offset=max(0, int(offset)),
            include_key=True,
        )

    itens = []
    nomes = []
    expires_at = iso(utc_now_naive() + timedelta(seconds=LINK_VALIDITY_S))
    for bruto in pagina["items"]:
        local = bruto.get("content_location") or "minio"
        chave = bruto.get("s3_key")
        # Two conditions, as in `get_run_artifacts`: without `s3_key` there is
        # no object to sign, even if the location says "minio" — an old
        # artifact or an interrupted write.
        disponivel = local != "executor" and bool(chave)
        protegido = bool(bruto.get("protected"))

        item = {
            "id": bruto["id_hash"],
            "workspace_id": bruto["workspace_id"],
            "workflow_id": bruto["workflow_id"],
            "run_id": bruto["run_id"],
            "format": bruto["format"],
            "size_bytes": bruto["size_bytes"],
            "features": bruto["features"],
            "protected": protegido,
            "is_published": bruto["is_published"],
            "content_location": local,
            "created_at": bruto["created_at"],
            # `content_expires_at`, and not `expires_at`: in the sibling tool
            # `get_run_artifacts` that key is the LINK's deadline, and here it
            # would be the file's retention. Two things with different orders
            # of magnitude — minutes versus days — under the same name would
            # make a client conclude that the link lasts a week.
            "content_expires_at": bruto["expires_at"],
            "available": disponivel,
        }
        if disponivel and not protegido:
            item["download_url"] = await presigned_get_async(
                chave, expires=LINK_VALIDITY_S, filename=bruto["filename"]
            )
            item["url_expires_at"] = expires_at
        else:
            item["hint"] = _why_no_link(local, disponivel, protegido)

        itens.append(item)
        # Human text, in the same order as the items. `output_key` goes in
        # here together with the other two: it is the label the person wrote
        # on the output node, not a value the platform generates — and at the
        # top level it would escape the `envelope`'s `sanitize`. That is
        # what `get_run_artifacts` already does.
        nomes.append({
            "filename": bruto["filename"],
            "workflow_name": bruto["workflow_name"],
            "output_key": bruto["output_key"],
        })

    return envelope(
        {
            "items": itens,
            "total": pagina["total"],
            "limit": pagina["limit"],
            "offset": pagina["offset"],
            "has_more": pagina["has_more"],
            "expires_in_seconds": LINK_VALIDITY_S,
        },
        names=nomes or None,
    )


def _why_no_link(local: str, disponivel: bool, protegido: bool) -> str:
    """ONE explanation, cascading — the most specific one that fits."""
    if local == "executor":
        return (
            "o conteúdo deste artefato permanece no executor e nunca foi enviado para a "
            "nuvem: não há download pela plataforma"
        )
    if not disponivel:
        return "este artefato não tem conteúdo no storage"
    return "este artefato exige credencial para download; baixe pela aplicação"


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="list_workflow_versions",
        title="Histórico de versões",
        description=(
            "Snapshots de um workflow, do mais novo para o mais antigo: número, nota da "
            "mudança e data. A definition de cada versão sai por get_workflow_version, uma "
            "por vez e redigida."
        ),
        annotations=anotacoes("list_workflow_versions"),
    )(list_workflow_versions)

    server.tool(
        name="get_workflow_version",
        title="Uma versão do histórico",
        description=(
            "A definition de uma versão anterior, sempre REDIGIDA: o histórico guarda "
            "credencial cifrada, e abri-la entregaria a senha do banco a qualquer membro. "
            "Restaurar não precisa disso — o restore copia o blob sem abri-lo."
        ),
        annotations=anotacoes("get_workflow_version"),
    )(get_workflow_version)

    server.tool(
        name="restore_workflow_version",
        title="Restaurar uma versão",
        description=(
            "Devolve o workflow ao estado de uma versão anterior. É REVERSÍVEL: o estado "
            "atual vira um snapshot novo antes da troca, e o número dele volta na resposta. "
            "O agendamento é ressincronizado pela definition restaurada, best-effort."
        ),
        annotations=anotacoes("restore_workflow_version"),
    )(restore_workflow_version)

    server.tool(
        name="duplicate_workflow",
        title="Duplicar workflow",
        description=(
            "Cria uma cópia no MESMO workspace, para experimentar sem arriscar o original. "
            "Pins, estado do portal e histórico de versões NÃO acompanham; o agendamento "
            "acompanha desligado. Sub-fluxo quebrado é recusado antes de copiar."
        ),
        annotations=anotacoes("duplicate_workflow"),
    )(duplicate_workflow)

    server.tool(
        name="list_artifacts",
        title="Artefatos do workspace",
        description=(
            "Os arquivos que as execuções produziram, com filtro por fluxo, execução, "
            "formato e texto. Diferente de get_run_artifacts, que olha uma execução só. "
            "Artefato que ficou no executor aparece com available:false e explicação, não "
            "como erro. URL de download vale 5 minutos."
        ),
        annotations=anotacoes("list_artifacts"),
    )(list_artifacts)
