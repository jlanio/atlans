# app/services/workflow_service.py
# Fachada que delega para serviços especializados, mantendo a interface pública original.

from app.core.utils.logger import get_logger

import copy
from datetime import datetime, timezone
from typing import Iterable, Optional
from uuid import uuid4

from fastapi import Request
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import REDIS_TTL_24H
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    CredentialAccessDeniedError,
    WorkflowDecryptionError,
    WorkflowInactiveError,
    WorkflowNameConflictError,
    WorkflowNotFoundError,
)
from app.core.scheduling.hooks import (
    apply_schedule_if_needed,
    disable_schedule_node,
    extract_schedule_node,
    sync_schedules_with_workflow_state,
)
from app.core.utils.encryption import decrypt_workflow_connections, encrypt_workflow_connections
from app.crud.workflow_crud import WorkflowCRUD
from app.models.models import Schedule, Workflow
from app.models.user import User
from app.schemas.workflow import WorkflowUpdate
from app.services.workflow_execution_service import (
    DispatchResult,
    _collect_credential_ids,
    _dispatch_job,
    _get_redis,
    _load_workflow,
    _resolve_candidates,
    _safe_pinned_outputs,
    _validate_trigger_credentials_only,
    _validate_trigger_inputs,
)
from app.core.authorization.credential_loader import (
    assert_credentials_accessible,
    resolve_credentials_from_ids,
)
from app.services.workflow_move_service import (
    _com_sufixo,
    move_workflow as _move_workflow,
    nome_livre as _nome_livre,
    nomes_no_workspace as _nomes_no_workspace,
)
from app.services.workflow_version_service import (
    _has_substantial_changes,
    list_versions as _ver_list_versions,
    restore_version as _ver_restore_version,
)

_logger = get_logger(__name__)


async def _cleanup_redis_pattern(pattern: str, contexto: str) -> int:
    """Remove do Redis todas as keys que casam com `pattern`.

    Idempotente — no-op se nenhuma key existir. Best-effort: falha no Redis
    apenas loga WARN e nao propaga (nao bloqueia o delete que a disparou).
    Retorna o numero de keys removidas.
    """
    removed = 0
    try:
        from app.core.redis import get_redis_pool
        rc = get_redis_pool()
        async for key in rc.scan_iter(match=pattern, count=200):
            await rc.delete(key)
            removed += 1
        if removed:
            _logger.info("ChangeDetector: %d key(s) removida(s) no %s", removed, contexto)
    except Exception as exc:
        _logger.warning(
            "ChangeDetector: falha ao limpar keys no %s (ignorando): %s",
            contexto, exc,
        )
    return removed


async def _cleanup_change_detector_keys(workflow_id_hash: str) -> int:
    """Remove keys `change_detector:wf:{workflow_hash}:*` do Redis."""
    return await _cleanup_redis_pattern(
        f"change_detector:wf:{workflow_id_hash}:*",
        f"delete do workflow {workflow_id_hash}",
    )


async def _cleanup_change_detector_ws_keys(workspace_id: str) -> int:
    """Remove keys `change_detector:ws:{workspace_id}:*` do Redis.

    Chamada no delete do workspace. As chaves de escopo workspace (shared_key)
    nao pertencem a workflow nenhum, entao o cleanup por workflow nao as
    alcanca — e com ttl_hours=0 elas viveriam para sempre. Um restore do
    workspace NAO devolve este estado: a primeira run apos o restore e
    "primeira execucao", aceitavel para um cache de deteccao de mudanca.
    """
    return await _cleanup_redis_pattern(
        f"change_detector:ws:{workspace_id}:*",
        f"delete do workspace {workspace_id}",
    )


async def soft_delete_workspace_workflows(
    db: AsyncSession, workspace_id: str, when: datetime,
) -> dict:
    """Soft-deleta os workflows de um workspace e desativa seus schedules.

    Chamada no DELETE do workspace. Sem isto os workflows continuavam ativos e
    invisiveis: a listagem e sempre por workspace acessivel, entao sumiam da UI,
    mas o AsyncScheduler seguia disparando seus schedules (o tick filtra apenas
    por Schedule.active, sem olhar workflow nem workspace). Rodando orfaos eles
    perdiam o executor dedicado do workspace — _resolve_candidates nao acha a
    linha e cai no pool default — e a allowlist de webhook, que vira lista vazia
    e deixa de ser aplicada.

    `when` e o mesmo timestamp gravado em Workspace.deleted_at: e ele que
    permite ao restore distinguir os workflows que cairam por causa do delete do
    workspace daqueles que ja estavam deletados antes.

    Nao commita — mas nao conte com isso para atomicidade: o chamador roda
    `schedule_workspace_data_expiry` logo depois, e ela commita por dentro (via
    purge_workspace_storage). Por isso o delete_workspace marca
    Workspace.deleted_at ANTES de chamar esta funcao, e nao depois.
    """
    from app.models.models import Schedule

    rows = (await db.execute(
        sa_select(Workflow.id_hash, Workflow.deleted_at).where(
            Workflow.workspace_id == workspace_id
        )
    )).all()

    all_ids = [r[0] for r in rows]
    if not all_ids:
        return {"workflows": 0, "schedules": 0}

    pending_ids = [r[0] for r in rows if r[1] is None]

    if pending_ids:
        await db.execute(
            Workflow.__table__.update()
            .where(Workflow.id_hash.in_(pending_ids))
            .values(deleted_at=when, flag_ative=False)
        )

    # Cobre todos os workflows do workspace, nao so os recem-deletados: um
    # schedule pode ter ficado ativo por caminhos anteriores a este cascade.
    sched_result = await db.execute(
        Schedule.__table__.update()
        .where(Schedule.workflow_hash.in_(all_ids), Schedule.active.is_(True))
        .values(active=False)
    )

    for wf_id in pending_ids:
        await _cleanup_change_detector_keys(wf_id)

    # Chaves de escopo workspace (ws:*) nao pertencem a workflow nenhum — sem
    # esta linha, um ChangeDetector com shared_key e ttl_hours=0 deixava
    # estado orfao no Redis para sempre apos o delete do workspace.
    await _cleanup_change_detector_ws_keys(workspace_id)

    return {"workflows": len(pending_ids), "schedules": sched_result.rowcount or 0}


