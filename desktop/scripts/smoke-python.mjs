// desktop/scripts/smoke-python.mjs
//
// Executa scripts/smoke.py dentro do runtime empacotado, no mesmo ambiente do
// spawn de producao (cwd=resources, PYTHONPATH=resources, env sanitizado).
//
// Roda SEMPRE no CI, inclusive quando o cache do runtime deu hit: o cache cobre
// resources/python/, mas executor/ e flow/ mudam a cada commit — e e justamente
// o import de flow via job_executor.py que quebra quando alguem mexe na arvore.
//
//   node scripts/smoke-python.mjs
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { PY_EXE, RESOURCES, SCRIPTS, assertRuntimeExists, fail, ok, pythonEnv, run, step } from './lib.mjs'

assertRuntimeExists()
for (const dir of ['executor', 'flow']) {
  if (!fs.existsSync(path.join(RESOURCES, dir))) {
    fail(`resources/${dir} ausente\n  -> rode: npm run payload:stage`)
  }
}

const env = pythonEnv({
  PYTHONPATH: RESOURCES,
  // Aponta para um caminho inexistente de proposito: sem isso o load_dotenv de
  // config.py pegaria o .env do desenvolvedor e o smoke passaria a testar a
  // maquina de quem roda, nao o bundle.
  EXECUTOR_ENV_PATH: path.join(RESOURCES, '.env.inexistente-no-smoke'),
})

step('Smoke do bundle Python')
run(PY_EXE, ['-X', 'utf8', path.join(SCRIPTS, 'smoke.py')], { cwd: RESOURCES, env })

// `enroll --help` cobre o caminho de entrada real do app: __main__.py chama
// bootstrap_ca() antes de qualquer import de sub-comando, e e la que um
// certifi/cryptography quebrado apareceria. Roda em cwd temporario porque o
// bootstrap escreve certs/ ao lado.
step('python -m executor enroll --help')
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-smoke-'))
try {
  run(PY_EXE, ['-X', 'utf8', '-m', 'executor', 'enroll', '--help'], { cwd: tmp, env, stdio: 'ignore' })
  ok('entry point responde')
} finally {
  fs.rmSync(tmp, { recursive: true, force: true })
}

console.log()
ok('bundle validado')
