# app/crud/workflow_crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Boolean
from sqlalchemy.exc import IntegrityError

from app.models.models import Workflow, WorkflowVersion
from app.core.exceptions import WorkflowVersionConflictError
from app.core.utils.logger import get_logger

# O nome da UNIQUE (workflow_hash, version_number). Estável nos três lugares que
# a definem: `app/models/workflow_version.py`, a migração inicial e
# `scripts/init_schema.sql`.
_NOME_DA_UNIQUE_DE_VERSAO = "uq_workflow_version"


def _e_colisao_de_versao(exc: IntegrityError) -> bool:
    """A violação é a da UNIQUE (workflow_hash, version_number)?

    Duas formas de reconhecer, porque as duas bases dizem coisas diferentes:

        PostgreSQL  duplicate key value violates unique constraint "uq_workflow_version"
        SQLite      UNIQUE constraint failed: workflow_versions.workflow_hash, ...

    O SQLite **não** cita o nome da constraint — cita as colunas. Casar só pelo
    nome faria o retry funcionar em produção e nunca nos testes, que é a pior
    combinação possível: o conserto pareceria não testado quando está certo, ou
    passaria a suíte por um caminho que produção não percorre.

    Medido, não suposto — as duas mensagens acima saíram de uma violação real de
    cada base.
    """
    texto = str(getattr(exc, "orig", exc)).lower()
    if _NOME_DA_UNIQUE_DE_VERSAO in texto:
        return True
    return "unique" in texto and "version_number" in texto

# Três tentativas cobrem contenção real (saves simultâneos do mesmo fluxo).
# Esgotar as três não é "mais azar": é sinal de outra coisa, e vira 409.
_TENTATIVAS_DE_VERSAO = 3

def _tem_node(nome: str, rotulo: str):
    """Marca de listagem: a definition menciona um node com este nome.

    Procura no texto de `definition['nodes']` — não traz o JSON para o Python,
    que é o ponto de existir na consulta e não em código.

    Limitação conhecida: é busca por substring no JSON serializado, então um nó
    cujo APELIDO seja o nome procurado, ou um script que mencione o nome num
    comentário, marcam o workflow. Verificado: os dois casos dão positivo. O
    desfecho é um selo a mais numa lista, e a alternativa exata (`cast(... AS
    jsonb) @> '[{"name": "..."}]'`) prende a consulta ao PostgreSQL e tira estes
    testes do SQLite. Se a precisão passar a importar, é essa a troca.

    O `coalesce` não é zelo: `definition` sem a chave `nodes` faz o `->>`
    devolver NULL, o `LIKE` propaga NULL, e o Pydantic recusa None num campo
    `bool` — a resposta inteira de GET /workflows/ virava 500, e não só a linha
    daquele workflow. A coluna é `nullable=False`, mas nada garante o formato
    de dentro do JSON.
    """
    return cast(
        func.coalesce(Workflow.definition["nodes"].as_string().contains(nome), False),
        Boolean,
    ).label(rotulo)


_has_publish_map_expr = _tem_node("PublishMap", "has_publish_map")

# Workflow que existe para ser CHAMADO por outro: declara a saida publica de
# sub-fluxo. `SubWorkflowOutput` e o unico node obrigatorio do contrato (ver
# validate_subworkflow_references_against_db) — a entrada e opcional, porque um
# sub-fluxo pode nao receber nada.
#
# Vale a pena marcar na listagem porque um sub-fluxo costuma NAO ter gatilho:
# executa-lo sozinho pelo botao da lista nao faz o que se espera.
_e_subfluxo_expr = _tem_node("SubWorkflowOutput", "is_subworkflow")

# Gatilhos, pelo mesmo mecanismo. Sao a natureza do workflow ("como ele
# dispara"), nao execucao — por isso saem na listagem e nao nas metricas.
# Os nomes sao os registrados em `flow/nodes/trigger/*` (`get_definition()['name']`).
#
# Colisoes de substring aceitas, alem das gerais de `_tem_node`: um node cujo
# nome CONTENHA o procurado tambem marca — "GeofenceTrigger" casa com a classe
# `GeofenceTriggerNode` se algum dia o nome registrado mudar para ela, o que e
# o resultado desejado; nao ha hoje node registrado que contenha "FileTrigger",
# "WebhookTrigger" ou "ScheduleTrigger" sem ser o proprio gatilho.
_has_webhook_trigger_expr = _tem_node("WebhookTrigger", "has_webhook_trigger")
_has_schedule_trigger_expr = _tem_node("ScheduleTrigger", "has_schedule_trigger")
_has_file_trigger_expr = _tem_node("FileTrigger", "has_file_trigger")
_has_geofence_trigger_expr = _tem_node("GeofenceTrigger", "has_geofence_trigger")

