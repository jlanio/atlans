from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
from uuid import uuid4

from app.schemas.schedule import ScheduleNotice

# ——— Schemas principais ———
class WorkflowBase(BaseModel):
    id_hash: str = Field(default_factory=lambda: str(uuid4()))
    flag_ative: Optional[bool] = True
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    priority: int = 0
    workspace_id: Optional[str] = None
    params_schema: Optional[Dict[str, Any]] = None
    notification_url: Optional[str] = None
    definition: Dict[str, Any]
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None

class WorkflowCreate(WorkflowBase):
    """
    Esquema usado para criar um novo Workflow.
    Não inclui campos gerados pelo banco (id, timestamps).
    """
    name: str = Field(..., description="Unique workflow name, no extension")
    definition: Dict[str, Any] = Field(..., description="Workflow JSON definition")
    # Obrigatorio: `Workflow.workspace_id` e NOT NULL, e criar sem tenant nunca
    # foi possivel na pratica — `create_workflow` chamava
    # `get_workspace_member_role(None)`, que devolvia None e virava 403. Exigir
    # aqui troca esse 403 confuso por um 422 que diz qual campo falta.
    workspace_id: str = Field(..., description="Workspace dono do workflow")

class WorkflowDuplicate(BaseModel):
    """Corpo opcional de POST /workflows/{id_hash}/duplicate.

    Sem `name`, o serviço escolhe o primeiro "Cópia de X" livre no workspace —
    há UniqueConstraint(name, workspace_id), e duplicar duas vezes o mesmo
    workflow devolvia 409 antes de o usuário ver a cópia.

    `extra="forbid"` como o irmão `WorkflowMove`: aceitar campo desconhecido em
    silêncio faz um cliente achar que mandou `workspace_id` e a cópia foi para
    outro lugar — quando na verdade o campo foi descartado.
    """
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(
        default=None, max_length=255,
        description="Nome da cópia. Omitido, deriva do original.",
    )


class WorkflowMove(BaseModel):
    """Corpo de POST /workflows/{id_hash}/move (e /move/preview).

    É a "rota própria" que o comentário de `WorkflowUpdate` (abaixo) pede: a
    troca de tenant não pode passar pelo PUT, porque lá a autorização é resolvida
    contra o workspace ANTERIOR à mudança.

    Sem `name`, o serviço mantém o nome atual e só desambigua se houver colisão
    no destino — há UniqueConstraint(name, workspace_id).
    """
    model_config = ConfigDict(extra="forbid")

    target_workspace_id: str = Field(
        ..., min_length=1, max_length=36,
        description="id_hash do workspace de destino.",
    )
    name: Optional[str] = Field(
        default=None, max_length=255,
        description="Novo nome no destino. Omitido, mantém o atual.",
    )


class WorkflowMoveWarning(BaseModel):
    """Um impacto da movimentação, pronto para exibir.

    O move nunca falha por dependência quebrada: o que deixaria de funcionar no
    destino é reportado aqui em vez de bloquear a operação.
    """
    code: str = Field(..., description="Identificador estável do tipo de aviso.")
    severity: Literal["warning", "info"] = "warning"
    message: str = Field(..., description="Texto em pt-BR pronto para exibir.")
    details: Dict[str, Any] = Field(default_factory=dict)


class WorkflowMoveResult(BaseModel):
    """Resposta de POST /workflows/{id_hash}/move.

    Em `/move/preview` os campos descrevem o que ACONTECERIA — nada foi gravado.
    """
    id: str
    name: str
    renamed: bool = False
    from_workspace_id: Optional[str] = None
    to_workspace_id: str
    dry_run: bool = False
    warnings: List[WorkflowMoveWarning] = Field(default_factory=list)


class WorkflowRead(BaseModel):
    id: int
    id_hash: str
    name: str
    flag_ative: bool
    description: Optional[str]
    version: Optional[str]
    priority: int
    workspace_id: Optional[str] = None
    group_id: Optional[str] = None
    params_schema: Optional[Dict[str, Any]] = None
    notification_url: Optional[str] = None
    definition: Dict[str, Any] = Field(
            ...,
            description="Definição JSON completa do workflow (nodes e edges)"
        )
    portal_access: Optional[str] = "disabled"
    portal_shared_with: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    # Avisos sobre o agendamento gerados por este save (workflow inativo,
    # expressão inválida). Vazio no GET e no caso normal; o editor mostra um
    # toast quando vem preenchido. Populado como atributo transiente no objeto
    # ORM retornado por `update_workflow` — não é coluna do banco.
    schedule_notices: List[ScheduleNotice] = Field(default_factory=list)

    class Config:
        from_attributes = True

