# app/core/exceptions.py
"""
Hierarquia de exceções de domínio do Atlas Studio.

Uso nos services:
    raise WorkflowNotFoundError("Workflow 'abc' não existe")

Uso nos routers:
    Não é necessário capturar — o exception handler global converte automaticamente
    para a resposta HTTP correta.
"""
from fastapi import status


class AtlasBaseError(Exception):
    """Classe base para todas as exceções de domínio do Atlas Studio."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code:  str = "internal_error"

    def __init__(self, detail: str = "Erro interno."):
        super().__init__(detail)
        self.detail = detail


# ── Workflow ──────────────────────────────────────────────────────────────────

class WorkflowError(AtlasBaseError):
    """Base para erros relacionados a workflows."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "workflow_error"


class WorkflowNotFoundError(WorkflowError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "workflow_not_found"


class WorkflowInactiveError(WorkflowError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "workflow_inactive"


class WorkflowDecryptionError(WorkflowError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "workflow_decryption_error"


class WorkflowNameConflictError(WorkflowError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "workflow_name_conflict"


class WorkflowVersionConflictError(WorkflowError):
    """Duas gravações do MESMO workflow disputaram o mesmo `version_number`.

    `create_version` calcula o número lendo o máximo atual e somando 1, e a
    UNIQUE `uq_workflow_version` é quem decide o empate. O CRUD já reconverge
    sozinho — relê e tenta o número seguinte. Esta exceção é o que sobra depois
    de esgotar as tentativas: raro a ponto de indicar outra coisa (uma enxurrada
    de saves no mesmo fluxo, ou um agente em laço), e aí 409 com "tente de novo"
    é resposta honesta. Antes disto, a violação subia como erro inesperado e o
    trabalho de quem salvou era perdido num 500.
    """
    status_code = status.HTTP_409_CONFLICT
    error_code  = "workflow_version_conflict"


class WorkflowMoveTargetError(WorkflowError):
    """Destino inválido para mover o workflow (hoje: já é o workspace atual)."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "workflow_move_target_invalid"


class WorkflowInputValidationError(WorkflowError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "workflow_input_validation"


class DisabledNodesInWorkflowError(WorkflowError):
    """Workflow contem 1+ nodes desabilitados pelo admin via /admin/nodes."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "workflow_has_disabled_nodes"


class DefinicaoInvalidaError(WorkflowError):
    """Definição que o executor nem consegue construir (nó inexistente, id
    duplicado, ciclo). `report` é o relatório do lint, que o tradutor de erros
    do MCP (`app/mcp/erros.py`) devolve higienizado — antes esses casos
    estouravam no `__init__` do executor e viravam um 500 genérico com a causa
    mascarada."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "invalid_definition"

    def __init__(self, detail: str = "Definição inválida.", *, report: dict | None = None):
        super().__init__(detail)
        self.report = report or {}


# ── Catálogo de fontes ────────────────────────────────────────────────────────

class FonteInvalidaError(AtlasBaseError):
    """A URL (ou a camada) de uma fonte não passa na forma: scheme, tamanho,
    credencial embutida. 422 como toda entrada malformada."""
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code  = "fonte_invalida"


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleError(AtlasBaseError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "schedule_error"


class InvalidScheduleError(ScheduleError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "invalid_schedule"


class ScheduleNotFoundError(ScheduleError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "schedule_not_found"


# ── Credential ────────────────────────────────────────────────────────────────

class CredentialError(AtlasBaseError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "credential_error"


class CredentialNotFoundError(CredentialError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "credential_not_found"


class CredentialValidationError(CredentialError):
    """Campos obrigatórios ausentes/ inválidos ao criar ou editar a credencial."""
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code  = "credential_validation"


# ── Workspace ─────────────────────────────────────────────────────────────────

class WorkspaceError(AtlasBaseError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "workspace_error"


class WorkspaceAccessDeniedError(WorkspaceError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "workspace_access_denied"


class WorkspacePolicyError(WorkspaceError):
    """Política de execução inválida: executor do pool num nível dedicado,
    executor inativo/sem chave, nível 2 sem nível 1, terminal desconhecido."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "workspace_policy_invalid"


class WorkspacePolicyFloorError(WorkspaceError):
    """O admin da plataforma fixou o piso `no_pool`: o dono não pode afrouxar."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "workspace_policy_floor"


class WorkspacePolicyConflictError(WorkspaceError):
    """A operação esvaziaria o nível principal de um workspace (sem `force`)."""
    status_code = status.HTTP_409_CONFLICT
    error_code  = "workspace_policy_conflict"

    def __init__(self, detail: str, *, workspaces: list[dict] | None = None):
        super().__init__(detail)
        self.workspaces = workspaces or []


# ── Drive / Arquivos ──────────────────────────────────────────────────────────

class FileError(AtlasBaseError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "file_error"


class FileNotFoundError(FileError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "file_not_found"


class FileValidationError(FileError):
    """Base das recusas de upload pelo arquivo em si. Quem mostra a recusa lê o
    `error_code` da subclasse — o web escolhe ícone e rótulo por ele, nunca pela
    frase —, e quem só precisa saber que é recusa captura esta classe."""
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code  = "file_validation_error"


class FileExtensionNotAllowedError(FileValidationError):
    """Extensão fora da lista que o admin habilitou — inclusive nenhuma."""
    error_code  = "extension_not_allowed"


class DangerousInnerExtensionError(FileValidationError):
    """Dupla extensão com a interna executável (`notas.sh.csv`)."""
    error_code  = "dangerous_inner_extension"


class EmptyFileError(FileValidationError):
    error_code  = "empty_file"


class FileTooLargeError(FileError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code  = "file_too_large"


class InvalidFileOperationError(FileError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "invalid_file_operation"


class ConteudoNoExecutorError(FileError):
    """Operacao que exigiria o CONTEUDO de um arquivo que so existe no executor.

    Vale para o registro de um arquivo catalogado (LGPD): a plataforma conhece a
    ficha, nunca os bytes. Excluir esse registro nao apagaria nada no disco de
    quem tem o arquivo — e apagar o arquivo do usuario por ordem do servidor
    seria destrutivo, porque ele nunca pertenceu a plataforma.

    409 e nao 400: nao ha nada de errado no pedido, e sim no ESTADO do recurso.
    """
    status_code = status.HTTP_409_CONFLICT
    error_code  = "conteudo_no_executor"


# ── Observabilidade / Runs ────────────────────────────────────────────────────

class RunNotFoundError(AtlasBaseError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "run_not_found"


class InvalidDateFormatError(AtlasBaseError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code  = "invalid_date_format"


# ── Executores ────────────────────────────────────────────────────────────────────

class ExecutorError(AtlasBaseError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "agent_error"


class NoExecutorAvailableError(ExecutorError):
    """Nenhum executor pôde receber o job.

    `category` distingue, nas métricas e no histórico, POR QUE não houve
    executor: `no_dedicated_executor` (workspace isolado com o grupo fora),
    `no_executor_chain` (dedicados e pool esgotados), `no_pool_executor`
    (modo pool com o pool fora) ou `isolation_violation` (barreira de §5.3 da
    spec). O texto continua sendo o que o dono lê.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code  = "no_agent_available"

    def __init__(
        self, detail: str = "Nenhum executor disponível.", *,
        category: str | None = None, run_id: str | None = None,
    ):
        super().__init__(detail)
        self.category = category or "no_executor"
        # Preenchido quando um run JÁ foi criado e marcado `failed` antes de
        # levantar (dispatch esgotado, barreira): quem captura não deve
        # materializar um segundo run para a mesma ocorrência.
        self.run_id = run_id


# ── Credentials ───────────────────────────────────────────────────────────────

class CredentialAccessDeniedError(CredentialError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "credential_access_denied"


# ── Recursos genéricos ────────────────────────────────────────────────────────

class DuplicateResourceError(AtlasBaseError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "duplicate_resource"


class ConfigurationError(AtlasBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "configuration_error"
