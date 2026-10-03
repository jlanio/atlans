// desktop/src/main/state/config.ts
//
// Reading and writing the executor's `.env`.
//
// Writing is reimplemented here instead of calling Python just to write one
// line, and it mirrors `executor/_env_utils.py::persist_env_var`: it preserves
// comments, order and keys the app does not know about. Rewriting the whole
// file from a dictionary would erase EXECUTOR_HOST_ALIASES, MINIO_*,
// LOG_FILE_AGENT and everything else the user or the enrollment put there.
import fs from 'node:fs'
import path from 'node:path'
import { CERT_DIR, ENV_FILE } from '../paths.js'
import { SERVIDOR } from '../../shared/servidor.js'
import {
  ESTRATEGIAS, INTERVALO_SYNC, MODOS_SYNC, PADRAO_SYNC,
  type EstrategiaConflito, type ModoSync,
} from '../../shared/geosync.js'
import { LIMITES, inteiroDoEnv } from '../../shared/limites.js'

/** Files the enrollment produces. Without both, `assert_enrolled` blocks the boot. */
const CERT_OBRIGATORIOS = ['cert.pem', 'key.pem']

/**
 * Identity material of THIS executor, discarded when redoing the enrollment.
 *
 * The list is explicit, and not an `rm -rf` of the cert dir, because the
 * folder also holds things that must SURVIVE:
 *
 *   - `server_signing.pub` — the server's Ed25519 key, pinned via TOFU.
 *     Deleting it would reopen the window that pinning closes: the next boot
 *     would accept any key that answered at the configured address.
 *   - `atlans-root.crt` / `atlans-ca-bundle.crt` — trust store of the internal
 *     CA, built by `_ca_bootstrap`. It has nothing to do with the executor's
 *     identity, and downgrading it only costs one extra download.
 */
const ARQUIVOS_DE_IDENTIDADE = [
  'cert.pem', 'chain.pem', 'ca.pem', 'key.pem', 'x25519_key.pem',
]

export interface EstadoConfiguracao {
  configurado: boolean
  executorId: string | null
  /** Missing step — mirrors the `step` of the `state: failed` event. */
  falta: 'config' | 'enrollment' | null
}

export function lerConfiguracao(): EstadoConfiguracao {
  const env = lerEnv()
  const executorId = (env.EXECUTOR_ID || '').trim() || null
  const temCertificado = CERT_OBRIGATORIOS.every((f) => fs.existsSync(path.join(CERT_DIR, f)))

  return {
    configurado: Boolean(executorId) && temCertificado,
    executorId,
    falta: !executorId ? 'config' : !temCertificado ? 'enrollment' : null,
  }
}

/**
 * Discards the current certificate so that a new enrollment can be done.
 *
 * Needed because enrollment is not idempotent from the server's point of
 * view: a revoked or removed executor still has a valid cert on disk, and the
 * executor starts, connects and gets a 4404 close — indefinitely. Without
 * deleting the material, the link form would not even appear
 * (`lerConfiguracao` would say "configured").
 *
 * The `EXECUTOR_ID` in `.env` is PRESERVED: it becomes the form's initial
 * value. When the executor was recreated on the server the ID changes, and the
 * user replaces it; when it was only revoked, it is still valid.
 */
export function descartarEnrollment(): { removidos: string[] } {
  const removidos: string[] = []
  for (const nome of ARQUIVOS_DE_IDENTIDADE) {
    const alvo = path.join(CERT_DIR, nome)
    if (!fs.existsSync(alvo)) continue
    try {
      fs.rmSync(alvo, { force: true })
      removidos.push(nome)
    } catch {
      // File in use by an executor that has not shut down yet. The caller stops
      // the process first; if it still fails, the next enrollment overwrites
      // it.
    }
  }
  return { removidos }
}

// ── GeoSync ──────────────────────────────────────────────────────────────────

/**
 * One folder, not a list.
 *
 * `EXECUTOR_SYNC_DIRS` accepts several, comma-separated, but GeoSync syncs
 * everything against ONE workspace: several folders dump different trees into
 * the same Drive, and the mapping back (Drive → which folder?) becomes
 * ambiguous as soon as two files share a name. A single root folder keeps the
 * correspondence one-to-one.
 */
