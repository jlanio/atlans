# app/services/workspace_executor_service.py
"""
Política de execução de um workspace (docs/specs/executor-isolation-routing.md).

    níveis:   [nível 1 = executores dedicados principais]
              [nível 2 = fallback, opcional: outros dedicados do próprio workspace]
    terminal: "fail" (Isolado — nunca pool) | "pool" (Dedicado com fallback)
    piso:     "none" | "no_pool" — só o admin da plataforma; força terminal "fail"

Modo pool = zero linhas em tier 1: a política nem é lida. Tudo aqui é a ÚNICA
fonte das regras — o dispatch, os endpoints e as cascatas (revogar/apagar
executor, promover a default) chamam este módulo em vez de reescrevê-las.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    WorkspaceAccessDeniedError,
    WorkspacePolicyConflictError,
    WorkspacePolicyError,
    WorkspacePolicyFloorError,
)
from app.core.utils.logger import get_logger
from app.models.audit_event import AuditEvent
from app.models.executor import Executor
from app.models.workspace import Workspace
from app.models.workspace_executor import WorkspaceExecutor

logger = get_logger(__name__)

TIER_PRIMARY = 1
TIER_FALLBACK = 2
TIERS = (TIER_PRIMARY, TIER_FALLBACK)

TERMINAL_FAIL = "fail"
TERMINAL_POOL = "pool"
TERMINALS = (TERMINAL_FAIL, TERMINAL_POOL)

FLOOR_NONE = "none"
FLOOR_NO_POOL = "no_pool"
FLOORS = (FLOOR_NONE, FLOOR_NO_POOL)

# Nível em que um job foi ENTREGUE (WorkflowRun.dispatch_tier).
DISPATCH_PRIMARY = "primary"
DISPATCH_FALLBACK = "fallback"
DISPATCH_POOL = "pool"

# Modo do workspace, derivado — nunca gravado.
MODE_POOL = "pool"                    # sem nível 1: pool compartilhado
MODE_ISOLATED = "isolated"            # nível 1 + terminal efetivo fail
MODE_DEDICATED_POOL = "dedicated_pool"  # nível 1 + terminal efetivo pool


@dataclass
class WorkspacePolicy:
    workspace_id: str
    primary: list[Executor] = field(default_factory=list)
    fallback: list[Executor] = field(default_factory=list)
    terminal_configured: str = TERMINAL_FAIL
    floor: str = FLOOR_NONE

    @property
    def has_primary(self) -> bool:
        return bool(self.primary)

    @property
    def terminal_effective(self) -> str:
        return effective_terminal_of(self.floor, self.terminal_configured)

    @property
    def floor_no_pool(self) -> bool:
        return (self.floor or FLOOR_NONE) == FLOOR_NO_POOL

    @property
    def mode(self) -> str:
        return mode_of(self.has_primary, self.floor, self.terminal_configured)

    @property
    def allows_pool(self) -> bool:
        """O pool pode receber jobs deste workspace? Nunca sob piso `no_pool`."""
        if self.floor_no_pool:
            return False
        return self.mode in (MODE_POOL, MODE_DEDICATED_POOL)

    @property
    def tier_ids(self) -> set[str]:
        return {e.id_hash for e in self.primary} | {e.id_hash for e in self.fallback}


def mode_of(has_primary: bool, floor: str | None, terminal: str | None) -> str:
    """Modo derivado (nunca gravado) — a MESMA conta para a política carregada
    e para listagens que só têm as contagens dos níveis (tela de admin).

    Sem nível 1 o workspace é pool — EXCETO sob piso: o admin da plataforma
    proibiu o pool, então não há para onde ir (spec §5.3 vence §4.2:
    "no_pool" é absoluto, não só um default do terminal)."""
    if not has_primary:
        return MODE_ISOLATED if (floor or FLOOR_NONE) == FLOOR_NO_POOL else MODE_POOL
    return MODE_ISOLATED if effective_terminal_of(floor, terminal) == TERMINAL_FAIL else MODE_DEDICATED_POOL


def effective_terminal_of(floor: str | None, terminal: str | None) -> str:
    """Terminal que VALE: o piso `no_pool` vence qualquer `fallback_terminal`.

    Calculado no dispatch e não só na escrita — mesmo que o banco carregue um
    estado que a API recusa (escrita direta, ordem de migração), o roteamento
    trata como `fail`.
    """
    if (floor or FLOOR_NONE) == FLOOR_NO_POOL:
        return TERMINAL_FAIL
    return terminal if terminal in TERMINALS else TERMINAL_FAIL


# ── Leitura ──────────────────────────────────────────────────────────────────

async def load_policy(db: AsyncSession, ws: Workspace) -> WorkspacePolicy:
    """Níveis (com os executores vivos) + terminal + piso de um workspace."""
    result = await db.execute(
        select(WorkspaceExecutor.tier, Executor)
        .join(Executor, Executor.id_hash == WorkspaceExecutor.executor_id)
        .where(
            WorkspaceExecutor.workspace_id == ws.id_hash,
            Executor.deleted_at.is_(None),
        )
        .order_by(WorkspaceExecutor.tier, WorkspaceExecutor.created_at)
    )
    policy = WorkspacePolicy(
        workspace_id=ws.id_hash,
        terminal_configured=getattr(ws, "fallback_terminal", None) or TERMINAL_FAIL,
        floor=getattr(ws, "isolation_floor", None) or FLOOR_NONE,
    )
    for tier, executor in result.all():
        (policy.primary if tier == TIER_PRIMARY else policy.fallback).append(executor)
    return policy


async def load_policy_by_id(db: AsyncSession, workspace_id: str) -> WorkspacePolicy | None:
    result = await db.execute(
        select(Workspace).where(Workspace.id_hash == workspace_id, Workspace.deleted_at.is_(None))
    )
    ws = result.scalar_one_or_none()
    if ws is None:
        return None
    return await load_policy(db, ws)


async def allowed_executor_ids(db: AsyncSession, policy: WorkspacePolicy) -> set[str]:
    """Conjunto PERMITIDO (spec §5.3): níveis ∪ pool, o pool só se a política
    o admite. É o que a barreira do dispatch confere antes de cifrar."""
    from app.services.user_executor_service import get_default_agents

    allowed = set(policy.tier_ids)
    if policy.allows_pool:
        allowed |= {e.id_hash for e in await get_default_agents(db)}
    return allowed


# ── Escrita: níveis ──────────────────────────────────────────────────────────

async def _get_executor(db: AsyncSession, executor_id: str) -> Executor | None:
    result = await db.execute(
        select(Executor).where(Executor.id_hash == executor_id, Executor.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def _rows_of(db: AsyncSession, workspace_id: str) -> list[WorkspaceExecutor]:
    result = await db.execute(
        select(WorkspaceExecutor).where(WorkspaceExecutor.workspace_id == workspace_id)
    )
    return list(result.scalars().all())


def _validate_member(executor: Executor | None, executor_id: str) -> Executor:
    if executor is None:
        raise WorkspacePolicyError("Executor não encontrado.")
    if executor.is_default:
        # Q3: um executor do pool dentro de um nível "dedicado" é contradição —
        # o job iria para uma máquina que também serve o pool aberto.
        raise WorkspacePolicyError(
            f"'{executor.name}' pertence ao pool compartilhado e não pode entrar num "
            "nível dedicado. O pool participa só como terminal da política."
        )
    if executor.status != "active":
        raise WorkspacePolicyError(
            f"Executor '{executor.name}' não está ativo (status: {executor.status})."
        )
    if not executor.public_key:
        raise WorkspacePolicyError(
            f"Executor '{executor.name}' ainda não concluiu o enrollment (sem chave pública) "
            "e não poderia receber jobs."
        )
    return executor


async def add_member(
    db: AsyncSession, ws: Workspace, executor_id: str, tier: int, *,
    actor_id: str | None, accessible_ids: set[str] | None = None,
) -> WorkspaceExecutor:
    """Inclui um executor num nível. `accessible_ids` = executores a que quem
    inclui tem acesso (None = admin da plataforma, sem restrição)."""
    if tier not in TIERS:
        raise WorkspacePolicyError("Nível inválido: use 1 (principal) ou 2 (fallback).")
    # Acesso ANTES da validação: quem não tem acesso ao executor não fica
    # sabendo se ele existe, se é do pool ou se está inativo.
    if accessible_ids is not None and executor_id not in accessible_ids:
        raise WorkspaceAccessDeniedError("Você não tem acesso a este executor.")
    executor = _validate_member(await _get_executor(db, executor_id), executor_id)

    rows = await _rows_of(db, ws.id_hash)
    if any(r.executor_id == executor_id for r in rows):
        raise WorkspacePolicyError(
            f"'{executor.name}' já está na política deste workspace (um executor "
            "fica em um nível só)."
        )
    if tier == TIER_FALLBACK and not any(r.tier == TIER_PRIMARY for r in rows):
        raise WorkspacePolicyError(
            "Adicione um executor ao nível principal antes de configurar o fallback."
        )

    row = WorkspaceExecutor(
        workspace_id=ws.id_hash, executor_id=executor_id, tier=tier, added_by=actor_id,
    )
    db.add(row)
    _audit(db, ws.id_hash, actor_id, "workspace.executor_policy.member_added",
           {"executor_id": executor_id, "executor_name": executor.name, "tier": tier})
    try:
        await db.commit()
    except IntegrityError:
        # Duas inclusões simultâneas do mesmo executor: a UNIQUE decide, e a
        # resposta é a mesma 422 do caminho sequencial — não um 500.
        await db.rollback()
        raise WorkspacePolicyError(
            f"'{executor.name}' já está na política deste workspace (um executor "
            "fica em um nível só)."
        )
    await _notify_executor(executor_id, "Workspace incluiu este executor na política.")
    return row


async def remove_member(
    db: AsyncSession, ws: Workspace, executor_id: str, *, actor_id: str | None,
) -> None:
    rows = await _rows_of(db, ws.id_hash)
    alvo = next((r for r in rows if r.executor_id == executor_id), None)
    if alvo is None:
        raise WorkspacePolicyError("Executor não está na política deste workspace.")

    await db.execute(
        delete(WorkspaceExecutor).where(WorkspaceExecutor.id == alvo.id)
    )
    # Nível 2 exige nível 1: esvaziar o principal apaga o fallback junto — e
    # o terminal volta a `fail`: "pool como último recurso" é uma escolha que
    # se faz COM um principal na mesa; sem ele, não pode sobreviver escondida
    # para reaparecer no próximo executor incluído sem confirmação.
    resto_primario = [r for r in rows if r.tier == TIER_PRIMARY and r.id != alvo.id]
    apagou_fallback = False
    if alvo.tier == TIER_PRIMARY and not resto_primario:
        await db.execute(
            delete(WorkspaceExecutor).where(
                WorkspaceExecutor.workspace_id == ws.id_hash,
                WorkspaceExecutor.tier == TIER_FALLBACK,
            )
        )
        apagou_fallback = any(r.tier == TIER_FALLBACK for r in rows)
        _reset_terminal(ws)
    _audit(db, ws.id_hash, actor_id, "workspace.executor_policy.member_removed",
           {"executor_id": executor_id, "tier": alvo.tier, "fallback_cleared": apagou_fallback})
    await db.commit()
    await _notify_executor(executor_id, "Workspace removeu este executor da política.")


async def replace_primary(
    db: AsyncSession, ws: Workspace, executor_id: str | None, *, actor_id: str | None,
) -> None:
    """Dual-write do endpoint LEGADO (`PUT /workspaces/{id}/executor`): o nível 1
    passa a ser {executor}; `None` limpa todos os níveis. Enquanto a flag de
    roteamento estiver `off`, é `target_executor_id` que vale — esta gravação só
    mantém os dois lados iguais para a virada não mudar nada."""
    rows = await _rows_of(db, ws.id_hash)
    executor = await _get_executor(db, executor_id) if executor_id else None
    if executor is None or executor.is_default:
        # `None`, executor apagado ou executor do POOL: nenhum nível faz
        # sentido. Apontar para um executor do pool é "quero o pool" — deixar
        # o nível 1 antigo de pé faria o roteamento por política ignorar a
        # escolha (e a tela mostrar o executor errado).
        if rows:
            await db.execute(
                delete(WorkspaceExecutor).where(WorkspaceExecutor.workspace_id == ws.id_hash)
            )
            _audit(db, ws.id_hash, actor_id, "workspace.executor_policy.cleared",
                   {"via": "legacy_endpoint", "target_executor_id": executor_id})
        _reset_terminal(ws)
        return
    primarios = [r for r in rows if r.tier == TIER_PRIMARY]
    if len(primarios) == 1 and primarios[0].executor_id == executor_id:
        return
    tinha_primario = bool(primarios)
    await db.execute(
        delete(WorkspaceExecutor).where(
            WorkspaceExecutor.workspace_id == ws.id_hash,
            WorkspaceExecutor.tier == TIER_PRIMARY,
        )
    )
    # Se o executor novo estava no fallback, sobe para o principal.
    await db.execute(
        delete(WorkspaceExecutor).where(
            WorkspaceExecutor.workspace_id == ws.id_hash,
            WorkspaceExecutor.executor_id == executor_id,
        )
    )
    db.add(WorkspaceExecutor(
        workspace_id=ws.id_hash, executor_id=executor_id, tier=TIER_PRIMARY, added_by=actor_id,
    ))
    terminal_ajustado = False
    if not tinha_primario and (ws.isolation_floor or FLOOR_NONE) != FLOOR_NO_POOL \
            and ws.fallback_terminal != TERMINAL_POOL:
        # Nível 1 nascendo pelo caminho LEGADO: hoje esse workspace transborda
        # para o pool quando o dedicado cai, e é isso que a política precisa
        # reproduzir na virada da flag (o mesmo que o backfill fez). Isolar é
        # decisão explícita, tomada no editor — não um efeito colateral do
        # seletor rápido.
        ws.fallback_terminal = TERMINAL_POOL
        terminal_ajustado = True
    _audit(db, ws.id_hash, actor_id, "workspace.executor_policy.primary_replaced",
           {"executor_id": executor_id, "via": "legacy_endpoint",
            "terminal_set_to_pool": terminal_ajustado})


# ── Escrita: terminal e piso ─────────────────────────────────────────────────

async def set_terminal(
    db: AsyncSession, ws: Workspace, terminal: str, *, actor_id: str | None,
) -> str:
    if terminal not in TERMINALS:
        raise WorkspacePolicyError("Terminal inválido: use 'fail' ou 'pool'.")
    if terminal == TERMINAL_POOL and (ws.isolation_floor or FLOOR_NONE) == FLOOR_NO_POOL:
        raise WorkspacePolicyFloorError(
            "O administrador da plataforma fixou este workspace como isolado: "
            "o fallback para o pool compartilhado não pode ser habilitado."
        )
    anterior = ws.fallback_terminal
    if anterior != terminal:
        ws.fallback_terminal = terminal
        _audit(db, ws.id_hash, actor_id, "workspace.executor_policy.terminal_changed",
               {"from": anterior, "to": terminal})
        await db.commit()
    return terminal


async def set_floor(
    db: AsyncSession, ws: Workspace, floor: str, *, actor_id: str | None,
) -> bool:
    """Só o admin da plataforma chama. Devolve True se o terminal foi forçado
    de 'pool' para 'fail' (o chamador avisa o dono)."""
    if floor not in FLOORS:
        raise WorkspacePolicyError("Piso inválido: use 'none' ou 'no_pool'.")
    anterior = ws.isolation_floor or FLOOR_NONE
    forcou = False
    if floor == FLOOR_NO_POOL and ws.fallback_terminal == TERMINAL_POOL:
        ws.fallback_terminal = TERMINAL_FAIL
        forcou = True
    if anterior != floor or forcou:
        ws.isolation_floor = floor
        _audit(db, ws.id_hash, actor_id, "workspace.executor_policy.floor_changed",
               {"from": anterior, "to": floor, "terminal_forced_to_fail": forcou})
        await db.commit()
    return forcou


# ── Cascatas: o executor some ou vira pool ───────────────────────────────────

async def workspaces_depending_on(db: AsyncSession, executor_id: str) -> list[dict]:
    """Workspaces que têm o executor em algum nível, com o tamanho do nível
    principal — é o que decide se removê-lo esvazia alguém."""
    result = await db.execute(
        select(WorkspaceExecutor, Workspace)
        .join(Workspace, Workspace.id_hash == WorkspaceExecutor.workspace_id)
        .where(WorkspaceExecutor.executor_id == executor_id, Workspace.deleted_at.is_(None))
    )
    pares = result.all()
    if not pares:
        return []
    ws_ids = [ws.id_hash for _, ws in pares]
    contagem = await db.execute(
        select(WorkspaceExecutor.workspace_id, WorkspaceExecutor.executor_id).where(
            WorkspaceExecutor.workspace_id.in_(ws_ids),
            WorkspaceExecutor.tier == TIER_PRIMARY,
        )
    )
    primarios: dict[str, int] = {}
    for ws_id, _ in contagem.all():
        primarios[ws_id] = primarios.get(ws_id, 0) + 1
    return [
        {
            "workspace_id": ws.id_hash,
            "workspace_name": ws.name,
            "owner_id": ws.owner_id,
            "tier": row.tier,
            "primary_count": primarios.get(ws.id_hash, 0),
            "would_empty_primary": row.tier == TIER_PRIMARY and primarios.get(ws.id_hash, 0) <= 1,
        }
        for row, ws in pares
    ]


async def detach_executor(
    db: AsyncSession, executor_id: str, *, force: bool, actor_id: str | None, reason: str,
) -> list[dict]:
    """Retira o executor de todos os níveis (revogação, remoção, promoção a
    default). Bloqueia (409) se esvaziaria o nível PRINCIPAL de algum workspace
    e `force` não foi pedido — um nível que esvazia em silêncio faz toda
    execução futura falhar ou transbordar sem ninguém saber (spec §4.4).

    NÃO faz commit: o chamador está no meio da própria transação."""
    deps = await workspaces_depending_on(db, executor_id)
    if not deps:
        # Nenhum workspace VIVO depende dele — mas linhas de workspaces na
        # lixeira podem existir, e um workspace restaurado depois não pode
        # voltar com um executor revogado no nível principal.
        await db.execute(delete(WorkspaceExecutor).where(WorkspaceExecutor.executor_id == executor_id))
        return []
    esvaziaria = [d for d in deps if d["would_empty_primary"]]
    if esvaziaria and not force:
        nomes = ", ".join(d["workspace_name"] for d in esvaziaria)
        raise WorkspacePolicyConflictError(
            f"Remover este executor esvaziaria o nível principal de: {nomes}. "
            "Adicione outro executor a esses workspaces ou repita com force=true.",
            workspaces=esvaziaria,
        )
    await db.execute(delete(WorkspaceExecutor).where(WorkspaceExecutor.executor_id == executor_id))
    # Esvaziou o principal de alguém: o fallback dele deixa de fazer sentido,
    # e o terminal volta a `fail` (mesma invariante de `remove_member`).
    for d in esvaziaria:
        await db.execute(
            delete(WorkspaceExecutor).where(
                WorkspaceExecutor.workspace_id == d["workspace_id"],
                WorkspaceExecutor.tier == TIER_FALLBACK,
            )
        )
        ws_esvaziado = (await db.execute(
            select(Workspace).where(Workspace.id_hash == d["workspace_id"])
        )).scalar_one_or_none()
        if ws_esvaziado is not None:
            _reset_terminal(ws_esvaziado)
    for d in deps:
        _audit(db, d["workspace_id"], actor_id, "workspace.executor_policy.member_detached",
               {"executor_id": executor_id, "tier": d["tier"], "reason": reason,
                "forced": bool(esvaziaria), "emptied_primary": d["would_empty_primary"]})
    return deps


# ── Quem depende de quem (ponteiro legado ∪ níveis) ──────────────────────────

async def workspace_ids_for_executor(db: AsyncSession, executor_id: str) -> set[str]:
    """Workspaces vivos servidos pelo executor: apontado pelo ponteiro legado
    OU membro de algum nível. É o conjunto que autoriza o executor no Drive,
    nos artefatos, no portal e no ChangeDetector — o roteamento por política
    manda jobs para membros de nível, e um job que roda sem essa autorização
    quebra na primeira leitura do Drive."""
    legado = await db.execute(
        select(Workspace.id_hash).where(
            Workspace.target_executor_id == executor_id,
            Workspace.deleted_at.is_(None),
        )
    )
    niveis = await db.execute(
        select(Workspace.id_hash)
        .join(WorkspaceExecutor, WorkspaceExecutor.workspace_id == Workspace.id_hash)
        .where(WorkspaceExecutor.executor_id == executor_id, Workspace.deleted_at.is_(None))
    )
    return set(legado.scalars().all()) | set(niveis.scalars().all())


async def executor_ids_for_workspaces(db: AsyncSession, workspace_ids: list[str] | set[str]) -> set[str]:
    """Executores que servem estes workspaces: ponteiros legados ∪ membros de nível."""
    ids = list(workspace_ids)
    if not ids:
        return set()
    legado = await db.execute(
        select(Workspace.target_executor_id).where(
            Workspace.id_hash.in_(ids), Workspace.target_executor_id.isnot(None),
        )
    )
    niveis = await db.execute(
        select(WorkspaceExecutor.executor_id).where(WorkspaceExecutor.workspace_id.in_(ids))
    )
    return set(legado.scalars().all()) | set(niveis.scalars().all())


# ── Helpers ──────────────────────────────────────────────────────────────────

def _reset_terminal(ws: Workspace) -> None:
    """Sem nível principal o terminal não tem o que decidir: volta ao padrão."""
    if getattr(ws, "fallback_terminal", None) != TERMINAL_FAIL:
        ws.fallback_terminal = TERMINAL_FAIL


def _audit(db: AsyncSession, workspace_id: str, user_id: str | None, action: str, details: dict) -> None:
    db.add(AuditEvent(
        workspace_id=workspace_id, user_id=user_id, action=action,
        resource_type="workspace", resource_id=workspace_id, details=details,
    ))


async def _notify_executor(executor_id: str, reason: str) -> None:
    """Mesmo aviso `config_changed` que o endpoint legado manda — best-effort."""
    try:
        from app.core.executor_connections import executor_registry
        await executor_registry.send_json(executor_id, {
            "type": "control", "action": "config_changed", "reason": reason,
        })
    except Exception as exc:  # pragma: no cover - rede
        logger.warning("Falha ao notificar executor '%s' (%s): %s", executor_id, reason, exc)
