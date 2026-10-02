# app/services/workflow_move_service.py
"""Movimentação de um workflow entre workspaces.

A troca de tenant não passa pelo `PUT /workflows/{id}`: `WorkflowUpdate` exclui
`workspace_id` de propósito, porque lá a autorização é resolvida contra o
workspace ANTERIOR à mudança — quem edita o próprio workflow poderia empurrá-lo
para dentro de um workspace alheio. Esta é a rota própria que aquele comentário
pede, e ela exige papel de admin/owner nos DOIS lados (ver o router).

O move nunca falha por dependência quebrada: o que deixa de funcionar no destino
sai como aviso (`workflow_move_report`). Em compensação, o que é consequência
determinística da troca de tenant é aplicado aqui, sem perguntar — agendamento
desligado, portal desativado, grupo e pins limpos.
"""

import copy
from uuid import uuid4

from sqlalchemy import select as sa_select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    WorkflowMoveTargetError,
    WorkflowNameConflictError,
    WorkflowNotFoundError,
)
from app.core.scheduling.hooks import disable_schedule_node
from app.core.utils.encryption import decrypt_workflow_connections, encrypt_workflow_connections
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.models import Schedule, Workflow
from app.services.workflow_move_report import collect_warnings, warn

_logger = get_logger(__name__)


async def nomes_no_workspace(db, workspace_id: str) -> set[str]:
    """Nomes já ocupados no workspace. Compartilhado com a duplicação."""
    return {
        n for (n,) in (
            await db.execute(
                sa_select(Workflow.name).where(
                    Workflow.workspace_id == workspace_id,
                    Workflow.deleted_at.is_(None),
                )
            )
        ).all()
    }


# `workflows.name` é String(255). Um sufixo de desambiguação sobre um nome já no
# limite estouraria a coluna, e DataError não é IntegrityError — escaparia do
# retry como 500, justamente na operação que promete não falhar.
_MAX_NOME = 255


def _com_sufixo(base: str, sufixo: str) -> str:
    """`base (sufixo)`, encurtando a base se o resultado passar de 255 chars."""
    excedente = len(base) + len(sufixo) + 3 - _MAX_NOME
    if excedente > 0:
        base = base[: max(1, len(base) - excedente)]
    return f"{base} ({sufixo})"


def nome_livre(base: str, existentes: set[str]) -> str:
    """Primeiro nome livre a partir de `base`: "X", "X (2)", "X (3)"…

    Existe UniqueConstraint(name, workspace_id): sem desambiguar, mover para um
    workspace que já tem um workflow homônimo estouraria IntegrityError — e o
    contrato deste recurso é que a movimentação não falha por isso.

    O teto e o sufixo aleatório repetem o que `_nome_de_copia` já faz na
    duplicação: é preferível um nome feio a um 409 na cara do usuário.
    """
    base = base[:_MAX_NOME]
    if base not in existentes:
        return base
    for i in range(2, 100):
        tentativa = _com_sufixo(base, str(i))
        if tentativa not in existentes:
            return tentativa
    return _com_sufixo(base, uuid4().hex[:6])


