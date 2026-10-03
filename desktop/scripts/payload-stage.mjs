// desktop/scripts/payload-stage.mjs
//
// Copies executor/ and flow/ into desktop/resources/, which is the layout the
// app packages and the one the smoke test exercises.
//
// The layout is NOT arbitrary. executor/job_executor.py does:
//
//     _AGENT_ROOT = dirname(dirname(abspath(__file__)))
//     sys.path.insert(0, _AGENT_ROOT)
//     from flow.executor import WorkflowExecutor
//
// that is, flow/ needs to be a SIBLING of executor/. Hence:
//
//     resources/{python, executor, flow}
//
// and the spawn uses cwd=resources and PYTHONPATH=resources.
//
// The copy is sorted on purpose: electron-updater's .blockmap compares blocks
// byte by byte between releases, and directory read order varying between
// machines would produce false diffs and bloated updates.
//
//   node scripts/payload-stage.mjs
import fs from 'node:fs'
import path from 'node:path'
import { REPO, RESOURCES, dirSize, fail, log, mb, ok, sortedEntries, rmrf, step } from './lib.mjs'

// Exclusions per source. Developer secrets (.env, certs/) must NEVER end up
// in the installer — the app uses %APPDATA%\AtlansExecutor for that.
const ALVOS = [
  {
    nome: 'executor',
    excluir: [
      /^\.env$/,                    // dev's local config
      /^certs$/,                    // dev's mTLS cert
      /^__pycache__$/,
      /\.pyc$/,
      /\.sqlite(-wal|-shm)?$/,      // outbox local
      /^requirements(-full)?\.(in|txt)$/, // the dependencies already come installed in the runtime
      /^README\.md$/,
    ],
    // .env.example STAYS: it is what seed_env_from_example copies on first boot.
  },
  { nome: 'flow', excluir: [/^__pycache__$/, /\.pyc$/] },
]

function copiar(origem, destino, excluir) {
  fs.mkdirSync(destino, { recursive: true })
  let arquivos = 0
  for (const e of sortedEntries(origem)) {
    if (excluir.some((re) => re.test(e.name))) continue
    const de = path.join(origem, e.name)
    const para = path.join(destino, e.name)
    if (e.isDirectory()) arquivos += copiar(de, para, excluir)
    else if (e.isFile()) { fs.copyFileSync(de, para); arquivos++ }
  }
  return arquivos
}

step('Copiando payload Python')
fs.mkdirSync(RESOURCES, { recursive: true })

for (const alvo of ALVOS) {
  const origem = path.join(REPO, alvo.nome)
  if (!fs.existsSync(origem)) fail(`nao encontrei ${origem}`)
  const destino = path.join(RESOURCES, alvo.nome)
  rmrf(destino)
  const n = copiar(origem, destino, alvo.excluir)
  log(`  ${alvo.nome.padEnd(9)} ${String(n).padStart(4)} arquivos  ${mb(dirSize(destino)).padStart(3)} MB`)
}

// Guardrail: if a dev .env slips into the installer, credentials leak.
// Cheap to check, expensive to find out later.
for (const proibido of ['executor/.env', 'executor/certs']) {
  if (fs.existsSync(path.join(RESOURCES, proibido))) {
    fail(`${proibido} entrou no payload — o filtro de exclusao falhou`)
  }
}

// The Atlans license and the third-party notices go with the installer
// (extraResources in electron-builder.yml): whoever distributes it distributes
// what goes inside it along with it.
for (const [de, para] of [['LICENSE', 'LICENSE.txt'], ['THIRD-PARTY-NOTICES.md', 'THIRD-PARTY-NOTICES.md']]) {
  const origem = path.join(REPO, de)
  if (!fs.existsSync(origem)) fail(`nao encontrei ${origem}`)
  fs.copyFileSync(origem, path.join(RESOURCES, para))
}

ok('payload pronto em resources/{executor,flow}, com a licenca e os avisos')
