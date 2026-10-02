# app/services/executor_service.py
"""
Operacoes de negocio para Executores:
  - Criacao (admin) — apenas registra metadata; credencial vem via enrollment OTP + cert mTLS.
  - CRUD basico + revogacao (`revogar_executor` + `concluir_revogacoes`, a
    unica versao para todos os caminhos que revogam).

A autenticacao do executor agora e feita inteiramente por mTLS — a API key
estatica foi removida e o JWT intermediario do WebSocket eliminado. Ver
app/services/executor_enrollment_service.py para o fluxo de bootstrap e
app/api/routers/executor_ws_router.py para auth do WS por cert.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.executor_connections import executor_registry
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.crud.executor_crud import ExecutorCRUD
from app.models.executor import Executor
from app.models.user_executor_assignment import UserExecutorAssignment
from app.services import workspace_executor_service as politica

logger = get_logger(__name__)


class ExecutorQuotaError(Exception):
    """Usuário sem permissão ou que atingiu sua cota de executores dedicados."""

    def __init__(self, message: str, *, status_code: int):
        super().__init__(message)
        self.status_code = status_code


# ── Operacoes de servico ──────────────────────────────────────────────────────


async def create_executor(
    db: AsyncSession,
    name: str,
    created_by: str,
    description: str | None = None,
    capabilities: list[str] | None = None,
    max_concurrent_jobs: int = 4,
    max_queue_size: int = 50,
    executor_type: str = "dedicated",
    is_default: bool = False,
    commit: bool = True,
) -> Executor:
    """
    Cria um novo executor em status 'pending'.

    Apos a criacao, o admin precisa gerar um OTP de enrollment (ver
    executor_enrollment_service.create_enrollment_otp) e entrega-lo ao operador.
    O executor troca o OTP por cert mTLS via POST /executores/enroll.

    commit=False deixa a transacao aberta (apenas flush para popular id_hash),
    permitindo ao chamador agrupar inserts relacionados num unico commit.
    """
    if executor_type not in ("default", "dedicated"):
        raise ValueError("executor_type deve ser 'default' ou 'dedicated'.")

    if is_default or executor_type == "default":
        is_default = True
        executor_type = "default"

    ag = Executor(
        name=name,
        description=description,
        created_by=created_by,
        capabilities=capabilities or [],
        max_concurrent_jobs=max_concurrent_jobs,
        max_queue_size=max_queue_size,
        executor_type=executor_type,
        is_default=is_default,
        status="pending",
    )
    db.add(ag)
    if commit:
        await db.commit()
        await db.refresh(ag)
    else:
        await db.flush()  # popula id_hash e demais defaults sem encerrar a transacao
    return ag


async def count_user_created_executors(db: AsyncSession, user_id: str) -> int:
    """
    Conta executores do usuário (created_by) que ainda ocupam vaga na cota.

    Ignora revogados e soft-deletados — executores nesses estados estão "mortos
    para todos os efeitos" e não devem bloquear o user de criar um novo
    quando o admin restaura a cota.
    """
    result = await db.execute(
        select(func.count())
        .select_from(Executor)
        .where(
            Executor.created_by == user_id,
            Executor.deleted_at.is_(None),
            Executor.status != "revoked",
        )
    )
    return int(result.scalar_one())


async def create_dedicated_for_user(
    db: AsyncSession,
    user,
    name: str,
    description: str | None = None,
    capabilities: list[str] | None = None,
    max_concurrent_jobs: int = 4,
    max_queue_size: int = 50,
) -> Executor:
    """
    Cria um executor dedicado em nome de um usuário comum (self-service).

    Valida a cota individual (User.agent_quota) — 0 bloqueia, e o número de
    executores próprios não-deletados não pode atingir a cota. Força tipo dedicado
    e cria a atribuição direta (UserExecutorAssignment) para dar visibilidade ao
    criador em /executores/my. Lança ExecutorQuotaError (403/409) em caso de bloqueio.
    """
    quota = user.agent_quota or 0
    if quota <= 0:
        raise ExecutorQuotaError(
            "Você não tem permissão para criar executores.", status_code=403
        )

    current = await count_user_created_executors(db, user.id_hash)
    if current >= quota:
        raise ExecutorQuotaError(
            f"Limite de executores atingido ({current}/{quota}).", status_code=409
        )

    # commit=False: executor + atribuição entram num único commit (criação atômica).
    # Sem isso, falha ao gravar a atribuição deixaria um executor órfão consumindo cota.
    ag = await create_executor(
        db,
        name=name,
        created_by=user.id_hash,
        description=description,
        capabilities=capabilities,
        max_concurrent_jobs=max_concurrent_jobs,
        max_queue_size=max_queue_size,
        executor_type="dedicated",
        is_default=False,
        commit=False,
    )

    db.add(UserExecutorAssignment(
        user_id=user.id_hash,
        executor_id=ag.id_hash,
        assigned_by=user.id_hash,
    ))
    await db.commit()
    await db.refresh(ag)
    return ag


async def update_agent(db: AsyncSession, executor_id: str, data: dict) -> Executor:
    """
    Atualiza name e/ou description de um executor.
    Lanca ValueError se executor nao encontrado, deletado ou revogado.
    """
    ag = await get_agent(db, executor_id)
    if ag is None:
        raise ValueError(f"Executor '{executor_id}' nao encontrado.")
    if ag.status == "revoked":
        raise ValueError("Executor revogado nao pode ser editado.")
    for field in ("name", "description"):
        if field in data and data[field] is not None:
            setattr(ag, field, data[field])
    await db.commit()
    await db.refresh(ag)
    return ag


async def get_agent(db: AsyncSession, executor_id: str, include_deleted: bool = False) -> Executor | None:
    """Busca executor por id_hash. Por padrao, ignora executores deletados."""
    return await ExecutorCRUD(db).get(executor_id, include_deleted=include_deleted)


async def list_agents(db: AsyncSession) -> list[Executor]:
    """Lista executores ativos (nao deletados)."""
    return await ExecutorCRUD(db).list()


async def delete_agent(db: AsyncSession, executor_id: str) -> Executor:
    """
    Soft-delete de um executor — so permitido quando status='revoked'.

    Preenche deleted_at com a data/hora atual; o executor deixa de aparecer
    nas listagens mas permanece no banco para preservar historico de execucoes.
    """
    ag = await ExecutorCRUD(db).get_any(executor_id)
    if ag is None:
        raise ValueError(f"Executor '{executor_id}' nao encontrado.")
    if ag.status != "revoked":
        raise ValueError("Apenas executores revogados podem ser removidos.")
    ag.deleted_at = utc_now_naive()
    await db.commit()
    await db.refresh(ag)
    return ag


# ── Revogação ─────────────────────────────────────────────────────────────────
#
# Uma só, para os quatro caminhos que revogam: o DELETE do executor, o "revogar
# todos" do operador, a suspensão/exclusão da conta e (só o cert) a revogação do
# certificado. Cada um copiava os passos à mão, e as cópias divergiram: a
# suspensão não tirava o executor dos níveis da política nem derrubava a sessão
# aberta, e o "revogar todos" avisava os donos com o id no lugar do nome.


@dataclass
class Revogacao:
    """Um executor revogado na sessão de quem chama, com o que só pode sair do
    banco depois do commit — ver `concluir_revogacoes`."""

    executor_id: str
    nome: str
    # O cert que acabou de ser anulado, para a blacklist.
    serial: str | None
    serial_expira_em: datetime | None
    # O que o executor ouve: o motivo do `control` e o do fechamento do WS.
    aviso: str
    fechamento: str
    # Workspaces que tinham o executor num nível (o retorno de `detach_executor`).
    afetados: Sequence[dict] = ()


async def revogar_executor(
    db: AsyncSession,
    ag: Executor,
    *,
    force: bool,
    actor_id: str | None,
    motivo: str,
    aviso: str,
    fechamento: str,
    desanexar: bool = True,
) -> Revogacao:
    """Revoga `ag` na transação de quem chama — NÃO faz commit.

    1. Com `desanexar` (o DELETE do executor e o "revogar todos" do operador),
       tira o executor de todos os níveis da política, com a auditoria
       (`detach_executor`; `WorkspacePolicyConflictError` se esvaziaria o nível
       principal de alguém e `force` não foi pedido; forçado, os donos são
       avisados). Sem `desanexar` (a suspensão e a exclusão da conta — ver
       `revogar_executores_do_usuario`), o executor fica nos níveis.
    2. Status `revoked` e cert anulado — se voltar, só com novo enrollment.

    Blacklist, aviso aos donos e o fechamento do WebSocket não são banco e só
    valem depois do commit: quem chama roda `concluir_revogacoes` com o que esta
    função devolve. Avisar antes seria agir sobre uma revogação que um rollback
    ainda desfaz — e o close 4403 é terminal para o executor.
    """
    afetados = await politica.detach_executor(
        db, ag.id_hash, force=force, actor_id=actor_id, reason=motivo,
    ) if desanexar else []
    revogacao = Revogacao(
        executor_id=ag.id_hash, nome=ag.name, serial=ag.cert_serial,
        serial_expira_em=ag.cert_expires_at, aviso=aviso, fechamento=fechamento,
        afetados=afetados,
    )
    ag.status = "revoked"
    ag.cert_serial = None
    return revogacao


async def revogar_executores_do_usuario(
    db: AsyncSession, usuario, *, motivo: str, desanexar: bool,
    actor_id: str | None = None,
) -> list[Revogacao]:
    """Revoga todos os executores criados por `usuario` que ainda não estão
    revogados — o "revogar todos" do operador e a suspensão/exclusão da conta
    (auditoria SEG-16: sem isto o executor de uma conta suspensa seguia
    conectado, recebendo jobs com código e credenciais em claro e renovando o
    próprio cert).

    Pendentes entram junto: uma conta suspensa não deixa executor à espera de
    enrollment (quem tem o OTP ainda o enrolaria). NÃO faz commit, como
    `revogar_executor`.

    `desanexar` é de quem chama, e as duas escolhas são deliberadas:

    - "revogar todos" (`True`, forçado): ação explícita do operador sobre os
      executores, a mesma do DELETE — sai dos níveis, e um nível principal
      esvaziado vira aviso ao dono.
    - suspensão/exclusão da conta (`False`): o executor FICA nos níveis dos
      workspaces — muitas vezes de outros donos —, como manda a spec
      (docs/specs/executor-isolation-routing.md §4.4: executor fora de serviço
      continua no nível e só deixa de ser elegível). O despacho o pula e segue
      a cadeia (reserva ou falha fechada). Tirá-lo à força esvaziava o nível
      principal: o workspace Isolado virava pool compartilhado (jobs com
      credenciais indo para a frota comum) e a configuração do dono se perdia
      sem volta, mesmo com a conta reativada depois.
    """
    result = await db.execute(
        select(Executor).where(
            Executor.created_by == usuario.id_hash,
            Executor.deleted_at.is_(None),
            Executor.status != "revoked",
        )
    )
    return [
        await revogar_executor(
            db, ag, force=True, actor_id=actor_id, motivo=motivo,
            aviso=f"Acesso do operador '{usuario.username}' revogado pelo admin.",
            fechamento="Operador revogado.", desanexar=desanexar,
        )
        for ag in result.scalars().all()
    ]


def avisar_donos_de_niveis_esvaziados(afetados: Sequence[dict], *, executor_name: str) -> None:
    """Remoção que esvaziou o nível principal de alguém: e-mail ao dono
    (best-effort, em background, com sessão própria — a da requisição fecha
    junto com a resposta). Sem isto o workspace descobriria pelo 503."""
    from app.services.execution_alert_service import notify_primary_emptied_background

    esvaziados = [d for d in afetados if d.get("would_empty_primary")]
    notify_primary_emptied_background(esvaziados, executor_name=executor_name)


async def concluir_revogacoes(revogacoes: Iterable[Revogacao]) -> None:
    """O que a revogação faz fora do banco, DEPOIS do commit de quem chama.

    Tudo best-effort e isolado por executor — a revogação já vale no banco, e a
    vigia da sessão (`_vigiar_revogacao`) derruba o WebSocket mesmo que o
    fechamento daqui se perca:

    - blacklist do cert no Redis (defesa em profundidade além da CRL);
    - e-mail aos donos dos workspaces cujo nível principal esvaziou;
    - `control: revoked` (o motivo, para o operador ler) e close 4403 — é o
      close que faz o executor parar, mesmo um que ignore o control. Os dois
      fazem relay pelo Redis quando o WebSocket está em outro worker: sem o
      relay, um admin que caísse num worker sem o WS revogava só o banco.
    """
    from app.services import executor_enrollment_service

    for r in revogacoes:
        if r.serial:
            try:
                await executor_enrollment_service.revoke_cert(r.serial, cert_expires_at=r.serial_expira_em)
            except Exception as exc:
                logger.warning(
                    "Falha ao marcar cert '%s' (executor %s) como revogado no Redis: %s",
                    r.serial, r.executor_id, exc,
                )
        avisar_donos_de_niveis_esvaziados(r.afetados, executor_name=r.nome)
        try:
            await executor_registry.send_json(r.executor_id, {
                "type": "control", "action": "revoked", "reason": r.aviso,
            })
        except Exception as exc:
            logger.warning("Falha ao notificar executor '%s' sobre a revogação: %s", r.executor_id, exc)
        try:
            await executor_registry.disconnect_executor(r.executor_id, code=4403, reason=r.fechamento)
        except Exception as exc:
            logger.warning("Falha ao desconectar executor '%s' revogado: %s", r.executor_id, exc)


async def update_agent_last_seen(db: AsyncSession, executor_id: str):
    """Atualiza last_seen_at — chamado no início de cada sessão WebSocket."""
    await ExecutorCRUD(db).touch_last_seen(executor_id)


async def motivo_da_revogacao(db: AsyncSession, executor_id: str) -> str | None:
    """Por que uma sessão WebSocket já aberta deixou de valer; None se vale.

    Espelha o que o mTLS exige na conexão (`validate_executor_mtls`): executor
    existente, não removido, ativo e com cert. A revogação do cert zera o
    `cert_serial`; a do executor (e a do operador, que revoga os executores
    dele) muda o status. A renovação troca o serial sem zerar — não derruba a
    sessão que a fez."""
    linha = (await db.execute(
        select(Executor.status, Executor.cert_serial, Executor.deleted_at)
        .where(Executor.id_hash == executor_id)
    )).one_or_none()
    if linha is None or linha.deleted_at is not None:
        return "Executor removido."
    if linha.status != "active":
        return "Executor revogado."
    if not linha.cert_serial:
        return "Cert revogado."
    return None


async def registrar_fim_da_sessao(db: AsyncSession, executor_id: str, visto_em) -> None:
    """Fim de uma sessão WebSocket: `last_seen_at` passa a ser o último contato
    dela — se for posterior ao que está no banco. O fim de uma sessão
    substituída chega depois do handshake da nova (segundos, até ~100 s quando
    o aviso de takeover se perde) e, gravado sem condição, apagava o início da
    nova: o "no ar desde" que os outros workers leem daqui."""
    await ExecutorCRUD(db).touch_last_seen_if_later(executor_id, visto_em)
