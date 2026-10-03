// service/types.ts
//
// The SINGLE home for the web's types that mirror the API. The
// `web/interface/` directory was absorbed here in F2 of the simplification
// (docs/specs/simplification.md, A7): two homes for the same kind of thing
// was an invitation for a third.
import type { ActionsType, ControlsType, TriggersType } from "@/consts/WorkflowIcons"

export interface IWorkflowVersion {
  id: number
  version_number: number
  workflow_hash: string
  created_at: string
  change_note: string | null
}

// "mcp" = triggered by an agent via the MCP server (personal access token).
export type TriggerSource = "manual" | "retry" | "webhook" | "schedule" | "mcp"

/** Category of the error that closed the run: the flow taxonomy + server categories. */
export type ErrorCategory =
  | "user" | "validation" | "timeout" | "resource" | "transient" | "internal"
  | "no_executor" | "executor_lost" | "isolation" | "dispatch"

export interface ITopFailingWorkflow {
  workflow_hash: string
  workflow_name: string | null
  failure_count: number
  total_runs: number
  /** Failures ÷ total for the workflow in the window. */
  failure_rate: number
  last_error: string | null
  last_error_category: ErrorCategory | string | null
  last_failed_at: string | null
}

/** A run in progress for longer than expected for the workflow. */
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

/** The moment of the query, with no window (docs/specs/metrics-history.md §3.1). */
export interface INowBlock {
  running: number
  pending: number
  stuck_count: number
  stuck: IStuckRun[]
  executors: { online: number; total: number }
  queued_on_executors: number | null
  /** Admin only; null for everyone else. */
  overdue_acks: number | null
}

export interface IObservabilityMetrics {
  period_days?: number
  total_workflows: number
  active_workflows: number
  total_runs: number
  failed_runs: number
  /** Completed ÷ (completed + failures) in the window; 0 without a denominator. */
  success_rate: number
  avg_duration_seconds: number
  runs_last_24h: number
  runs_last_7d: number
  runs_prev_7d: number
  success_rate_prev_7d: number | null
  by_status: { success: number; failed: number; running: number; other: number; cancelled?: number; pending?: number }
  top_failing_workflows: ITopFailingWorkflow[]
  // ── new (History redesign) ──
  success_runs?: number
  cancelled_runs?: number
  running_runs?: number
  pending_runs?: number
  /** Previous window of the same size. */
  prev_period?: {
    total_runs: number; success_runs: number; failed_runs: number; success_rate: number
    p50_seconds: number | null
  }
  /** Only completed ones with duration > 0; null without data. */
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
  // Populated only when the requester is an admin (the backend returns them
  // via _resolve_workflow_meta in observability_service.py).
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
  /** Policy tier it ran on; null for runs predating the column. */
  dispatch_tier?: DispatchTier | null
  // For any user in scope (the workspace filter already guarantees access).
  workflow_name?: string
  workspace_id?: string | null
  workspace_name?: string | null
  executor_id?: string | null
  /** Friendly name of the executor; null without a host. */
  executor_name?: string | null
  trigger_source?: TriggerSource | null
  triggered_by?: string | null
  triggered_by_username?: string | null
  error_category?: ErrorCategory | string | null
  schedule_id?: number | null
  /**
   * Origin of the WORKFLOW ("usuario" | "assistente"), not of the trigger — that
   * one is `trigger_source`. `null` when the workflow was permanently deleted.
   */
  workflow_origem?: string | null
  // Populated only when the requester is an admin.
  workflow_active?: boolean
  owner_username?: string | null
}

export interface IExecutorMetrics {
  /** null on the row for runs without an executor (dispatch failures). */
  agent_host: string | null
  display_name: string
  total_runs: number
  success_runs: number
  failed_runs: number
  success_rate: number
  avg_duration_seconds: number | null
  last_run_at: string | null
  // ── new (History redesign) ──
  executor_id?: string | null
  executor_type?: "default" | "dedicated" | null
  is_default?: boolean
  status?: string | null
  online?: boolean
  /** null when the executor does not publish capacity. */
  capacity?: { running: number; queued: number; max_concurrent: number; max_queue: number } | null
  p50_seconds?: number | null
  /** "Sem executor" (no executor) row: runs that failed before reaching an executor. */
  unassigned?: boolean
}

