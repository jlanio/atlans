// desktop/scripts/dev.mjs
//
// Development mode: Vite serving the renderer with HMR + Electron pointed at
// it.
//
// In dev the app uses `resources/python` if it exists and falls back to the
// system Python if not — so you can iterate on the UI without rebuilding 390 MB
// on every change (see `resolverPythonDev` in src/main/paths.ts).
//
//   node scripts/dev.mjs
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { createServer } from 'vite'
import { DESKTOP, log, ok, run, step } from './lib.mjs'

// The Electron binary does not come with `npm ci`: the package (44+) downloads
// it the first time it is called, and desktop/.npmrc turns off install scripts
// anyway. It is downloaded here, once and in a visible step (not hidden in the
// `import('electron')` further down), by the package's own install.js — which
// checks the SHA-256 against the checksums.json that came in the npm tarball
// (which in turn is checked against the package-lock hash).
const ELECTRON = path.join(DESKTOP, 'node_modules', 'electron')
if (!fs.existsSync(path.join(ELECTRON, 'path.txt'))) {
  step('Baixando o binario do Electron (primeira vez depois do npm ci)')
  run(process.execPath, [path.join(ELECTRON, 'install.js')], { stdio: 'inherit' })
}

step('Subindo o dev server do renderer')
const vite = await createServer({ configFile: `${DESKTOP}/vite.config.ts` })
await vite.listen()
const url = vite.resolvedUrls?.local?.[0]
if (!url) throw new Error('o Vite nao reportou a URL local')
ok(`renderer em ${url}`)

step('Compilando main e preload (com sourcemap)')
run(process.execPath, [`${DESKTOP}/scripts/build-main.mjs`, '--dev'], { stdio: 'inherit' })

step('Abrindo o Electron')

// `ELECTRON_RUN_AS_NODE` turns the Electron executable into plain Node: no
// `electron` module, no window, and the process dies with
// "Cannot find module 'electron'" — which with `stdio: inherit` gets lost in the
// middle of Vite's output. Editors' integrated terminals set this variable, and
// it is inherited by everything run from there.
//
// Removed here, and not documented as a prerequisite: requiring the user to
// know this to run `npm run dev` would hand them a problem the script can solve
// on its own.
const env = { ...process.env, VITE_DEV_SERVER_URL: url }
if (env.ELECTRON_RUN_AS_NODE) {
  log('ELECTRON_RUN_AS_NODE estava definido no ambiente — removido para este processo.')
  delete env.ELECTRON_RUN_AS_NODE
}

const electron = spawn((await import('electron')).default, [DESKTOP], {
  stdio: 'inherit',
  env,
})

// Fechar o app derruba o dev server junto: um Vite orfao segurando a porta faz
// o proximo `npm run dev` falhar com "port is already in use".
electron.on('exit', (codigo) => {
  log(`Electron encerrou (${codigo})`)
  void vite.close().then(() => process.exit(codigo ?? 0))
})

for (const sinal of ['SIGINT', 'SIGTERM']) {
  process.on(sinal, () => { electron.kill(); void vite.close() })
}
