// service/types.ts
//
// A casa ÚNICA dos tipos do web que espelham a API. O diretório
// `web/interface/` foi absorvido aqui na F2 da simplificação
// (docs/specs/simplificacao.md, A7): duas casas para o mesmo tipo de
// coisa era convite para a terceira.
import type { ActionsType, ControlsType, TriggersType } from "@/consts/WorkflowIcons"

export interface IWorkflowVersion {
  id: number
  version_number: number
  workflow_hash: string
  created_at: string
  change_note: string | null
}

// "mcp" = disparado por um agente via servidor MCP (token pessoal de acesso).
export type TriggerSource = "manual" | "retry" | "webhook" | "schedule" | "mcp"

/** Categoria do erro que fechou o run: taxonomia do flow + categorias do servidor. */
export type ErrorCategory =
  | "user" | "validation" | "timeout" | "resource" | "transient" | "internal"
  | "no_executor" | "executor_lost" | "isolation" | "dispatch"

export interface ITopFailingWorkflow {
  workflow_hash: string
  workflow_name: string | null
  failure_count: number
  total_runs: number
  /** Falhas ÷ total do workflow na janela. */
  failure_rate: number
  last_error: string | null
  last_error_category: ErrorCategory | string | null
  last_failed_at: string | null
}

/** Execução em andamento há mais tempo que o esperado para o workflow. */
export interface IStuckRun {
  run_id: string
  workflow_hash: string
  workflow_name: string | null
  agent_host: string | null
  executor_name: string | null
  started_at: string | null
  elapsed_seconds: number
  typical_seconds: number | null
}

/** O instante da consulta, sem janela (docs/specs/historico-metricas.md §3.1). */
export interface INowBlock {
  running: number
  pending: number
  stuck_count: number
  stuck: IStuckRun[]
  executors: { online: number; total: number }
  queued_on_executors: number | null
  /** Só admin; null para os demais. */
  overdue_acks: number | null
}

export interface IObservabilityMetrics {
  period_days?: number
  total_workflows: number
  active_workflows: number
  total_runs: number
  failed_runs: number
  /** Concluídas ÷ (concluídas + falhas) na janela; 0 sem denominador. */
  success_rate: number
  avg_duration_seconds: number
  runs_last_24h: number
  runs_last_7d: number
  runs_prev_7d: number
  success_rate_prev_7d: number | null
  by_status: { success: number; failed: number; running: number; other: number; cancelled?: number; pending?: number }
  top_failing_workflows: ITopFailingWorkflow[]
  // ── novos (redesenho do Histórico) ──
  success_runs?: number
  cancelled_runs?: number
  running_runs?: number
  pending_runs?: number
  /** Janela anterior de mesmo tamanho. */
  prev_period?: {
    total_runs: number; success_runs: number; failed_runs: number; success_rate: number
    p50_seconds: number | null
  }
  /** Só concluídas com duração > 0; null sem dados. */
  duration?: { p50_seconds: number | null; p95_seconds: number | null }
  now?: INowBlock
}

export interface INodeStatSummary {
  node_id: string
  node_name: string
  execution_count: number
  avg_duration_ms: number
  failure_count: number
  cache_hits: number
  avg_input_features: number | null
  avg_output_features: number | null
}

export interface IWorkflowMetrics {
  workflow_id: string
  workflow_name: string
  total_runs: number
  failed_runs: number
  success_rate: number
  avg_duration_seconds: number
  min_duration_seconds: number | null
  max_duration_seconds: number | null
  last_runs: IRunSummary[]
  node_stats_summary: INodeStatSummary[]
  // Populados somente quando o requester e admin (backend retorna
  // via _resolve_workflow_meta no observability_service.py).
  workflow_active?: boolean
  owner_username?: string | null
  workspace_id?: string | null
  workspace_name?: string | null
}

export interface IRunSummary {
  run_id: string
  workflow_hash?: string
  status: string
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  error_message: string | null
  retry_count: number
  agent_host: string | null
  /** Nível da política em que rodou; nulo em runs anteriores à coluna. */
  dispatch_tier?: DispatchTier | null
  // Para qualquer usuário no escopo (o filtro por workspace já garante o acesso).
  workflow_name?: string
  workspace_id?: string | null
  workspace_name?: string | null
  executor_id?: string | null
  /** Nome amigável do executor; null sem host. */
  executor_name?: string | null
  trigger_source?: TriggerSource | null
  triggered_by?: string | null
  triggered_by_username?: string | null
  error_category?: ErrorCategory | string | null
  schedule_id?: number | null
  /**
   * Origem do FLUXO ("usuario" | "assistente"), não do disparo — este é
   * `trigger_source`. `null` quando o fluxo foi apagado de vez.
   */
  workflow_origem?: string | null
  // Populados somente quando o requester é admin.
  workflow_active?: boolean
  owner_username?: string | null
}

export interface IExecutorMetrics {
  /** null na linha das execuções sem executor (falhas de despacho). */
  agent_host: string | null
  display_name: string
  total_runs: number
  success_runs: number
  failed_runs: number
  success_rate: number
  avg_duration_seconds: number | null
  last_run_at: string | null
  // ── novos (redesenho do Histórico) ──
  executor_id?: string | null
  executor_type?: "default" | "dedicated" | null
  is_default?: boolean
  status?: string | null
  online?: boolean
  /** null quando o executor não publica capacidade. */
  capacity?: { running: number; queued: number; max_concurrent: number; max_queue: number } | null
  p50_seconds?: number | null
  /** Linha "Sem executor": runs que falharam antes de chegar a um executor. */
  unassigned?: boolean
}

