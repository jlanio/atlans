// desktop/scripts/smoke-supervisor.mjs
//
// Integracao de verdade: o supervisor do app contra o executor Python real.
//
// Os testes de vitest usam um `spawnFn` falso — provam a politica de reinicio,
// nao a ponte. Este script prova a ponte inteira: spawn com o ambiente
// sanitizado, NDJSON chegando pelo stdout, log humano pelo stderr, comando indo
// pelo stdin e o `ack` voltando.
//
// Nao precisa de servidor: com um cert dir falso, o executor sobe, emite
// `hello`, tenta a fase 0 e reporta `state: failed`. Isso exercita exatamente o
// caminho que a GUI mais precisa acertar — a falha de boot com causa.
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

// O supervisor nao importa `electron` (de proposito — a logica de processo tem
// de ser testavel fora dele), entao da para carrega-lo aqui direto.
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

// ── Ambiente minimo para o executor passar do assert_enrolled ────────────────
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
  // Porta fechada: a fase 0 falha rapido, sem depender de rede externa.
  EXECUTOR_SERVER_URL: 'wss://127.0.0.1:1',
  LOG_COLOR: 'never',
}

step('Subindo o executor sob o supervisor')
const sup = new PythonSupervisor({ pythonExe: PY_EXE, cwd: RESOURCES, env })

const eventos = []
const estados = []
const stderrLinhas = []
const stdoutBrutas = []

sup.on('evento', (e) => eventos.push(e))
sup.on('estado', (e, d) => { estados.push(e); log(`  estado: ${e}${d ? ` — ${d}` : ''}`) })
sup.on('linha', (t, origem) => (origem === 'stderr' ? stderrLinhas : stdoutBrutas).push(t))

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
 * Campos declarados em `Snapshot`, lido de `src/shared/events.ts`.
 *
 * Derivar do arquivo, em vez de manter uma lista aqui, é o que faz esta
 * checagem não envelhecer: quem adicionar um campo no dataclass Python e
 * esquecer o espelho TS (ou o contrário) vê exatamente qual campo ficou de
 * fora, em vez de um número que não bate.
 *
 * `Snapshot \{` com a chave é proposital: sem ela o regex casaria também com
 * `SnapshotEvent`, e os campos dos dois se misturariam.
 */
function camposDoEspelhoTS() {
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
  // O que importa aqui é o CONTRATO entre o dataclass Python e o espelho em
  // events.ts, não uma contagem. A versão anterior afirmava "55 campos" e
  // quebrou ao ganhar dois — e o erro (`55 != 57`) não dizia quais, nem de que
  // lado estava a divergência.
  const esperados = camposDoEspelhoTS()
  const recebidos = new Set(Object.keys(snap))
  const faltando = [...esperados].filter((c) => !recebidos.has(c))
  const sobrando = [...recebidos].filter((c) => !esperados.has(c))

  checar(`snapshot casa com o espelho TS (${esperados.size} campos)`,
         faltando.length === 0 && sobrando.length === 0)
  if (faltando.length) log(`         so em events.ts: ${faltando.join(', ')}`)
  if (sobrando.length) log(`         so no Python:    ${sobrando.join(', ')}`)
  checar('snapshot traz o executor_id', snap.executor_id === env.EXECUTOR_ID)

  // O ping so responde se o comando atravessou stdin -> thread -> event loop e
  // o ack voltou pelo stdout. E o teste do transporte de ida e volta.
  sup.enviar({ cmd: 'ping', id: 'smoke-1' })
  await esperar(() => eventos.some((e) => e.t === 'ack' && e.id === 'smoke-1'), 10_000, 'o ack do ping')
  const ack = eventos.find((e) => e.t === 'ack' && e.id === 'smoke-1')
  checar('ack do ping veio com ok', ack.ok === true)

  await esperar(() => estados.includes('failed'), 30_000, 'a falha de boot')
  const falha = eventos.find((e) => e.t === 'state' && e.data.phase === 'failed')
  checar('state failed identifica o passo', falha?.data.step === 'server_key')
  checar('state failed traz a causa', typeof falha?.data.detail === 'string' && falha.data.detail.length > 0)
  checar('supervisor nao tenta religar apos falha com causa', sup.estado === 'failed')

  checar('stderr recebeu o log humano', stderrLinhas.length > 0)
  checar('stdout nao teve linha fora do framing', stdoutBrutas.length === 0)
} finally {
  // ESPERA o processo morrer antes de sair.
  //
  // `forcar()` dispara `taskkill` de forma assincrona; sair do script na
  // sequencia deixava o `python.exe` VIVO, segurando as DLLs de
  // `resources/python`. O sintoma aparecia longe daqui: o proximo
  // `npm run python:build` falhava com `EPERM: unlink libcrypto-1_1-x64.dll`,
  // sem nenhuma pista de que um smoke anterior era o culpado.
  const pid = sup.pid
  sup.forcar()
  for (let i = 0; i < 50 && pid; i++) {
    try {
      process.kill(pid, 0)          // so testa a existencia
    } catch {
      break                         // ja morreu
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
