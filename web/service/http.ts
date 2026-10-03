import axios, { AxiosError } from "axios"
import { INodesAPI } from "./types"
import { resolveAxiosError, resolveResponse } from "./resolveResponse"
import { IWorkflow } from "./types"
import { IResponse } from "./types"
import { ICredentials, ICredentialsRequest, ICredentialTypeSchema } from "./types"
import { ISystemHealth } from "./types"
import { API_URL } from "@/utils/env"
import type {
  IWorkflowVersion, IObservabilityMetrics, IWorkflowMetrics, IRunSummary,
  IRunDetail, IRunEventsResponse, IRunsByDay, IExecutorMetrics, IWorkflowMetricsRow, IArtifactSettings,
  IExecutor, IExecutorCreateRequest, IExecutorCreatedResponse, IExecutorUserAssignment,
  IExecutorEnrollmentOtpResponse, IWorkflowMoveResult, IDesktopInstaller,
  IWorkspacePolicy, IWorkspacePolicyAdmin, PolicyTerminal, IsolationFloor,
  ApiToken, ApiTokenCreate, ApiTokenCreated,
} from "./types"

// Token sincronizado pelo SessionSync em providers.tsx
let _token: string | null = null
export function setAuthToken(token: string | null) { _token = token }

// Interceptor: attaches the JWT token only to requests to the internal API (/terra)
axios.interceptors.request.use((config) => {
  if (_token && config.headers && config.url) {
    const isRelative = config.url.startsWith("/")
    const isSameOrigin = typeof window !== "undefined" && config.url.startsWith(window.location.origin)
    if (isRelative || isSameOrigin) {
      config.headers["Authorization"] = `Bearer ${_token}`
    }
  }
  return config
})

axios.interceptors.response.use((response) => response, (error: AxiosError) => Promise.reject(error))


// ── Helpers internos ────���───────────────────────────────────────────────────

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "") sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ""
}

/**
 * Identical GETs IN FLIGHT share a single request.
 *
 * The data layer (`lib/consultas.ts`, react-query; screen patterns §10) still
 * covers few screens and does not cache by default, and several places ask for
 * the same list at the same time: opening /projects fired two simultaneous
 * `GET /workflows/?workspace_id=X` (the layout's ActiveRunsProvider and the
 * page itself), and opening /workspaces fired two `GET /workspaces/`. On a
 * slow network, the time until the list appeared was that of the slower of the
 * two responses — and the backend did twice the work.
 *
 * The window is strictly "while the request is in flight": nothing is
 * memoized after it responds, so the next read is always fresh.
 */
const getsEmVoo = new Map<string, Promise<unknown>>()

/**
 * Write epoch: incremented BEFORE and AFTER every mutation, and used as the
 * prefix of the dedup key.
 *
 * Without it, the key was just the URL and the coalescing window spanned the
 * write: on /executores, with the 15s tick of `GET /executores/` already in
 * flight, the `refetch()` fired on a DELETE's success received the SAME
 * promise — a response computed on the server BEFORE the deletion. The deleted
 * card reappeared in the list right after the "Executor excluído" (executor
 * deleted) toast. Same thing on /projects, where the freshly duplicated copy
 * did not show up in the following `getProjects()`.
 *
 * With the prefix, every read requested after a write uses a new key and
 * really goes to the network; dedup still applies to the case it exists to
 * solve (two simultaneous readers on mount).
 */
let epocaEscrita = 0

// No verb here rejects: a network drop, 4xx and 5xx come back resolved, with
// `error` filled in (`resolveAxiosError`). A `try/catch` around the call is
// dead code — the screen reads the failure in `res.error` (`dadoOuAviso`, in
// lib/respostas.ts).
export function get<T>(url: string): Promise<IResponse<T>> {
  const chave = `${epocaEscrita}|${url}`
  const emAndamento = getsEmVoo.get(chave)
  if (emAndamento) return emAndamento as Promise<IResponse<T>>

  const requisicao = (async () => {
    try { return resolveResponse((await axios.get(`${API_URL}${url}`)).data) as IResponse<T> }
    catch (e) { return resolveAxiosError(e as AxiosError) as IResponse<T> }
    finally { getsEmVoo.delete(chave) }
  })()

  getsEmVoo.set(chave, requisicao)
  return requisicao
}

/** Wraps a mutation, opening a new epoch before and after: neither a read
 *  from before the write nor one fired in the middle of it can be reused by
 *  whoever reads after it has finished. */
async function mutar<T>(executar: () => Promise<IResponse<T>>): Promise<IResponse<T>> {
  epocaEscrita++
  try { return await executar() }
  finally { epocaEscrita++ }
}

export function post<T>(url: string, body?: unknown): Promise<IResponse<T>> {
  return mutar(async () => {
    try { return resolveResponse((await axios.post(`${API_URL}${url}`, body)).data) as IResponse<T> }
    catch (e) { return resolveAxiosError(e as AxiosError) as IResponse<T> }
  })
}
export function put<T>(url: string, body?: unknown): Promise<IResponse<T>> {
  return mutar(async () => {
    try { return resolveResponse((await axios.put(`${API_URL}${url}`, body)).data) as IResponse<T> }
    catch (e) { return resolveAxiosError(e as AxiosError) as IResponse<T> }
  })
}
export function patch<T>(url: string, body?: unknown): Promise<IResponse<T>> {
  return mutar(async () => {
    try { return resolveResponse((await axios.patch(`${API_URL}${url}`, body)).data) as IResponse<T> }
    catch (e) { return resolveAxiosError(e as AxiosError) as IResponse<T> }
  })
}
export function del(url: string): Promise<IResponse<undefined>> {
  return mutar(async () => {
    try { await axios.delete(`${API_URL}${url}`); return resolveResponse() as IResponse<undefined> }
    catch (e) { return resolveAxiosError(e as AxiosError) as IResponse<undefined> }
  })
}
/** DELETE that preserves the response body. Same as `del`, and likewise
 *  wrapped by `mutar` — it exists because some DELETEs return a payload and
 *  reimplementing them by hand left them outside the write epoch. */
export function delComRetorno<T>(url: string): Promise<IResponse<T>> {
  return mutar(async () => {
    try { return resolveResponse((await axios.delete(`${API_URL}${url}`)).data) as IResponse<T> }
    catch (e) { return resolveAxiosError(e as AxiosError) as IResponse<T> }
  })
}