class WorkflowVersionMeta(BaseModel):
    """Metadados de versão sem a definition — usado na listagem de versões."""
    id: int
    workflow_hash: str
    version_number: int
    change_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowScheduleSummary(BaseModel):
    """Resumo do agendamento de um workflow, para a listagem de Projetos.

    E um recorte de `ScheduleRead`, sem `id`/`job_id`/`retry_count`: a lista
    so precisa dizer "agendado todo dia as 06:00, proxima amanha" e se esta
    pausado. Quem edita o agendamento continua usando a rota de schedules.

    `next_run_at` None tem dois sentidos que a web distingue por `active`:
    pausado (o agendador nao calcula proxima para inativo) ou recem-criado
    (o agendador preenche em ate 30 s).
    """
    active: bool
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    strategy: str
    cron_expression: Optional[str] = None
    interval: Optional[int] = None
    unit: Optional[str] = None
    rrule_expression: Optional[str] = None
    timezone: Optional[str] = None


class WorkflowListItem(BaseModel):
    """Schema leve para listagem de workflows — exclui campos JSON pesados
    (definition, pinned_outputs, pin_metadata, params_schema).
    Economiza ~10KB por workflow nas respostas de listagem.

    Todo campo novo tem default: `ActiveRunsContext`, a paleta de comandos e o
    helper de sub-fluxo leem so `id_hash`/`name`/`description`, e nenhum deles
    pode quebrar quando a listagem ganha uma coluna.
    """
    id: int
    id_hash: str
    name: str
    flag_ative: bool
    description: Optional[str] = None
    version: Optional[str] = None
    priority: int = 0
    workspace_id: Optional[str] = None
    group_id: Optional[str] = None
    notification_url: Optional[str] = None
    portal_access: Optional[str] = "disabled"
    portal_shared_with: Optional[List[str]] = None
    has_publish_map: bool = False
    # Declara contrato de sub-fluxo: pode ser chamado por outro workflow.
    is_subworkflow: bool = False
    # Gatilhos — mesmo mecanismo de `has_publish_map`/`is_subworkflow` (ver
    # `_tem_node` no CRUD). "So manual" e nenhum dos quatro e nao ser
    # sub-fluxo; a web deriva, para nao haver um quinto booleano redundante.
    has_webhook_trigger: bool = False
    has_schedule_trigger: bool = False
    has_file_trigger: bool = False
    has_geofence_trigger: bool = False
    # Mesclado pelo servico a partir da tabela `schedules` (uma query em lote
    # por pagina, nunca uma por linha). None = sem agendamento.
    schedule: Optional[WorkflowScheduleSummary] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None
    # Proveniencia do fluxo: "usuario" (padrao) ou "assistente". Todo campo novo
    # tem default, pela regra do topo desta classe.
    origem: str = "usuario"
    # Nomes resolvidos em lote pelo servico; usuario apagado vira None e a web
    # mostra so "alterado ha X". `deleted_at` saiu daqui de proposito: a
    # listagem filtra `deleted_at IS NULL`, entao o campo era sempre nulo.
    created_by_username: Optional[str] = None
    updated_by_username: Optional[str] = None

    class Config:
        from_attributes = True


class WorkflowUpdate(BaseModel):
    """
    Esquema para atualização parcial de um Workflow.
    Todos os campos são opcionais; inclua apenas os que deseja alterar.

    NÃO inclui `workspace_id` nem `updated_by_id`, e isso é deliberado:

    - `workspace_id` definia o tenant dono. Como `update_workflow` repassa o
      payload inteiro ao CRUD, que faz `setattr` campo a campo, bastava um
      `PUT /workflows/{meu_id} {"workspace_id": "<workspace_da_vítima>"}` para
      mover o workflow para outro tenant — e a autorização não pegava, porque
      resolve o papel contra o workspace ANTERIOR à mudança. Mudança de tenant
      precisa de rota própria, que valide papel de editor nos DOIS workspaces.
    - `updated_by_id` é trilha de auditoria: quem editou tem que sair da
      identidade autenticada, nunca do corpo da requisição. Hoje é carimbado
      pelo servidor em `WorkflowService.update_workflow`.

    `extra="forbid"`: campo desconhecido vira 422 em vez de ser descartado em
    silêncio. Sem isso, um cliente que mandasse `workspace_id` continuaria
    achando que a mudança foi aplicada.
    """
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    name: Optional[str] = Field(None, description="Nome do workflow")
    description: Optional[str] = Field(None, description="Descrição do workflow")
    version: Optional[str] = Field(None, description="Versão do workflow")
    priority: Optional[int] = Field(None, description="Prioridade (maior = executa antes)")
    params_schema: Optional[Dict[str, Any]] = Field(None, description="Schema de parâmetros tipados para o workflow")
    notification_url: Optional[str] = Field(None, description="URL para webhook de notificação pós-execução")
    definition: Optional[Dict[str, Any]] = Field(None, description="Nova definição JSON do workflow")
    flag_ative: Optional[bool] = Field(None, description="Se o workflow está ativo")
