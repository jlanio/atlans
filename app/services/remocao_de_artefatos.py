# app/services/remocao_de_artefatos.py
"""
Remoção de artefatos: um algoritmo só para os cinco caminhos que apagam.

DELETE /artifacts/{id}, POST /artifacts/batch-delete, a retenção
(`artifact_cleanup.purge_expired_artifacts`), o reenvio ao executor que
reconecta (`artifact_cleanup.purgar_pendentes_do_executor`) e a purga do
workspace (`storage_purge_service.purge_workspace_storage`) tinham cada um a
sua cópia do laço, e as cópias divergiram: só a purga apagava a camada do
portal de um artefato LOCAL entregue — nos outros caminhos a linha sumia e a
PortalLayer ficava no ar. Quem chama escolhe QUAIS artefatos (a query) e
traduz o desfecho (204/202/502, contadores, log); a regra mora aqui:

- Conteúdo no disco de um executor (`content_location='executor'`): a ordem de
  remoção vai para o executor (`_ordenar_remocao_local`, uma por máquina) e a
  linha só cai quando ela foi ENTREGUE. Apagar antes deixaria o arquivo órfão
  no disco do usuário e o servidor sem registro nenhum dele — para dado
  pessoal, pior que não ter apagado. Sem `executor_id`/`local_path` não há a
  quem mandar: a linha fica, para não perder o rastro do arquivo.
- Objeto no MinIO: sai PRIMEIRO. Se o S3 falhar por outro motivo que não "not
  found", a linha fica — o objeto não vira órfão invisível, e a próxima
  passada (ou a reconciliação) tenta de novo. `s3_key` começando com "/" é o
  fallback local antigo do executor: não existe no MinIO, só a linha sai.
- A camada do portal (e as features, em cascata) sai junto com a linha de todo
  artefato publicado apagado, de qualquer localidade.

NÃO faz commit: quem chama decide quando persistir.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.portal_layer import PortalLayer

logger = get_logger(__name__)


@dataclass
class Remocao:
    """O desfecho, artefato por artefato. Só `apagados` saiu do banco."""

    apagados: list = field(default_factory=list)
    # Objeto que o MinIO não apagou: a linha fica, e repetir resolve.
    falhas_s3: list = field(default_factory=list)
    # Local cuja ordem não foi entregue (executor offline): a linha fica, e a
    # ordem é reenviada quando ele reconectar.
    pendentes_local: list = field(default_factory=list)
    # Local sem executor_id/local_path: não há a quem mandar a ordem.
    sem_rastro: list = field(default_factory=list)

    @property
    def bytes(self) -> int:
        return sum(int(a.size_bytes or 0) for a in self.apagados)


async def remover_artefatos(
    db: AsyncSession, artefatos, *, agendar_pendentes: bool,
) -> Remocao:
    """Remove `artefatos` (objetos da sessão `db`) — ver a semântica acima.

    `agendar_pendentes`: os que ficaram no disco de um executor (ordem não
    entregue, ou sem rastro) são marcados como vencidos, sem pin, para a
    retenção concluir sozinha — é o que o usuário pediu nas rotas de exclusão.
    O pin PRECISA cair junto: a retenção ignora artefato fixado, e um fixado
    marcado como vencido sumiria da tela como "removendo" e nunca seria
    removido. Na retenção e na purga eles já estão no alcance da próxima
    passada, e nada é marcado.
    """
    # Da retenção: é ela que assina, envia e devolve só os ids ENTREGUES.
    from app.core.artifact_cleanup import _ordenar_remocao_local
    from app.core import storage as s3

    remocao = Remocao()

    por_executor: dict[str, list[dict]] = {}
    locais: list = []
    for a in artefatos:
        if a.content_location != "executor":
            continue
        if not a.executor_id or not a.local_path:
            logger.warning(
                "Remoção: artefato local %s sem executor_id/local_path — mantido no banco "
                "para não perder o rastro do arquivo.", a.id_hash,
            )
            remocao.sem_rastro.append(a)
            continue
        por_executor.setdefault(a.executor_id, []).append(
            {"id_hash": a.id_hash, "local_path": a.local_path, "_id": a.id}
        )
        locais.append(a)
    if por_executor:
        entregues = set(await _ordenar_remocao_local(por_executor))
        for a in locais:
            (remocao.apagados if a.id in entregues else remocao.pendentes_local).append(a)

    for a in artefatos:
        if a.content_location == "executor":
            continue
        if a.s3_key and not a.s3_key.startswith("/"):
            try:
                await s3.delete_strict_async(a.s3_key, allow_missing=True)
            except Exception as exc:
                logger.warning("Remoção: mantendo artefato %s no banco (S3 falhou: %s).", a.s3_key, exc)
                remocao.falhas_s3.append(a)
                continue
        remocao.apagados.append(a)

    for a in remocao.apagados:
        await _apagar_camada_do_portal(db, a)
    if remocao.apagados:
        await db.execute(delete(Artifact).where(Artifact.id.in_([a.id for a in remocao.apagados])))

    if agendar_pendentes:
        agora = utc_now_naive()
        for a in (*remocao.pendentes_local, *remocao.sem_rastro):
            a.expires_at = agora
            a.is_pinned = False
    return remocao


async def _apagar_camada_do_portal(db: AsyncSession, artefato) -> None:
    """A camada publicada do artefato (as features caem em cascata)."""
    if artefato.is_published and artefato.workflow_hash:
        await db.execute(
            delete(PortalLayer).where(
                PortalLayer.workflow_hash == artefato.workflow_hash,
                PortalLayer.layer_key == artefato.output_key,
            )
        )
