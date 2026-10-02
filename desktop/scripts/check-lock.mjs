// desktop/scripts/check-lock.mjs
//
// Confere, no CPython do Windows, que o lock do executor instala. O
// executor/requirements-full.txt (gerado por scripts/travar_python.py, com o
// hash de cada arquivo) é o que o build do runtime instala: o app desktop roda
// as mesmas versoes, e os mesmos arquivos, do executor do Docker.
//
// Por que nao um lock proprio do Windows, como antes: ele era uma copia do lock
// do executor que precisava ser regerada no Windows a cada mudanca, e o
// Dependabot, que o via como arquivo solto, subia as transitivas so nele —
// deixando a imagem para tras. Um lock so nao tem como divergir.
//
// O lock e resolvido no Linux. O que so o Windows revela aparece aqui, no CI,
// e nao no build do instalador:
//   - um pacote sem wheel win_amd64 para o cp312 do runtime (--only-binary);
//   - uma dependencia que so o Windows pede e que o lock nao tem: no modo de
//     hash, o pip recusa instalar o que nao esta no arquivo;
//   - incompatibilidade entre os pacotes instalados (pip check).
//
// O ambiente e SEMPRE limpo, extraido do tarball em cache (conferido pelo
// SHA-256). Nao reutiliza resources/python/, que ja foi podado (sem pip).
//
//   node scripts/check-lock.mjs
import fs from 'node:fs'
import path from 'node:path'
import {
  DESKTOP, LOCK, REPO, RESOURCES, capture, fail, log, ok, pythonEnv,
  readRuntimeSpec, rmrf, sha256, step, tarExtract,
} from './lib.mjs'

const spec = readRuntimeSpec()
const tarball = path.join(RESOURCES, '.cache', spec.asset)
const lockDir = path.join(RESOURCES, '.lockenv')
const lockPy = path.join(lockDir, 'python', 'python.exe')

if (!fs.existsSync(LOCK)) fail(`nao encontrei ${LOCK}\n  -> rode: python scripts/travar_python.py`)
if (!fs.existsSync(tarball)) fail(`tarball do runtime ausente\n  -> rode: npm run python:fetch`)
if (sha256(tarball) !== spec.sha256) fail('tarball em cache com hash divergente — rode npm run python:fetch --force')

const py = (args) => capture(lockPy, args, { env: pythonEnv() })

step('Conferindo o lock do executor no Windows')
rmrf(lockDir)
tarExtract(tarball, lockDir)
log(`ambiente limpo em ${path.relative(DESKTOP, lockDir)}`)

try {
  // As mesmas flags do build do runtime (build-python-runtime.mjs).
  py(['-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:', '--no-compile', '--quiet',
      '--disable-pip-version-check', '-r', LOCK])
  py(['-m', 'pip', 'check'])
  ok(`${path.relative(REPO, LOCK)} instala no CPython ${spec.version} (win_amd64), com hash e consistente`)
} finally {
  rmrf(lockDir)
}