async def move_workflow(
    crud,
    id_hash: str,
    target_workspace_id: str,
    *,
    new_name: str | None = None,
    moved_by_id: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Move o workflow para `target_workspace_id` e devolve o relatório.

    Com `dry_run=True` nada é gravado — serve ao preview que o diálogo mostra
    antes de confirmar.

    ATENÇÃO À DEFINITION: `decrypt_workflow_connections` muta o dict in place, e
    a dependency da rota (`get_accessible_workflow_with_role`) já chamou
    `get_workflow_by_hash`, que descriptografa. Como a sessão é a mesma, o objeto
    do identity map pode chegar aqui COM a connectionString em texto puro. Hoje
    isso não vaza porque ninguém reescreve a coluna; este método reescreve. Por
    isso toda gravação passa por `encrypt_workflow_connections`, que é
    idempotente — trocar `get_workflow_by_hash` por `get_by_hash` não basta.
    """
    db = crud.db

    wf = await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")

    origin_ws = wf.workspace_id
    if target_workspace_id == origin_ws:
        # Invariante da operação, não validação de payload: mover para o próprio
        # workspace não seria um no-op — geraria versão, desligaria o
        # agendamento, apagaria pins e desativaria o portal. Fica aqui para que
        # qualquer chamador (rota, limpeza em lote, script) herde a guarda.
        raise WorkflowMoveTargetError("O workflow já está neste workspace.")

    # deepcopy ANTES de descriptografar: a análise não pode tocar o objeto do ORM.
    definition_clara = decrypt_workflow_connections(copy.deepcopy(wf.definition or {}))

    warnings = await collect_warnings(db, wf, definition_clara, origin_ws, target_workspace_id)

    nome_desejado = (new_name or "").strip() or wf.name
    existentes = await nomes_no_workspace(db, target_workspace_id)
    nome_final = nome_livre(nome_desejado, existentes)
    renamed = nome_final != wf.name
    if nome_final != nome_desejado:
        warnings.insert(0, warn(
            "name_conflict",
            f"Já havia um workflow chamado '{nome_desejado}' no destino; "
            f"este foi renomeado para '{nome_final}'.",
            severity="info",
            requested_name=nome_desejado, final_name=nome_final,
        ))

    resultado = {
        "id": wf.id_hash,
        "name": nome_final,
        "renamed": renamed,
        "from_workspace_id": origin_ws,
        "to_workspace_id": target_workspace_id,
        "dry_run": dry_run,
        "warnings": warnings,
    }

    if dry_run:
        return resultado

    # Desligar o agendamento na definition. Vai junto na mesma transação do
    # UPDATE em `schedules`, abaixo. `definition_clara` já é uma cópia privada
    # (nada mais a lê depois daqui), então a mutação in place é segura.
    disable_schedule_node(definition_clara)

    # `definition` cifrada uma vez só: `encrypt_workflow_connections` muta o dict
    # que recebe, e reaproveitar o resultado evita depender de idempotência entre
    # as duas tentativas.
    definition_cifrada = encrypt_workflow_connections(definition_clara)
    # Snapshot do estado ANTERIOR. O explícito não é redundante: pelo motivo da
    # docstring, `wf.definition` pode estar em claro na sessão, e
    # workflow_versions é tabela persistida como outra qualquer.
    snapshot = encrypt_workflow_connections(copy.deepcopy(wf.definition or {}))
    pins_para_apagar = _pin_keys(wf.pinned_outputs)

    async def _aplicar(nome: str) -> None:
        """Escreve tudo o que compõe o move. Reexecutável após um rollback.

        `create_version` faz apenas `flush`, e o UPDATE em `schedules` é DML na
        mesma transação — um rollback desfaz os dois junto com a troca de
        workspace. Por isso a tentativa de retry precisa repetir o bloco inteiro,
        e não só renomear: senão o workflow acabaria movido sem snapshot de
        versão e, pior, com o agendamento ainda ativo apontando para o novo
        workspace.
        """
        await crud.create_version(
            workflow_hash=id_hash,
            definition=copy.deepcopy(snapshot),
            change_note=f"Movido do workspace {origin_ws} para {target_workspace_id}",
        )

        # UPDATE direto na tabela em vez de `apply_schedule_if_needed`: o
        # ScheduleCRUD commita por dentro (quebraria a transação), a função pode
        # deletar e recriar o schedule, e `create_schedule` recusa workflow
        # desativado. Desligar nos dois lugares é obrigatório — o AsyncScheduler
        # tica sobre `Schedule.active` no banco, e o canvas lê o `active` do nó.
        await db.execute(
            Schedule.__table__.update()
            .where(Schedule.workflow_hash == id_hash)
            .values(active=False, workspace_id=target_workspace_id)
        )

        # As linhas de artefato do pin acompanham os objetos que serão apagados:
        # ficariam como downloads mortos para os membros da origem, e
        # `_upsert_pin_artifact` (que busca por workflow_hash + node_id, sem
        # filtrar tenant) reaproveitaria a linha num futuro pin no destino,
        # repontando-a para um objeto de lá sem trocar o `workspace_id`.
        await db.execute(
            Artifact.__table__.delete().where(
                Artifact.workflow_hash == id_hash,
                Artifact.is_pinned.is_(True),
            )
        )

        alvo = await crud.get_by_hash(id_hash)
        alvo.workspace_id = target_workspace_id
        alvo.name = nome
        alvo.group_id = None                # o grupo pertence ao workspace de origem
        alvo.portal_access = "disabled"     # portal_shared_with lista o tenant antigo
        alvo.portal_shared_with = None
        alvo.pinned_outputs = None          # apontam para pin-cache/{ws_origem}/…
        alvo.pin_metadata = None
        alvo.definition = copy.deepcopy(definition_cifrada)
        if moved_by_id:
            alvo.updated_by_id = moved_by_id
        await db.commit()

    try:
        await _aplicar(nome_final)
    except IntegrityError as exc:
        await db.rollback()
        if "uq_workflow_name_workspace" not in str(exc.orig):
            raise
        # Corrida real: alguém criou um workflow com este nome no destino entre a
        # checagem e o commit. Uma segunda tentativa com sufixo aleatório resolve
        # sem devolver 409 para uma operação que prometeu não falhar.
        _logger.warning(
            "Colisão de nome ao mover o workflow %s para %s; tentando sufixo único.",
            id_hash, target_workspace_id,
        )
        nome_final = _com_sufixo(nome_desejado[:_MAX_NOME], uuid4().hex[:6])
        try:
            await _aplicar(nome_final)
        except IntegrityError as exc2:
            # Colidir de novo com um sufixo aleatório é improvável a ponto de
            # indicar outra coisa; ainda assim, 409 legível é melhor do que
            # deixar o IntegrityError escapar como 500.
            #
            # O filtro pelo nome da constraint não é simetria estética com o
            # `except` de cima: sem ele, QUALQUER IntegrityError desta segunda
            # tentativa virava "não há nome livre no destino" — mensagem
            # factualmente falsa, que manda investigar o lugar errado. E fica
            # mais necessário agora que `create_version` reconverge sozinho: uma
            # violação que chegue até aqui passou a ser genuinamente inesperada,
            # e rotulá-la como conflito de nome esconderia justamente o caso novo.
            await db.rollback()
            if "uq_workflow_name_workspace" not in str(exc2.orig):
                raise
            raise WorkflowNameConflictError(
                "Não foi possível encontrar um nome livre no workspace de destino."
            ) from exc2
        resultado["name"] = nome_final
        resultado["renamed"] = True

    await _apagar_pins(pins_para_apagar)
    return resultado


def _pin_keys(pinned_outputs) -> list[str]:
    """s3_keys dos pins, para remoção depois do commit."""
    if not isinstance(pinned_outputs, dict):
        return []
    return [
        ref["__pin_s3_key__"]
        for ref in pinned_outputs.values()
        if isinstance(ref, dict) and isinstance(ref.get("__pin_s3_key__"), str)
    ]


async def _apagar_pins(keys: list[str]) -> None:
    """Remove os objetos de pin do MinIO. Best-effort, depois do commit.

    As keys estão sob `pin-cache/{workspace_origem}/…` e o workflow já não vive
    lá: mantê-las produziria lixo que ninguém mais alcança, e o unpin futuro
    apagaria um objeto do outro workspace. Falha aqui não desfaz o move — o pior
    caso é um objeto órfão, que a reconciliação de storage já sabe auditar.
    """
    if not keys:
        return
    from app.core import storage as s3
    for key in keys:
        try:
            await s3.delete_async(key)
        except Exception as exc:
            _logger.warning("Falha ao apagar pin '%s' após mover o workflow: %s", key, exc)
