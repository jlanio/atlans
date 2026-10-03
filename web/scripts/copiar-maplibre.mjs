#!/usr/bin/env node
// web/scripts/copiar-maplibre.mjs
//
// Copies the MapLibre worker (`maplibre-gl-worker.mjs` and the
// `maplibre-gl-shared.mjs` it imports) from `node_modules/maplibre-gl/dist`
// to `public/maplibre`. MapLibreMap points `setWorkerUrl` there.
//
// Why: maplibre-gl 6 ships only as ESM and runs the worker from a URL. With a
// bundler it does not find the file on its own: it creates the worker with the
// page's own URL, the worker dies silently and the vector tiles never load.
// `new URL(..., import.meta.url)` does not work either, because Turbopack (and
// `next build --webpack`) emits the worker without `shared` next to it, and the
// worker fails on the first import. MapLibre's recipe for Next is this: serve
// both from `public/`, in the same folder.
//
// Runs at the start of `npm run build` and `npm run dev`, like
// copiar-monaco.mjs (called from the script, not via a hook: web/.npmrc turns
// on ignore-scripts, and with it npm does not run pre/post hooks). The
// destination folder is generated: it is in the web's .gitignore and
// .dockerignore.
//
// Usage: node scripts/copiar-maplibre.mjs

import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync } from "node:fs"
import { createRequire } from "node:module"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..")
const require = createRequire(join(WEB, "package.json"))
// maplibre-gl's `exports` exposes package.json and the dist folder.
const pacote = dirname(require.resolve("maplibre-gl/package.json"))
const { version } = JSON.parse(readFileSync(join(pacote, "package.json"), "utf8"))

const ORIGEM = join(pacote, "dist")
const DESTINO = join(WEB, "public", "maplibre")
const ARQUIVOS = ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]

for (const arquivo of ARQUIVOS) {
  if (!existsSync(join(ORIGEM, arquivo))) {
    console.error(`copiar-maplibre: ${ORIGEM}/${arquivo} não existe — o maplibre-gl ${version} mudou de layout?`)
    process.exit(1)
  }
}

// Every relative import of the copied files must be in the list. If a new
// version splits the worker into more pieces, the build stops here, instead of
// shipping a map that never loads the tiles.
for (const arquivo of ARQUIVOS) {
  const codigo = readFileSync(join(ORIGEM, arquivo), "utf8")
  for (const [, importado] of codigo.matchAll(/(?:\bfrom|\bimport\s*\(?)\s*["'`]\.\/([^"'`]+)["'`]/g)) {
    if (!ARQUIVOS.includes(importado)) {
      console.error(`copiar-maplibre: ${arquivo} importa ./${importado}, que não é copiado — o maplibre-gl ${version} mudou de layout?`)
      process.exit(1)
    }
  }
}

// The folder is removed entirely first: no file from a previous version is left behind.
rmSync(DESTINO, { recursive: true, force: true })
mkdirSync(DESTINO, { recursive: true })
for (const arquivo of ARQUIVOS) copyFileSync(join(ORIGEM, arquivo), join(DESTINO, arquivo))
// MapLibre's license (BSD-3-Clause requires the notice alongside the binary)
// goes next to the served worker, as copiar-monaco.mjs does with Monaco's.
if (!existsSync(join(pacote, "LICENSE.txt"))) {
  console.error(`copiar-maplibre: ${join(pacote, "LICENSE.txt")} não existe — o maplibre-gl ${version} mudou de layout?`)
  process.exit(1)
}
copyFileSync(join(pacote, "LICENSE.txt"), join(DESTINO, "LICENSE.txt"))
console.log(`copiar-maplibre: worker do maplibre-gl ${version} copiado para public/maplibre`)
