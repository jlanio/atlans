// service/GisFlowService.ts
//
// A fachada do cliente HTTP: os métodos moram em service/dominios/* (um
// arquivo por domínio — F5/A12 da simplificação) e este objeto os agrega,
// então todo call site continua `GisFlowService.metodo()`. O transporte
// (token, interceptores, dedup de GETs, get/post/…) está em service/http.ts.

export { setAuthToken } from "./http"

import * as admin from "./dominios/admin"
import * as agendamentos from "./dominios/agendamentos"
import * as artefatos from "./dominios/artefatos"
import * as credenciais from "./dominios/credenciais"
import * as drive from "./dominios/drive"
import * as executores from "./dominios/executores"
import * as observabilidade from "./dominios/observabilidade"
import * as tokens from "./dominios/tokens"
import * as workflows from "./dominios/workflows"
import * as workspaces from "./dominios/workspaces"

export const GisFlowService = {
  ...admin, ...agendamentos, ...artefatos, ...credenciais, ...drive,
  ...executores, ...observabilidade, ...tokens, ...workflows,
  ...workspaces,
}

export type {
  IWorkflowVersion, IObservabilityMetrics, IWorkflowMetrics, IRunSummary,
  IRunDetail, IRunEvent, IRunEventsResponse, IRunsByDay, IExecutorMetrics, IWorkflowMetricsRow,
  IArtifactItem, IArtifactSettings, IArtifactListParams, IArtifactListResponse,
  IDriveFile, IDriveFileList, IDriveListParams,
  IExecutor, IExecutorCreateRequest, IExecutorCreatedResponse,
  INodeStatSummary, IExecutorCapacity, IExecutorSystemInfo,
  IAdminUser, IAdminUserListParams, IAdminUserListResponse, IAdminBulkActionResponse,
  IStorageUsage, IStorageUsageAdmin, IStorageWorkspaceUsage,
  IAssistenteEstado, IAssistenteCota,
  IWorkspace, IWorkspaceTrash, IWorkspaceRestoreResult,
  IWorkspaceMember, IUserSearchResult,
  IWorkspaceNotifications, IWorkspaceNotificationTarget,
  ApiToken, ApiTokenCreate, ApiTokenCreated, ApiTokenScope, ApiTokenStatus, ApiTokenExpiresInDays,
} from "./types"