async def restore_workspace_workflows(
    db: AsyncSession, workspace_id: str, when: datetime,
) -> int:
    """Desfaz o soft delete em cascata de um workspace restaurado.

    Restaura apenas os workflows cujo `deleted_at` bate exatamente com o do
    workspace — os que ja estavam deletados antes continuam deletados.

    Devolve os workflows DESATIVADOS (`flag_ative` continua False), pelo mesmo
    motivo que os schedules nao sao religados: o cascade zera `flag_ative` de
    todo mundo, entao nao ha como saber quem ja estava desativado de proposito
    antes do delete. Reativar em bloco ressuscitaria justamente o workflow que o
    dono tinha desligado — de bom grado, e sem avisar. O dono religa o que ainda
    fizer sentido.

    (`flag_ative` continua sendo a trava de execucao real: portal_router,
    webhook_router, schedule_service, drive_service e workflow_groups_router
    filtram por ele sem olhar `deleted_at`. Por isso o cascade precisa zera-lo,
    e por isso o restore nao pode devolve-lo no palpite.)

    Nao commita: o chamador fecha a transacao junto com o restore do workspace.
    """
    # O indice de nome e PARCIAL (so vale entre os vivos), entao um nome que
    # estava "guardado" por um workflow deste cascade pode ter sido reocupado
    # enquanto o workspace estava na lixeira. E estreito — workspace na lixeira
    # nao aparece em listagem —, mas o UPDATE em lote falharia INTEIRO e
    # derrubaria o restore do workspace junto. Renomear quem volta e melhor que
    # nao devolver nada.
    voltando = (await db.execute(
        sa_select(Workflow.id_hash, Workflow.name).where(
            Workflow.workspace_id == workspace_id,
            Workflow.deleted_at == when,
        )
    )).all()

    if voltando:
        ocupados = await _nomes_no_workspace(db, workspace_id)
        vistos = set()
        for id_hash, nome in voltando:
            livre = _nome_livre(nome, ocupados | vistos)
            vistos.add(livre)
            if livre != nome:
                _logger.warning(
                    "Restore do workspace %s: nome '%s' foi reocupado — o workflow %s volta como '%s'.",
                    workspace_id, nome, id_hash, livre,
                )
                await db.execute(
                    Workflow.__table__.update()
                    .where(Workflow.id_hash == id_hash)
                    .values(name=livre)
                )

    result = await db.execute(
        Workflow.__table__.update()
        .where(Workflow.workspace_id == workspace_id, Workflow.deleted_at == when)
        .values(deleted_at=None)
    )
    return result.rowcount or 0


# Retrocompatibilidade: re-exporta as exceções para que importadores existentes não quebrem.
__all__ = [
    "WorkflowService",
    "WorkflowNotFoundError",
    "WorkflowInactiveError",
    "WorkflowDecryptionError",
    "DispatchResult",
    "soft_delete_workspace_workflows",
    "restore_workspace_workflows",
    "_safe_pinned_outputs",
    "_has_substantial_changes",
    "_get_redis",
    "_validate_trigger_credentials_only",
]


# ── Mescla da listagem (agendamento e autoria) ───────────────────────────────
#
# A listagem de Projetos sai do CRUD como RowMapping (imutavel) com as colunas
# leves; o que vem de OUTRAS tabelas — o resumo do agendamento e os nomes de
# quem criou/alterou — e buscado aqui, em lote por pagina, e mesclado em dicts.
# Sao 3 queries por listagem, todas por indice; nunca uma por linha.
#
# Os helpers `_como_utc` e `_nomes_de_usuarios` sao gemeos dos de
# `app/services/observability/`. Ficam locais de proposito: importar aquele pacote
# so por duas funcoes de cinco linhas acoplaria a listagem de workflows ao
# servico de metricas inteiro (e ao seu tempo de import) sem ganho.

# Colunas do schedule que a lista mostra — `WorkflowScheduleSummary`.
_SCHEDULE_COLUMNS = (
    Schedule.workflow_hash,
    Schedule.active,
    Schedule.next_run_at,
    Schedule.last_run_at,
    Schedule.strategy,
    Schedule.cron_expression,
    Schedule.interval,
    Schedule.unit,
    Schedule.rrule_expression,
    Schedule.timezone,
)


def _como_utc(valor: Optional[datetime]) -> Optional[datetime]:
    """`next_run_at`/`last_run_at` sao gravados UTC NAIVE (ver `_to_utc_naive`
    no agendador). Sem o tzinfo, o Pydantic serializa sem offset e a web le a
    hora como local — "proxima 06:00" viraria "proxima 03:00" em Cuiaba."""
    if valor is None or valor.tzinfo is not None:
        return valor
    return valor.replace(tzinfo=timezone.utc)


def _ordem_de_preferencia(linha) -> tuple:
    """Quando um workflow tem mais de um schedule, a lista mostra um so: a
    ativa com a menor `next_run_at` (e a que vai disparar primeiro); ativa sem
    proxima calculada depois; sem nenhuma ativa, qualquer uma."""
    return (
        not linha.active,
        linha.next_run_at is None,
        linha.next_run_at or datetime.min,
    )