/** A row of the "By workflow" view (`GET /observability/metrics/workflows`). */
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
  /** Who created the workflow: "usuario" | "assistente" (the list's badge). */
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
  /** The workflow's p50 over the last 90 days; null without data. */
  typical_seconds?: number | null
  // Populated only when the requester is an admin.
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
    /** Columns per output port, when the executor published them (>= 2.4.0 and
     *  without the stat's 8KB cut). Rehydrates the column-name suggestion
     *  when opening the workflow — without this key the type hid data the
     *  backend always returned. */
    output_columns?: Record<string, string[]> | null
    /** The executor marked the stat as truncated (8KB cut) — the column lists
     *  may be reduced to the first 50. */
    __truncated__?: boolean
  }>
}

/** A raw event from the run channel, as persisted in the Redis history. */
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
  /** true when the history has already expired in Redis (1h TTL) or is empty. */
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
   * Where the CONTENT lives.
   *
   * `minio` is the usual case. `executor` means the bytes never left the
   * machine — an output node with the "Manter apenas no executor" (keep on the
   * executor only) locality, or that machine's policy. There is no download.
   *
   * The API already returned the field; it was the type that did not declare
   * it, and the screen guessed via `executor_id && !size_bytes` — a heuristic
   * that fails precisely on local artifacts, because they DO have a size.
   */
  content_location?: "minio" | "executor"
  created_at:       string | null
  expires_at:       string | null
}

/**
 * Filters for `GET /artifacts/`.
 *
 * `limit`/`offset` exist because the screen downloaded the user's whole
 * artifact table and paginated on the client — in a workspace with history
 * that freezes the tab for seconds. `search` and `workspace_id` are the same
 * filters the screen applied in memory, pushed down to SQL.
 */
export interface IArtifactListParams {
  workflow_id?:    string
  run_id?:         string
  fmt?:            string
  /** Run x publication slice — what the screen called tabs. */
  kind?:           "execution" | "publication"
  search?:         string
  workspace_id?:   string
  include_pinned?: boolean
  limit?:          number
  offset?:         number
}

export interface IArtifactListResponse {
  items:  IArtifactItem[]
  /** Total for the whole filter, not the page — feeds "see more". */
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
  /** Truly nullable: the upload confirm can store the metadata without a
   *  size (and the HEAD does not always respond), as `WorkspaceFileOut` declares.
   *  Without the `| null` here the next consumer formatted an `undefined` with
   *  no warning from the compiler. */
  size:          number | null
  uploaded_by:   string | null
  created_at:    string
  updated_at:    string | null
  /**
   * Last CONTENT write. An overwritten file keeps the original created_at.
   * Distinct from `updated_at`, which any update of the row triggers
   * (renaming, for example) and which is NOT triggered when the overwrite does
   * not change any field — showing it did not explain the order the user saw.
   */
  content_written_at: string | null
  /**
   * Where the CONTENT lives.
   *
   * `minio` is the usual case. `executor` means the file was cataloged by
   * GeoSync in catalog mode (LGPD): the platform knows the name, the type and
   * the spatial metadata, but the bytes never left the executor's machine —
   * and that is why there is no download.
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

/** The body's `error` when the Drive rejects an upload because of the file
 *  itself — the subclasses of `FileValidationError` and the `FileTooLargeError`
 *  in `app/core/exceptions.py`. Arrives in `IResponse.error.code`. The
 *  rejection is classified by it (and by the status), never by the phrase,
 *  which may change. */
export type UploadErrorCode =
  | "extension_not_allowed"
  | "dangerous_inner_extension"
  | "empty_file"
  | "file_too_large"

/** `page`/`page_size` always existed in the backend and no consumer sent them:
 *  files past the 50th were unreachable from the UI. */
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
  /** Executors' host (AGENTS_URL); empty when the server does not know it. */
  server_url: string
  /** This installation's site (FRONTEND_URL), where install.sh is downloaded from. */
  public_url: string
}


export interface IExecutorUserAssignment {
  user_id:     string
  username:    string
  email:       string
  assigned_at: string
  assigned_by: string | null
}

