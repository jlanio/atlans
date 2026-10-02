// desktop/scripts/payload-stage.mjs
//
// Copia executor/ e flow/ para desktop/resources/, que e o layout que o app
// empacota e o que o smoke test exercita.
//
// O layout NAO e arbitrario. executor/job_executor.py faz:
//
//     _AGENT_ROOT = dirname(dirname(abspath(__file__)))
//     sys.path.insert(0, _AGENT_ROOT)
//     from flow.executor import WorkflowExecutor
//
// ou seja, flow/ precisa ser IRMAO de executor/. Dai:
//
//     resources/{python, executor, flow}
//
// e o spawn usa cwd=resources e PYTHONPATH=resources.
//
// A copia e ordenada de proposito: o .blockmap do electron-updater compara
// blocos byte a byte entre releases, e ordem de leitura de diretorio variando
// entre maquinas produziria diffs falsos e updates gordos.
//
//   node scripts/payload-stage.mjs
import fs from 'node:fs'
import path from 'node:path'
import { REPO, RESOURCES, dirSize, fail, log, mb, ok, sortedEntries, rmrf, step } from './lib.mjs'

// Exclusoes por origem. Segredos do desenvolvedor (.env, certs/) NUNCA podem
// entrar no instalador — o app usa %APPDATA%\AtlansExecutor para isso.
const ALVOS = [
  {
    nome: 'executor',
    excluir: [
      /^\.env$/,                    // config local do dev
      /^certs$/,                    // cert mTLS do dev
      /^__pycache__$/,
      /\.pyc$/,
      /\.sqlite(-wal|-shm)?$/,      // outbox local
      /^requirements(-full)?\.(in|txt)$/, // as dependencias ja vem instaladas no runtime
      /^README\.md$/,
    ],
    // .env.example FICA: e o que seed_env_from_example copia no primeiro boot.
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

// Guarda-corpo: se um .env do dev escapar para o instalador, vaza credencial.
// Barato de checar, caro de descobrir depois.
for (const proibido of ['executor/.env', 'executor/certs']) {
  if (fs.existsSync(path.join(RESOURCES, proibido))) {
    fail(`${proibido} entrou no payload — o filtro de exclusao falhou`)
  }
}

// A licença do Atlans e os avisos de terceiros vão com o instalador
// (extraResources do electron-builder.yml): quem o distribui distribui junto
// o que vai dentro dele.
for (const [de, para] of [['LICENSE', 'LICENSE.txt'], ['THIRD-PARTY-NOTICES.md', 'THIRD-PARTY-NOTICES.md']]) {
  const origem = path.join(REPO, de)
  if (!fs.existsSync(origem)) fail(`nao encontrei ${origem}`)
  fs.copyFileSync(origem, path.join(RESOURCES, para))
}

ok('payload pronto em resources/{executor,flow}, com a licenca e os avisos')