async def _resumos_de_agendamento(db: AsyncSession, hashes: Iterable[str]) -> dict[str, dict]:
    """Um resumo por workflow_hash, ja com os instantes em UTC aware."""
    hashes = [h for h in set(hashes) if isinstance(h, str)]
    if not hashes:
        return {}
    result = await db.execute(
        sa_select(*_SCHEDULE_COLUMNS).where(Schedule.workflow_hash.in_(hashes))
    )
    escolhido: dict[str, object] = {}
    for linha in result.all():
        atual = escolhido.get(linha.workflow_hash)
        if atual is None or _ordem_de_preferencia(linha) < _ordem_de_preferencia(atual):
            escolhido[linha.workflow_hash] = linha
    return {
        hash_: {
            "active": bool(linha.active),
            "next_run_at": _como_utc(linha.next_run_at),
            "last_run_at": _como_utc(linha.last_run_at),
            "strategy": linha.strategy,
            "cron_expression": linha.cron_expression,
            "interval": linha.interval,
            "unit": linha.unit,
            "rrule_expression": linha.rrule_expression,
            "timezone": linha.timezone,
        }
        for hash_, linha in escolhido.items()
    }


async def _nomes_de_usuarios(db: AsyncSession, user_ids: Iterable[Optional[str]]) -> dict[str, str]:
    """id_hash -> username. Id sem linha em `users` nao aparece no dict (a
    listagem devolve None e a web mostra so "alterado ha X"). Usuario excluido
    pelo admin e soft delete: a linha permanece, entao o nome continua saindo —
    a mesma atribuicao que o Historico mostra."""
    ids = [i for i in set(user_ids) if isinstance(i, str)]
    if not ids:
        return {}
    result = await db.execute(sa_select(User.id_hash, User.username).where(User.id_hash.in_(ids)))
    return {r.id_hash: r.username for r in result.all()}


async def _mesclar_listagem(db: AsyncSession, linhas) -> list[dict]:
    """Converte as linhas do CRUD em dicts e acrescenta `schedule`,
    `created_by_username` e `updated_by_username`."""
    itens = [dict(linha) for linha in linhas]
    if not itens:
        return itens
    agendamentos = await _resumos_de_agendamento(db, (i["id_hash"] for i in itens))
    nomes = await _nomes_de_usuarios(
        db, [i.get("created_by_id") for i in itens] + [i.get("updated_by_id") for i in itens],
    )
    for item in itens:
        item["schedule"] = agendamentos.get(item["id_hash"])
        item["created_by_username"] = nomes.get(item.get("created_by_id"))
        item["updated_by_username"] = nomes.get(item.get("updated_by_id"))
    return itens


_MENSAGEM_CREDENCIAL_ALHEIA = (
    "A definição referencia credencial que você não pode usar. "
    "Use uma credencial sua ou compartilhada com o workspace."
)


async def assert_credenciais_da_definicao(
    db: AsyncSession, definition: object, *, user_id: str, workspace_id: str | None,
) -> None:
    """Recusa gravar uma definition que referencie credencial que o autor não
    pode acessar (auditoria SEG-12 — confused deputy).

    Sem isto, um editor inseria num fluxo compartilhado um nó com o
    `credential_id` PRIVADO de outro membro e uma `url` dele; ao a vítima
    executar, o dispatch resolvia a credencial (triggered_by = vítima) e mandava
    o token ao servidor do atacante. Validamos TODOS os nós com `credential_id`
    (não só os novos): trocar a URL de um nó existente também escaparia.
    Credencial própria ou compartilhada com o workspace passa; a privada de
    outro membro, não.

    Mora no serviço, e não na borda, porque a borda eram duas: a REST checava e
    o MCP pulava com `validate_first=False`, ao duplicar e ao restaurar versão.
    As quatro escritas do `WorkflowService` a chamam contra o autor, que é
    OBRIGATÓRIO nelas (`created_by_id`, `updated_by_id`, `duplicated_by`,
    `restored_by`: keyword-only, sem default, e vazio é recusado por
    `_exigir_autor`) — o autor é quem precisa alcançar as credenciais. Quando o
    autor era opcional, um chamador que o esquecesse pulava a guarda calado.

    Levanta `CredentialAccessDeniedError` (403 no handler de domínio da REST,
    `forbidden` no MCP).
    """
    if not isinstance(definition, dict):
        return
    ids = _collect_credential_ids(definition)
    if not ids:
        return
    try:
        await assert_credentials_accessible(db, ids, user_id, shared_workspace_id=workspace_id)
    except CredentialAccessDeniedError as exc:
        raise CredentialAccessDeniedError(_MENSAGEM_CREDENCIAL_ALHEIA) from exc