// ── Admin: User Management ───────────────────────────────────────────────────

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
 * Workspace as the backend returns it in GET /workspaces/ (WorkspaceOut).
 *
 * Re-exported as `Workspace` by WorkspaceContext, which owns the active
 * workspace's state — components keep importing from there.
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
/** pool = no tier 1 · isolated = tier 1 + terminal fail · dedicated_pool = tier 1 + terminal pool */
export type PolicyMode = "pool" | "isolated" | "dedicated_pool"

/** Member of an execution policy tier ( GET /workspaces/{id}/executors ). */
export interface IPolicyMember {
  id_hash:       string
  name:          string
  executor_type: "default" | "dedicated"
  status:        string
  tier:          1 | 2
  /** null = unknown presence (Redis down / reconnecting) */
  online:        boolean | null
  capacity:      { queued?: number; running?: number; max_concurrent?: number; max_queue?: number } | null
}

/** A row of the "Piso de isolamento" (isolation floor) admin screen (GET /admin/workspaces/policies). */
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
 * The workspace's execution policy (docs/specs/executor-isolation-routing.md).
 * `policy_routing_enabled=false` means the server still routes through the
 * legacy path — the screen shows the policy as a preview.
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
 * Row of the member list ( GET /workspaces/{id}/members ).
 *
 * The owner ALWAYS comes first, with `role: "owner"` — a synthetic row, built
 * at read time, because the owner has no record in `workspace_members`. It is
 * not an assignable role: the backend rejects PUT/DELETE on it.
 */
export interface IWorkspaceMember {
  user_id:   string
  username:  string
  email:     string
  /** "owner" | "admin" | "operator" | "editor" | "viewer" */
  role:      string
  joined_at: string
}

/** Result of GET /workspaces/users/search — already registered users. */
export interface IUserSearchResult {
  id_hash:  string
  username: string
  email:    string
}

/**
 * A workflow of the workspace that sends a webhook, and whether the current
 * allowlist lets it through. `allowed` comes from the backend using the SAME
 * function the consumer applies when firing — it is what the screen can
 * promise without lying.
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
 * An empty `allowlist` means "no additional policy" — every webhook that passes
 * the SSRF check is accepted. When filled in, everything outside it is
 * silently blocked after the run.
 */
export interface IWorkspaceNotifications {
  allowlist: string[]
  workflows: IWorkspaceNotificationTarget[]
}

/**
 * An impact of moving a workflow between workspaces.
 *
 * The move never fails on a broken dependency: what stops working in the
 * destination arrives here. `message` already comes in pt-BR, ready to
 * display; `details` carries the ids involved.
 */
export interface IWorkflowMoveWarning {
  code:     string
  severity: "warning" | "info"
  message:  string
  details:  Record<string, unknown>
}

/**
 * Response of POST /workflows/{id}/move — and of /move/preview, where it
 * describes what WOULD HAPPEN (`dry_run: true`) without having written anything.
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
 * Trash row ( GET /admin/workspaces/trash ). Admin-only: lists what any user
 * of the platform deleted, which is why it carries the owner's data.
 */
export interface IWorkspaceTrash {
  id_hash:         string
  name:            string
  description:     string | null
  owner_id:        string | null
  owner_username:  string | null
  owner_email:     string | null
  deleted_at:      string
  /** How many workflows come back if this workspace is restored. */
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
   * active  — live workspace
   * trashed — in the trash (soft delete): only the admin has access, via /admin/settings
   * purged  — row removed from the database: orphaned data, nobody can reach it anymore
   */
  workspace_state?: "active" | "trashed" | "purged"
  /** true for trashed and purged. Kept for the table's visual marking. */
  workspace_deleted?: boolean
}

