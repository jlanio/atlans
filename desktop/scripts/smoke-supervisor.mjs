// desktop/scripts/smoke-supervisor.mjs
//
// Real integration: the app's supervisor against the real Python executor.
//
// The vitest tests use a fake `spawnFn` — they prove the restart policy, not
// the bridge. This script proves the whole bridge: spawn with the sanitized
// environment, NDJSON arriving over stdout, human log over stderr, a command
// going over stdin and the `ack` coming back.
//
// It needs no server: with a fake cert dir, the executor starts, emits
// `hello`, attempts phase 0 and reports `state: failed`. That exercises exactly
// the path the GUI most needs to get right — boot failure with a cause.
//
//   node scripts/smoke-supervisor.mjs
import { build } from 'esbuild'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import {
  DESKTOP, PY_EXE, RESOURCES, assertRuntimeExists, fail, log, ok, pythonEnv, step,
} from './lib.mjs'

assertRuntimeExists()
for (const dir of ['executor', 'flow']) {
  if (!fs.existsSync(path.join(RESOURCES, dir))) {
    fail(`resources/${dir} ausente\n  -> rode: npm run payload:stage`)
  }
}

// The supervisor does not import `electron` (on purpose — the process logic
// has to be testable outside it), so it can be loaded here directly.
step('Compilando o supervisor')
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-sup-'))
const saida = path.join(tmp, 'supervisor.mjs')
await build({
  entryPoints: [path.join(DESKTOP, 'src/main/python/supervisor.ts')],
  outfile: saida,
  bundle: true, platform: 'node', target: 'node20', format: 'esm',
  external: ['electron'], logLevel: 'error',
})
const { PythonSupervisor } = await import(pathToFileURL(saida).href)

// ── Minimal environment for the executor to get past assert_enrolled ─────────
const certDir = path.join(tmp, 'certs')
fs.mkdirSync(certDir, { recursive: true })
for (const f of ['cert.pem', 'key.pem']) fs.writeFileSync(path.join(certDir, f), '')

const env = {
  ...pythonEnv(),
  PYTHONPATH: RESOURCES,
  PYTHONUNBUFFERED: '1',
  EXECUTOR_ID: '00000000-1111-2222-3333-444444444444',
  EXECUTOR_ENV_PATH: path.join(tmp, '.env'),
  EXECUTOR_CERT_DIR: certDir,
  EXECUTOR_ARTIFACTS_DIR: path.join(tmp, 'artifacts'),
  EXECUTOR_LOG_DIR: path.join(tmp, 'logs'),
  EXECUTOR_DASHBOARD: 'json',
  EXECUTOR_DASHBOARD_INTERVAL: '0.3',
  EXECUTOR_AUTO_RESTART: 'never',
  EXECUTOR_SUPERVISOR_PID: String(process.pid),
  // Closed port: phase 0 fails fast, without depending on an external network.
  EXECUTOR_SERVER_URL: 'wss://127.0.0.1:1',
  LOG_COLOR: 'never',
}

step('Subindo o executor sob o supervisor')
const sup = new PythonSupervisor({ pythonExe: PY_EXE, cwd: RESOURCES, env })

const eventos = []
const estados = []
const stderrLines = []
const stdoutRaw = []

sup.on('evento', (e) => eventos.push(e))
sup.on('estado', (e, d) => { estados.push(e); log(`  estado: ${e}${d ? ` — ${d}` : ''}`) })
sup.on('linha', (t, origem) => (origem === 'stderr' ? stderrLines : stdoutRaw).push(t))

const esperar = (cond, ms, oque) => new Promise((res, rej) => {
  const t0 = Date.now()
  const iv = setInterval(() => {
    if (cond()) { clearInterval(iv); res() }
    else if (Date.now() - t0 > ms) { clearInterval(iv); rej(new Error(`timeout esperando ${oque}`)) }
  }, 50)
})

const tipos = () => eventos.map((e) => e.t)
const checagens = []
const checar = (nome, ok_) => { checagens.push([nome, ok_]); log(`  ${ok_ ? 'OK   ' : 'FALHA'} ${nome}`) }

/**
 * Fields declared in `Snapshot`, read from `src/shared/events.ts`.
 *
 * Deriving from the file, instead of keeping a list here, is what keeps this
 * check from going stale: whoever adds a field to the Python dataclass and
 * forgets the TS mirror (or the other way around) sees exactly which field was
 * left out, instead of a number that doesn't match.
 *
 * `Snapshot \{` with the brace is intentional: without it the regex would also
 * match `SnapshotEvent`, and the fields of the two would get mixed up.
 */
