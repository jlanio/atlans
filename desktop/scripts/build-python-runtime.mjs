// desktop/scripts/build-python-runtime.mjs
//
// Installs the executor's dependencies (the executor/requirements-full.txt
// lock, with hashes) into the runtime downloaded by fetch-python.mjs, prunes
// what goes nowhere and writes resources/payload.json with the measurements.
//
// Two decisions worth explaining:
//
// 1. We do NOT create a venv. We install directly into the interpreter. A venv
//    writes `home = <absolute path of the build agent>` into pyvenv.cfg and
//    embeds the same path in the .exe files of Scripts/ — none of that exists
//    on the user's machine. Installing directly makes the tree relocatable by
//    construction, with no "first run" step (which is what the old
//    agent-desktop's conda-unpack did, extracting ~600 MB on first boot).
//
// 2. `--only-binary=:all:`. If some day a dependency loses its win_amd64
//    wheel, we want the build RED in CI, not a runner trying to compile GDAL
//    and producing a bundle that only works on it.
//
//   node scripts/build-python-runtime.mjs [--no-prune] [--no-compile]
import fs from 'node:fs'
import path from 'node:path'
import {
  DESKTOP, LOCK, PY_DIR, PY_EXE, RESOURCES, assertRuntimeExists, dirSize, fail,
  log, mb, ok, python, pythonCapture, readRuntimeSpec, rmrf, step, tarExtract, walk,
} from './lib.mjs'

const semPoda    = process.argv.includes('--no-prune')
const semCompile = process.argv.includes('--no-compile')
const SP = path.join(PY_DIR, 'Lib', 'site-packages')
const medicoes = []

function medir(rotulo, fn) {
  const antes = dirSize(PY_DIR)
  fn()
  const depois = dirSize(PY_DIR)
  const delta = antes - depois
  medicoes.push({ passo: rotulo, delta_bytes: delta, total_bytes: depois })
  const sinal = delta >= 0 ? '-' : '+'
  log(`  ${rotulo.padEnd(34)} ${sinal}${mb(Math.abs(delta)).padStart(4)} MB  ->  ${mb(depois).padStart(4)} MB`)
  return depois
}

assertRuntimeExists()
const spec = readRuntimeSpec()

// ── Clean runtime ────────────────────────────────────────────────────────────
// Pruning removes pip (nothing is installed at runtime), so running this script
// twice failed with "No module named pip" — the build only worked from a fresh
// `fetch`, and `npm run runtime` broke on the second run.
//
// Re-extracting is cheap (the tarball is cached and the hash check has already
// happened) and makes the build idempotent, which is what a build script needs
// to be.
if (!fs.existsSync(path.join(SP, 'pip'))) {
  step('Runtime ja podado — re-extraindo do cache')
  const tarball = path.join(RESOURCES, '.cache', spec.asset)
  if (!fs.existsSync(tarball)) {
    fail(`runtime sem pip e sem tarball em cache.\n  -> rode: npm run python:fetch -- --force`)
  }
  rmrf(PY_DIR)
  tarExtract(tarball, RESOURCES)
  fs.writeFileSync(
    path.join(PY_DIR, '.runtime-spec.json'),
    JSON.stringify({ ...spec, extraido_em: new Date().toISOString() }, null, 2),
  )
  ok('runtime restaurado')
}

// ── Instalacao ───────────────────────────────────────────────────────────────
step('Instalando dependencias')
if (!fs.existsSync(LOCK)) {
  fail(`${LOCK} nao existe.\n  -> rode, na raiz do repositorio: python scripts/travar_python.py`)
}
const bruto = dirSize(PY_DIR)
log(`runtime limpo: ${mb(bruto)} MB`)

python([
  '-m', 'pip', 'install',
  '--require-hashes',             // every file checked against the lock's hash
  '--only-binary=:all:',          // never compile — see header
  '--no-compile',                 // .pyc comes later, all at once, in compileall
  '--no-warn-script-location',
  '--disable-pip-version-check',
  '--quiet',
  '-r', LOCK,
])
const instalado = dirSize(PY_DIR)
ok(`instalado: ${mb(instalado)} MB (+${mb(instalado - bruto)} MB)`)
medicoes.push({ passo: 'pip install', delta_bytes: -(instalado - bruto), total_bytes: instalado })