/**
 * Contract (public API) of a workflow for use as a sub-workflow.
 *
 * The server extracts it from SubWorkflowInput (inputs) and SubWorkflowOutput
 * (outputs) — keys come from the edges connected to those nodes.
 * `has_input_node` / `has_output_node` indicate whether the contract is declared.
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
 * Entry of the admin node list ( GET /admin/nodes ).
 *
 * Reflects NODE_REGISTRY merged with SystemConfig.disabled_nodes — when
 * `enabled=false`, `reason`/`disabled_at`/`disabled_by` come populated.
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
 * Health indicators for storage tracking. The server exposes them via
 * /admin/storage to give visibility into silent drift (abandoned pending,
 * artifact without size, orphans).
 *
 * Optional field for compatibility with mixed deploys during rollout — the UI
 * does not render the section if it comes undefined.
 */
export interface ITrackingHealth {
  pending_drive_files:          number
  pending_drive_bytes:          number
  null_size_artifacts:          number
  /** Subset of null_size: too old for the retry — they will not resolve. */
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
  /** Artifacts living on the disk of an OFFLINE executor: the removal order
   *  was not delivered, so the row stays and the next pass tries again. */
  pending_executor?:    number
  /** Local artifacts without executor_id/local_path — nobody to send the
   *  order to; the row stays so the file's trail is not lost. */
  skipped_sem_rastro?:  number
  /** Drive files cataloged on the executor: preserved by policy (they belong
   *  to the user, in the folder they sync, and take up no platform
   *  storage). */
  skipped_catalogados?: number
}

export interface IStorageUsageAdmin {
  totals:           IStorageUsage
  tracking_health?: ITrackingHealth
  by_workspace:     IStorageWorkspaceUsage[]
}

/** Desktop app installer for Windows, published on GitHub Releases. */
export interface IDesktopInstaller {
  versao: string
  url: string
  tamanho: number
  publicado_em: string
  nome: string
}

// ── Access tokens (API) ──────────────────────────────────────────────────────
//
// Contract of `/auth/tokens`: a token gives an agent or integration what the
// owner's account can already do — never more than that. The secret only
// travels in the POST response (`ApiTokenCreated.token`), a single time; the
// listing brings only the `token_prefix`.

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
  /** First characters of the secret, to recognize the token in the list. */
  token_prefix: string
  scopes: ApiTokenScope[]
  /** `null` = all of the owner's workspaces, including those they join later. */
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

/** POST response: the token plus the plaintext secret, shown ONCE. */
export interface ApiTokenCreated extends ApiToken {
  token: string
}

// ── Assistente ─────────────────────────────────────────────────────────────────

export interface IAssistenteCota {
  /** Tokens consumed in the current window. */
  gasto: number
  teto: number
  /** How long until the window reopens; null if it has not started yet. */
  reabre_em_segundos: number | null
}

/**
 * What the panel queries before appearing on screen. `ativo: false` is a
 * state, not an error: the installation simply has not configured the key, and
 * `motivo` says what is missing.
 */
export interface IAssistenteEstado {
  ativo: boolean
  motivo?: string | null
  cota?: IAssistenteCota | null
  /** The plan that sets this person's ceiling, on an installation with plans (an
   *  extension); `null` without them. */
  plano?: string | null
  /** The installation has something to sell (a plans extension, with a payment
   *  provider). Without this, the full-quota offer would be a dead end. */
  assinaturas_ativas?: boolean
}

// ── Mine (per-person slices) ─────────────────────────────────────────────────

/**
 * A schedule in the person's list (GET /me/schedules): one per row, across all
 * of their workspaces. A null `next_run_at` is "paused" when `active` is
 * false, or "just created" (≤30 s) when true. "Paused" has two causes — the
 * schedule's `active` or the workflow's `flag_ative` turned off —, which is why
 * the two fields come together.
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
  // Always present in the response (Pydantic serializes Optional as null), and it
  // is what `resumirAgendamento` (from gatilho.ts) expects — nullable, not optional.
  next_run_at: string | null
  last_run_at: string | null
  retry_count: number
  workflow_id: string
  workflow_name: string
  flag_ative: boolean
  workspace_id?: string | null
  /** Provenance of the workflow (usuario|assistente), for the "assistente" badge. */
  origem?: string
}

/**
 * The page + the TOTAL of `GET /me/schedules` — the SAME envelope as
 * `IConversaLista`. The route has a ceiling (200 per page); without the total it
 * truncated silently and whoever saw 200 rows concluded that was all of them.
 */
