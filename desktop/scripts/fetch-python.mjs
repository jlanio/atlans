// desktop/scripts/fetch-python.mjs
//
// Baixa o CPython standalone descrito em desktop/python-runtime.json, confere o
// SHA-256 e extrai em desktop/resources/python/.
//
// Idempotente: se o runtime ja esta la com a versao certa, nao faz nada — e o
// que torna o cache do CI util. O tarball fica em resources/.cache/ para que um
// rebuild local nao rebaixe 40 MB.
//
//   node scripts/fetch-python.mjs [--force]
import fs from 'node:fs'
import path from 'node:path'
import {
  PY_DIR, PY_EXE, RESOURCES, fail, log, mb, ok, pythonCapture,
  readRuntimeSpec, rmrf, sha256, step, tarExtract,
} from './lib.mjs'

const force = process.argv.includes('--force')
const spec = readRuntimeSpec()
const url = `https://github.com/astral-sh/python-build-standalone/releases/download/${spec.release}/${encodeURIComponent(spec.asset)}`
const cacheDir = path.join(RESOURCES, '.cache')
const tarball = path.join(cacheDir, spec.asset)
const stamp = path.join(PY_DIR, '.runtime-spec.json')

// ── Ja instalado? ────────────────────────────────────────────────────────────
if (!force && fs.existsSync(PY_EXE) && fs.existsSync(stamp)) {
  const atual = JSON.parse(fs.readFileSync(stamp, 'utf8'))
  if (atual.release === spec.release && atual.asset === spec.asset) {
    // Confere que o interpretador realmente roda: um cache do CI restaurado pela
    // metade passaria no teste de existencia do arquivo e falharia so no pip.
    const v = pythonCapture(['-c', 'import sys; print(sys.version.split()[0])']).trim()
    if (v === spec.version) {
      ok(`runtime ${spec.version} (${spec.release}) ja presente — nada a fazer`)
      process.exit(0)
    }
    log(`stamp diz ${spec.version} mas o interpretador reporta ${v} — refazendo`)
  } else {
    log(`runtime instalado e ${atual.release}, esperado ${spec.release} — refazendo`)
  }
}

// ── Download ─────────────────────────────────────────────────────────────────
step(`CPython ${spec.version} (${spec.release})`)
fs.mkdirSync(cacheDir, { recursive: true })

let precisaBaixar = true
if (fs.existsSync(tarball)) {
  log('tarball em cache — conferindo hash')
  if (sha256(tarball) === spec.sha256) { ok('hash confere, download dispensado'); precisaBaixar = false }
  else { log('hash do cache diverge — rebaixando'); fs.rmSync(tarball) }
}

if (precisaBaixar) {
  log(`baixando ${url}`)
  const resp = await fetch(url, { redirect: 'follow' })
  if (!resp.ok) fail(`download falhou: HTTP ${resp.status} ${resp.statusText}`)
  const buf = Buffer.from(await resp.arrayBuffer())
  fs.writeFileSync(tarball, buf)
  ok(`${mb(buf.length)} MB baixados`)
}

// ── Verificacao ──────────────────────────────────────────────────────────────
// Antes de extrair, sempre. Uma release re-publicada com outro binario e
// exatamente o cenario que o pin de hash existe para pegar.
const hash = sha256(tarball)
if (hash !== spec.sha256) {
  fail(
    `SHA-256 nao confere.\n` +
    `    esperado: ${spec.sha256}\n` +
    `    obtido:   ${hash}\n\n` +
    `  Se a atualizacao do runtime foi intencional, atualize o campo "sha256"\n` +
    `  em desktop/python-runtime.json no mesmo PR que muda "release"/"asset".`
  )
}
ok(`SHA-256 confere (${hash.slice(0, 16)}…)`)

// ── Extracao ─────────────────────────────────────────────────────────────────
// O install_only extrai como `python/…`, entao extraimos em resources/ e o
// diretorio nasce com o nome certo.
rmrf(PY_DIR)
tarExtract(tarball, RESOURCES)
if (!fs.existsSync(PY_EXE)) fail(`extracao nao produziu ${PY_EXE}`)

const versao = pythonCapture(['-c', 'import sys; print(sys.version.split()[0])']).trim()
if (versao !== spec.version) fail(`interpretador extraido e ${versao}, esperado ${spec.version}`)

fs.writeFileSync(stamp, JSON.stringify({ ...spec, extraido_em: new Date().toISOString() }, null, 2))
ok(`Python ${versao} pronto em ${PY_DIR}`)