export interface ConfigGeoSync {
  pasta: string | null
  modo: ModoSync
  conflito: EstrategiaConflito
  workspaceId: string | null
}

export function lerGeoSync(): ConfigGeoSync {
  const env = lerEnv()
  const modo = env.EXECUTOR_SYNC_MODE as ModoSync
  const conflito = env.EXECUTOR_SYNC_CONFLICT_STRATEGY as EstrategiaConflito

  return {
    // Only the first one gets in: a `.env` with several folders (hand-edited, or
    // coming from an earlier configuration) must not make the screen show
    // something it cannot represent.
    pasta: (env.EXECUTOR_SYNC_DIRS ?? '').split(',').map((p) => p.trim()).filter(Boolean)[0] ?? null,
    // Without a valid value, whatever the executor uses — see PADRAO_SYNC.
    modo: MODOS_SYNC.includes(modo) ? modo : PADRAO_SYNC.modo,
    conflito: ESTRATEGIAS.includes(conflito) ? conflito : PADRAO_SYNC.conflito,
    workspaceId: (env.EXECUTOR_WORKSPACE_ID || '').trim() || null,
  }
}

/** Folder rejected on save. See `validarPasta`. */
export interface PastaInvalida { caminho: string; motivo: string }

/**
 * `EXECUTOR_SYNC_DIRS` is a COMMA-separated list, and Python splits it blindly
 * (`config.py`: `SYNC_DIRS.split(",")`). A folder with a comma in its name
 * would become two nonexistent entries, and GeoSync would sync nothing without
 * saying why. Blocking it in the UI is the only place where this can be
 * explained.
 */
export function validarPasta(pasta: string | null): PastaInvalida | null {
  if (!pasta) return null
  if (pasta.includes(',')) {
    return { caminho: pasta, motivo: 'o caminho contém vírgula, que separa as pastas na configuração' }
  }
  if (!fs.existsSync(pasta)) return { caminho: pasta, motivo: 'a pasta não existe' }
  return null
}

export function gravarGeoSync(cfg: ConfigGeoSync): void {
  gravarEnv({
    EXECUTOR_SYNC_DIRS: cfg.pasta ?? '',
    EXECUTOR_SYNC_MODE: cfg.modo,
    EXECUTOR_SYNC_INTERVAL: String(INTERVALO_SYNC),
    EXECUTOR_SYNC_CONFLICT_STRATEGY: cfg.conflito,
    // Empty is valid: it means "auto-detect", which is what the executor does
    // when there is exactly one accessible workspace.
    EXECUTOR_WORKSPACE_ID: cfg.workspaceId ?? '',
  })
}

// ── Execution ────────────────────────────────────────────────────────────────

/**
 * The server is not here: it is the constant {@link SERVIDOR}, and that is why
 * it is not a setting. See the header of `shared/servidor.ts`.
 */
export interface ConfigExecucao {
  workers: number
  filaMax: number
  timeoutS: number
  artifactsDir: string
  nivelLog: NivelLog
}

