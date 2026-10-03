# app/mcp/tools/drive.py
"""Drive tools. The guards for each one are in app/mcp/guardas.py."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from app.core.authorization.workflow_access import verify_workspace_access
# See the note in `drive_escrita.py`: this is NOT the builtin and does not
# inherit from it.
from app.core.exceptions import FileNotFoundError as AppFileNotFoundError
from app.core.storage import presigned_get_async
from app.core.utils.datetime_utils import utc_now_naive
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import resolve_workspace
from app.mcp.saida import envelope, sanitize, iso
from app.mcp.tools.base import ferramenta
from app.services.drive_service import DriveService

# Validity of the signed URL. The storage module's default is one hour, meant
# for the browser of someone who is logged in; here the link travels through a
# conversation and may be recorded in a client log, so it lasts the minimum
# needed to download the file.
LINK_VALIDITY_S = 300

# Ceiling of files per page — the same context-budget reason as the other
# listings.
MAX_PAGE_SIZE = 100

# How many columns of the spatial metadata go out per file. A 300-column table
# would describe the file better than the entire rest of the response.
MAX_COLUMNS = 50


def _spatial_summary(bruto: Any) -> dict | None:
    """CRS, extent, count and the first columns — never the whole list."""
    if not isinstance(bruto, Mapping):
        return None
    colunas = bruto.get("columns")
    resumo: dict[str, Any] = {
        "crs": bruto.get("crs"),
        "bbox": bruto.get("bbox"),
        "feature_count": bruto.get("feature_count"),
        "geometry_type": bruto.get("geometry_type"),
    }
    if isinstance(colunas, list):
        # A column name is written by whoever produced the file: it goes through
        # the sanitizer like any other text of human origin.
        resumo["columns"] = sanitize(colunas[:MAX_COLUMNS])
        resumo["columns_total"] = len(colunas)
    return {chave: valor for chave, valor in resumo.items() if valor is not None}


@ferramenta
async def list_drive_files(
    ctx: Context,
    workspace_id: str | None = None,
    search: str | None = None,
    ext: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Lists the files in a workspace's Drive.

    It is where the identifier that a data input node consumes comes from. The
    spatial metadata comes summarized: CRS, extent, feature count and the first
    columns.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:read")

    pagina = max(1, int(page))
    tamanho = max(1, min(int(page_size), MAX_PAGE_SIZE))

    async with infra.sessao() as db:
        ws = await resolve_workspace(db, escopo, workspace_id)
        arquivos, total = await DriveService(db).list_files(
            ws, search=search, ext=ext, page=pagina, page_size=tamanho
        )
        brutos = [
            {
                "id": a.id_hash,
                "extension": a.extension,
                "mime_type": a.mime_type,
                "size": a.size,
                "content_location": a.content_location or "minio",
                "spatial_metadata": _spatial_summary(a.spatial_metadata),
                "updated_at": iso(a.content_written_at or a.updated_at or a.created_at),
                "original_name": a.original_name,
            }
            for a in arquivos
        ]

    itens = [
        envelope(
            {chave: valor for chave, valor in bruto.items() if chave != "original_name"},
            original_name=bruto["original_name"],
        )
        for bruto in brutos
    ]
    return {
        "items": itens,
        "total": total,
        "workspace_id": ws,
        "page": pagina,
        "page_size": tamanho,
    }


@ferramenta
async def get_drive_download_url(ctx: Context, file_id: str) -> dict:
    """A temporary download URL for a Drive file.

    The URL is a BEARER URL and is valid for five minutes: whoever has the link
    downloads the file, with no authentication. Use it and discard it.

    A file whose content lives on the executor comes back with
    `available=false` instead of an error: there is nothing to download through
    the platform (the bytes were never uploaded), but the file exists and is
    still usable by workflows that run on that executor — the client needs to
    know the difference between "does not exist" and "cannot be downloaded
    from here".
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:read")

    async with infra.sessao() as db:
        try:
            arquivo = await DriveService(db).get_file(str(file_id))
        except AppFileNotFoundError as exc:
            raise erro(
                "not_found",
                "Nenhum arquivo do Drive com este identificador.",
                "use list_drive_files para ver os arquivos do workspace",
            ) from exc
        # 403 when the file belongs to another workspace: the id lookup has
        # already happened, and what is protected here is the content, not the
        # existence.
        verify_workspace_access(arquivo.workspace_id, list(escopo.workspace_ids))
        local = arquivo.content_location or "minio"
        chave = arquivo.s3_key
        nome = arquivo.original_name
        dados = {
            "id": arquivo.id_hash,
            "workspace_id": arquivo.workspace_id,
            "content_location": local,
            "size": arquivo.size,
        }

    if local == "executor" or not chave:
        return envelope(
            {
                **dados,
                "available": False,
                "download_url": None,
                "expires_at": None,
                "hint": (
                    "O conteúdo deste arquivo permanece no executor e nunca foi enviado "
                    "para a nuvem: não há download pela plataforma. Fluxos que rodem "
                    "naquele executor continuam lendo o arquivo normalmente."
                ),
            },
            filename=nome,
        )

    url = await presigned_get_async(chave, expires=LINK_VALIDITY_S, filename=nome)
    return envelope(
        {
            **dados,
            "available": True,
            "download_url": url,
            "expires_in_seconds": LINK_VALIDITY_S,
            "expires_at": iso(utc_now_naive() + timedelta(seconds=LINK_VALIDITY_S)),
        },
        filename=nome,
    )


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="list_drive_files",
        title="Listar arquivos do Drive",
        description=(
            "Lista os arquivos do Drive de um workspace, com extensão, tamanho, onde o "
            "conteúdo está e um resumo do metadado espacial (CRS, extensão, feições, "
            "colunas). O `id` devolvido é o que os nós de entrada de dados consomem."
        ),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )(list_drive_files)

    server.tool(
        name="get_drive_download_url",
        title="Link de download do Drive",
        description=(
            "Gera uma URL temporária (5 minutos) para baixar um arquivo do Drive. A URL "
            "é portadora: quem tiver o link baixa o arquivo. Arquivos cujo conteúdo mora "
            "no executor voltam com `available=false`."
        ),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            # Each call signs a new URL, with its own validity.
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )(get_drive_download_url)
