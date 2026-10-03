// desktop/scripts/build-main.mjs
//
// Bundles the main process and the preload with esbuild.
//
// They come out as **.cjs**, not ESM, even though package.json has "type": "module".
// Reason: the preload runs with `sandbox: true`, and in that mode Electron only
// accepts CommonJS — an ESM preload simply does not load, and the failure is
// silent (the window opens with `window.atlas` undefined). Keeping both in the
// same format avoids the question "why is only one of them cjs".
//
// `electron` stays external: it is a module built into the runtime, not a
// package to bundle.
import { build } from 'esbuild'
import fs from 'node:fs'
import path from 'node:path'
import { addressDefines, buildAddresses, buildBrand } from './enderecos.mjs'
import { DESKTOP, log, ok, step } from './lib.mjs'

const dev = process.argv.includes('--dev')
const saida = path.join(DESKTOP, 'dist')

step('Empacotando main e preload')
fs.mkdirSync(saida, { recursive: true })

const enderecos = buildAddresses({ dev })

const comum = {
  bundle: true,
  platform: 'node',
  target: 'node20',           // Electron 33 traz Node 20
  format: 'cjs',
  sourcemap: dev ? 'inline' : false,
  minify: !dev,
  external: ['electron'],
  logLevel: 'info',
  define: {
    'process.env.NODE_ENV': JSON.stringify(dev ? 'development' : 'production'),
    // The installation's server and UI, baked into the executable (enderecos.mjs).
    ...addressDefines(enderecos),
  },
}

await build({
  ...comum,
  entryPoints: [path.join(DESKTOP, 'src/main/index.ts')],
  outfile: path.join(saida, 'main', 'index.cjs'),
})

await build({
  ...comum,
  entryPoints: [path.join(DESKTOP, 'src/preload/index.ts')],
  outfile: path.join(saida, 'main', 'preload.cjs'),
})

// Preload for the web window (janela-web.ts). Separate from the panel's preload
// on purpose: to the remote content of the web UI it exposes ONLY the read-only
// bridge window.atlansDesktop (the executor's public status) — no ipcRenderer
// and no window.atlas. See the header of preload/web.ts.
await build({
  ...comum,
  entryPoints: [path.join(DESKTOP, 'src/preload/web.ts')],
  outfile: path.join(saida, 'main', 'web-preload.cjs'),
})

// `import.meta.dirname` does not exist in CJS; esbuild converts it, but the
// code uses the value to find the preloads and icons next to the bundle.
// Confirming that the files ended up in the SAME directory avoids a "preload
// not found" that would only show up in the packaged app.
for (const arquivo of ['index.cjs', 'preload.cjs', 'web-preload.cjs']) {
  const p = path.join(saida, 'main', arquivo)
  if (!fs.existsSync(p)) throw new Error(`esbuild nao produziu ${p}`)
  log(`  ${arquivo.padEnd(16)} ${(fs.statSync(p).size / 1024).toFixed(0)} KB`)
}

// Which mode this bundle was built in: packaging only accepts the production
// one (build/antes-de-empacotar.cjs).
fs.writeFileSync(
  path.join(saida, 'main', 'build.json'),
  JSON.stringify(buildBrand({ dev, ...enderecos }), null, 2) + '\n',
)

ok('main e preload prontos em dist/main/')