/** Uma linha da visão "Por workflow" (`GET /observability/metrics/workflows`). */
export interface IWorkflowMetricsRow {
  workflow_hash: string
  workflow_name: string
  workspace_id: string | null
  workspace_name: string | null
  active: boolean
  total_runs: number
  success_runs: number
  failed_runs: number
  running_runs: number
  success_rate: number
  p50_seconds: number | null
  last_run_at: string | null
  last_status: string | null
  last_error: string | null
  last_error_category: ErrorCategory | string | null
  /** Quem criou o fluxo: "usuario" | "assistente" (o selo da lista). */
  origem?: string | null
}

export interface IRunDetail {
  run_id: string
  workflow_hash: string
  status: string
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  error_message: string | null
  retry_count: number
  agent_host: string | null
  dispatch_tier?: DispatchTier | null
  workflow_name?: string
  workspace_id?: string | null
  workspace_name?: string | null
  executor_id?: string | null
  executor_name?: string | null
  trigger_source?: TriggerSource | null
  triggered_by?: string | null
  triggered_by_username?: string | null
  error_category?: ErrorCategory | string | null
  schedule_id?: number | null
  /** p50 do workflow nos últimos 90 dias; null sem dados. */
  typical_seconds?: number | null
  // Populados somente quando o requester é admin.
  workflow_active?: boolean
  owner_username?: string | null
  node_stats: Record<string, {
    node_name: string
    duration_ms: number
    status: string
    cache_hit: boolean
    input_features: number | null
    output_features: number | null
    error: string | null
    started_at: string | null
    output_keys: string[]
    /** Colunas por porta de saída, quando o executor as publicou (>= 2.4.0 e
     *  sem o corte de 8KB do stat). Re-hidrata a sugestão de nome de coluna
     *  ao abrir o workflow — sem esta chave o tipo escondia um dado que o
     *  backend sempre devolveu. */
    output_columns?: Record<string, string[]> | null
    /** O executor marcou o stat como truncado (corte de 8KB) — as listas de
     *  colunas podem estar reduzidas às primeiras 50. */
    __truncated__?: boolean
  }>
}

/** Um evento cru do canal de execução, como persistido no histórico do Redis. */
export interface IRunEvent {
  run_id?: string
  node?: string
  kind?: string
  level?: string
  status?: string
  timestamp?: number
  duration_ms?: number | null
  error?: string | null
  extra?: Record<string, unknown> | null
}

export interface IRunEventsResponse {
  run_id: string
  events: IRunEvent[]
  /** true quando o histórico já expirou no Redis (TTL de 1h) ou está vazio. */
  expired: boolean
}

export interface IRunsByDay {
  day: string
  total: number
  success: number
  failed: number
  /** running + pending. */
  running: number
  cancelled?: number
  other?: number
}

export interface IArtifactItem {
  id_hash:          string
  workspace_id:     string | null
  workflow_id:      string | null
  workflow_name:    string
  run_id:           string
  node_id:          string | null
  output_key:       string
  filename:         string
  format:           string | null
  size_bytes:       number | null
  features:         number | null
  protected:        boolean
  is_published:     boolean
  is_portal_active: boolean
  is_pinned:        boolean
  executor_id:         string | null
  /**
   * Onde o CONTEÚDO mora.
   *
   * `minio` é o caso de sempre. `executor` significa que os bytes nunca saíram
   * da máquina — nó de saída com localidade "Manter apenas no executor", ou a
   * política daquela máquina. Não há download.
   *
   * A API já devolvia o campo; era o tipo que não o declarava, e a tela
   * adivinhava por `executor_id && !size_bytes` — heurística que erra
   * justamente nos artefatos locais, porque eles TÊM tamanho.
   */
  content_location?: "minio" | "executor"
  created_at:       string | null
  expires_at:       string | null
}

/**
 * Filtros de `GET /artifacts/`.
 *
 * `limit`/`offset` existem porque a tela baixava a tabela inteira de artefatos
 * do usuario e paginava no cliente — num workspace com historico isso trava a
 * aba por segundos. `search` e `workspace_id` sao os mesmos filtros que a tela
 * fazia em memoria, empurrados para o SQL.
 */
export interface IArtifactListParams {
  workflow_id?:    string
  run_id?:         string
  fmt?:            string
  /** Recorte execucao x publicacao — o que a tela chamava de abas. */
  kind?:           "execution" | "publication"
  search?:         string
  workspace_id?:   string
  include_pinned?: boolean
  limit?:          number
  offset?:         number
}

export interface IArtifactListResponse {
  items:  IArtifactItem[]
  /** Total do filtro inteiro, nao da pagina — alimenta o "ver mais". */
  total:  number
  limit?:  number
  offset?: number
}

export interface IArtifactSettings {
  artifact_retention_days: number | null
}

// ── Drive ─────────────────────────────────────────────────────────────────────

export interface IDriveFile {
  id_hash:       string
  workspace_id:  string
  original_name: string
  extension:     string
  mime_type:     string | null
  /** Nulavel de verdade: o confirm do upload pode gravar os metadados sem
   *  tamanho (e o HEAD nem sempre responde), como `WorkspaceFileOut` declara.
   *  Sem o `| null` aqui o proximo consumidor formatava um `undefined` sem
   *  nenhum aviso do compilador. */
  size:          number | null
  uploaded_by:   string | null
  created_at:    string
  updated_at:    string | null
  /**
   * Ultima escrita de CONTEUDO. Um arquivo sobrescrito mantem o created_at
   * original. Distinta de `updated_at`, que qualquer update da linha dispara
   * (renomear, por exemplo) e que NAO dispara quando a sobrescrita nao muda
   * nenhum campo — exibi-lo nao explicava a ordem que o usuario via.
   */
  content_written_at: string | null
  /**
   * Onde o CONTEUDO mora.
   *
   * `minio` e o caso de sempre. `executor` significa que o arquivo foi
   * catalogado pelo GeoSync em modo catalogo (LGPD): a plataforma conhece o
   * nome, o tipo e os metadados espaciais, mas os bytes nunca sairam da maquina
   * do executor — e por isso nao ha download.
   */
  content_location?:    "minio" | "executor"
  content_executor_id?: string | null
  spatial_metadata?:    Record<string, unknown> | null
}

