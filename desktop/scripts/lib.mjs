// desktop/scripts/lib.mjs
//
// Helpers compartilhados pelos scripts de build do runtime Python.
// Sem dependencias de npm: tudo aqui usa stdlib do Node 20 + o `tar` que o
// Windows 10+ ja traz em System32. Uma dependencia a menos e um `npm ci` a
// menos entre o CI e o interpretador.
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
// O lock do executor (scripts/travar_python.py, com o hash de cada arquivo): o
// runtime do desktop instala direto dele, com as mesmas versoes do Docker.
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
 * Ambiente sanitizado para invocar o Python embarcado.
 *
 * As variaveis removidas nao sao paranoia: numa maquina com QGIS ou ArcGIS
 * instalado, GDAL_DATA/PROJ_LIB apontam para os dados DAQUELA instalacao, e o
 * pyogrio/pyproj do bundle carrega tabelas de projecao incompativeis com as
 * DLLs que ele empacota. O sintoma e um to_crs() que devolve coordenada errada
 * em vez de estourar — o pior tipo de bug.
 *
 * PYTHONHOME/PYTHONPATH herdados apontariam para outro interpretador.
 * SSL_CERT_FILE/REQUESTS_CA_BUNDLE atrapalham o _ca_bootstrap do executor.
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

/** Tamanho em bytes de uma arvore. Usado para medir cada passo da poda. */
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
 * Percorre a arvore chamando `visit(caminho, dirent)`. Diretorios sao visitados
 * ANTES de descer, e devolver `false` para um diretorio poda a descida — assim
 * remover uma pasta grande nao custa varrer o que havia dentro dela.
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

/** Ordena para que a copia seja deterministica — o blockmap do updater depende disso. */
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
 * Extrai com o bsdtar do Windows (System32), resolvido por caminho absoluto.
 *
 * O caminho absoluto NAO e preciosismo: quem roda o build de dentro do Git Bash
 * tem o GNU tar na frente do PATH, e o GNU tar le `C:\...` como `host:caminho`
 * (sintaxe de fita remota). O erro que sai e "Cannot connect to C: resolve
 * failed", que nao ajuda ninguem. O bsdtar entende letra de unidade.
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
