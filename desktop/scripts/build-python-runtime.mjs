// desktop/scripts/build-python-runtime.mjs
//
// Instala as dependencias do executor (o lock executor/requirements-full.txt,
// com hash) no runtime baixado por fetch-python.mjs, poda o que nao vai a
// lugar nenhum e escreve resources/payload.json com as medicoes.
//
// Duas decisoes que valem explicacao:
//
// 1. NAO criamos venv. Instalamos direto no interpretador. Um venv grava
//    `home = <caminho absoluto do build agent>` em pyvenv.cfg e embute o mesmo
//    caminho nos .exe de Scripts/ — nada disso existe na maquina do usuario.
//    Instalar direto torna a arvore relocavel por construcao, sem passo de
//    "primeira execucao" (era o que o conda-unpack do agent-desktop antigo
//    fazia, extraindo ~600 MB no primeiro boot).
//
// 2. `--only-binary=:all:`. Se algum dia uma dependencia perder a wheel
//    win_amd64, queremos o build VERMELHO no CI, e nao um runner tentando
//    compilar GDAL e produzindo um bundle que so funciona nele.
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

// ── Runtime limpo ────────────────────────────────────────────────────────────
// A poda remove o pip (nada e instalado em runtime), entao rodar este script
// duas vezes falhava com "No module named pip" — o build so funcionava a partir
// de um `fetch` novo, e `npm run runtime` quebrava na segunda execucao.
//
// Re-extrair e barato (o tarball esta em cache e a verificacao de hash ja
// aconteceu) e torna o build idempotente, que e o que um script de build
// precisa ser.
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
  '--require-hashes',             // todo arquivo conferido com o hash do lock
  '--only-binary=:all:',          // nunca compilar — ver cabecalho
  '--no-compile',                 // .pyc vem depois, de uma vez, no compileall
  '--no-warn-script-location',
  '--disable-pip-version-check',
  '--quiet',
  '-r', LOCK,
])
const instalado = dirSize(PY_DIR)
ok(`instalado: ${mb(instalado)} MB (+${mb(instalado - bruto)} MB)`)
medicoes.push({ passo: 'pip install', delta_bytes: -(instalado - bruto), total_bytes: instalado })

// ── Poda ─────────────────────────────────────────────────────────────────────
// Cada passo e medido: sem numero, "podar" vira crenca. Os valores da Fase 0
// estao em docs — se um passo comecar a render zero, alguem mudou a arvore.
if (semPoda) {
  log('poda desativada (--no-prune)')
} else {
  step('Podando')

  medir('stdlib GUI/test', () => {
    for (const alvo of ['Lib/test', 'Lib/idlelib', 'Lib/tkinter', 'tcl']) rmrf(path.join(PY_DIR, alvo))
    // _tkinter.pyd sem tkinter/ e peso morto; idem as DLLs do Tcl/Tk.
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
      // .pyi/.pxd/.pyx so servem para type-checking e para compilar extensao —
      // nada disso acontece na maquina do usuario.
      if (e.isFile() && /\.(pyi|c|h|pxd|pyx|lib|exp)$/i.test(e.name)) fs.rmSync(p, { force: true })
    })
  })

  medir('pip/setuptools/Scripts', () => {
    // Nada e instalado em runtime, e o entry point e `python.exe -m executor` —
    // nenhum console script de Scripts/ e usado.
    for (const alvo of ['pip', 'setuptools', 'wheel', 'pkg_resources', '_distutils_hack']) {
      rmrf(path.join(SP, alvo))
    }
    for (const e of fs.readdirSync(SP)) {
      if (/^(pip|setuptools|wheel)-.*\.(dist-info|egg-info)$/.test(e)) rmrf(path.join(SP, e))
    }
    rmrf(path.join(PY_DIR, 'Scripts'))

    // Os .pth do setuptools sao executados pelo `site` em TODO start do Python,
    // e o `distutils-precedence.pth` faz `import _distutils_hack` — que acabou
    // de ser removido acima. O resultado e um traceback de 6 linhas em toda
    // invocacao do executor, no stderr, antes de qualquer coisa util:
    //
    //   Error processing line 1 of ...distutils-precedence.pth
    //   ModuleNotFoundError: No module named '_distutils_hack'
    //
    // Nao quebra nada, mas polui o painel de log do app e assusta quem le.
    for (const pth of ['distutils-precedence.pth', '__editable__.pth']) {
      fs.rmSync(path.join(SP, pth), { force: true })
    }
  })

  medir('botocore/data (exceto s3 e sts)', () => {
    // Unico uso de boto3 no projeto e flow/nodes/outputs/save_to_s3.py contra
    // MinIO. Os outros ~400 servicos da AWS sao ~20 MB de JSON inerte.
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

// ── Pre-compilacao ───────────────────────────────────────────────────────────
// Feita DEPOIS da poda (compilar o que seria apagado e desperdicio) e mantendo
// os .py: traceback legivel no suporte vale mais que os MB economizados.
//
// Compilar aqui e o que permite NAO passar PYTHONDONTWRITEBYTECODE no spawn:
// sem .pyc pronto, cada boot recompila pandas/geopandas e o executor demora
// visivelmente para subir.
if (semCompile) {
  log('compileall desativado (--no-compile)')
} else {
  step('Pre-compilando (.pyc)')
  medir('compileall', () => {
    // -q silencia; falha de sintaxe em modulo isolado (ha varios em stdlib para
    // versoes futuras) nao deve derrubar o build — dai o exit code ignorado.
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
  // `final` inclui os .pyc do compileall, entao `instalado - final` NAO e o
  // quanto a poda cortou — seria a poda menos a pre-compilacao, um numero que
  // nao significa nada. Os dois sao reportados separados.
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