export interface IDriveFileList {
  items: IDriveFile[]
  /** COUNT do filtro inteiro — a lista vem cortada em `page_size`. */
  total: number
}

/** O `error` do corpo quando o Drive recusa um upload pelo arquivo em si — as
 *  subclasses de `FileValidationError` e o `FileTooLargeError` de
 *  `app/core/exceptions.py`. Chega em `IResponse.error.code`. A recusa se
 *  classifica por ele (e pelo status), nunca pela frase, que pode mudar. */
export type UploadErrorCode =
  | "extension_not_allowed"
  | "dangerous_inner_extension"
  | "empty_file"
  | "file_too_large"

/** `page`/`page_size` sempre viajaram no backend e nenhum consumidor os enviava:
 *  arquivos alem do 50o ficavam inalcancaveis pela UI. */
export interface IDriveListParams {
  workspace_id: string
  search?:      string
  ext?:         string
  page?:        number
  page_size?:   number
}

export interface IExecutorCapacity {
  queued:          number
  running:         number
  max_concurrent:  number
  max_queue:       number
  disk_free_gb?:   number
  ram_available_gb?: number
}

export interface IExecutorSystemInfo {
  hostname?:         string
  os_name?:          string
  os_version?:       string
  cpu_cores?:        number
  ram_total_gb?:     number
  disk_total_gb?:    number
  disk_free_gb?:     number
  ram_available_gb?: number
  container?:        boolean
}

export interface IExecutor {
  id_hash:             string
  name:                string
  description:         string | null
  status:              "pending" | "active" | "inactive" | "revoked"
  executor_type:          "default" | "dedicated"
  is_default:          boolean
  capabilities:        string[]
  max_concurrent_jobs: number
  max_queue_size:      number
  executor_version:       string | null
  last_seen_at:        string | null
  created_at:          string
  created_by:          string | null
  online:              boolean
  capacity:            IExecutorCapacity | null
  connected_at:        string | null
  system_info:         IExecutorSystemInfo | null
}

export interface IExecutorCreateRequest {
  name:                string
  description?:        string
  capabilities?:       string[]
  max_concurrent_jobs?: number
  max_queue_size?:     number
  executor_type?:         "default" | "dedicated"
}

export interface IExecutorCreatedResponse {
  executor_id:  string
  status:    string
  next_step: string
}

export interface IExecutorEnrollmentOtpResponse {
  otp:        string
  expires_at: string
  executor_id:   string
  /** Host dos executores (AGENTS_URL); vazio quando o servidor não o conhece. */
  server_url: string
  /** O site desta instalação (FRONTEND_URL), de onde o install.sh é baixado. */
  public_url: string
}


export interface IExecutorUserAssignment {
  user_id:     string
  username:    string
  email:       string
  assigned_at: string
  assigned_by: string | null
}

// ── Admin: Gestão de Usuários ────────────────────────────────────────────────

export interface IAdminUser {
  id_hash:       string
  username:      string
  email:         string
  status:        "active" | "suspended" | "deleted"
  role:          string
  agent_quota:   number
  workspace_id:  string | null
  last_login_at: string | null
  suspended_at:  string | null
  deleted_at:    string | null
  created_at:    string
  updated_at:    string
}

export interface IAdminUserListParams {
  search?:     string
  status?:     string
  role?:       string
  sort_by?:    string
  sort_order?: "asc" | "desc"
  date_from?:  string
  date_to?:    string
  limit?:      number
  offset?:     number
}

export interface IAdminUserListResponse {
  items:  IAdminUser[]
  total:  number
  limit:  number
  offset: number
}

export interface IAdminBulkActionResponse {
  processed: number
  errors:    { user_id: string; error: string }[]
}

// ── Workspaces ───────────────────────────────────────────────────────────────

/**
 * Workspace como o backend devolve em GET /workspaces/ (WorkspaceOut).
 *
 * Re-exportado como `Workspace` por WorkspaceContext, que e o dono do estado
 * do workspace ativo — os componentes seguem importando de la.
 */
export interface IWorkspace {
  id_hash:     string
  name:        string
  description: string | null
  owner_id:    string | null
  is_default:  boolean
  /** "owner" | "viewer" | "editor" | "operator" | "admin" */
  my_role:     string | null
}

export type DispatchTier = "primary" | "fallback" | "pool"
export type PolicyTerminal = "fail" | "pool"
export type IsolationFloor = "none" | "no_pool"
/** pool = sem nível 1 · isolated = nível 1 + terminal fail · dedicated_pool = nível 1 + terminal pool */
export type PolicyMode = "pool" | "isolated" | "dedicated_pool"

/** Membro de um nível da política de execução ( GET /workspaces/{id}/executors ). */
export interface IPolicyMember {
  id_hash:       string
  name:          string
  executor_type: "default" | "dedicated"
  status:        string
  tier:          1 | 2
  /** null = presença desconhecida (Redis fora / reconectando) */
  online:        boolean | null
  capacity:      { queued?: number; running?: number; max_concurrent?: number; max_queue?: number } | null
}

/** Uma linha da tela de admin "Piso de isolamento" (GET /admin/workspaces/policies). */
export interface IWorkspacePolicyAdmin {
  id_hash:            string
  name:               string
  is_default:         boolean
  owner_id:           string | null
  owner_username:     string | null
  mode:               PolicyMode
  isolation_floor:    IsolationFloor
  fallback_terminal:  PolicyTerminal
  effective_terminal: PolicyTerminal
  primary_count:      number
  fallback_count:     number
}