# Colunas leves para listagem — exclui definition, pinned_outputs, pin_metadata,
# params_schema. `deleted_at` tambem fica de fora: as duas consultas que usam
# esta lista filtram `deleted_at IS NULL`, entao a coluna era sempre nula.
_METADATA_COLUMNS = [
    Workflow.id,
    Workflow.id_hash,
    Workflow.name,
    Workflow.flag_ative,
    Workflow.description,
    Workflow.version,
    Workflow.priority,
    Workflow.workspace_id,
    Workflow.group_id,
    Workflow.notification_url,
    Workflow.portal_access,
    Workflow.portal_shared_with,
    _has_publish_map_expr,
    _e_subfluxo_expr,
    _has_webhook_trigger_expr,
    _has_schedule_trigger_expr,
    _has_file_trigger_expr,
    _has_geofence_trigger_expr,
    Workflow.created_at,
    Workflow.updated_at,
    Workflow.created_by_id,
    Workflow.updated_by_id,
    Workflow.origem,
]

logger = get_logger(__name__)

class WorkflowCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_hash(self, id_hash: str) -> Workflow | None:
        stmt = (
            select(Workflow)
            .where(Workflow.id_hash == id_hash)
        )
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        return workflow
    
    # Os dois metodos abaixo carregavam `OR workspace_id IS NULL` para nao
    # esconder workflows legados. O efeito colateral era entrega-los na listagem
    # de TODO usuario autenticado, de qualquer tenant. A coluna e NOT NULL desde
    # a migration 20260828_0001, que atribuiu esses legados ao workspace certo —
    # nao ha mais legado a acomodar, e o filtro passa a ser so o do tenant.

    async def get_all_metadata(
        self, workspace_id: str | None = None, *, incluir_do_assistente: bool = False,
    ):
        """Retorna workflows SEM os campos JSON pesados (definition, pinned_outputs, etc.).
        Ideal para listagem — economiza ~10KB por workflow.

        Por padrao esconde os fluxos do assistente (`origem = "assistente"`): eles
        sao meio de entrega da Home, nao itens que o dono gerencia. Quem passa
        `incluir_do_assistente=True` hoje: o `ActiveRunsContext` (precisa dos
        nomes para o badge do run), a tool `list_workflows` quando quem chama e o
        proprio assistente, e a rota `GET /workflows?assistente=1`.

        ATENCAO — a tela de Projetos AINDA NAO tem o interruptor que usaria essa
        rota, e a observabilidade (inventario do Dashboard, contagens de grupo)
        nao filtra `origem`. Enquanto os dois lados nao concordarem, um fluxo do
        assistente aparece no Historico e nas metricas sem existir em Projetos.
        Os agendamentos dele aparecem de proposito, com selo — ver
        `schedule_service.listar_agendamentos_de`."""
        stmt = select(*_METADATA_COLUMNS).where(Workflow.deleted_at.is_(None))
        if not incluir_do_assistente:
            stmt = stmt.where(Workflow.origem != "assistente")
        if workspace_id:
            stmt = stmt.where(Workflow.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.mappings().all()

    async def get_all_metadata_by_workspace_ids(
        self, workspace_ids: list[str], *, incluir_do_assistente: bool = False,
    ):
        """Retorna workflows (somente metadados) dos workspaces fornecidos.

        Esconde os fluxos do assistente por padrao — ver `get_all_metadata`."""
        stmt = select(*_METADATA_COLUMNS).where(
            Workflow.deleted_at.is_(None),
            Workflow.workspace_id.in_(workspace_ids),
        )
        if not incluir_do_assistente:
            stmt = stmt.where(Workflow.origem != "assistente")
        result = await self.db.execute(stmt)
        return result.mappings().all()

    async def create(self, name: str, definition: dict, **kwargs) -> Workflow:
        wf = Workflow(name=name, definition=definition, **kwargs)
        self.db.add(wf)
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    async def update(self, wf: Workflow, updates: dict) -> Workflow:
        for key, value in updates.items():
            setattr(wf, key, value)
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    async def soft_delete_by_hash(self, id_hash: str) -> Workflow | None:
        """Soft delete: marca deleted_at e desativa o workflow sem removê-lo do banco."""
        from app.core.utils.datetime_utils import utc_now_naive
        stmt = select(Workflow).where(Workflow.id_hash == id_hash)
        result = await self.db.execute(stmt)
        wf = result.scalars().first()

        if wf is None:
            return None

        wf.deleted_at = utc_now_naive()
        wf.flag_ative = False
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    # ------------------------------------------------------------------ #
    # Workflow Versioning                                                  #
    # ------------------------------------------------------------------ #

    async def create_version(
        self,
        workflow_hash: str,
        definition: dict,
        change_note: str | None = None,
        *,
        tentativas: int = _TENTATIVAS_DE_VERSAO,
    ) -> WorkflowVersion:
        """Snapshot automático: salva a versão ATUAL antes de uma atualização.

        O número da versão é read-modify-write — lê o máximo atual e soma 1 —, e
        a UNIQUE `uq_workflow_version` é a única árbitra do empate. Dois saves
        simultâneos do mesmo workflow leem o mesmo máximo, e o segundo INSERT
        viola.

        **A janela não é a de um INSERT.** Como esta função só faz `flush()` (o
        commit é do chamador, de propósito — ver `workflow_move_service._aplicar`,
        que depende disso para desfazer tudo junto), ela vai do `SELECT max()`
        até o commit lá adiante, cobrindo tudo o que o chamador fizer no meio.

        Por que SAVEPOINT e não `try` solto: no PostgreSQL uma violação de
        constraint envenena a transação INTEIRA, e esta roda dentro da transação
        de outra pessoa, que ainda vai commitar trabalho não relacionado. Sem o
        `begin_nested`, capturar o erro não conserta — só troca o 500 por um
        `PendingRollbackError` no commit seguinte. Mesmo motivo, e mesmo molde,
        de `_upsert_pin_artifact` (`app/core/run_result_consumer.py`),
        `api_token_service.marcar_uso` e `credential_loader`.

        Por que NÃO `SELECT ... FOR UPDATE` na linha do workflow: `FOR UPDATE`
        conflita com o `FOR KEY SHARE` que todo INSERT com FK pede na linha
        referenciada, e `WorkflowVersion.workflow_hash` é FK para
        `workflows.id_hash`. O comentário de `app/core/async_scheduler.py` (no
        `with_for_update`) registra o auto-deadlock que isso já custou aqui, e
        `api_token_service` registra o descarte do mesmo recurso por custo.

        O retry **relê** o máximo em vez de incrementar o número que falhou: dois
        perdedores simultâneos que incrementassem colidiriam de novo entre si.
        """
        for _ in range(max(1, tentativas)):
            max_ver_result = await self.db.execute(
                select(func.max(WorkflowVersion.version_number)).where(
                    WorkflowVersion.workflow_hash == workflow_hash
                )
            )
            current_max = max_ver_result.scalar() or 0
            version = WorkflowVersion(
                workflow_hash=workflow_hash,
                version_number=current_max + 1,
                definition=definition,
                change_note=change_note,
            )
            try:
                async with self.db.begin_nested():
                    self.db.add(version)
                    await self.db.flush()   # obtém ID sem commit separado
                return version
            except IntegrityError as exc:
                if not _e_colisao_de_versao(exc):
                    raise
                # Não há `expunge(version)` aqui, e a ausência é medida: o
                # rollback do SAVEPOINT já retira da sessão o objeto adicionado
                # dentro dele, e chamar `expunge` depois levanta
                # `InvalidRequestError: Instance is not present in this Session`.
                # Cada volta do laço cria um `WorkflowVersion` novo, então nada
                # do INSERT que falhou sobrevive para ser reemitido.
                logger.info(
                    "Colisão de version_number no workflow %s; relendo o máximo.",
                    workflow_hash,
                )

        raise WorkflowVersionConflictError(
            "Outra gravação deste workflow está em andamento. Tente salvar de novo."
        )

    async def get_versions(self, workflow_hash: str) -> list[WorkflowVersion]:
        result = await self.db.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_hash == workflow_hash)
            .order_by(WorkflowVersion.version_number.desc())
        )
        return result.scalars().all()

    async def get_version(self, workflow_hash: str, version_number: int) -> WorkflowVersion | None:
        result = await self.db.execute(
            select(WorkflowVersion).where(
                WorkflowVersion.workflow_hash == workflow_hash,
                WorkflowVersion.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()