export type NivelLog = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
export const NIVEIS_LOG: NivelLog[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

/**
 * The numbers go through the ranges in `shared/limites.ts`, the mirror of
 * those in `executor/config.py`: Python discards an out-of-range value and
 * falls back to the default, so accepting a different one here would make the
 * UI show 500 workers with the executor running 4, with nothing explaining the
 * difference.
 */
export function lerExecucao(artifactsDirPadrao: string): ConfigExecucao {
  const env = lerEnv()
  const nivel = (env.LOG_LEVEL || '').toUpperCase() as NivelLog
  return {
    workers: inteiroDoEnv(env.EXECUTOR_MAX_CONCURRENT, LIMITES.workers),
    filaMax: inteiroDoEnv(env.EXECUTOR_MAX_QUEUE_SIZE, LIMITES.filaMax),
    timeoutS: inteiroDoEnv(env.EXECUTOR_JOB_TIMEOUT, LIMITES.timeoutS),
    artifactsDir: (env.EXECUTOR_ARTIFACTS_DIR || '').trim() || artifactsDirPadrao,
    nivelLog: NIVEIS_LOG.includes(nivel) ? nivel : 'INFO',
  }
}

export function gravarExecucao(cfg: ConfigExecucao): void {
  gravarEnv({
    EXECUTOR_MAX_CONCURRENT: String(inteiroDoEnv(String(cfg.workers), LIMITES.workers)),
    EXECUTOR_MAX_QUEUE_SIZE: String(inteiroDoEnv(String(cfg.filaMax), LIMITES.filaMax)),
    EXECUTOR_JOB_TIMEOUT: String(inteiroDoEnv(String(cfg.timeoutS), LIMITES.timeoutS)),
    EXECUTOR_ARTIFACTS_DIR: cfg.artifactsDir.trim(),
    // Reasserted on every save, and not read from `cfg`: if someone hand-edited
    // the `.env` to another address, saving any setting brings the file back
    // to the correct server instead of preserving the change.
    EXECUTOR_SERVER_URL: SERVIDOR,
    LOG_LEVEL: NIVEIS_LOG.includes(cfg.nivelLog) ? cfg.nivelLog : 'INFO',
  })
}

/**
 * Artifacts directory the spawn must use.
 *
 * The `.env` wins over the default: without this, setting the folder on the
 * Settings screen wrote the value but the executor kept writing to the default
 * directory — the user would change it and nothing would happen.
 */
export function artifactsDirEfetivo(padrao: string): string {
  return (lerEnv().EXECUTOR_ARTIFACTS_DIR || '').trim() || padrao
}

export function lerEnv(): Record<string, string> {
  if (!fs.existsSync(ENV_FILE)) return {}
  const valores: Record<string, string> = {}
  for (const linha of fs.readFileSync(ENV_FILE, 'utf8').split(/\r?\n/)) {
    const t = linha.trim()
    if (!t || t.startsWith('#')) continue
    const i = t.indexOf('=')
    if (i <= 0) continue
    const chave = t.slice(0, i).trim()
    let valor = t.slice(i + 1).trim()
    // dotenv accepts quoted values and a comment at the end of the line (` # ...`,
    // with a space before it); strip both so that comparison and use match
    // what Python sees. Without this, `EXECUTOR_SYNC_MODE=bidirectional # x`
    // was not recognized, the screen fell back to the default and saving
    // GeoSync changed the executor's mode.
    const entreAspas = /^(["'])(.*)\1(?:\s+#.*)?$/.exec(valor)
    valor = entreAspas ? entreAspas[2]! : valor.replace(/\s+#.*$/, '')
    valores[chave] = valor
  }
  return valores
}

/**
 * Writes (or updates) keys in the `.env`, idempotently.
 *
 * Rules, the same as those of `_env_utils.persist_env_var`:
 *   - an existing key is rewritten IN PLACE, keeping its position in the file;
 *   - a new key goes to the end;
 *   - comments and blank lines survive;
 *   - a commented-out key (`# EXECUTOR_X=`) does NOT count as existing.
 */
export function gravarEnv(valores: Record<string, string>): void {
  fs.mkdirSync(path.dirname(ENV_FILE), { recursive: true })

  const original = fs.existsSync(ENV_FILE) ? fs.readFileSync(ENV_FILE, 'utf8') : ''
  const linhas = original ? original.split(/\r?\n/) : []
  const pendentes = new Map(Object.entries(valores))

  const saida = linhas.map((linha) => {
    const t = linha.trim()
    if (!t || t.startsWith('#')) return linha
    const i = t.indexOf('=')
    if (i <= 0) return linha
    const chave = t.slice(0, i).trim()
    if (!pendentes.has(chave)) return linha
    const novo = `${chave}=${pendentes.get(chave)}`
    pendentes.delete(chave)
    return novo
  })

  if (pendentes.size) {
    // A file that ends in `\n` produces an empty element at the end of the
    // split. Pushing the new key after it would create a blank line — and
    // another on every following write, until the `.env` is full of blanks.
    // They are removed only at the END: blank lines in the middle separate
    // sections and are intentional.
    while (saida.length && saida[saida.length - 1]!.trim() === '') saida.pop()
    for (const [chave, valor] of pendentes) saida.push(`${chave}=${valor}`)
  }

  // The file always ends with a newline: without it, the next key added
  // sticks to the last line and becomes `A=1B=2`.
  const texto = saida.join('\n').replace(/\n*$/, '\n')
  fs.writeFileSync(ENV_FILE, texto, { encoding: 'utf8', mode: 0o600 })
}
