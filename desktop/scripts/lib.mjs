// desktop/scripts/lib.mjs
//
// Helpers shared by the Python runtime build scripts.
// No npm dependencies: everything here uses the Node 20 stdlib + the `tar` that
// Windows 10+ already ships in System32. One dependency fewer is one `npm ci`
// fewer between CI and the interpreter.
import { execFileSync, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const SCRIPTS  = path.dirname(fileURLToPath(import.meta.url))
export const DESKTOP  = path.resolve(SCRIPTS, '..')
export const REPO     = path.resolve(DESKTOP, '..')
export const RESOURCES = path.join(DESKTOP, 'resources')
export const PY_DIR   = path.join(RESOURCES, 'python')
export const PY_EXE   = path.join(PY_DIR, 'python.exe')
// The executor lock (scripts/travar_python.py, with each file's hash): the
// desktop runtime installs directly from it, with the same versions as Docker.
export const LOCK     = path.join(REPO, 'executor', 'requirements-full.txt')
export const RUNTIME_JSON = path.join(DESKTOP, 'python-runtime.json')

// ── Saida ────────────────────────────────────────────────────────────────────
const t0 = Date.now()
const ts = () => `${((Date.now() - t0) / 1000).toFixed(1)}s`.padStart(6)

export const log  = (msg) => console.log(`[${ts()}] ${msg}`)
export const step = (msg) => console.log(`\n[${ts()}] ── ${msg} ${'─'.repeat(Math.max(0, 60 - msg.length))}`)
export const ok   = (msg) => console.log(`[${ts()}]  OK  ${msg}`)

export function fail(msg) {
  console.error(`\n  ERRO: ${msg}\n`)
  process.exit(1)
}

// ── Ambiente ─────────────────────────────────────────────────────────────────

/**
 * Sanitized environment for invoking the embedded Python.
 *
 * The removed variables are not paranoia: on a machine with QGIS or ArcGIS
 * installed, GDAL_DATA/PROJ_LIB point to THAT installation's data, and the
 * bundle's pyogrio/pyproj load projection tables incompatible with the DLLs it
 * ships. The symptom is a to_crs() that returns a wrong coordinate instead of
 * blowing up — the worst kind of bug.
 *
 * Inherited PYTHONHOME/PYTHONPATH would point to another interpreter.
 * SSL_CERT_FILE/REQUESTS_CA_BUNDLE get in the way of the executor's _ca_bootstrap.
 */
export function pythonEnv(extra = {}) {
  const env = { ...process.env }
  for (const k of [
    'PYTHONHOME', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONUSERBASE',
    'GDAL_DATA', 'GDAL_DRIVER_PATH', 'PROJ_LIB', 'PROJ_DATA',
    'SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE',
  ]) delete env[k]
  for (const k of Object.keys(env)) if (k.startsWith('EXECUTOR_')) delete env[k]
  return { ...env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', ...extra }
}

// ── Processos ────────────────────────────────────────────────────────────────

export function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', ...opts })
  if (r.error) fail(`falha ao executar ${cmd}: ${r.error.message}`)
  if (r.status !== 0) fail(`${cmd} saiu com codigo ${r.status}`)
}

export function capture(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { encoding: 'utf8', ...opts })
  if (r.error) fail(`falha ao executar ${cmd}: ${r.error.message}`)
  if (r.status !== 0) {
    process.stderr.write(r.stderr || '')
    fail(`${cmd} saiu com codigo ${r.status}`)
  }
  return r.stdout
}

export const python = (args, opts = {}) =>
  run(PY_EXE, args, { env: pythonEnv(opts.env), ...opts })

export const pythonCapture = (args, opts = {}) =>
  capture(PY_EXE, args, { env: pythonEnv(opts.env), ...opts })

// ── Arquivos ─────────────────────────────────────────────────────────────────

export function sha256(file) {
  return createHash('sha256').update(fs.readFileSync(file)).digest('hex')
}

/** Size in bytes of a tree. Used to measure each pruning step. */
export function dirSize(dir) {
  let total = 0
  const stack = [dir]
  while (stack.length) {
    let entries
    try { entries = fs.readdirSync(stack.pop(), { withFileTypes: true }) } catch { continue }
    for (const e of entries) {
      const p = path.join(e.parentPath ?? e.path, e.name)
      if (e.isDirectory()) stack.push(p)
      else if (e.isFile()) { try { total += fs.statSync(p).size } catch { /* corrida */ } }
    }
  }
  return total
}

export const mb = (bytes) => (bytes / 1048576).toFixed(0)

export function rmrf(target) {
  fs.rmSync(target, { recursive: true, force: true })
}

/**
 * Walks the tree calling `visit(caminho, dirent)`. Directories are visited
 * BEFORE descending, and returning `false` for a directory prunes the descent —
 * so removing a large folder does not cost scanning what was inside it.
 */
export function walk(dir, visit) {
  let entries
  try { entries = fs.readdirSync(dir, { withFileTypes: true }) } catch { return }
  for (const e of entries) {
    const p = path.join(dir, e.name)
    if (visit(p, e) === false) continue
    if (e.isDirectory()) walk(p, visit)
  }
}

/** Sorts so that the copy is deterministic — the updater's blockmap depends on it. */
export function sortedEntries(dir) {
  return fs.readdirSync(dir, { withFileTypes: true })
    .sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
}

export function readRuntimeSpec() {
  const spec = JSON.parse(fs.readFileSync(RUNTIME_JSON, 'utf8'))
  for (const k of ['release', 'version', 'asset', 'sha256']) {
    if (!spec[k]) fail(`python-runtime.json sem o campo obrigatorio "${k}"`)
  }
  return spec
}

export function assertRuntimeExists() {
  if (!fs.existsSync(PY_EXE)) {
    fail(`runtime nao encontrado em ${PY_EXE}\n  -> rode: npm run python:fetch && npm run python:build`)
  }
}

/**
 * Extracts with Windows' bsdtar (System32), resolved by absolute path.
 *
 * The absolute path is NOT fussiness: whoever runs the build from inside Git
 * Bash has GNU tar first on the PATH, and GNU tar reads `C:\...` as `host:path`
 * (remote tape syntax). The resulting error is "Cannot connect to C: resolve
 * failed", which helps nobody. bsdtar understands drive letters.
 */
export function tarExtract(archive, cwd) {
  fs.mkdirSync(cwd, { recursive: true })
  const system32 = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'tar.exe')
  const bin = fs.existsSync(system32) ? system32 : 'tar'
  try {
    execFileSync(bin, ['xzf', archive, '-C', cwd], { stdio: 'inherit' })
  } catch (e) {
    fail(`falha ao extrair ${archive} com ${bin}: ${e.message}`)
  }
}
