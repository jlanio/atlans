// desktop/vite.config.ts
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
import { addressDefines, buildAddresses } from './scripts/enderecos.mjs'

/**
 * Blocks `electron` and `node:*` in the renderer bundle.
 *
 * The renderer runs in Chromium, with `sandbox: true` and no Node integration.
 * None of that exists there. The way to fall into this trap is importing a
 * VALUE from a main-process module —
 * `import { SYNC_INTERVAL } from '../../main/state/config'` — which in turn
 * imports `node:fs` and `paths.ts`. Types are safe (they vanish at compile
 * time); values drag the whole tree along.
 *
 * The symptom without this guard is cruel: `tsc` passes, `vite build` passes,
 * and the app opens with the WINDOW PAINTED AND EMPTY — the background has
 * already been drawn by `backgroundColor`, and the module blows up before React
 * mounts. No error shows up in the terminal, only in the DevTools nobody
 * opened.
 *
 * Here it becomes a build error, pointing at who imported what.
 */
function forbidMainModules(): Plugin {
  return {
    name: 'atlans:proibir-modulos-do-main',
    enforce: 'pre',
    resolveId(id, importer) {
      if (id !== 'electron' && !id.startsWith('node:')) return null
      throw new Error(
        `O renderer não pode importar "${id}" (via ${importer ?? 'desconhecido'}).\n`
        + 'Isso acontece ao importar um VALOR de src/main — só `import type` é seguro.\n'
        + 'Mova a constante para src/shared/.',
      )
    },
  }
}

export default defineConfig(({ command }) => ({
  root: 'src/renderer',
  // The installation's server and UI (scripts/enderecos.mjs): `vite build`
  // requires those from the environment; the dev server falls back to the local ones.
  define: addressDefines(buildAddresses({ dev: command === 'serve' })),
  // A relative path is mandatory: packaged, the window loads via `file://`, and
  // Vite's default absolute `/assets/...` would point to the root of the disk.
  base: './',
  plugins: [forbidMainModules(), tailwindcss(), react()],
  build: {
    outDir: '../../dist/renderer',
    emptyOutDir: true,
    target: 'chrome130',      // Electron 33
    sourcemap: false,
  },
  server: { port: 5273, strictPort: true },
}))