function tsMirrorFields() {
  const src = fs.readFileSync(path.join(DESKTOP, 'src', 'shared', 'events.ts'), 'utf8')
  const corpo = /export interface Snapshot \{([\s\S]*?)\n\}/.exec(src)
  if (!corpo) fail('Não achei a interface Snapshot em src/shared/events.ts')
  return new Set(
    [...corpo[1].matchAll(/^ {2}([a-z_][a-zA-Z0-9_]*)\??:/gm)].map((m) => m[1]),
  )
}

try {
  sup.start()

  await esperar(() => tipos().includes('hello'), 30_000, 'o handshake')
  const hello = eventos.find((e) => e.t === 'hello')
  checar('hello e o primeiro evento', eventos[0].t === 'hello')
  checar('hello traz o pid do processo', hello.data.pid === sup.pid)
  checar('hello anuncia os comandos', Array.isArray(hello.data.comandos) && hello.data.comandos.includes('ping'))
  checar('supervisor foi para running', sup.estado === 'running')

  await esperar(() => tipos().includes('snapshot'), 15_000, 'o primeiro snapshot')
  const snap = eventos.find((e) => e.t === 'snapshot').data
  // What matters here is the CONTRACT between the Python dataclass and the
  // mirror in events.ts, not a count. The previous version asserted "55 fields"
  // and broke when it gained two — and the error (`55 != 57`) said neither
  // which ones nor on which side the divergence was.
  const esperados = tsMirrorFields()
  const recebidos = new Set(Object.keys(snap))
  const faltando = [...esperados].filter((c) => !recebidos.has(c))
  const sobrando = [...recebidos].filter((c) => !esperados.has(c))

  checar(`snapshot casa com o espelho TS (${esperados.size} campos)`,
         faltando.length === 0 && sobrando.length === 0)
  if (faltando.length) log(`         so em events.ts: ${faltando.join(', ')}`)
  if (sobrando.length) log(`         so no Python:    ${sobrando.join(', ')}`)
  checar('snapshot traz o executor_id', snap.executor_id === env.EXECUTOR_ID)

  // The ping only answers if the command crossed stdin -> thread -> event loop
  // and the ack came back over stdout. It is the round-trip transport test.
  sup.enviar({ cmd: 'ping', id: 'smoke-1' })
  await esperar(() => eventos.some((e) => e.t === 'ack' && e.id === 'smoke-1'), 10_000, 'o ack do ping')
  const ack = eventos.find((e) => e.t === 'ack' && e.id === 'smoke-1')
  checar('ack do ping veio com ok', ack.ok === true)

  await esperar(() => estados.includes('failed'), 30_000, 'a falha de boot')
  const falha = eventos.find((e) => e.t === 'state' && e.data.phase === 'failed')
  checar('state failed identifica o passo', falha?.data.step === 'server_key')
  checar('state failed traz a causa', typeof falha?.data.detail === 'string' && falha.data.detail.length > 0)
  checar('supervisor nao tenta religar apos falha com causa', sup.estado === 'failed')

  checar('stderr recebeu o log humano', stderrLines.length > 0)
  checar('stdout nao teve linha fora do framing', stdoutRaw.length === 0)
} finally {
  // WAITS for the process to die before exiting.
  //
  // `forcar()` fires `taskkill` asynchronously; exiting the script right after
  // left `python.exe` ALIVE, holding the DLLs of `resources/python`. The
  // symptom showed up far from here: the next `npm run python:build` failed
  // with `EPERM: unlink libcrypto-1_1-x64.dll`, with no clue that an earlier
  // smoke run was the culprit.
  const pid = sup.pid
  sup.forcar()
  for (let i = 0; i < 50 && pid; i++) {
    try {
      process.kill(pid, 0)          // so testa a existencia
    } catch {
      break                         // already dead
    }
    await new Promise((r) => setTimeout(r, 100))
  }
  fs.rmSync(tmp, { recursive: true, force: true })
}

console.log()
const falhas = checagens.filter(([, v]) => !v)
if (falhas.length) {
  fail(`${falhas.length} checagem(ns) falharam:\n` + falhas.map(([n]) => `    - ${n}`).join('\n'))
}
ok(`${checagens.length}/${checagens.length} checagens — a ponte supervisor <-> executor funciona`)