export interface IAgendamentosMeus {
  itens: IAgendamentoMeu[]
  total: number
}

// ── Home assistant (conversations) ───────────────────────────────────────────

/** A row of the conversation list (GET /assistente/conversas). */
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

/** A replay frame — the SAME vocabulary as the SSE (`tool_result` never comes out). */
export interface IQuadroDoReplay {
  tipo: string
  dados: Record<string, unknown>
}

/** The replay of a conversation (GET /assistente/conversas/{id}), for the panel to reapply. */
export interface IConversaDetalhe {
  id: string
  titulo?: string | null
  workflow_id?: string | null
  quadros: IQuadroDoReplay[]
}

/**
 * A globe layer (GET /assistente/camadas/{artifact_id}). `tipo` decides how the
 * web loads it: `geojson` (fetch of the presigned `download_url` → in-memory
 * FeatureCollection), `mvt` (tiles at `/terra/assistente/tiles/…`, the pair comes
 * in `mvt`), or `indisponivel` (no preview; `hint` says why). `bbox` only frames
 * safely when `crs` is EPSG:4326.
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
  /** The source file can be downloaded — see `baixavel` in `schemas/assistente.py`. */
  baixavel?: boolean
  hint?: string | null
  workflow_id?: string | null
  run_id?: string | null
  expires_at?: string | null
}


// ── Assistant model ──────────────────────────────────────────────────────────
//
// The admin panel: the model in use and the provider's catalog. An extension
// (`web/extensoes`) can add fields to it.

export interface IModeloDoCatalogo {
  id: string
  nome: string
  /** `null`, and NEVER 0: a model without a known price cannot appear as free
   *  in a cost table — that reading is what would lead to the wrong choice. */
  entrada_por_milhao: number | null
  saida_por_milhao: number | null
  contexto: number | null
}

export interface ISituacaoDoModelo {
  modelo: string
  /** `ambiente` = nobody has chosen yet, `ASSISTENTE_MODELO` applies. The two
   *  states call for different buttons: one offers to set it, the other offers
   *  to go back to the default. */
  origem: "banco" | "ambiente"
  definido_por: string | null
  definido_em: string | null
  padrao_do_ambiente: string
}

export interface IPainelDoModelo {
  atual: ISituacaoDoModelo
  catalogo: IModeloDoCatalogo[]
  /** Why the catalog came back empty. A provider being down must not take down
   *  the screen — but the screen needs to say what happened. */
  catalogo_indisponivel: string | null
}

// ── Service response envelope ────────────────────────────────────────────────

export interface IResponse<T> {
  success: boolean
  data?: T
  error?: {
    message?: string
    name: "AxiosError" | (string & {})
    /** The API's domain code (`error` in the body), when there is one. */
    code?: string
    /** Execution policy 409: workspaces whose main tier would be emptied. */
    workspaces?: { workspace_id: string; workspace_name: string }[]
  },
  status: number
}

// ── Nodes — catalog (GET /nodes) and canvas runtime ──────────────────────────

export interface INodePortAPI {
  name: string
  /** Data type the port accepts/emits (TIPOS_DE_CAMPO contract). */
  type?: string
  description?: string
}

/**
 * Fields shared across all representations of a node.
 *
 * The project has 3 node "shapes" that vary by context:
 * - `INodesAPI` — catalog coming from the backend (GET /nodes) with the field schema
 * - `INodes` — runtime on the canvas (ReactFlow) with values + resolved schema
 * - `INodesDefinition` — persistence format (definition.nodes in the DB)
 *
 * This interface groups what is common to the 3 to avoid typing drift.
 */
export interface INodeBase {
  /** Custom label — filled in when the user renames the node on the canvas */
  alias?: string
  /** Node category (e.g. "trigger", "action", "control", "datasource") */
  type: string
}

/**
 * Node in the backend catalog (response of GET /nodes).
 *
 * Defines the node's **schema**: which properties it accepts, types, descriptions.
 * Used by the canvas to build the node drawer and validate inputs.
 *
 * - `properties`: array of field *schemas* (not values).
 * - Has no `id` or `position` (it is a template, not an instance).
 */
