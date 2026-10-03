# app/mcp/tools/drive_escrita.py
"""
Writing to the Drive: putting a file, completing the upload and deleting.

Closes `drive:write`, the last of the six scopes that the tokens screen offers
with an affirmative description. With it, Phase 2 stops promising what it does
not deliver.

## The upload is THREE calls, and that is design, not red tape

```
create_drive_upload_url  →  PUT straight to storage  →  confirm_drive_upload
      (the tool)              (whoever has the bytes)        (the tool)
```

The middle step **does not go through here**, and that is the reason the flow
exists: MCP is JSON-RPC, and sending a file through it would mean carrying it
whole in base64 inside a message — a 40 MB shapefile would become 54 MB of text
in the caller's context, costing more than any analysis it was meant to feed.
The presigned URL puts the bytes on the short path.

The practical consequence, and the tool says so: **an agent that does not have
the file on disk cannot use these tools.** It can ask for the URL and hand it
to whoever has the file, but it cannot invent the content. Pretending otherwise
would make the agent promise an upload that never happened.

## Two things the Drive does NOT have

**It is flat.** There is no rename, no move, no create folder — neither in
REST nor in the model. A file has a name and a workspace, and that is all. It is
written here because the alternative is the agent finding out by trying, and
spending a round on it.

**Overwriting is not an operation.** Uploading the same name creates another
record. Whoever wants to replace deletes and uploads again — and the delete
tool says so.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from mcp.server.mcpserver import Context

from app.core.authorization.workflow_access import (
    exigir_papel, get_workspace_member_role,
)
# The app's `FileNotFoundError` SHADOWS the builtin and does not inherit from it
# — it extends `FileError`/`AtlasBaseError`. An `except FileNotFoundError`
# without this import catches the builtin and does NOT match, letting the
# exception go up to `@ferramenta`, which maps it by `status_code` and returns
# the service's message instead of the tool's hint. The alias makes the
# difference visible instead of depending on whoever remembers.
from app.core.exceptions import FileNotFoundError as AppFileNotFoundError
from app.core.rbac import ROLE_EDITOR
from app.core.storage import _PRESIGN_EXPIRY
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import resolve_workspace
from app.mcp.saida import envelope, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.core.exceptions import FileValidationError
from app.services.drive_service import (
    ContentOnExecutorError, DriveService, FileTooLargeError,
)

logger = get_logger("app.mcp.tools.drive_escrita")

# Validity of the upload URL: READ from the storage, not chosen here.
#
# `DriveService.create_upload_url` signs with the module's default
# (`presigned_put_async` without `expires`), which is `MINIO_PRESIGN_EXPIRY` —
# one hour, configurable per environment. Announcing a different number would be
# lying about a deadline the client uses to decide whether there is still time
# to upload a large file, and the error would show up as "the URL expired
# earlier than you said" in the middle of a twenty-minute upload.
#
# It is the same care as with the download URLs, with one difference that
# explains why it is longer here: there the clock runs until a click, here it
# runs during the ENTIRE TRANSFER.
UPLOAD_VALIDITY_S = _PRESIGN_EXPIRY

_ROLE_MESSAGE = "Requer papel 'editor' ou superior neste workspace."


async def _exigir_editor(db, escopo, workspace_id: str) -> None:
    """The pair the REST route applies with `require_workspace_role(..., ROLE_EDITOR)`.

    The Drive is per WORKSPACE, not per workflow, so there is no
    `carregar_workflow` to return the role along with it: it is fetched here.
    `resolve_workspace` has already guaranteed the workspace is within the
    token's reach; what is missing is the caller's role INSIDE it.
    """
    papel = await get_workspace_member_role(db, workspace_id, escopo.user_id)
    exigir_papel(papel, ROLE_EDITOR, _ROLE_MESSAGE)


def _file_error(exc: Exception):
    """`FileValidationError` covers a forbidden extension, a double extension and a
    name without an extension — all with the cause already in the message."""
    return erro(
        "validation",
        str(exc),
        "use list_drive_files para ver extensões que já entraram neste workspace; "
        "a lista permitida é configurada pelo administrador",
    )


# ── 1. Pedir a URL ───────────────────────────────────────────────────────────


@ferramenta
async def create_drive_upload_url(
    ctx: Context, filename: str, size_bytes: int, workspace_id: Optional[str] = None
) -> dict:
    """First of the three steps of an upload: requests the URL to send the bytes.

    Returns `upload_url`, which accepts a **PUT** with the file's content, and
    `file_id`, which identifies the record from here on.

    **This tool does not send the file.** It does not see the bytes and cannot
    invent them: the PUT is made by whoever has the file on disk. If you do not
    have it, hand the URL to whoever does — and do not announce that the upload
    happened.

    After the PUT, call `confirm_drive_upload(file_id)`. Without that third
    call the file **does not appear in the Drive**: a pending record remains,
    which the cleanup deletes later, and the uploaded bytes go with it.

    `size_bytes` is checked here against the workspace's ceiling, and **again
    on confirm** against the real object — declaring a small number and
    uploading a large file is refused at the end, with the object deleted.

    The extension has to be on the list the administrator allows, and a name
    with a dangerous inner extension (`relatorio.exe.csv`) is refused.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:write")

    try:
        tamanho = int(size_bytes)
    except (TypeError, ValueError):
        raise erro("validation", "size_bytes precisa ser um número inteiro de bytes.")
    if tamanho <= 0:
        raise erro(
            "validation",
            "size_bytes precisa ser maior que zero.",
            "é o tamanho do arquivo que você vai enviar, em bytes",
        )

    async with infra.sessao() as db:
        ws = await resolve_workspace(db, escopo, workspace_id)
        await _exigir_editor(db, escopo, ws)

        try:
            criado = await DriveService(db).create_upload_url(
                ws, str(filename), tamanho, uploaded_by=escopo.user_id,
            )
        except FileTooLargeError as exc:
            raise erro(
                "validation", str(exc),
                "o teto é do workspace e o administrador o configura",
            )
        except FileValidationError as exc:
            raise _file_error(exc)

    return envelope(
        {
            "file_id": criado["id_hash"],
            "workspace_id": ws,
            "upload_url": criado["upload_url"],
            "method": "PUT",
            "expires_in_seconds": UPLOAD_VALIDITY_S,
            "expires_at": iso(utc_now_naive() + timedelta(seconds=UPLOAD_VALIDITY_S)),
            "hint": (
                "faça PUT do conteúdo nesta URL e depois chame "
                "confirm_drive_upload(file_id) — sem o confirm o arquivo não "
                "entra no Drive"
            ),
        },
        filename=str(filename),
    )


