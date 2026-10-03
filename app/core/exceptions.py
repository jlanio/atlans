# app/core/exceptions.py
"""
Domain exception hierarchy of Atlas Studio.

Usage in services:
    raise WorkflowNotFoundError("Workflow 'abc' não existe")

Usage in routers:
    No need to catch — the global exception handler automatically converts
    to the correct HTTP response.
"""
from fastapi import status


class AtlasBaseError(Exception):
    """Base class for all Atlas Studio domain exceptions."""
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
    """Two saves of the SAME workflow competed for the same `version_number`.

    `create_version` computes the number by reading the current maximum and adding 1, and the
    UNIQUE `uq_workflow_version` is what breaks the tie. The CRUD already reconverges
    on its own — it re-reads and tries the next number. This exception is what is left after
    the attempts run out: rare enough to point to something else (a flood
    of saves on the same workflow, or an agent in a loop), and then a 409 with "try again"
    is an honest answer. Before this, the violation bubbled up as an unexpected error and the
    saver's work was lost in a 500.
    """
    status_code = status.HTTP_409_CONFLICT
    error_code  = "workflow_version_conflict"


class WorkflowMoveTargetError(WorkflowError):
    """Invalid destination for moving the workflow (today: it is already the current workspace)."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "workflow_move_target_invalid"


class WorkflowInputValidationError(WorkflowError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "workflow_input_validation"


class DisabledNodesInWorkflowError(WorkflowError):
    """Workflow contem 1+ nodes desabilitados pelo admin via /admin/nodes."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "workflow_has_disabled_nodes"


class InvalidDefinitionError(WorkflowError):
    """A definition the executor cannot even build (nonexistent node, duplicate
    id, cycle). `report` is the lint report, which the MCP error translator
    (`app/mcp/erros.py`) returns sanitized — before, these cases
    blew up in the executor's `__init__` and became a generic 500 with the cause
    masked."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "invalid_definition"

    def __init__(self, detail: str = "Definição inválida.", *, report: dict | None = None):
        super().__init__(detail)
        self.report = report or {}


# ── Source catalog ────────────────────────────────────────────────────────────

class InvalidSourceError(AtlasBaseError):
    """A source's URL (or layer) does not pass the shape check: scheme, length,
    embedded credential. 422 like every malformed input."""
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
    """Required fields missing/invalid when creating or editing the credential."""
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
    """Invalid execution policy: a pool executor in a dedicated tier,
    an inactive/keyless executor, tier 2 without tier 1, an unknown terminal."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "workspace_policy_invalid"


class WorkspacePolicyFloorError(WorkspaceError):
    """The platform admin set the `no_pool` floor: the owner cannot loosen it."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "workspace_policy_floor"


class WorkspacePolicyConflictError(WorkspaceError):
    """The operation would empty a workspace's main tier (without `force`)."""
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
    """Base of the upload refusals caused by the file itself. Whoever shows the refusal reads the
    subclass's `error_code` — the web picks the icon and label by it, never by the
    sentence —, and whoever only needs to know it is a refusal catches this class."""
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code  = "file_validation_error"


class FileExtensionNotAllowedError(FileValidationError):
    """Extension outside the list the admin enabled — including none at all."""
    error_code  = "extension_not_allowed"


class DangerousInnerExtensionError(FileValidationError):
    """Double extension with an executable inner one (`notas.sh.csv`)."""
    error_code  = "dangerous_inner_extension"


class EmptyFileError(FileValidationError):
    error_code  = "empty_file"


class FileTooLargeError(FileError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code  = "file_too_large"


class InvalidFileOperationError(FileError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "invalid_file_operation"


class ContentOnExecutorError(FileError):
    """Operation that would require the CONTENT of a file that only exists on the executor.

    Applies to the record of a cataloged file (LGPD): the platform knows the
    record card, never the bytes. Deleting that record would erase nothing on the disk of
    whoever has the file — and deleting the user's file on the server's orders
    would be destructive, because it never belonged to the platform.

    409 and not 400: there is nothing wrong with the request, but with the resource's STATE.
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
    """No executor could receive the job.

    `category` distinguishes, in the metrics and in the history, WHY there was no
    executor: `no_dedicated_executor` (isolated workspace with the group down),
    `no_executor_chain` (dedicated ones and pool exhausted), `no_pool_executor`
    (pool mode with the pool down) or `isolation_violation` (the barrier from §5.3 of the
    spec). The text is still what the owner reads.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code  = "no_agent_available"

    def __init__(
        self, detail: str = "Nenhum executor disponível.", *,
        category: str | None = None, run_id: str | None = None,
    ):
        super().__init__(detail)
        self.category = category or "no_executor"
        # Filled in when a run HAS ALREADY been created and marked `failed` before
        # raising (dispatch exhausted, barrier): whoever catches it must not
        # materialize a second run for the same occurrence.
        self.run_id = run_id


# ── Credentials ───────────────────────────────────────────────────────────────

class CredentialAccessDeniedError(CredentialError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "credential_access_denied"


# ── Generic resources ─────────────────────────────────────────────────────────

class DuplicateResourceError(AtlasBaseError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "duplicate_resource"


class ConfigurationError(AtlasBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "configuration_error"
