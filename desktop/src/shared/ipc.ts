// desktop/src/shared/ipc.ts
//
// Contract between the main process and the renderer. Source of truth for the
// channel names: the preload, main and renderer import FROM HERE, so renaming a
// channel breaks the compilation instead of becoming a handler that never fires.
import type { CommandName } from './events.js'
import type { AppState, LogBatch } from '../main/state/store.js'
import type { RunConfig, ConfigGeoSync, ConfigState, InvalidFolder } from '../main/state/config.js'
import type { DeepLinkRequest } from '../main/deeplink.js'
import type { StatusResult } from '../main/python/status.js'
import type { EnrollRequest, EnrollResult } from '../main/python/enroll.js'
import type { AutostartState } from '../main/ui/autostart.js'

export const CHANNELS = {
  /** renderer -> main, with a response. */
  estado: 'atlas:estado',
  iniciar: 'atlas:iniciar',
  parar: 'atlas:parar',
  reiniciar: 'atlas:reiniciar',
  forcar: 'atlas:forcar',
  comando: 'atlas:comando',
  info: 'atlas:info',
  configuracao: 'atlas:configuracao',
  enrolar: 'atlas:enrolar',
  refazerEnrollment: 'atlas:refazer-enrollment',
  escolherPasta: 'atlas:escolher-pasta',
  abrirCaminho: 'atlas:abrir-caminho',
  autostart: 'atlas:autostart',
  janela: 'atlas:janela',
  geosync: 'atlas:geosync',
  salvarGeosync: 'atlas:salvar-geosync',
  workspaces: 'atlas:workspaces',
  deepLinkPendente: 'atlas:deep-link-pendente',
  execucao: 'atlas:execucao',
  salvarExecucao: 'atlas:salvar-execucao',
  exportarLog: 'atlas:exportar-log',
  abrirJanelaLog: 'atlas:abrir-janela-log',
  log: 'atlas:log',

  /** main -> renderer, push. */
  aoAtualizarEstado: 'atlas:estado-mudou',
  aoReceberDeepLink: 'atlas:deep-link',
  aoReceberLog: 'atlas:log-lote',
} as const

export const WINDOW_ACTIONS = ['minimizar', 'alternar-maximizar', 'fechar', 'esta-maximizada'] as const
export type WindowAction = (typeof WINDOW_ACTIONS)[number]

export interface InfoApp {
  versao: string
  versaoElectron: string
  envFile: string
  certDir: string
  logDir: string
  artifactsDir: string
  dev: boolean
}

/** Surface exposed to the renderer by the preload, via contextBridge. */
export interface AtlasApi {
  estado(): Promise<AppState>
  info(): Promise<InfoApp>
  configuracao(): Promise<ConfigState>
  /** Runs the enrollment. On success the executor is started right after. */
  enrolar(pedido: EnrollRequest): Promise<EnrollResult>
  /**
   * Stops the executor and discards the current certificate, returning the app
   * to the linking form. Used when the server revoked or removed the executor —
   * the certificate on disk remains valid locally, but useless.
   */
  refazerEnrollment(): Promise<ConfigState>
  iniciar(): Promise<void>
  /**
   * Requests the orderly shutdown and RETURNS right away.
   *
   * Does not wait for the drain: it takes up to 150 s, and holding the promise
   * until then kept the whole window "busy" — including the "Forçar" buttons,
   * which are the only way out of the wait. Progress arrives on its own through
   * the state subscription (`supervisor: 'draining'` + `running_count` from the
   * snapshots).
   */
  parar(): Promise<void>
  /**
   * Stops and starts again, in that order. Resolves when the executor is back.
   *
   * Exists because the sequencing no longer fits in the renderer: with `parar`
   * returning right away, a `parar()` followed by `iniciar()` from the other
   * side would call `start()` with the old process still alive — and it would
   * exit without doing anything, leaving the executor stopped after the drain.
   */
  reiniciar(): Promise<void>
  forcar(): Promise<void>
  comando(cmd: CommandName): Promise<boolean>
  escolherPasta(atual?: string): Promise<string | null>
  abrirCaminho(caminho: string): Promise<void>
  /**
   * Reads (with no argument) or sets "start with Windows".
   *
   * Returns the state RE-READ from the registry, not the requested one: the
   * write may be blocked by group policy, and the item may be disabled in Task
   * Manager even with the entry present.
   */
  autostart(ativar?: boolean): Promise<AutostartState>
  /**
   * Controls of the frameless window. `fechar` hides instead of quitting — the
   * app lives in the tray and the executor keeps running.
   */
  janela(acao: WindowAction): Promise<boolean>

  geosync(): Promise<ConfigGeoSync>
  /** Saves and returns the rejected folders — empty means everything was saved. */
  salvarGeosync(cfg: ConfigGeoSync): Promise<{ salvo: boolean; invalidas: InvalidFolder[] }>
  /**
   * Workspaces accessible to this executor.
   *
   * The query spawns a second Python interpreter and talks to the server over
   * mTLS — several seconds, up to 30 with a bad network. That is why the result
   * is kept in the main process for the session: `atualizar: true` (the screen's
   * "Atualizar" button) is what forces the query again.
   */
  workspaces(atualizar?: boolean): Promise<StatusResult>
  /** Linking request that arrived before the renderer mounted. Consumed once. */
  deepLinkPendente(): Promise<DeepLinkRequest | null>

  execucao(): Promise<RunConfig>
  salvarExecucao(cfg: RunConfig): Promise<RunConfig>
  /** Saves the visible log to a file chosen by the user. Returns the path. */
  exportarLog(texto: string): Promise<string | null>
  /**
   * Opens (or brings to the front) a window with only the log.
   *
   * Used to follow the log alongside something else — the app's dashboard, the
   * Studio in the browser, an editor. In a single window, reading the log means
   * losing sight of everything else.
   */
  abrirJanelaLog(): Promise<void>

  /**
   * Complete log buffer. Used once, when the window mounts.
   *
   * The log does NOT travel in the state: it is append-only and large, and
   * sending it whole on every change cost ~150-200 KB per window per broadcast.
   * See the header of `main/state/store.ts`.
   */
  log(): Promise<LogBatch>

  /** Return the unsubscribe function — the renderer needs it in the cleanup. */
  aoAtualizarEstado(fn: (e: AppState) => void): () => void
  /** Only the NEW lines since the last batch. */
  aoReceberLog(fn: (lote: LogBatch) => void): () => void
  /** Linking requested by `atlans://enroll?…`. The app NEVER enrolls on its own:
   *  the form is filled in and the confirmation is the user's. */
  aoReceberDeepLink(fn: (p: DeepLinkRequest) => void): () => void
}

declare global {
  interface Window {
    atlas: AtlasApi
  }
}
