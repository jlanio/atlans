# app/mcp/tools/drive_escrita.py
"""
Escrita no Drive: pôr arquivo, concluir o envio e apagar.

Fecha `drive:write`, o último dos seis escopos que a tela de tokens oferece com
descrição afirmativa. Com ele, a Fase 2 deixa de prometer o que não cumpre.

## O upload são TRÊS chamadas, e isso é desenho, não burocracia

```
create_drive_upload_url  →  PUT direto no storage  →  confirm_drive_upload
      (a tool)                (quem tem os bytes)          (a tool)
```

O passo do meio **não passa por aqui**, e é o motivo de o fluxo existir: MCP é
JSON-RPC, e mandar um arquivo por ele significaria carregá-lo inteiro em base64
dentro de uma mensagem — um shapefile de 40 MB viraria 54 MB de texto no
contexto de quem chamou, custando mais do que qualquer análise que ele fosse
alimentar. A URL pré-assinada põe os bytes no caminho curto.

A consequência prática, e a tool diz isso: **um agente que não tem o arquivo em
disco não consegue usar estas tools.** Ele pode pedir a URL e entregá-la a quem
tem, mas não pode inventar o conteúdo. Fingir o contrário faria o agente
prometer um upload que nunca aconteceu.

## Duas coisas que o Drive NÃO tem

**Ele é plano.** Não existe renomear, mover, nem criar pasta — nem na REST, nem
no modelo. Um arquivo tem nome e workspace, e é só. Está escrito aqui porque a
alternativa é o agente descobrir tentando, e gastar uma rodada para isso.

**Sobrescrever não é uma operação.** Enviar o mesmo nome cria outro registro.
Quem quer substituir apaga e envia de novo — e a tool de apagar diz isso.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from mcp.server.mcpserver import Context

from app.core.authorization.workflow_access import (
    exigir_papel, get_workspace_member_role,
)
# `FileNotFoundError` do app SOMBREIA a builtin e nao herda dela — ela estende
# `FileError`/`AtlasBaseError`. Um `except FileNotFoundError` sem este import
# pega a builtin e NAO casa, deixando a excecao subir para o `@ferramenta`, que
# a mapeia pelo `status_code` e devolve a mensagem do servico no lugar da dica
# da tool. O alias torna a diferenca visivel em vez de depender de quem lembra.
from app.core.exceptions import FileNotFoundError as ArquivoNaoEncontradoError
from app.core.rbac import ROLE_EDITOR
from app.core.storage import _PRESIGN_EXPIRY
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import resolver_workspace
from app.mcp.saida import envelope, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.core.exceptions import FileValidationError
from app.services.drive_service import (
    ConteudoNoExecutorError, DriveService, FileTooLargeError,
)

logger = get_logger("app.mcp.tools.drive_escrita")

# Validade da URL de envio: LIDA do storage, não escolhida aqui.
#
# `DriveService.create_upload_url` assina com o default do módulo
# (`presigned_put_async` sem `expires`), que é `MINIO_PRESIGN_EXPIRY` — uma
# hora, configurável por ambiente. Anunciar um número diferente seria mentir
# sobre um prazo que o cliente usa para decidir se ainda dá tempo de enviar um
# arquivo grande, e o erro apareceria como "a URL expirou antes do que você
# disse" no meio de um upload de vinte minutos.
#
# É o mesmo cuidado das URLs de download, com uma diferença que explica por que
# aqui é mais longo: lá o relógio corre até um clique, aqui corre durante a
# TRANSFERÊNCIA inteira.
VALIDADE_DO_ENVIO_S = _PRESIGN_EXPIRY

_MENSAGEM_PAPEL = "Requer papel 'editor' ou superior neste workspace."


async def _exigir_editor(db, escopo, workspace_id: str) -> None:
    """O par que a rota REST aplica com `exigir_papel_no_workspace(..., ROLE_EDITOR)`.

    O Drive é por WORKSPACE, não por workflow, então não há
    `carregar_workflow` para devolver o papel junto: ele é buscado aqui.
    `resolver_workspace` já garantiu que o workspace está no alcance do token;
    o que falta é o papel de quem chama DENTRO dele.
    """
    papel = await get_workspace_member_role(db, workspace_id, escopo.user_id)
    exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL)


def _erro_de_arquivo(exc: Exception):
    """`FileValidationError` cobre extensão proibida, dupla extensão e nome sem
    extensão — todos com a causa já na mensagem."""
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
    """Primeiro dos três passos de um upload: pede a URL para enviar os bytes.

    Devolve `upload_url`, que aceita um **PUT** com o conteúdo do arquivo, e
    `file_id`, que identifica o registro daqui em diante.

    **Esta tool não envia o arquivo.** Ela não vê os bytes e não pode
    inventá-los: quem faz o PUT é quem tem o arquivo em disco. Se você não o
    tem, entregue a URL a quem tem — e não anuncie que o upload aconteceu.

    Depois do PUT, chame `confirm_drive_upload(file_id)`. Sem essa terceira
    chamada o arquivo **não aparece no Drive**: fica um registro pendente que a
    faxina apaga depois, e os bytes enviados vão junto.

    `size_bytes` é conferido aqui contra o teto do workspace, e **de novo no
    confirm** contra o objeto real — declarar um número pequeno e enviar um
    arquivo grande é recusado no fim, com o objeto apagado.

    A extensão precisa estar na lista que o administrador permite, e nome com
    extensão interna perigosa (`relatorio.exe.csv`) é recusado.
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
        ws = await resolver_workspace(db, escopo, workspace_id)
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
            raise _erro_de_arquivo(exc)

    return envelope(
        {
            "file_id": criado["id_hash"],
            "workspace_id": ws,
            "upload_url": criado["upload_url"],
            "method": "PUT",
            "expires_in_seconds": VALIDADE_DO_ENVIO_S,
            "expires_at": iso(utc_now_naive() + timedelta(seconds=VALIDADE_DO_ENVIO_S)),
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
    """Terceiro passo: conclui o upload e faz o arquivo aparecer no Drive.

    Até esta chamada o registro está pendente e invisível na listagem. Aqui o
    servidor **mede o objeto de verdade** no storage e grava o tamanho real —
    não o que foi declarado no passo 1.

    Se o arquivo real estiver acima do teto do workspace, a confirmação é
    recusada **e os bytes são apagados**: aceitar um objeto acima do limite
    porque já está lá seria só uma forma mais lenta de não ter limite.

    `not_found` aqui quase sempre significa que o PUT não chegou a acontecer,
    ou que a URL do passo 1 expirou antes do envio terminar. Nesse caso, peça
    outra URL e refaça o envio.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:write")

    async with infra.sessao() as db:
        servico = DriveService(db)
        try:
            arquivo = await servico.get_file(str(file_id))
        except ArquivoNaoEncontradoError as exc:
            raise erro(
                "not_found",
                "Nenhum arquivo do Drive com este identificador.",
                "o file_id é o que create_drive_upload_url devolveu",
            ) from exc

        # Resolver PELO workspace do arquivo, e não por um parâmetro: um
        # `workspace_id` vindo do chamador aqui só serviria para ele apontar
        # para um workspace seu e confirmar o arquivo de outro.
        await resolver_workspace(db, escopo, arquivo.workspace_id)
        await _exigir_editor(db, escopo, arquivo.workspace_id)

        try:
            confirmado = await servico.confirm_upload(str(file_id))
        except FileTooLargeError as exc:
            raise erro(
                "validation",
                f"{exc} O objeto enviado foi apagado.",
                "confira o tamanho real do arquivo e peça uma URL nova",
            )
        except ArquivoNaoEncontradoError as exc:
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
            # O tamanho MEDIDO, que pode diferir do declarado no passo 1.
            "size": confirmado.size,
            "status": confirmado.status,
        }
        nome = confirmado.original_name

    return envelope(dados, filename=nome)


# ── Apagar ───────────────────────────────────────────────────────────────────


@ferramenta
async def delete_drive_file(ctx: Context, file_id: str, confirm: bool = False) -> dict:
    """Apaga um arquivo do Drive, de vez. Exige `confirm=true`.

    Não há lixeira: o registro e os bytes somem juntos e não voltam. E o
    estrago não para no arquivo — um fluxo que o lê passa a falhar na próxima
    execução, sem nada ligando uma coisa à outra para quem for investigar.

    Sem `confirm=true` nada é apagado: a resposta descreve o arquivo, para você
    mostrar a quem pediu antes de repetir a chamada.

    **Isto é também como se substitui um arquivo**, porque sobrescrever não é
    uma operação do Drive: apague e envie de novo com o mesmo nome.

    Arquivo cujo conteúdo mora no executor (`content_location: "executor"`) é
    recusado. A plataforma guarda a ficha, nunca os bytes — apagar o registro
    não removeria nada do disco de quem tem o arquivo, e mandar o executor
    apagá-lo seria destruir dado que nunca pertenceu à plataforma.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "drive:write")

    async with infra.sessao() as db:
        servico = DriveService(db)
        try:
            arquivo = await servico.get_file(str(file_id))
        except ArquivoNaoEncontradoError as exc:
            raise erro(
                "not_found",
                "Nenhum arquivo do Drive com este identificador.",
                "use list_drive_files para ver os arquivos do workspace",
            ) from exc

        await resolver_workspace(db, escopo, arquivo.workspace_id)
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
        except ConteudoNoExecutorError as exc:
            raise erro(
                "unavailable_local", str(exc),
                "quem quer que o arquivo suma apaga o arquivo na máquina do "
                "executor, ou tira a pasta do GeoSync",
            )
        except Exception as exc:  # noqa: BLE001 — a falha do storage é do caminho
            # `delete_file` recusa apagar a linha se o storage falhar, de
            # propósito: assim a reconciliação tenta de novo e o objeto não
            # vira órfão. O que não pode é isso subir como erro inesperado.
            logger.error("delete_drive_file: storage falhou para %s (%s).", file_id, exc)
            raise erro(
                "unavailable",
                "O arquivo não pôde ser apagado do armazenamento; nada foi removido.",
                "tente de novo em instantes — o registro foi preservado de propósito",
            )

    return envelope({**descricao, "outcome": "deleted"}, filename=nome)


def registrar(server) -> None:
    """Registra as tools deste domínio."""
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
