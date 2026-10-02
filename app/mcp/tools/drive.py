# app/mcp/tools/drive.py
"""Tools de drive. As guardas de cada uma estão em app/mcp/guardas.py."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from app.core.authorization.workflow_access import verify_workspace_access
# Ver a nota em `drive_escrita.py`: esta NAO e a builtin e nao herda dela.
from app.core.exceptions import FileNotFoundError as ArquivoNaoEncontradoError
from app.core.storage import presigned_get_async
from app.core.utils.datetime_utils import utc_now_naive
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import resolver_workspace
from app.mcp.saida import envelope, higienizar, iso
from app.mcp.tools.base import ferramenta
from app.services.drive_service import DriveService

# Validade da URL assinada. O default do módulo de storage é uma hora, pensado
# para o navegador de quem está logado; aqui o link viaja por uma conversa e
# pode ser registrado em log de cliente, então dura o mínimo necessário para
# baixar o arquivo.
VALIDADE_DO_LINK_S = 300

# Teto de arquivos por página — o mesmo motivo de orçamento de contexto das
# demais listagens.
PAGE_SIZE_MAXIMO = 100

# Quantas colunas do metadado espacial saem por arquivo. Uma tabela de 300
# colunas descreveria o arquivo melhor do que o restante da resposta inteira.
MAX_COLUNAS = 50


def _resumo_espacial(bruto: Any) -> dict | None:
    """CRS, extensão, contagem e as primeiras colunas — nunca a lista inteira."""
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
        # Nome de coluna é escrito por quem produziu o arquivo: passa pelo
        # higienizador como qualquer outro texto de origem humana.
        resumo["columns"] = higienizar(colunas[:MAX_COLUNAS])
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
    """Lista os arquivos do Drive de um workspace.

    É de onde sai o identificador que um nó de entrada de dados consome. O
    metadado espacial vem resumido: CRS, extensão, contagem de feições e as
    primeiras colunas.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:read")

    pagina = max(1, int(page))
    tamanho = max(1, min(int(page_size), PAGE_SIZE_MAXIMO))

    async with infra.sessao() as db:
        ws = await resolver_workspace(db, escopo, workspace_id)
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
                "spatial_metadata": _resumo_espacial(a.spatial_metadata),
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
    """Uma URL de download temporária para um arquivo do Drive.

    A URL é PORTADORA e vale cinco minutos: quem tiver o link baixa o arquivo,
    sem autenticação. Use e descarte.

    Arquivo cujo conteúdo mora no executor volta com `available=false` em vez de
    erro: não há o que baixar pela plataforma (os bytes nunca foram enviados),
    mas o arquivo existe e continua utilizável por fluxos que rodem naquele
    executor — o cliente precisa saber a diferença entre "não existe" e "não dá
    para baixar daqui".
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:read")

    async with infra.sessao() as db:
        try:
            arquivo = await DriveService(db).get_file(str(file_id))
        except ArquivoNaoEncontradoError as exc:
            raise erro(
                "not_found",
                "Nenhum arquivo do Drive com este identificador.",
                "use list_drive_files para ver os arquivos do workspace",
            ) from exc
        # 403 quando o arquivo é de outro workspace: a leitura do id já
        # aconteceu, e o que se protege aqui é o conteúdo, não a existência.
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

    url = await presigned_get_async(chave, expires=VALIDADE_DO_LINK_S, filename=nome)
    return envelope(
        {
            **dados,
            "available": True,
            "download_url": url,
            "expires_in_seconds": VALIDADE_DO_LINK_S,
            "expires_at": iso(utc_now_naive() + timedelta(seconds=VALIDADE_DO_LINK_S)),
        },
        filename=nome,
    )


def registrar(server) -> None:
    """Registra as tools deste domínio."""
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
            # Cada chamada assina uma URL nova, com validade própria.
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )(get_drive_download_url)