export interface IPoolHealth {
  total:     number
  available: number
}

/**
 * Política de execução do workspace (docs/specs/executor-isolation-routing.md).
 * `policy_routing_enabled=false` significa que o servidor ainda roteia pelo
 * caminho legado — a tela mostra a política como prévia.
 */
export interface IWorkspacePolicy {
  workspace_id:           string
  mode:                   PolicyMode
  primary:                IPolicyMember[]
  fallback:               IPolicyMember[]
  fallback_terminal:      PolicyTerminal
  effective_terminal:     PolicyTerminal
  isolation_floor:        IsolationFloor
  available_primary:      number
  available_fallback:     number
  pool:                   IPoolHealth | null
  policy_routing_enabled: boolean
  target_executor_id:     string | null
}

/**
 * Linha da lista de membros ( GET /workspaces/{id}/members ).
 *
 * O dono vem SEMPRE primeiro, com `role: "owner"` — uma linha sintetica, montada
 * na leitura, porque ele nao tem registro em `workspace_members`. Nao e um role
 * atribuivel: o backend recusa PUT/DELETE sobre ela.
 */
export interface IWorkspaceMember {
  user_id:   string
  username:  string
  email:     string
  /** "owner" | "admin" | "operator" | "editor" | "viewer" */
  role:      string
  joined_at: string
}

/** Resultado de GET /workspaces/users/search — usuarios ja cadastrados. */
export interface IUserSearchResult {
  id_hash:  string
  username: string
  email:    string
}

/**
 * Um workflow do workspace que envia webhook, e se a allowlist atual o deixa
 * passar. `allowed` vem do backend usando a MESMA funcao que o consumer aplica
 * ao disparar — e o que a tela pode prometer sem mentir.
 */
export interface IWorkspaceNotificationTarget {
  id_hash:          string
  name:             string
  notification_url: string
  host:             string
  allowed:          boolean
}

/**
 * GET/PUT /workspaces/{id}/notifications.
 *
 * `allowlist` vazia significa "sem politica adicional" — todo webhook que passe
 * na verificacao de SSRF e aceito. Preenchida, tudo que estiver fora dela e
 * bloqueado em silencio depois da execucao.
 */
export interface IWorkspaceNotifications {
  allowlist: string[]
  workflows: IWorkspaceNotificationTarget[]
}

/**
 * Um impacto da movimentacao de um workflow entre workspaces.
 *
 * O move nunca falha por dependencia quebrada: o que deixa de funcionar no
 * destino chega aqui. `message` ja vem em pt-BR, pronto para exibir; `details`
 * carrega os ids envolvidos.
 */
export interface IWorkflowMoveWarning {
  code:     string
  severity: "warning" | "info"
  message:  string
  details:  Record<string, unknown>
}

/**
 * Resposta de POST /workflows/{id}/move — e de /move/preview, onde descreve o
 * que ACONTECERIA (`dry_run: true`) sem ter gravado nada.
 */
export interface IWorkflowMoveResult {
  id:                string
  name:              string
  renamed:           boolean
  from_workspace_id: string | null
  to_workspace_id:   string
  dry_run:           boolean
  warnings:          IWorkflowMoveWarning[]
}

/**
 * Linha da lixeira ( GET /admin/workspaces/trash ). Admin-only: lista o que
 * qualquer usuario da plataforma deletou, por isso traz os dados do dono.
 */
export interface IWorkspaceTrash {
  id_hash:         string
  name:            string
  description:     string | null
  owner_id:        string | null
  owner_username:  string | null
  owner_email:     string | null
  deleted_at:      string
  /** Quantos workflows voltam se este workspace for restaurado. */
  workflows:       number
}

export interface IWorkspaceRestoreResult {
  workspace_id:       string
  workflows_restored: number
  detail:             string
}

// ── Armazenamento (MinIO) ────────────────────────────────────────────────────

export interface IStorageUsage {
  drive_bytes:     number
  artifacts_bytes: number
  total_bytes:     number
  drive_files:     number
  artifact_files:  number
}

export interface IStorageWorkspaceUsage extends IStorageUsage {
  workspace_id:    string
  workspace_name:  string
  owner_username:  string
  /**
   * active  — workspace vivo
   * trashed — na lixeira (soft delete): so o admin acessa, via /admin/settings
   * purged  — linha removida do banco: dados orfaos, ninguem mais alcanca
   */
  workspace_state?: "active" | "trashed" | "purged"
  /** true para trashed e purged. Mantido para a marcacao visual da tabela. */
  workspace_deleted?: boolean
}

/**
 * Contrato (API publica) de um workflow para uso como sub-fluxo.
 *
 * Servidor extrai de SubWorkflowInput (inputs) e SubWorkflowOutput (outputs)
 * — chaves vem das edges conectadas a esses nodes. `has_input_node` /
 * `has_output_node` indicam se o contrato esta declarado.
 */
export interface IWorkflowContractPort {
  name:        string
  type?:       string | null
  description?: string | null
}

export interface IWorkflowContract {
  inputs:           IWorkflowContractPort[]
  outputs:          IWorkflowContractPort[]
  has_input_node:   boolean
  has_output_node:  boolean
  is_active?:       boolean
}

/**
 * Entry da lista admin de nodes ( GET /admin/nodes ).
 *
 * Reflete o NODE_REGISTRY mesclado com SystemConfig.disabled_nodes — quando
 * `enabled=false`, `reason`/`disabled_at`/`disabled_by` vem populados.
 */