export interface INodesAPI<T = ActionsType | TriggersType | ControlsType | unknown>
  extends INodeBase, Record<string, unknown> {
  name: T
  description: string
  alias: string
  properties: INodesPropertyAPI[]
  /** If true, this node requires a credential to execute */
  requires_credential?: boolean
  /**
   * The node's output fields — the single, typed source of the contract (A13).
   * Each field is a key an edge can carry (`from_key`); those with
   * `port: true` get their own connection point on the canvas (2+ of them ⇒
   * named handles). The handles are derived by `portasDeSaida`
   * (utils/node-ports).
   */
  outputs?: INodeOutputField[]
  /** Named input ports (binary nodes only, e.g. [{name:"layerA"},{name:"layerB"}]) */
  inputs?: INodePortAPI[]
  /**
   * The inputs are declared by the USER, in the `ports` property, not fixed in
   * the catalog. The connection points are built by `portasDeEntrada`
   * (workflow/index.tsx), reading `properties.ports` instead of `inputs`.
   */
  dynamic_inputs?: boolean
  /**
   * The outputs are declared by the USER, in the `output_vars` property, not
   * fixed in the catalog. They are built by `saidasDoNo` (utils/node-ports).
   */
  dynamic_output?: boolean
  /**
   * The outputs come from the `ports` property — each port is its own output
   * connection point (e.g. SubWorkflowInput exposes the sub-workflow's input
   * keys). Symmetric to `dynamic_inputs`, on the output side; built by
   * `portasDeSaida` (utils/node-ports).
   */
  outputs_from_ports?: boolean
  /**
   * BRANCH node (Conditional, JinjaBranch, ChangeDetector): the output points
   * are `true`/`false` — they route the execution — and not the `outputs` fields.
   */
  branches?: boolean
}

/**
 * Node in the canvas runtime (inside ReactFlow's `Node<INodes>`).
 *
 * Combines **values** filled in by the user with the **schema** resolved from
 * the catalog — used by the canvas components to render and edit.
 *
 * - `properties`: Record of values (filled in by the user).
 * - `fields`: array of schemas resolved from INodesAPI (for the form).
 * - `id` and `position` live in ReactFlow's Node wrapper, not here.
 */
export interface INodes<T = ActionsType | TriggersType | ControlsType | (string & {})>
  extends INodeBase, Record<string, unknown> {
  name: T
  description: string
  alias: string
  properties: Record<string, string>
  fields: INodesPropertyAPI[]
  /** If true, this node requires a credential to execute */
  requires_credential?: boolean
  /** OUTPUT connection points of this instance (derived from the catalog). */
  outputs?: INodePortAPI[]
  inputs?: INodePortAPI[]
  /** Output fields from the catalog (`INodesAPI.outputs`) — what an edge can carry. */
  saidas?: INodeOutputField[]
  /** The node routes through true/false branches (see INodesAPI.branches). */
  branches?: boolean
}

export interface INodeOutputField {
  name: string
  type?: string
  description?: string
  /** The field has its own connection point on the canvas. */
  port?: boolean
}

export interface ISelectOption {
  value: string
  label: string
}

/**
 * Conditional visibility rule for a field: it is shown only when the current
 * value of `field` is in `in`. An array of rules is combined with AND.
 */
export interface IVisibleWhen {
  field: string
  in: (string | number | boolean)[]
}

export interface INodesPropertyAPI {
  name: string
  /** Label shown in the UI. When missing, uses name. */
  label?: string
  type: "string" | "object" | "number" | "integer" | "boolean" | "code" | "credential" | "drive" | "artifact" | "sql" | "select" | "ports" | "chips" | "keyvalue"
  /** Field that expects a COLUMN NAME. The value is the input port the data
   *  comes from, or "*" for all — the editor suggests the names seen in the
   *  last run on that side. */
  suggest_columns?: string | null
  default: unknown,
  description: string | null
  /** Compatible credential types — only when type == "credential" */
  credential_types?: string[]
  /** Allowed file extensions — only when type == "drive" */
  drive_extensions?: string[]
  /** Options for type == "select" */
  options?: ISelectOption[]
  /** Conditional visibility (declarative). A single rule or a list (AND). */
  visibleWhen?: IVisibleWhen | IVisibleWhen[]
  /** execute() rejects empty — the label gets an asterisk (a signal, not a block). */
  required?: boolean
  /** Example of the expected format, shown in the empty input. */
  placeholder?: string
}

