# app/services/storage_purge_service.py
"""
Purga de armazenamento por workspace (Drive + Artefatos).

Dois usos:

1. **Botão do admin** em /admin/storage — libera espaço de um workspace ativo,
   ou limpa os órfãos deixados por um workspace já deletado.
2. **DELETE /workspaces/{id}** — antes o hard delete não tocava nos dados, e os
   artefatos ficavam apontando para um workspace inexistente: inacessíveis
   (`verify_workspace_access` nunca casa) e ocupando disco para sempre.

Os artefatos saem por `remocao_de_artefatos.remover_artefatos`, a mesma regra
das rotas de exclusão e da retenção: objeto do MinIO primeiro (falha preserva a
linha, e repetir a purga resolve), conteúdo local só com a ordem ENTREGUE ao
executor (offline mantém a linha e a próxima passada reenvia), camada do portal
junto. Aqui só se somam os contadores.

Arquivo de Drive catalogado (`content_location='executor'`) NÃO segue essa
semântica, e a diferença é deliberada: ele é um arquivo do próprio usuário,
numa pasta que ele escolheu sincronizar, do qual a plataforma nunca teve os
bytes nem ocupa armazenamento. `drive_service._recusar_se_catalogado` recusa
apagá-lo na exclusão avulsa; aqui ele é preservado e contado em
`skipped_catalogados`.
"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.workspace_file import WorkspaceFile
from app.services.remocao_de_artefatos import remover_artefatos

logger = get_logger(__name__)

SCOPES = ("all", "artifacts", "drive")


async def purge_workspace_storage(
    db: AsyncSession, workspace_id: str, *, scope: str = "all",
) -> dict:
    """Remove objetos do MinIO e as linhas correspondentes. IRREVERSÍVEL.

    `scope`: "all" | "artifacts" | "drive".
    Retorna contadores do que foi efetivamente removido e o que ficou pendente
    por falha no S3 (esses são re-tentáveis: basta repetir a purga).
    """
    if scope not in SCOPES:
        raise ValueError(f"scope inválido: {scope!r}. Use um de {SCOPES}.")

    from app.core import storage as s3

    removed = {
        "workspace_id":     workspace_id,
        "scope":            scope,
        "artifacts":        0,
        "artifact_bytes":   0,
        "drive_files":      0,
        "drive_bytes":      0,
        "skipped_s3_errors": 0,
        # Artefatos locais cuja ordem de remoção não foi entregue (executor
        # offline): a linha fica, e a próxima passada tenta de novo.
        "pending_executor": 0,
        # Artefatos locais sem executor_id/local_path — sem rastro para onde
        # mandar a ordem; a linha fica para não perder o registro do arquivo.
        "skipped_sem_rastro": 0,
        # Arquivos de Drive catalogados no executor: preservados por política.
        "skipped_catalogados": 0,
        # Referências de pin zeradas nos workflows do workspace: os objetos do
        # pin-cache caem junto com os demais artefatos, e a ref pendurada seria
        # um 404 permanente. Zerar (em vez de remover) preserva a intenção de
        # pin — pin_metadata fica — e a próxima run regrava o cache sozinha.
        "pins_resetados": 0,
    }

    # ── Artefatos ─────────────────────────────────────────────────────────────
    if scope in ("all", "artifacts"):
        result = await db.execute(select(Artifact).where(Artifact.workspace_id == workspace_id))
        remocao = await remover_artefatos(db, result.scalars().all(), agendar_pendentes=False)
        removed["artifacts"] += len(remocao.apagados)
        removed["artifact_bytes"] += remocao.bytes
        removed["skipped_s3_errors"] += len(remocao.falhas_s3)
        removed["pending_executor"] += len(remocao.pendentes_local)
        removed["skipped_sem_rastro"] += len(remocao.sem_rastro)

        # Pins dos workflows deste workspace: os objetos do pin-cache acabaram
        # de ser apagados do MinIO (logo acima), então toda ref `__pin_s3_key__`
        # que sobrar aponta para o nada — 404 em cada run seguinte, e como o
        # auto-pin só dispara com a ref VAZIA, a quebra não se resolvia sozinha.
        # Zera a ref e mantém pin_metadata: a intenção de pin sobrevive e a
        # próxima execução regrava o cache sob uma chave nova.
        from sqlalchemy.orm.attributes import flag_modified
        from app.models.workflow import Workflow

        wf_result = await db.execute(
            select(Workflow).where(Workflow.workspace_id == workspace_id)
        )
        for wf in wf_result.scalars():
            pins = wf.pinned_outputs
            if not isinstance(pins, dict):
                continue
            zerados = {
                nid for nid, ref in pins.items()
                if isinstance(ref, dict) and "__pin_s3_key__" in ref
            }
            if not zerados:
                continue
            wf.pinned_outputs = {
                nid: ({} if nid in zerados else ref) for nid, ref in pins.items()
            }
            flag_modified(wf, "pinned_outputs")
            removed["pins_resetados"] += len(zerados)

    # ── Drive ─────────────────────────────────────────────────────────────────
    if scope in ("all", "drive"):
        result = await db.execute(
            select(WorkspaceFile).where(WorkspaceFile.workspace_id == workspace_id)
        )
        files = result.scalars().all()

        ids = []
        for wf in files:
            # Arquivo CATALOGADO (GeoSync "manter apenas no executor"): a
            # plataforma nunca teve os bytes, e o arquivo está na pasta que o
            # próprio usuário escolheu sincronizar. Apagar a linha não removeria
            # nada e destruiria a única ficha que registra o vínculo; mandar o
            # executor apagar seria destruir dado do usuário que nunca
            # pertenceu à plataforma. É a mesma recusa que
            # `drive_service._recusar_se_catalogado` aplica na exclusão avulsa —
            # aqui o registro era apagado em silêncio, contradizendo aquela
            # política. Ele também não ocupa armazenamento nenhum da plataforma,
            # então preservá-lo não conflita com o objetivo da purga.
            if getattr(wf, "content_location", "minio") == "executor":
                removed["skipped_catalogados"] += 1
                continue
            if wf.s3_key:
                try:
                    await s3.delete_strict_async(wf.s3_key, allow_missing=True)
                except Exception as exc:
                    logger.warning(
                        "Purge: mantendo arquivo %s no banco (S3 falhou: %s).", wf.s3_key, exc,
                    )
                    removed["skipped_s3_errors"] += 1
                    continue
            ids.append(wf.id)
            removed["drive_files"] += 1
            removed["drive_bytes"] += int(wf.size or 0)

        if ids:
            await db.execute(delete(WorkspaceFile).where(WorkspaceFile.id.in_(ids)))

    await db.commit()
    logger.warning(
        "Purge de armazenamento no workspace '%s' (scope=%s): %d artefato(s) e %d arquivo(s) "
        "removidos, %d pendente(s) por falha no S3.",
        workspace_id, scope, removed["artifacts"], removed["drive_files"],
        removed["skipped_s3_errors"],
    )
    return removed


async def schedule_workspace_data_expiry(db: AsyncSession, workspace_id: str) -> dict:
    """Marca os dados do workspace para remoção pelo cleanup global.

    Usado no DELETE do workspace. Preferimos `expires_at` a apagar na hora:
    dá janela de arrependimento e reaproveita `purge_expired_artifacts`, que já
    trata MinIO, PortalLayer e retry em falha de S3.

    Arquivos do Drive não têm coluna de expiração, então são purgados
    imediatamente — deixá-los seria manter no MinIO um dado que ninguém mais
    consegue listar (a listagem é sempre por workspace).
    """
    now = utc_now_naive()

    artifacts = (await db.execute(
        select(func.count(Artifact.id)).where(Artifact.workspace_id == workspace_id)
    )).scalar() or 0

    # Expira imediatamente: o cleanup roda periodicamente e faz a remoção real.
    await db.execute(
        Artifact.__table__.update()
        .where(Artifact.workspace_id == workspace_id)
        .values(expires_at=now)
    )

    drive = await purge_workspace_storage(db, workspace_id, scope="drive")

    return {"artifacts": int(artifacts), "drive_files": drive["drive_files"]}