export interface INodeAdminEntry {
  name:           string
  alias:          string
  type:           string | null
  enabled:        boolean
  reason?:        string | null
  disabled_at?:   string | null
  disabled_by?:   string | null
}

/**
 * Indicadores de saude do tracking de storage. Servidor expoe via
 * /admin/storage para dar visibilidade ao drift silencioso (pending
 * abandonado, artefato sem tamanho, orfaos).
 *
 * Campo opcional para compat com deploys mistos durante rollout — UI
 * nao renderiza a secao se vier undefined.
 */
export interface ITrackingHealth {
  pending_drive_files:          number
  pending_drive_bytes:          number
  null_size_artifacts:          number
  /** Subconjunto de null_size: antigos demais para o retry — nao se resolvem. */
  unrecoverable_size_artifacts: number
  /** Artefatos cujo workspace foi deletado: inacessiveis e ocupando disco. */
  orphaned_workspace_artifacts: number
}

export interface IStoragePurgeResult {
  workspace_id:      string
  artifacts:         number
  artifact_bytes:    number
  drive_files:       number
  drive_bytes:       number
  scope:             "all" | "artifacts" | "drive"
  skipped_s3_errors: number
  /** Artefatos que vivem no disco de um executor OFFLINE: a ordem de remoção
   *  não foi entregue, então a linha fica e a próxima passada tenta de novo. */
  pending_executor?:    number
  /** Artefatos locais sem executor_id/local_path — sem para quem mandar a
   *  ordem; a linha fica para não perder o rastro do arquivo. */
  skipped_sem_rastro?:  number
  /** Arquivos de Drive catalogados no executor: preservados por política (são
   *  do próprio usuário, na pasta que ele sincroniza, e não ocupam
   *  armazenamento da plataforma). */
  skipped_catalogados?: number
}

export interface IStorageUsageAdmin {
  totals:           IStorageUsage
  tracking_health?: ITrackingHealth
  by_workspace:     IStorageWorkspaceUsage[]
}

/** Instalador do app desktop para Windows, publicado em GitHub Releases. */
export interface IDesktopInstaller {
  versao: string
  url: string
  tamanho: number
  publicado_em: string
  nome: string
}

// ── Tokens de acesso (API) ───────────────────────────────────────────────────
//
// Contrato de `/auth/tokens`: um token dá a um agente ou integração o que a
// conta do dono já pode fazer — nunca mais que isso. O segredo só viaja na
// resposta do POST (`ApiTokenCreated.token`), uma única vez; a listagem traz
// apenas o `token_prefix`.

export type ApiTokenScope =
  | "workflows:read"
  | "workflows:write"
  | "runs:execute"
  | "triggers:manage"
  | "drive:read"
  | "drive:write"

export type ApiTokenStatus = "active" | "expired" | "revoked"

/** Validades aceitas pelo POST, em dias. */
export type ApiTokenExpiresInDays = 30 | 90 | 180 | 365

export interface ApiToken {
  id: string
  name: string
  /** Primeiros caracteres do segredo, para reconhecer o token na lista. */
  token_prefix: string
  scopes: ApiTokenScope[]
  /** `null` = todos os workspaces do dono, inclusive os que ele entrar depois. */
  workspace_ids: string[] | null
  expires_at: string
  last_used_at: string | null
  revoked_at: string | null
  created_at: string
  status: ApiTokenStatus
}

export interface ApiTokenCreate {
  name: string
  scopes: ApiTokenScope[]
  workspace_ids: string[] | null
  expires_in_days: ApiTokenExpiresInDays
}

/** Resposta do POST: o token mais o segredo em claro, mostrado UMA vez. */
export interface ApiTokenCreated extends ApiToken {
  token: string
}

// ── Assistente ─────────────────────────────────────────────────────────────────

export interface IAssistenteCota {
  /** Tokens consumidos na janela atual. */
  gasto: number
  teto: number
  /** Quanto falta para a janela reabrir; nulo se ela ainda não começou. */
  reabre_em_segundos: number | null
}

/**
 * O que o painel consulta antes de aparecer na tela. `ativo: false` é um
 * estado, não um erro: a instalação simplesmente não configurou a chave, e o
 * `motivo` diz o que falta.
 */
export interface IAssistenteEstado {
  ativo: boolean
  motivo?: string | null
  cota?: IAssistenteCota | null
  /** O plano que dá o teto desta pessoa, numa instalação com planos (uma
   *  extensão); `null` sem eles. */
  plano?: string | null
  /** A instalação tem o que vender (uma extensão de planos, com provedor de
   *  pagamento). Sem isto, a oferta da cota cheia viraria um beco. */
  assinaturas_ativas?: boolean
}

// ── Meu (recortes por pessoa) ────────────────────────────────────────────────

/**
 * Um agendamento na lista da pessoa (GET /me/schedules): um por linha, entre
 * todos os workspaces dela. `next_run_at` nulo é "pausado" quando `active` é
 * false, ou "recém-criado" (≤30 s) quando true. "Pausado" tem duas causas — o
 * `active` do agendamento ou o `flag_ative` do workflow desligado —, por isso os
 * dois campos vêm juntos.
 */
export interface IAgendamentoMeu {
  job_id: string
  id_hash: string
  active: boolean
  strategy: "cron" | "interval" | "rrule" | (string & {})
  cron_expression?: string | null
  interval?: number | null
  unit?: string | null
  rrule_expression?: string | null
  timezone?: string | null
  // Sempre presentes na resposta (Pydantic serializa o Optional como null), e é o
  // que `resumirAgendamento` (de gatilho.ts) espera — nulável, não opcional.
  next_run_at: string | null
  last_run_at: string | null
  retry_count: number
  workflow_id: string
  workflow_name: string
  flag_ative: boolean
  workspace_id?: string | null
  /** Proveniência do fluxo (usuario|assistente), para o selo "assistente". */
  origem?: string
}