// ── Workflows — persistence, scheduling and groups ───────────────────────────

/**
 * Node in the persistence format (stored in `workflow.definition.nodes` in the DB).
 *
 * Represents the minimal **serializable state** of a node — what needs to be
 * restored when reopening the workflow. The schema (fields, outputs, saidas)
 * comes from the `INodesAPI` catalog at load time; it is not persisted here.
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
   * Routing branch of a conditional node. ONLY for "true"/"false" handles —
   * before, any named handle fell in here as `condition: false`, which
   * destroyed the port id and made the edge vanish from the canvas on reopening.
   */
  condition?: boolean
  /**
   * Id of the React Flow output Handle (e.g. "output", "metadata", "true").
   * It is not redundant with `from_key`: they match when the handle is a data
   * port, but differ on a conditional node (handle "true", from_key "output")
   * and on a single-output node with a picker (handle null, from_key "crs").
   */
  source_handle?: string
  /** Key of the parent node's output to extract (e.g. "file_a", "output") */
  from_key?: string
  /** Key under which the value arrives in the child node's inputs (e.g. "layerA", "layerB") */
  to_key?: string
}

/** A partial definition like the ones the assistant's proposals carry:
 *  only nodes and edges, no viewport. It is the piece of `IWorkflow["definition"]`
 *  that travels between the engine and the two surfaces. */
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
 * Summary of the schedule that the listing brings (spec docs/specs/projects.md §2.1).
 * A null `next_run_at` with `active` = true is "just created, the scheduler is
 * still computing" (≤30 s); with `active` = false it is "paused".
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
 * Notice about the schedule produced by a save (inactive workflow, invalid
 * expression). Mirrors the backend's `ScheduleNotice`; the editor shows it as a toast.
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
  // Fields added in the latest backend version
  workspace_id?: string
  group_id?: string | null
  params_schema?: Record<string, IParamSchema>
  notification_url?: string | null
  portal_access?: "disabled" | "public" | "private"
  portal_shared_with?: string[] | null
  has_publish_map?: boolean
  /** Declares a sub-workflow contract (Sub-Workflow Output node): it exists to be
   *  called by another workflow, and generally has no trigger of its own. */
  is_subworkflow?: boolean
  /** Triggers present in the definition (projects spec §2.1). None = "manual only". */
  has_webhook_trigger?: boolean
  has_schedule_trigger?: boolean
  has_file_trigger?: boolean
  has_geofence_trigger?: boolean
  /** Provenance of the workflow: "usuario" (default) or "assistente" (created by
   *  the Home assistant, hidden from listings by default). */
  origem?: "usuario" | "assistente" | (string & {})
  /** The workflow's schedule, when a ScheduleTrigger node is applied. */
  schedule?: IWorkflowSchedule | null
  created_by_username?: string | null
  updated_by_username?: string | null
  pinned_outputs?: Record<string, Record<string, unknown>> | null
  pin_metadata?: Record<string, { pinned_at: string; expires_at: string | null; ttl_hours: number | null }> | null
  created_at?: string
  updated_at?: string
  deleted_at?: string | null
  /** Schedule notices from this save (empty in the normal case). */
  schedule_notices?: IScheduleNotice[]
}

export interface IWorkflowGroup {
  id: number
  id_hash: string
  name: string
  description?: string | null
  workspace_id?: string | null
  /** Order chosen by hand on the Projects screen. */
  position?: number
  /** All non-deleted workflows in the group (inactive ones included). */
  workflow_count: number
  /** Only the active ones. */
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
  /** The creator's id_hash — the UI uses it to tell "mine" from "shared with me". */
  owner_id?: string | null
  /** If filled in, the credential is shared with the members of this workspace. */
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

// ── System health ────────────────────────────────────────────────────────────

/** GET /admin/health: only the webhook whitelist, which is what the Settings
 *  screen reads. */
export interface ISystemHealth {
  webhook_whitelist: string[]
}