def _exigir_autor(autor: object, parametro: str) -> str:
    """O autor de uma escrita: um id de usuário, nunca vazio.

    Os quatro parâmetros de autoria já são obrigatórios na assinatura; isto
    fecha o `None` explícito — um `getattr(user, "id_hash", None)` distraído —,
    que pularia a guarda do mesmo jeito que o argumento esquecido. Não existe
    hoje escrita de sistema sem usuário: a que vier terá de decidir contra
    quem a definition é conferida, e dizê-lo aqui, em vez de passar vazio.
    """
    if not isinstance(autor, str) or not autor:
        raise TypeError(
            f"Escrita de workflow sem autor (`{parametro}`): a guarda de credenciais "
            "(SEG-12) confere a definition contra quem grava."
        )
    return autor


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.crud = WorkflowCRUD(db)

    async def create_workflow(
        self, name: str, definition: dict, workspace_id: str | None = None, *,
        created_by_id: str, **extras,
    ):
        """`extras` são colunas adicionais do Workflow (description, params_schema…).

        Existe para a duplicação: a criação pela UI só manda nome e definition,
        mas copiar um workflow tem de levar junto o que define como ele se
        comporta — `params_schema`, por exemplo, é o que faz a tela pedir os
        parâmetros antes de executar.

        `created_by_id` é obrigatório: é contra ele que a guarda de credenciais
        (SEG-12) confere a definition.
        """
        autor = _exigir_autor(created_by_id, "created_by_id")

        # 0. Credenciais da definition ao alcance de quem grava (SEG-12). A
        #    duplicação passa por aqui com `created_by_id` = quem duplicou.
        await assert_credenciais_da_definicao(
            self.crud.db, definition, user_id=autor, workspace_id=workspace_id,
        )

        # 1. Criptografa dados sensíveis
        secure_definition = encrypt_workflow_connections(definition)

        # 2. Cria o workflow no banco (workspace_id vincula ao workspace ativo)
        kwargs = dict(extras, created_by_id=autor)
        if workspace_id:
            kwargs["workspace_id"] = workspace_id
        try:
            workflow = await self.crud.create(name, secure_definition, **kwargs)
        except IntegrityError as exc:
            await self.crud.db.rollback()
            if "uq_workflow_name_workspace" in str(exc.orig):
                # Cita o nome: a mensagem chega ao usuário como toast, longe do
                # campo, e "este nome" não diz qual quando quem escolheu o nome
                # foi o servidor (duplicação).
                raise WorkflowNameConflictError(
                    f"Já existe um workflow chamado '{name}' neste workspace."
                ) from exc
            raise

        # 3. Aplica agendamento, se houver ScheduleTrigger
        if extract_schedule_node(definition):
            try:
                await apply_schedule_if_needed(workflow, definition, self.crud.db)
            except Exception as exc:
                _logger.warning("Falha ao criar agendamento para workflow %s: %s", workflow.id_hash, exc)

        return workflow

    async def duplicate_workflow(
        self, id_hash: str, novo_nome: str | None = None, *, duplicated_by: str,
    ) -> Workflow:
        """Cria uma cópia do workflow no MESMO workspace.

        O que NÃO acompanha a cópia, e por quê:

        - `pinned_outputs`/`pin_metadata` apontam para artefatos de runs do
          workflow original; herdá-los faria a cópia servir dados que ela nunca
          produziu, sem nada na tela dizendo isso.
        - `portal_access` volta a "disabled": publicar uma cópia porque o
          original estava publicado expõe conteúdo sem ninguém ter pedido.
        - o histórico de versões começa vazio — as versões do original
          descrevem edições que não aconteceram nesta cópia.

        O agendamento acompanha, mas DESLIGADO: duplicar costuma preceder uma
        edição, e nascer disparando sozinho dobraria a carga e a escrita no
        Drive em silêncio. Desligar na própria definition (e não só no banco)
        mantém canvas e schedule coerentes — `apply_schedule_if_needed` lê o
        `active` do nó, então o que o usuário vê no canvas é o que vale.

        Fica no mesmo workspace de propósito: `credential_id` na definition só
        resolve para quem tem acesso ao workspace, e sub-workflows referenciados
        precisam viver nele. Copiar para outro workspace produziria um workflow
        que parece íntegro e falha ao executar.
        """
        autor = _exigir_autor(duplicated_by, "duplicated_by")
        original = await self.get_workflow_by_hash(id_hash)

        # Deep copy: `encrypt_workflow_connections` grava no dict recebido, e o
        # de `original.definition` é o objeto que o SQLAlchemy observa — mutá-lo
        # marcaria o workflow de origem como sujo.
        definition = copy.deepcopy(original.definition or {})

        disable_schedule_node(definition)

        nome_pedido = novo_nome.strip() if novo_nome and novo_nome.strip() else None

        # Tudo que vem do `original` é lido AGORA, enquanto a sessão está limpa.
        #
        # Uma colisão de nome faz `create_workflow` chamar `rollback()`, e o
        # rollback expira todo objeto da sessão — inclusive este `original`, que
        # nem participou da escrita. Ler qualquer atributo dele depois disso
        # dispara refresh lazy, e numa AsyncSession isso não é um SELECT extra:
        # é `MissingGreenlet`. A retentativa abaixo transformaria o 409 em 500 —
        # exatamente no caminho que existe para nunca falhar.
        nome_original = original.name
        workspace_id = original.workspace_id
        # O que define COMO o workflow se comporta acompanha a cópia.
        # `params_schema` em especial: é ele que faz a tela pedir os parâmetros
        # antes de executar (ver handleRunClick no front) — sem ele a cópia
        # dispararia direto, calada, com o schema vazio.
        herdado = dict(
            description=original.description,
            params_schema=original.params_schema,
            group_id=original.group_id,
            priority=original.priority,
            notification_url=original.notification_url,
            # A copia herda a proveniencia do original: duplicar um fluxo do
            # assistente sem isto criaria uma copia "usuario" que vaza para as
            # listagens que o assistente devia manter escondidas.
            origem=original.origem,
        )
        # Autoria da CÓPIA é de quem copiou, não do dono do original: a cópia é
        # um workflow novo, e é a pessoa que clicou quem responde por ele. Sem
        # isto a cópia nascia sem dono nenhum — `created_by_id` nulo —, e a tela
        # de Projetos, que mostra autoria, não tinha o que mostrar.
        #
        # A tool `duplicate_workflow` do MCP já carimbava (`app/mcp/tools/
        # acervo.py`); esta era a divergência registrada como dívida no #96.
        # `duplicated_by` é obrigatório: é também contra ele que
        # `create_workflow` confere as credenciais da cópia (SEG-12).
        herdado["created_by_id"] = autor
        herdado["updated_by_id"] = autor

        async def _criar(nome: str) -> Workflow:
            return await self.create_workflow(
                nome, definition, workspace_id=workspace_id, **herdado,
            )

        # Nome escolhido a dedo pelo usuário: colidir é resposta, não acidente.
        # Renomear por conta própria criaria "Meu Fluxo (2)" para quem digitou
        # "Meu Fluxo" — melhor devolver o 409 e deixar a pessoa decidir.
        if nome_pedido:
            return await _criar(nome_pedido)

        # Nome derivado: a promessa da duplicação é "clicou, copiou". Colisão
        # aqui é falha nossa, não escolha do usuário, então resolvemos sozinhos.
        #
        # `_nome_de_copia` consulta os nomes ocupados e o INSERT vem depois: a
        # janela entre os dois é real (duas duplicações simultâneas leem o mesmo
        # conjunto). O `move` já tratava isso — a duplicação não, e o 409 subia
        # até a tela. Ver workflow_move_service._aplicar.
        nome = await self._nome_de_copia(nome_original, workspace_id)
        try:
            return await _criar(nome)
        except WorkflowNameConflictError:
            # `create_workflow` já fez rollback. Recalcular é a primeira aposta:
            # a nova leitura enxerga o nome que causou a colisão e devolve o
            # próximo livre — "(2)" continua sendo melhor nome que um hex.
            _logger.warning(
                "Colisão de nome ao duplicar o workflow %s (nome '%s'); recalculando.",
                id_hash, nome,
            )
            nome = await self._nome_de_copia(nome_original, workspace_id)
            try:
                return await _criar(nome)
            except WorkflowNameConflictError as exc:
                # Colidir duas vezes seguidas indica corrida persistente. O
                # sufixo aleatório não disputa com ninguém.
                nome = _com_sufixo(f"Cópia de {nome_original}", uuid4().hex[:6])
                _logger.warning(
                    "Segunda colisão ao duplicar o workflow %s; usando sufixo único '%s'.",
                    id_hash, nome,
                )
                try:
                    return await _criar(nome)
                except WorkflowNameConflictError:
                    raise WorkflowNameConflictError(
                        "Não foi possível encontrar um nome livre para a cópia neste workspace."
                    ) from exc

    async def move_workflow(
        self,
        id_hash: str,
        target_workspace_id: str,
        *,
        new_name: str | None = None,
        moved_by_id: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Move o workflow para outro workspace (ver workflow_move_service).

        A autorização — admin/owner nos DOIS workspaces — fica no router, que é
        quem tem a identidade do requisitante.
        """
        return await _move_workflow(
            self.crud, id_hash, target_workspace_id,
            new_name=new_name, moved_by_id=moved_by_id, dry_run=dry_run,
        )

    async def _nome_de_copia(self, nome_base: str, workspace_id: str | None) -> str:
        """"Cópia de X", "Cópia de X (2)", ... — o primeiro livre no workspace.

        Existe UniqueConstraint(name, workspace_id): sem desambiguar, duplicar
        duas vezes o mesmo workflow devolvia 409 e o usuário tinha de inventar
        um nome antes de ver a cópia.
        """
        # Mesma consulta e mesma busca de nome livre usadas pelo move — só muda
        # a base. Duplicar o critério faria duplicar e mover divergirem quando o
        # escopo de "nome ocupado" mudar (soft-delete, workflows inativos…).
        existentes = await _nomes_no_workspace(self.crud.db, workspace_id)
        return _nome_livre(f"Cópia de {nome_base}", existentes)

    async def get_workflow_by_hash(self, id_hash: str) -> Workflow:
        wf = await self.crud.get_by_hash(id_hash)
        if not wf:
            raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

        # Descriptografa a definition (caso contenha connectionString criptografada)
        if wf.definition:
            try:
                wf.definition = decrypt_workflow_connections(wf.definition)
            except Exception as e:
                _logger.error("Falha ao descriptografar definition do workflow %s: %s", id_hash, e)
                raise WorkflowDecryptionError(
                    f"Não foi possível descriptografar a definição do workflow {id_hash}."
                ) from e

        return wf

    async def start_analysis(
        self,
        id_hash: str,
        inputs: dict = None,
        request: Request = None,
        debug_mode: bool = False,
        idempotency_key: str | None = None,
        autenticar_entrada: bool = True,
        workflow: Workflow | None = None,
        triggered_by: str | None = None,
        trigger_source: str = "manual",
        schedule_id: int | None = None,
    ) -> DispatchResult:
        """Despacha uma execução.

        `autenticar_entrada` diz se o token do gatilho de webhook deve
        autenticar ESTA chamada. O padrão é `True` de propósito: um chamador
        novo que esqueça o parâmetro passa a exigir o token (o comportamento de
        sempre), em vez de abrir o endpoint público sem autenticação. Os
        caminhos já autenticados por sessão ou pelo agendador passam `False`.

        `workflow` é o objeto que o chamador já carregou — ver `_load_workflow`.
        Os disparos HTTP passam o que a dependency de autorização acabou de
        buscar; o agendador, que só tem o hash, deixa em None.

        `triggered_by` é o id_hash de QUEM disparou (nas rotas HTTP autenticadas).
        É a dimensão de dono do escopo de credenciais (ver passo 5): só as
        credenciais dessa pessoa — ou as compartilhadas com o workspace do
        workflow — são resolvidas. Cron/webhook não têm usuário e deixam None,
        alcançando apenas as compartilhadas.

        `trigger_source` e `schedule_id` são só rótulo do run
        (docs/specs/metrics-history.md §2): "manual" | "retry" | "webhook"
        | "schedule" | "mcp". Não entram em nenhuma decisão de despacho — existem para
        o Histórico distinguir "agendado às 03:00" de "manual · fulano". O
        default "manual" mantém os chamadores antigos funcionando.
        """
        # ── 1. Idempotência ───────────────────────────────────────────────
        # A chave é por USUÁRIO e por WORKFLOW: antes era global à instalação,
        # e dois usuários mandando `Idempotency-Key: 1` recebiam o task_id um do
        # outro (cross-tenant). Chamadores sem usuário (cron/webhook não passam
        # chave hoje) caem em "-". Chaves antigas no Redis ficam órfãs por até
        # 24 h — inofensivo.
        cache_key: str | None = None
        if idempotency_key:
            cache_key = f"idempotency:wf_execute:{triggered_by or '-'}:{id_hash}:{idempotency_key}"
            _redis = _get_redis()
            existing = await _redis.get(cache_key)
            if existing:
                return DispatchResult(id=existing)

        # ── 2. Carregar e descriptografar ─────────────────────────────────
        wf, definition = await self._load_workflow(id_hash, request, workflow=workflow)

        # ── 2a. Validar inputs contra payload_schema dos triggers ────────
        _validate_trigger_inputs(definition, inputs)

        # ── 2b. Bloquear se workflow usa nodes desabilitados pelo admin ───
        from app.services.disabled_nodes_service import disabled_names
        from app.services.workflow_execution_service import (
            _validate_no_disabled_nodes,
        )
        from flow.utils.workflow_contract import (
            collect_subworkflow_definitions_recursive,
        )

        disabled_now = await disabled_names(self.crud.db)
        _validate_no_disabled_nodes(definition, disabled_now)

        # ── 3. Resolver executores candidatos (fail-fast) ─────────────────
        # Adiantado de propósito: é a ÚNICA verificação daqui em diante que
        # pode abortar tudo com 503, e ficava por ÚLTIMA. Sem executor online,
        # o servidor colecionava sub-fluxos e descriptografava credenciais —
        # vários round-trips ao banco e dezenas de milissegundos de CPU — só
        # para jogar fora. Continua DEPOIS da checagem de nodes desabilitados
        # para não trocar a precedência das mensagens de erro: aquela checagem
        # agora sai do cache e não custa round-trip nenhum.
        #
        # SEG: só é adiantado quando quem chamou JÁ está autenticado — execute,
        # retry e cron passam `autenticar_entrada=False`. Quem autentica o
        # chamador de um webhook protegido é o passo 5 (o token do
        # WebhookTrigger); antecipar o 503 também nesse caminho fazia um
        # chamador ANÔNIMO receber "Nenhum executor disponível (pool padrão
        # vazio ou todos offline)" antes de qualquer 401/403 — um oráculo sobre
        # a frota de execução do tenant, que ainda deixava distinguir "infra
        # fora do ar" de "meu token está errado" sem apresentar credencial
        # nenhuma. Para o webhook o fail-fast roda logo APÓS a validação do
        # token, antes do despacho.
        candidates = None
        if not autenticar_entrada:
            candidates = await self._resolve_candidates(wf)

        # ── 4. Pre-resolver a cadeia de sub-workflows ─────────────────────
        # Vai no envelope: o executor nao tem acesso ao DB do servidor.
        subworkflow_defs = await collect_subworkflow_definitions_recursive(
            definition, self.crud.db, workspace_id=wf.workspace_id,
        )

        # ── 5. Resolver credenciais UMA VEZ (usado por validate + inject) ─
        # O escopo e o workspace do workflow: so credenciais de quem tem acesso
        # a ele sao resolvidas. Sem isso, um credential_id copiado da definition
        # (texto puro, legivel por qualquer membro) funcionava em QUALQUER
        # workflow, de qualquer workspace. Vale para todos os disparos —
        # inclusive cron e webhook, que nao tem usuario identificado.
        # Inclui a cadeia de sub-fluxos: as credenciais deles vao no mesmo
        # envelope e sao resolvidas com o MESMO escopo de workspace — o coletor
        # acima ja descarta sub-fluxos de outros workspaces.
        all_cred_ids = _collect_credential_ids(definition, *subworkflow_defs.values())
        pre_resolved: dict = {}
        if all_cred_ids:
            if not wf.workspace_id:
                raise CredentialAccessDeniedError(
                    f"Workflow '{id_hash}' usa credenciais mas não tem workspace — "
                    "não há como autorizar o acesso a elas."
                )
            # Escopo D: resolvem-se só as credenciais DE QUEM DISPAROU
            # (triggered_by) OU explicitamente compartilhadas com o workspace do
            # workflow. Ser apenas MEMBRO do workspace não basta — senão um
            # membro usaria a credencial PRIVADA de outro só copiando o
            # credential_id (texto puro na definition). Disparo sem usuário
            # (cron/webhook) tem triggered_by=None e alcança apenas as
            # compartilhadas; se um trigger exigir credencial privada, o
            # _validate_trigger_credentials_only abaixo devolve 403 claro.
            pre_resolved = await resolve_credentials_from_ids(
                all_cred_ids,
                allowed_owner_ids={triggered_by} if triggered_by else set(),
                shared_workspace_id=wf.workspace_id,
                # A sessão do request vai junto: sem ela o resolver abria uma
                # SEGUNDA conexão do mesmo pool sem soltar a primeira, e sob
                # concorrência o dispatch travava no pool_timeout.
                db=self.crud.db,
            )
        await _validate_trigger_credentials_only(
            definition, request=request, pre_resolved=pre_resolved,
            autenticar_entrada=autenticar_entrada,
        )

        # ── 5b. Fail-fast do webhook (ver passo 3) ────────────────────────
        # O chamador já se identificou: a partir daqui o 503 não vaza nada que
        # ele não pudesse descobrir disparando o fluxo.
        if candidates is None:
            candidates = await self._resolve_candidates(wf)

        # ── 6. Despachar job ──────────────────────────────────────────────
        # disabled_nodes e subworkflow_definitions vao no envelope para o
        # executor validar/resolver sub-fluxos sem consultar o DB do servidor.
        result = await self._dispatch_job(
            wf, definition, candidates, inputs, debug_mode,
            pre_resolved=pre_resolved,
            disabled_nodes=sorted(disabled_now),
            subworkflow_definitions=subworkflow_defs,
            trigger_source=trigger_source,
            triggered_by=triggered_by,
            schedule_id=schedule_id,
        )

        # ── 7. Registrar idempotência (TTL: 24h) ─────────────────────────
        if cache_key:
            try:
                _redis = _get_redis()
                await _redis.set(cache_key, result.id, ex=REDIS_TTL_24H)
            except Exception as exc:
                _logger.warning("Falha ao registrar chave de idempotência no Redis: %s", exc)

        return result

    # Wrappers que delegam para as funções do módulo workflow_execution_service.
    # Existem como métodos para que testes possam substituí-los via
    # `service._load_workflow = AsyncMock(...)` e patches por instância.
    async def _load_workflow(
        self, id_hash: str, request: Request | None = None,
        *, workflow: Workflow | None = None,
    ):
        return await _load_workflow(self.crud, id_hash, request, workflow)

    async def _resolve_candidates(self, wf: Workflow):
        return await _resolve_candidates(self.crud.db, wf)

    async def _dispatch_job(
        self,
        wf: Workflow,
        definition: dict,
        candidates: list,
        inputs: dict | None,
        debug_mode: bool,
        *,
        pre_resolved: dict | None = None,
        disabled_nodes: list[str] | None = None,
        subworkflow_definitions: dict | None = None,
        trigger_source: str | None = None,
        triggered_by: str | None = None,
        schedule_id: int | None = None,
    ) -> DispatchResult:
        return await _dispatch_job(
            wf, definition, candidates, inputs, debug_mode,
            db=self.crud.db,
            pre_resolved=pre_resolved,
            disabled_nodes=disabled_nodes,
            subworkflow_definitions=subworkflow_definitions,
            trigger_source=trigger_source,
            triggered_by=triggered_by,
            schedule_id=schedule_id,
        )

    async def list_workflows_metadata(
        self, workspace_id: str | None = None, *, incluir_do_assistente: bool = False,
    ) -> list[dict]:
        """Listagem leve — metadados sem definition, mais o resumo do
        agendamento e os nomes de autoria (ver `_mesclar_listagem`).

        `incluir_do_assistente` repassa o interruptor da tela: por padrao os
        fluxos do assistente ficam de fora."""
        linhas = await self.crud.get_all_metadata(
            workspace_id=workspace_id, incluir_do_assistente=incluir_do_assistente,
        )
        return await _mesclar_listagem(self.crud.db, linhas)

    async def list_workflows_metadata_by_ids(
        self, workspace_ids: list[str], *, incluir_do_assistente: bool = False,
    ) -> list[dict]:
        """Listagem leve por workspace IDs — mesma mescla de `list_workflows_metadata`."""
        linhas = await self.crud.get_all_metadata_by_workspace_ids(
            workspace_ids, incluir_do_assistente=incluir_do_assistente,
        )
        return await _mesclar_listagem(self.crud.db, linhas)

    async def delete_workflow(self, id_hash: str) -> None:
        """Soft delete: desativa o workflow e seus schedules associados."""
        from app.models.models import Schedule

        wf = await self.crud.soft_delete_by_hash(id_hash)
        if not wf:
            raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

        # Desativa schedules vinculados para não disparar execuções
        result = await self.crud.db.execute(
            sa_select(Schedule).where(Schedule.workflow_hash == id_hash)
        )
        for sched in result.scalars().all():
            sched.active = False
        await self.crud.db.commit()

        # Limpa estado de ChangeDetector — workflow nao executa mais. Se for
        # restaurado, a primeira run sera "Mudou" (seguro). Best-effort: falha
        # no Redis nao bloqueia o delete.
        await _cleanup_change_detector_keys(id_hash)

        return wf

    async def update_workflow(
        self,
        id_hash: str,
        workflow_in: WorkflowUpdate,
        change_note: str | None = None,
        *,
        updated_by_id: str,
    ) -> Workflow:
        autor = _exigir_autor(updated_by_id, "updated_by_id")

        # 1. Garante que o workflow existe — usa get_by_hash (sem decrypt) para não
        #    marcar definition como dirty na sessão SQLAlchemy e evitar que o commit
        #    subsequente salve a definition descriptografada no banco.
        wf = await self.crud.get_by_hash(id_hash)
        if not wf:
            raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

        # 2. Extrai apenas os campos do payload
        updates: dict = workflow_in.model_dump(exclude_unset=True)
        flag_ative_anterior = bool(wf.flag_ative)

        # 2a. Autoria vem da identidade autenticada, nunca do corpo — `WorkflowUpdate`
        #     não expõe mais `updated_by_id` justamente para que o cliente não possa
        #     forjar quem editou.
        updates["updated_by_id"] = autor

        # 2b. Credenciais da nova definition ao alcance de quem edita (SEG-12),
        #     antes de qualquer escrita — inclusive do snapshot abaixo.
        if "definition" in updates:
            await assert_credenciais_da_definicao(
                self.crud.db, updates["definition"],
                user_id=autor, workspace_id=wf.workspace_id,
            )

        # 3. Se a definition vai mudar e houve mudanças substanciais, cria snapshot
        if "definition" in updates:
            # A CÓPIA não é zelo: `decrypt_workflow_connections` MUTA o dict que
            # recebe e devolve o mesmo objeto. Decifrando `wf.definition` direto,
            # ele saía daqui em texto claro e o snapshot logo abaixo gravava a
            # credencial legível em `workflow_versions` — um histórico que
            # ninguém mais reescreve.
            old_def = decrypt_workflow_connections(copy.deepcopy(wf.definition))
            if _has_substantial_changes(old_def, workflow_in.definition):
                # E o `get_by_hash` do passo 1 NÃO basta para o snapshot sair
                # cifrado. A dependency da rota (`get_accessible_workflow_with_role`)
                # já chamou `get_workflow_by_hash`, que faz
                # `wf.definition = decrypt_workflow_connections(...)` — mutação in
                # place na linha viva. Como a sessão é a mesma, `get_by_hash`
                # devolve o MESMO objeto Python, já em claro, e copiá-lo só
                # duplica o texto claro. Cifrar explicitamente é o que fecha:
                # `encrypt_workflow_connections` é idempotente (pula o que já
                # começa com `gAAAA`), então cobre os dois estados possíveis da
                # sessão. Mesmo remédio, e pelo mesmo motivo, de
                # `workflow_move_service._aplicar`.
                #
                # Esta chamada fica FORA do `try/except IntegrityError` logo
                # abaixo, e isso é deliberado — mas engana quem lê depressa.
                # `create_version` só faz `flush()`, então o INSERT sai aqui, e
                # uma colisão de `version_number` estouraria vinte linhas antes
                # do `try`. O `except` de baixo é do conflito de NOME, que vem do
                # `crud.update`.
                #
                # Não há vazamento porque quem trata a colisão de versão é o
                # próprio `create_version`, na origem: savepoint e reconvergência.
                # Se alguém algum dia tirar aquele tratamento, o buraco reabre
                # AQUI — como um 500 que perde o save do usuário —, e não no
                # `except` abaixo, que não tem como alcançá-lo.
                await self.crud.create_version(
                    workflow_hash=id_hash,
                    definition=encrypt_workflow_connections(copy.deepcopy(wf.definition or {})),
                    change_note=change_note,
                )
            updates["definition"] = encrypt_workflow_connections(updates["definition"])

        # 4. Aplica updates no banco
        #
        # O nome sai do objeto ANTES do commit: `crud.update` faz setattr e
        # commita, e o `rollback()` do except expira toda a sessão. Ler
        # `wf.name` depois dispara refresh lazy — que numa AsyncSession não é
        # um SELECT a mais, é `MissingGreenlet`, ou seja, o 409 desta mensagem
        # viraria 500 justamente no caminho de erro.
        nome_tentado = updates.get("name") or wf.name
        try:
            wf = await self.crud.update(wf, updates)
        except IntegrityError as exc:
            await self.crud.db.rollback()
            if "uq_workflow_name_workspace" in str(exc.orig):
                raise WorkflowNameConflictError(
                    f"Já existe um workflow chamado '{nome_tentado}' neste workspace."
                ) from exc
            raise

        # 5. Sincroniza agendamentos sempre que a definição muda — a função
        # apply_schedule_if_needed remove schedules antigos e só cria novo se
        # houver ScheduleTrigger. Sem este sync incondicional, remover o
        # ScheduleTrigger do workflow deixava o Schedule antigo ativo no banco
        # e o async_scheduler continuava disparando o workflow em loop.
        schedule_notices = []
        if "definition" in updates:
            try:
                schedule_notices = await apply_schedule_if_needed(wf, workflow_in.definition, self.crud.db)
            except Exception as exc:
                _logger.warning("Falha ao sincronizar agendamento para workflow %s: %s", wf.id_hash, exc)

        # 6. O switch "Ativado/Inativo" da lista de projetos manda `flag_ative`
        # SOZINHO — sem definition, o passo 5 nem roda. Desativar o workflow
        # deixava o Schedule ativo apontando para ele, e o AsyncScheduler
        # tentava disparar a cada ocorrência do cron até alguém ler o log.
        # Roda depois do passo 5 de propósito: `apply_schedule_if_needed` sai
        # cedo quando o workflow está desativado (preserva a config antiga), e é
        # este sync que dá a palavra final sobre `active`.
        if bool(wf.flag_ative) != flag_ative_anterior:
            try:
                await sync_schedules_with_workflow_state(wf, self.crud.db)
            except Exception as exc:
                _logger.warning(
                    "Falha ao sincronizar agendamento com flag_ative do workflow %s: %s",
                    wf.id_hash, exc,
                )

        # Avisos do agendamento viajam na resposta como atributo transiente
        # (não é coluna): `WorkflowRead.schedule_notices` os lê e o editor os
        # transforma em toast. Setado sempre — vazio no caso normal.
        wf.schedule_notices = schedule_notices
        return wf

    async def list_versions(self, id_hash: str):
        return await _ver_list_versions(self.crud, id_hash)

    async def restore_version(
        self, id_hash: str, version_number: int, *, restored_by: str,
    ) -> Workflow:
        """Restaura a versão. Antes confere as credenciais da versão contra
        `restored_by` (SEG-12): restaurar não pode reintroduzir uma credencial
        que quem restaura não acessa. Versão inexistente levanta
        `WorkflowNotFoundError` já aqui — o erro não é engolido para "pular" a
        guarda."""
        autor = _exigir_autor(restored_by, "restored_by")

        # A versão CRUA, sem decifrar: `credential_id` não é cifrado, e abrir o
        # blob faria uma versão com `connectionString` que não decifra mais
        # (chave rotacionada) falhar aqui — a restauração em si só copia o
        # blob, sem abri-lo.
        versao = await self.crud.get_version(id_hash, version_number)
        if not versao:
            raise WorkflowNotFoundError(
                f"Versão {version_number} do workflow {id_hash} não encontrada"
            )
        wf = await self.crud.get_by_hash(id_hash)
        await assert_credenciais_da_definicao(
            self.crud.db, versao.definition,
            user_id=autor, workspace_id=wf.workspace_id if wf else None,
        )
        return await _ver_restore_version(self.crud, id_hash, version_number)