/**
 * A página + o TOTAL de `GET /me/schedules` — o MESMO envelope de
 * `IConversaLista`. A rota tem teto (200 por página); sem o total ela truncava
 * em silêncio e quem via 200 linhas concluía que eram todas.
 */
export interface IAgendamentosMeus {
  itens: IAgendamentoMeu[]
  total: number
}

// ── Assistente da Home (conversas) ───────────────────────────────────────────

/** Uma linha da lista de conversas (GET /assistente/conversas). */
export interface IConversaResumo {
  id: string
  titulo?: string | null
  workflow_id?: string | null
  tokens_total: number
  created_at?: string | null
  updated_at?: string | null
}

export interface IConversaLista {
  itens: IConversaResumo[]
  total: number
}

/** Um quadro do replay — o MESMO vocabulário do SSE (`tool_result` nunca sai). */
export interface IQuadroDoReplay {
  tipo: string
  dados: Record<string, unknown>
}

/** O replay de uma conversa (GET /assistente/conversas/{id}), para o painel reaplicar. */
export interface IConversaDetalhe {
  id: string
  titulo?: string | null
  workflow_id?: string | null
  quadros: IQuadroDoReplay[]
}

/**
 * Uma camada do globo (GET /assistente/camadas/{artifact_id}). `tipo` decide como a
 * web carrega: `geojson` (fetch da `download_url` pré-assinada → FeatureCollection
 * em memória), `mvt` (tiles em `/terra/assistente/tiles/…`, o par vem em `mvt`), ou
 * `indisponivel` (sem prévia; `hint` diz por quê). `bbox` só enquadra com segurança
 * quando `crs` é EPSG:4326.
 */
export interface ICamadaDoGlobo {
  artifact_id: string
  nome: string
  output_key?: string | null
  format?: string | null
  tipo: "geojson" | "mvt" | "indisponivel"
  available: boolean
  download_url?: string | null
  url_expires_in?: number | null
  mvt?: { workflow_id?: string; layer_key?: string } | null
  bbox?: number[] | null
  crs?: string | null
  geometry_type?: string | null
  features?: number | null
  size_bytes?: number | null
  /** O arquivo de origem pode ser baixado — ver `baixavel` em `schemas/assistente.py`. */
  baixavel?: boolean
  hint?: string | null
  workflow_id?: string | null
  run_id?: string | null
  expires_at?: string | null
}


// ── Modelo do assistente ─────────────────────────────────────────────────────
//
// O painel do admin: o modelo em uso e o catálogo do provedor. Uma extensão
// (`web/extensoes`) pode somar campos a ele.

export interface IModeloDoCatalogo {
  id: string
  nome: string
  /** `null`, e NUNCA 0: um modelo sem preço conhecido não pode aparecer como
   *  gratuito numa tabela de custo — é a leitura que faria escolher errado. */
  entrada_por_milhao: number | null
  saida_por_milhao: number | null
  contexto: number | null
}

export interface ISituacaoDoModelo {
  modelo: string
  /** `ambiente` = ninguém escolheu ainda, vale `ASSISTENTE_MODELO`. Os dois
   *  estados pedem botões diferentes: um oferece definir, o outro oferece
   *  voltar ao padrão. */
  origem: "banco" | "ambiente"
  definido_por: string | null
  definido_em: string | null
  padrao_do_ambiente: string
}

export interface IPainelDoModelo {
  atual: ISituacaoDoModelo
  catalogo: IModeloDoCatalogo[]
  /** Por que o catálogo veio vazio. Provedor fora do ar não pode derrubar a
   *  tela — mas a tela precisa dizer o que houve. */
  catalogo_indisponivel: string | null
}

// ── Envelope de resposta do service ──────────────────────────────────────────

export interface IResponse<T> {
  success: boolean
  data?: T
  error?: {
    message?: string
    name: "AxiosError" | (string & {})
    /** Código de domínio da API (`error` no corpo), quando houver. */
    code?: string
    /** 409 da política de execução: workspaces cujo nível principal esvaziaria. */
    workspaces?: { workspace_id: string; workspace_name: string }[]
  },
  status: number
}

// ── Nós — catálogo (GET /nodes) e runtime do canvas ──────────────────────────

export interface INodePortAPI {
  name: string
  /** Tipo de dado que a porta aceita/emite (contrato TIPOS_DE_CAMPO). */
  type?: string
  description?: string
}

/**
 * Campos compartilhados entre todas as representações de um nó.
 *
 * O projeto tem 3 "shapes" de nó que variam conforme o contexto:
 * - `INodesAPI` — catálogo vindo do backend (GET /nodes) com schema dos campos
 * - `INodes` — runtime no canvas (ReactFlow) com valores + schema resolvido
 * - `INodesDefinition` — formato de persistência (definition.nodes no DB)
 *
 * Esta interface agrupa o que é comum aos 3 para evitar drift de tipagem.
 */
export interface INodeBase {
  /** Rótulo customizado — preenchido quando o usuário renomeia o nó no canvas */
  alias?: string
  /** Categoria do nó (e.g. "trigger", "action", "control", "datasource") */
  type: string
}

/**
 * Nó no catálogo do backend (resposta de GET /nodes).
 *
 * Define o **schema** do nó: quais propriedades aceita, tipos, descrições.
 * É usado pelo canvas para construir o drawer de nós e validar inputs.
 *
 * - `properties`: array de *schemas* de campo (não valores).
 * - Não tem `id` nem `position` (é um template, não uma instância).
 */
