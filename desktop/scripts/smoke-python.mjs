// desktop/scripts/smoke-python.mjs
//
// Runs scripts/smoke.py inside the packaged runtime, in the same environment as
// the production spawn (cwd=resources, PYTHONPATH=resources, sanitized env).
//
// ALWAYS runs in CI, even when the runtime cache hit: the cache covers
// resources/python/, but executor/ and flow/ change with every commit — and it
// is precisely the import of flow via job_executor.py that breaks when someone
// touches the tree.
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
  // Points to a nonexistent path on purpose: without it, config.py's
  // load_dotenv would pick up the developer's .env and the smoke test would
  // end up testing the machine of whoever runs it, not the bundle.
  EXECUTOR_ENV_PATH: path.join(RESOURCES, '.env.inexistente-no-smoke'),
})

step('Smoke do bundle Python')
run(PY_EXE, ['-X', 'utf8', path.join(SCRIPTS, 'smoke.py')], { cwd: RESOURCES, env })

// `enroll --help` covers the app's real entry path: __main__.py calls
// bootstrap_ca() before any subcommand import, and that is where a broken
// certifi/cryptography would show up. Runs in a temporary cwd because the
// bootstrap writes certs/ next to it.
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