// ── Pruning ──────────────────────────────────────────────────────────────────
// Every step is measured: without a number, "pruning" becomes a belief. The
// Phase 0 values are in docs — if a step starts yielding zero, someone changed
// the tree.
if (semPoda) {
  log('poda desativada (--no-prune)')
} else {
  step('Podando')

  medir('stdlib GUI/test', () => {
    for (const alvo of ['Lib/test', 'Lib/idlelib', 'Lib/tkinter', 'tcl']) rmrf(path.join(PY_DIR, alvo))
    // _tkinter.pyd without tkinter/ is dead weight; same for the Tcl/Tk DLLs.
    walk(path.join(PY_DIR, 'DLLs'), (p, e) => {
      if (e.isFile() && /^(tcl|tk|_tkinter)/i.test(e.name)) fs.rmSync(p, { force: true })
    })
  })

  medir('suites de teste dos pacotes', () => {
    walk(SP, (p, e) => {
      if (e.isDirectory() && /^(tests?|testing)$/.test(e.name)) { rmrf(p); return false }
    })
  })

  medir('headers e fontes', () => {
    rmrf(path.join(PY_DIR, 'include'))
    rmrf(path.join(PY_DIR, 'libs'))
    walk(SP, (p, e) => {
      if (e.isDirectory() && e.name === 'include') { rmrf(p); return false }
      // .pyi/.pxd/.pyx only serve for type-checking and for compiling extensions —
      // none of that happens on the user's machine.
      if (e.isFile() && /\.(pyi|c|h|pxd|pyx|lib|exp)$/i.test(e.name)) fs.rmSync(p, { force: true })
    })
  })

  medir('pip/setuptools/Scripts', () => {
    // Nothing is installed at runtime, and the entry point is
    // `python.exe -m executor` — no console script from Scripts/ is used.
    for (const alvo of ['pip', 'setuptools', 'wheel', 'pkg_resources', '_distutils_hack']) {
      rmrf(path.join(SP, alvo))
    }
    for (const e of fs.readdirSync(SP)) {
      if (/^(pip|setuptools|wheel)-.*\.(dist-info|egg-info)$/.test(e)) rmrf(path.join(SP, e))
    }
    rmrf(path.join(PY_DIR, 'Scripts'))

    // setuptools' .pth files are executed by `site` on EVERY Python start, and
    // `distutils-precedence.pth` does `import _distutils_hack` — which was just
    // removed above. The result is a 6-line traceback on every executor
    // invocation, on stderr, before anything useful:
    //
    //   Error processing line 1 of ...distutils-precedence.pth
    //   ModuleNotFoundError: No module named '_distutils_hack'
    //
    // It breaks nothing, but it pollutes the app's log panel and scares whoever
    // reads it.
    for (const pth of ['distutils-precedence.pth', '__editable__.pth']) {
      fs.rmSync(path.join(SP, pth), { force: true })
    }
  })

  medir('botocore/data (exceto s3 e sts)', () => {
    // The only use of boto3 in the project is flow/nodes/outputs/save_to_s3.py
    // against MinIO. The other ~400 AWS services are ~20 MB of inert JSON.
    const data = path.join(SP, 'botocore', 'data')
    if (!fs.existsSync(data)) return
    for (const e of fs.readdirSync(data, { withFileTypes: true })) {
      if (e.isDirectory() && !['s3', 'sts'].includes(e.name)) rmrf(path.join(data, e.name))
    }
  })

  medir('__pycache__', () => {
    walk(PY_DIR, (p, e) => {
      if (e.isDirectory() && e.name === '__pycache__') { rmrf(p); return false }
    })
  })
}

// ── Pre-compilation ──────────────────────────────────────────────────────────
// Done AFTER pruning (compiling what would be deleted is waste) and keeping
// the .py files: a readable traceback in support is worth more than the MB saved.
//
// Compiling here is what makes it possible NOT to pass PYTHONDONTWRITEBYTECODE
// at spawn: without ready .pyc files, every boot recompiles pandas/geopandas
// and the executor takes visibly longer to start.
if (semCompile) {
  log('compileall desativado (--no-compile)')
} else {
  step('Pre-compilando (.pyc)')
  medir('compileall', () => {
    // -q silences; a syntax error in an isolated module (there are several in
    // the stdlib for future versions) must not bring down the build — hence the
    // ignored exit code.
    python(['-m', 'compileall', '-q', '-j', '0', path.join(PY_DIR, 'Lib')], { stdio: 'ignore' })
  })
}

// ── Manifesto ────────────────────────────────────────────────────────────────
step('Manifesto')
const versoes = JSON.parse(pythonCapture(['-c', `
import json, importlib.metadata as md
pacotes = {d.metadata["Name"].lower(): d.version for d in md.distributions() if d.metadata["Name"]}
print(json.dumps(pacotes, sort_keys=True))
`]))

const final = dirSize(PY_DIR)
const payload = {
  gerado_em: new Date().toISOString(),
  runtime: { ...spec, _comment: undefined },
  python: pythonCapture(['-c', 'import sys; print(sys.version.split()[0])']).trim(),
  pacotes: versoes,
  // `final` includes the .pyc files from compileall, so `instalado - final` is
  // NOT how much pruning cut — it would be pruning minus pre-compilation, a
  // number that means nothing. Both are reported separately.
  tamanho: {
    runtime_limpo_mb: +mb(bruto),
    apos_pip_mb: +mb(instalado),
    podado_mb: +mb(medicoes.filter((m) => m.delta_bytes > 0).reduce((s, m) => s + m.delta_bytes, 0)),
    pyc_mb: +mb(medicoes.filter((m) => m.delta_bytes < 0 && m.passo === 'compileall')
                        .reduce((s, m) => s - m.delta_bytes, 0)),
    final_mb: +mb(final),
  },
  medicoes: medicoes.map((m) => ({ ...m, delta_mb: +mb(Math.abs(m.delta_bytes)) })),
}
delete payload.runtime._comment
fs.mkdirSync(RESOURCES, { recursive: true })
fs.writeFileSync(path.join(RESOURCES, 'payload.json'), JSON.stringify(payload, null, 2))

console.log()
ok(`${Object.keys(versoes).length} pacotes  |  ${mb(instalado)} MB instalados  ->  ${mb(final)} MB apos poda`)
ok(`manifesto em ${path.relative(DESKTOP, path.join(RESOURCES, 'payload.json'))}`)
