// desktop/src/main/python/status.ts
//
// Queries `python -m executor status --json`, which talks to the server using
// the executor's mTLS certificate.
//
// The query goes through Python on purpose: the call requires the executor's
// cert, the internal CA's trust store and the normalization of `wss://` to
// `https://`. Reimplementing that in Node would be a second authentication
// implementation to keep up to date — and the first to diverge when the CA
// changed.
import { spawn } from 'node:child_process'
import {
  ARTIFACTS_DIR_PADRAO, PYTHON_EXE, RESOURCES, ambienteDoSpawn, envDoExecutor,
} from '../paths.js'

export interface Workspace {
  id_hash: string
  name?: string
}

export type StatusResult =
  | { ok: true; executor_id: string; server_url: string; status: string | null; workspaces: Workspace[] }
  | { ok: false; codigo: 'config' | 'enrollment' | 'revoked' | 'rede' | 'http' | 'resposta' | 'falha'; erro: string }

const TIMEOUT_MS = 30_000

// ── Cache ────────────────────────────────────────────────────────────────────
//
// The query is expensive: cold start of the packaged interpreter,
// `bootstrap_ca()` (which may build the trust store), importing
// httpx/cryptography and an HTTPS round-trip — up to 30 s on a bad network.
// Without a cache, opening the GeoSync tab repeated all of it, and the screen
// sat with a pulsing skeleton while Python started up.
//
// Only SUCCESS is stored: caching a network failure would make the
// "Tentar de novo" (try again) button lie. An executor's list of workspaces
// changes through actions in the Studio, not on its own, so a value from the
// current session is good enough — and `forcar` covers anyone who wants to
// query again.

let cache: StatusResult | null = null
/** In-flight query, so that two simultaneous requests do not cause two spawns. */
let inFlight: Promise<StatusResult> | null = null
/**
 * Serial number of the valid query.
 *
 * Bumped on every new query AND on every `invalidarStatus()`. A query takes up
 * to 30 s; in that interval the link may have been redone (new certificate,
 * other workspaces) or the user may have clicked "Atualizar" (refresh). The
 * result of the stale query is still delivered to whoever asked for it, but it
 * does NOT become the cache — without this, the old query's `.then`
 * repopulated the cache with the workspaces of the OLD link, and the GeoSync
 * tab (which queries only once and stays mounted for the app's lifetime)
 * offered a destination this certificate no longer reaches.
 */
let serie = 0

/**
 * Query with a session cache.
 *
 * `forcar` is the screen's "Atualizar" (refresh) button: whoever clicks it is
 * saying the server changed, and returning the cache — or an in-flight query
 * started BEFORE the change — would ignore the request.
 */
export function consultarStatusCacheado(forcar = false): Promise<StatusResult> {
  if (!forcar && cache) return Promise.resolve(cache)
  if (inFlight && !forcar) return inFlight

  const mySerial = ++serie
  const p: Promise<StatusResult> = queryStatus()
    // `queryStatus` resolves even on errors, but `spawn` can throw
    // synchronously (invalid argument, nonexistent cwd). Without this catch the
    // rejection leaked to the renderer's `invoke` as an IPC error — and, worse,
    // left `emVoo` stuck forever, freezing the screen on "carregando" (loading).
    .catch((e: unknown): StatusResult => ({
      ok: false, codigo: 'falha', erro: e instanceof Error ? e.message : String(e),
    }))
    .then((r) => {
      if (r.ok && mySerial === serie) cache = r
      return r
    })
    .finally(() => {
      // Only clears it if it is still the current query: a stale query must not
      // take down the one that replaced it.
      if (inFlight === p) inFlight = null
    })
  inFlight = p
  return p
}

/**
 * Forgets the queried link.
 *
 * Mandatory when discarding or redoing the enrollment: the workspaces are the
 * ones THAT certificate reaches, and showing the old link's list after
 * switching executors would make the person pick a destination that no longer
 * exists.
 *
 * Also drops the IN-FLIGHT query — it was made with the old certificate, and
 * keeping it was the path through which the invalidated data came back.
 */
export function invalidarStatus(): void {
  cache = null
  inFlight = null
  serie++
}

/** The raw query. Private: outside callers go through the cache above. */
function queryStatus(): Promise<StatusResult> {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON_EXE, ['-X', 'utf8', '-m', 'executor', 'status', '--json'], {
      cwd: RESOURCES,
      env: ambienteDoSpawn(envDoExecutor(ARTIFACTS_DIR_PADRAO)),
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    let saida = ''
    let erro = ''
    let terminou = false
    const finish = (r: StatusResult) => {
      if (terminou) return
      terminou = true
      clearTimeout(timer)
      resolve(r)
    }

    const timer = setTimeout(() => {
      proc.kill()
      finish({ ok: false, codigo: 'rede', erro: 'O servidor não respondeu a tempo.' })
    }, TIMEOUT_MS)

    proc.stdout.setEncoding('utf8')
    proc.stdout.on('data', (c: string) => { saida += c })
    proc.stderr.setEncoding('utf8')
    proc.stderr.on('data', (c: string) => { erro += c })

    proc.on('error', (e) => finish({ ok: false, codigo: 'falha', erro: e.message }))

    proc.on('close', () => {
      // `_ca_bootstrap` writes informational lines before the JSON; taking the
      // last non-empty one ignores them.
      const linha = saida.split('\n').map((l) => l.trim()).filter(Boolean).pop()
      if (!linha) {
        finish({ ok: false, codigo: 'falha', erro: erro.trim() || 'Sem resposta.' })
        return
      }
      try {
        finish(JSON.parse(linha) as StatusResult)
      } catch {
        finish({ ok: false, codigo: 'resposta', erro: erro.trim() || linha.slice(0, 200) })
      }
    })
  })
}
