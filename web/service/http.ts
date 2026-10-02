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

// Interceptor: anexa token JWT apenas em requisições para a API interna (/terra)
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
 * GETs idênticos EM VOO compartilham uma única requisição.
 *
 * A camada de dados (`lib/consultas.ts`, react-query; padrao-telas §10) ainda
 * cobre poucas telas e não guarda cache por padrão, e vários pontos pedem a
 * mesma lista ao mesmo tempo: abrir /projects disparava dois
 * `GET /workflows/?workspace_id=X` simultâneos (o ActiveRunsProvider do layout
 * e a própria página), e abrir /workspaces disparava dois `GET /workspaces/`.
 * Em rede lenta, o tempo até a lista aparecer era o da resposta mais lenta das
 * duas — e o backend fazia o dobro do trabalho.
 *
 * A janela é estritamente "enquanto a requisição está em voo": nada é
 * memorizado depois que ela responde, então a próxima leitura é sempre nova.
 */
const getsEmVoo = new Map<string, Promise<unknown>>()

/**
 * Época de escrita: incrementada ANTES e DEPOIS de toda mutação, e usada como
 * prefixo da chave de dedup.
 *
 * Sem ela, a chave era só a URL e a janela de coalescência atravessava a
 * escrita: em /executores, com o tick de 15s de `GET /executores/` já em voo, o
 * `refetch()` disparado no sucesso de um DELETE recebia a MESMA promise — uma
 * resposta calculada no servidor ANTES da exclusão. O card excluído reaparecia
 * na lista logo depois do toast "Executor excluído". Mesma coisa em /projects,
 * onde a cópia recém-duplicada não aparecia no `getProjects()` seguinte.
 *
 * Com o prefixo, toda leitura pedida depois de uma escrita usa uma chave nova e
 * vai mesmo à rede; a dedup continua valendo para o caso que ela existe para
 * resolver (dois leitores simultâneos no mount).
 */
let epocaEscrita = 0

// Nenhum verbo daqui rejeita: queda de rede, 4xx e 5xx voltam resolvidos, com
// `error` preenchido (`resolveAxiosError`). Um `try/catch` em volta da chamada é
// código morto — a tela lê a falha em `res.error` (`dadoOuAviso`, em
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

/** Envolve uma mutação abrindo uma época nova antes e depois: nem uma leitura
 *  anterior à escrita, nem uma disparada no meio dela, podem ser reaproveitadas
 *  por quem lê depois que ela terminou. */
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
/** DELETE que preserva o corpo da resposta. Igual a `del`, e igualmente
 *  envolvido por `mutar` — existe porque alguns DELETEs devolvem payload e
 *  reimplementá-los à mão os deixava fora da época de escrita. */
export function delComRetorno<T>(url: string): Promise<IResponse<T>> {
  return mutar(async () => {
    try { return resolveResponse((await axios.delete(`${API_URL}${url}`)).data) as IResponse<T> }
    catch (e) { return resolveAxiosError(e as AxiosError) as IResponse<T> }
  })
}