export interface INodesAPI<T = ActionsType | TriggersType | ControlsType | unknown>
  extends INodeBase, Record<string, unknown> {
  name: T
  description: string
  alias: string
  properties: INodesPropertyAPI[]
  /** Se true, este nó exige uma credencial para executar */
  requires_credential?: boolean
  /**
   * Campos de saída do nó — a fonte única e tipada do contrato (A13). Cada
   * campo é uma chave que uma aresta pode transportar (`from_key`); os que
   * têm `port: true` ganham ponto de conexão próprio no canvas (2+ deles ⇒
   * handles nomeados). Quem deriva os handles é `portasDeSaida`
   * (utils/node-ports).
   */
  outputs?: INodeOutputField[]
  /** Portas de entrada nomeadas (apenas nós binários, ex: [{name:"layerA"},{name:"layerB"}]) */
  inputs?: INodePortAPI[]
  /**
   * As entradas são declaradas pelo USUÁRIO, na propriedade `ports`, e não
   * fixas no catálogo. Quem monta os pontos de conexão é `portasDeEntrada`
   * (workflow/index.tsx), lendo `properties.ports` em vez de `inputs`.
   */
  dynamic_inputs?: boolean
  /**
   * As saídas são declaradas pelo USUÁRIO, na propriedade `output_vars`, e não
   * fixas no catálogo. Quem as monta é `saidasDoNo` (utils/node-ports).
   */
  dynamic_output?: boolean
  /**
   * As saídas vêm da propriedade `ports` — cada porta é um ponto de conexão de
   * saída próprio (ex.: o SubWorkflowInput expõe as chaves de entrada do
   * sub-fluxo). Simétrico ao `dynamic_inputs`, no lado da saída; quem monta é
   * `portasDeSaida` (utils/node-ports).
   */
  outputs_from_ports?: boolean
  /**
   * Nó de RAMO (Conditional, JinjaBranch, ChangeDetector): os pontos de saída
   * são `true`/`false` — roteiam a execução — e não os campos de `outputs`.
   */
  branches?: boolean
}

/**
 * Nó no runtime do canvas (dentro de `Node<INodes>` do ReactFlow).
 *
 * Combina **valores** preenchidos pelo usuário com **schema** resolvido do
 * catálogo — usado pelos componentes do canvas para renderizar e editar.
 *
 * - `properties`: Record de valores (preenchidos pelo usuário).
 * - `fields`: array de schemas resolvidos do INodesAPI (para o form).
 * - `id` e `position` vivem no Node wrapper do ReactFlow, não aqui.
 */
export interface INodes<T = ActionsType | TriggersType | ControlsType | (string & {})>
  extends INodeBase, Record<string, unknown> {
  name: T
  description: string
  alias: string
  properties: Record<string, string>
  fields: INodesPropertyAPI[]
  /** Se true, este nó exige uma credencial para executar */
  requires_credential?: boolean
  /** Pontos de conexão de SAÍDA desta instância (derivados do catálogo). */
  outputs?: INodePortAPI[]
  inputs?: INodePortAPI[]
  /** Campos de saída do catálogo (`INodesAPI.outputs`) — o que uma aresta pode carregar. */
  saidas?: INodeOutputField[]
  /** O nó roteia por ramos true/false (ver INodesAPI.branches). */
  branches?: boolean
}

export interface INodeOutputField {
  name: string
  type?: string
  description?: string
  /** O campo tem ponto de conexão próprio no canvas. */
  port?: boolean
}

export interface ISelectOption {
  value: string
  label: string
}

/**
 * Regra de visibilidade condicional de um campo: só é exibido quando o valor
 * atual de `field` está em `in`. Um array de regras é combinado com AND.
 */
export interface IVisibleWhen {
  field: string
  in: (string | number | boolean)[]
}

export interface INodesPropertyAPI {
  name: string
  /** Label exibido na UI. Quando ausente, usa name. */
  label?: string
  type: "string" | "object" | "number" | "integer" | "boolean" | "code" | "credential" | "drive" | "artifact" | "sql" | "select" | "ports" | "chips" | "keyvalue"
  /** Campo que espera NOME DE COLUNA. O valor é a porta de entrada de onde o
   *  dado vem, ou "*" para todas — o editor sugere os nomes vistos na última
   *  execução daquele lado. */
  suggest_columns?: string | null
  default: unknown,
  description: string | null
  /** Tipos de credencial compatíveis — apenas quando type == "credential" */
  credential_types?: string[]
  /** Extensões de arquivo permitidas — apenas quando type == "drive" */
  drive_extensions?: string[]
  /** Opções para type == "select" */
  options?: ISelectOption[]
  /** Visibilidade condicional (declarativa). Regra única ou lista (AND). */
  visibleWhen?: IVisibleWhen | IVisibleWhen[]
  /** O execute() recusa vazio — o rótulo ganha asterisco (sinalização, não bloqueio). */
  required?: boolean
  /** Exemplo do formato esperado, exibido no input vazio. */
  placeholder?: string
}

// ── Workflows — persistência, agendamento e grupos ───────────────────────────

/**
 * Nó no formato de persistência (gravado em `workflow.definition.nodes` no DB).
 *
 * Representa o **estado serializável** mínimo de um nó — o que precisa ser
 * restaurado ao reabrir o workflow. Schema (fields, outputs, saidas)
 * vem do catálogo `INodesAPI` no load time, não é persistido aqui.
 */
export interface INodesDefinition extends INodeBase {
  id: string
  name: ActionsType | TriggersType | ControlsType | (string & {})
  properties: Record<string, string>
  position: {
    x: number
    y: number
  }
}