# ── 3. Confirmar ─────────────────────────────────────────────────────────────


@ferramenta
async def confirm_drive_upload(ctx: Context, file_id: str) -> dict:
    """Third step: completes the upload and makes the file appear in the Drive.

    Until this call the record is pending and invisible in the listing. Here
    the server **measures the real object** in the storage and saves the real
    size — not the one declared in step 1.

    If the real file is above the workspace's ceiling, the confirmation is
    refused **and the bytes are deleted**: accepting an object above the limit
    because it is already there would just be a slower way of having no limit.

    `not_found` here almost always means the PUT never happened, or that the
    step 1 URL expired before the upload finished. In that case, ask for
    another URL and redo the upload.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:write")

    async with infra.sessao() as db:
        servico = DriveService(db)
        try:
            arquivo = await servico.get_file(str(file_id))
        except AppFileNotFoundError as exc:
            raise erro(
                "not_found",
                "Nenhum arquivo do Drive com este identificador.",
                "o file_id é o que create_drive_upload_url devolveu",
            ) from exc

        # Resolve BY the file's workspace, and not by a parameter: a
        # `workspace_id` coming from the caller here would only serve to let
        # it point at a workspace of its own and confirm someone else's file.
        await resolve_workspace(db, escopo, arquivo.workspace_id)
        await _exigir_editor(db, escopo, arquivo.workspace_id)

        try:
            confirmado = await servico.confirm_upload(str(file_id))
        except FileTooLargeError as exc:
            raise erro(
                "validation",
                f"{exc} O objeto enviado foi apagado.",
                "confira o tamanho real do arquivo e peça uma URL nova",
            )
        except AppFileNotFoundError as exc:
            raise erro(
                "not_found",
                "O conteúdo não chegou ao storage: o envio não aconteceu ou não terminou.",
                "refaça o PUT na upload_url, ou peça outra com "
                "create_drive_upload_url se a anterior expirou",
            ) from exc

        dados = {
            "file_id": confirmado.id_hash,
            "workspace_id": confirmado.workspace_id,
            "extension": confirmado.extension,
            "mime_type": confirmado.mime_type,
            # The MEASURED size, which may differ from the one declared in step 1.
            "size": confirmado.size,
            "status": confirmado.status,
        }
        nome = confirmado.original_name

    return envelope(dados, filename=nome)


# ── Apagar ───────────────────────────────────────────────────────────────────


@ferramenta
async def delete_drive_file(ctx: Context, file_id: str, confirm: bool = False) -> dict:
    """Deletes a file from the Drive, for good. Requires `confirm=true`.

    There is no trash: the record and the bytes disappear together and do not
    come back. And the damage does not stop at the file — a workflow that reads
    it starts failing on its next run, with nothing linking one thing to the
    other for whoever investigates.

    Without `confirm=true` nothing is deleted: the response describes the file,
    for you to show to whoever asked before repeating the call.

    **This is also how a file is replaced**, because overwriting is not a Drive
    operation: delete and upload again with the same name.

    A file whose content lives on the executor (`content_location: "executor"`)
    is refused. The platform keeps the record, never the bytes — deleting the
    record would remove nothing from the disk of whoever has the file, and
    telling the executor to delete it would be destroying data that never
    belonged to the platform.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:write")

    async with infra.sessao() as db:
        servico = DriveService(db)
        try:
            arquivo = await servico.get_file(str(file_id))
        except AppFileNotFoundError as exc:
            raise erro(
                "not_found",
                "Nenhum arquivo do Drive com este identificador.",
                "use list_drive_files para ver os arquivos do workspace",
            ) from exc

        await resolve_workspace(db, escopo, arquivo.workspace_id)
        await _exigir_editor(db, escopo, arquivo.workspace_id)

        descricao = {
            "file_id": arquivo.id_hash,
            "workspace_id": arquivo.workspace_id,
            "extension": arquivo.extension,
            "size": arquivo.size,
            "content_location": arquivo.content_location or "minio",
        }
        nome = arquivo.original_name

        if not confirm:
            return envelope(
                {
                    **descricao,
                    "outcome": "not_confirmed",
                    "hint": (
                        "nada foi apagado. Repita com confirm=true para apagar — "
                        "não há lixeira, e um fluxo que leia este arquivo passa a "
                        "falhar na próxima execução"
                    ),
                },
                filename=nome,
            )

        try:
            await servico.delete_file(arquivo)
        except ContentOnExecutorError as exc:
            raise erro(
                "unavailable_local", str(exc),
                "quem quer que o arquivo suma apaga o arquivo na máquina do "
                "executor, ou tira a pasta do GeoSync",
            )
        except Exception as exc:  # noqa: BLE001 — the storage failure is part of the path
            # `delete_file` refuses to delete the row if the storage fails, on
            # purpose: that way reconciliation retries and the object does not
            # become an orphan. What must not happen is this going up as an
            # unexpected error.
            logger.error("delete_drive_file: storage falhou para %s (%s).", file_id, exc)
            raise erro(
                "unavailable",
                "O arquivo não pôde ser apagado do armazenamento; nada foi removido.",
                "tente de novo em instantes — o registro foi preservado de propósito",
            )

    return envelope({**descricao, "outcome": "deleted"}, filename=nome)


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="create_drive_upload_url",
        title="Pedir URL de envio",
        description=(
            "Primeiro de três passos: devolve uma URL que aceita PUT com o conteúdo. Esta "
            "tool NÃO envia o arquivo — quem faz o PUT é quem tem os bytes em disco. Depois "
            "do PUT, chame confirm_drive_upload, senão o arquivo não entra no Drive."
        ),
        annotations=anotacoes("create_drive_upload_url"),
    )(create_drive_upload_url)

    server.tool(
        name="confirm_drive_upload",
        title="Concluir o envio",
        description=(
            "Terceiro passo: mede o objeto real no storage e faz o arquivo aparecer no "
            "Drive. Acima do teto do workspace, recusa e apaga os bytes. not_found aqui "
            "quase sempre quer dizer que o PUT não aconteceu."
        ),
        annotations=anotacoes("confirm_drive_upload"),
    )(confirm_drive_upload)

    server.tool(
        name="delete_drive_file",
        title="Apagar arquivo do Drive",
        description=(
            "Apaga de vez; exige confirm=true. Não há lixeira, e um fluxo que leia o "
            "arquivo passa a falhar. É também como se substitui um arquivo, porque "
            "sobrescrever não existe no Drive."
        ),
        annotations=anotacoes("delete_drive_file"),
    )(delete_drive_file)