export interface IEdgeDefinition {
  source: string
  target: string
  /**
   * Ramo de roteamento de um nó condicional. SOMENTE para handles "true"/"false"
   * — antes qualquer handle nomeado caía aqui como `condition: false`, o que
   * destruía o id da porta e fazia a aresta sumir do canvas ao reabrir.
   */
  condition?: boolean
  /**
   * Id do Handle de saída do React Flow (ex: "output", "metadata", "true").
   * Não é redundante com `from_key`: coincidem quando o handle é uma porta de
   * dado, mas divergem em nó condicional (handle "true", from_key "output") e
   * em nó de saída única com picker (handle null, from_key "crs").
   */
  source_handle?: string
  /** Chave do output do nó pai a ser extraída (ex: "file_a", "output") */
  from_key?: string
  /** Chave com que o valor chega no inputs do nó filho (ex: "layerA", "layerB") */
  to_key?: string
}

/** Uma definition parcial como as propostas do assistente carregam:
 *  só nós e arestas, sem viewport. É o pedaço de `IWorkflow["definition"]`
 *  que trafega entre o motor e as duas superfícies. */
export interface CanvasDefinition {
  nodes?: INodesDefinition[]
  edges?: IEdgeDefinition[]
}

export interface IPinNodeMeta {
  node_id: string
  pinned_at: string | null
  expires_at: string | null
  ttl_hours: number | null
  expired: boolean
}

/**
 * Resumo do agendamento que a listagem traz (spec docs/specs/projetos.md §2.1).
 * `next_run_at` nulo com `active` = true é "recém-criado, o agendador ainda
 * calcula" (≤30 s); com `active` = false é "pausado".
 */
export interface IWorkflowSchedule {
  active: boolean
  next_run_at: string | null
  last_run_at: string | null
  strategy: "cron" | "interval" | "rrule" | (string & {})
  cron_expression?: string | null
  interval?: number | null
  unit?: string | null
  rrule_expression?: string | null
  timezone?: string | null
}

/**
 * Aviso sobre o agendamento gerado por um save (workflow inativo, expressão
 * inválida). Espelha `ScheduleNotice` do backend; o editor o mostra como toast.
 */
export interface IScheduleNotice {
  code: "workflow_inactive" | "invalid_schedule" | (string & {})
  severity: "warning" | "info"
  message: string
  details?: Record<string, unknown>
}

export interface IWorkflow {
  id?: number
  id_hash: string
  flag_ative: boolean,
  name: string
  description: string
  version: string
  priority: number,
  definition: {
    nodes: INodesDefinition[],
    edges: IEdgeDefinition[],
    viewport?: { x: number; y: number; zoom: number }
  },
  created_by_id: string,
  updated_by_id: string,
  // Campos adicionados na última versão do backend
  workspace_id?: string
  group_id?: string | null
  params_schema?: Record<string, IParamSchema>
  notification_url?: string | null
  portal_access?: "disabled" | "public" | "private"
  portal_shared_with?: string[] | null
  has_publish_map?: boolean
  /** Declara contrato de sub-fluxo (nó Saída do Sub-Workflow): existe para ser
   *  chamado por outro workflow, e em geral não tem gatilho próprio. */
  is_subworkflow?: boolean
  /** Gatilhos presentes na definição (spec projetos §2.1). Nenhum = "só manual". */
  has_webhook_trigger?: boolean
  has_schedule_trigger?: boolean
  has_file_trigger?: boolean
  has_geofence_trigger?: boolean
  /** Proveniência do fluxo: "usuario" (padrão) ou "assistente" (criado pelo
   *  assistente da Home, escondido das listagens por padrão). */
  origem?: "usuario" | "assistente" | (string & {})
  /** Agendamento do workflow, quando há um nó ScheduleTrigger aplicado. */
  schedule?: IWorkflowSchedule | null
  created_by_username?: string | null
  updated_by_username?: string | null
  pinned_outputs?: Record<string, Record<string, unknown>> | null
  pin_metadata?: Record<string, { pinned_at: string; expires_at: string | null; ttl_hours: number | null }> | null
  created_at?: string
  updated_at?: string
  deleted_at?: string | null
  /** Avisos do agendamento deste save (vazio no caso normal). */
  schedule_notices?: IScheduleNotice[]
}

export interface IWorkflowGroup {
  id: number
  id_hash: string
  name: string
  description?: string | null
  workspace_id?: string | null
  /** Ordem escolhida a mão na tela de Projetos. */
  position?: number
  /** Todos os workflows não excluídos do grupo (inativos inclusive). */
  workflow_count: number
  /** Só os ativos. */
  active_count?: number
  created_at: string
  updated_at: string
}

export interface IParamSchema {
  type: "string" | "number" | "boolean" | "object"
  description?: string
  default?: unknown
  required?: boolean
}

// ── Credenciais ──────────────────────────────────────────────────────────────

export interface ICredentials {
  id: string
  name: string
  type: string
  description?: string | null
  tags?: string[] | null
  /** id_hash do criador — a UI usa para distinguir "minha" de "compartilhada comigo". */
  owner_id?: string | null
  /** Se preenchido, a credencial é compartilhada com os membros deste workspace. */
  workspace_id?: string | null
  created_at: string
  updated_at: string
  last_used_at?: string | null
  expires_at?: string | null
}

export interface ICredentialsRequest extends ICredentials{
  data: Record<string, string>
}

export interface ICredentialFieldSchema {
  key: string
  label: string
  type: "text" | "password" | "number" | "select"
  required: boolean
  placeholder?: string
  default?: string
  options?: string[]
  description?: string
}

export interface ICredentialTypeSchema {
  type: string
  label: string
  description: string
  node_types: string[]
  fields: ICredentialFieldSchema[]
}

// ── Saúde do sistema ─────────────────────────────────────────────────────────

/** GET /admin/health: só a whitelist de webhook, que é o que a tela de
 *  Configurações lê. */
export interface ISystemHealth {
  webhook_whitelist: string[]
}
