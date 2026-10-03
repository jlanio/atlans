#!/usr/bin/env node
// web/scripts/copiar-monaco.mjs
//
// Copies `node_modules/monaco-editor/min/vs` to `public/monaco/vs`: the code
// editor (monaco-code-editor.tsx) now loads Monaco from its own origin.
//
// Why serve it from here: @monaco-editor/loader fetches, by default, the AMD
// loader and the workers from jsdelivr. With the blocking CSP (next.config.ts)
// that is `script-src` outside the list — the editor would sit on the skeleton
// forever — and, even without a CSP, it makes the editor depend on open egress
// (on a corporate network it does not even open) and on a version that may not
// be the installed one.
//
// Runs at the start of `npm run build` and `npm run dev` (called explicitly
// from the script, not via a prebuild/predev hook: web/.npmrc turns on
// ignore-scripts, and with it npm does not run pre/post hooks). The
// destination folder is generated: it is in the web's .gitignore and .dockerignore.
//
// Usage: node scripts/copiar-monaco.mjs

import { cpSync, existsSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { createRequire } from "node:module"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..")
const require = createRequire(join(WEB, "package.json"))
// The package root comes from the same node_modules lookup that `require`
// does, and not from `require.resolve("monaco-editor/package.json")`: since
// 0.56 monaco-editor's `exports` maps "./*" to "./esm/vs/*.js", and that path
// became esm/vs/package.json.js, which does not exist.
const pacote = require.resolve.paths("monaco-editor")
  .map((dir) => join(dir, "monaco-editor"))
  .find((dir) => existsSync(join(dir, "package.json")))
if (!pacote) {
  console.error("copiar-monaco: o monaco-editor não está instalado (rode `npm ci` no web/)")
  process.exit(1)
}
const { version } = JSON.parse(readFileSync(join(pacote, "package.json"), "utf8"))

const ORIGEM = join(pacote, "min", "vs")
const DESTINO = join(WEB, "public", "monaco", "vs")
// The copied version is stored alongside: without it, changing monaco-editor in
// package.json and running dev again would leave the old copy in place.
const MARCA = join(WEB, "public", "monaco", "VERSAO")

if (!existsSync(join(ORIGEM, "loader.js"))) {
  console.error(`copiar-monaco: ${ORIGEM}/loader.js não existe — o monaco-editor ${version} mudou de layout?`)
  process.exit(1)
}

const copiada = existsSync(MARCA) ? readFileSync(MARCA, "utf8").trim() : null
if (copiada === version && existsSync(join(DESTINO, "loader.js"))) {
  console.log(`copiar-monaco: monaco-editor ${version} já em public/monaco/vs`)
} else {
  // The marker is removed FIRST and only comes back at the end: an interrupted
  // copy (Ctrl+C in dev, a killed build) leaves the folder without a marker and
  // the next run redoes everything, instead of taking a half-copied folder as
  // complete.
  rmSync(MARCA, { force: true })
  rmSync(DESTINO, { recursive: true, force: true })
  cpSync(ORIGEM, DESTINO, { recursive: true })
  writeFileSync(MARCA, `${version}\n`)
  console.log(`copiar-monaco: monaco-editor ${version} copiado para public/monaco/vs`)
}

// Monaco's license and the notices for what it bundles go along with the code
// the installation serves: the web build does not carry node_modules.
for (const nome of ["LICENSE", "ThirdPartyNotices.txt"]) {
  if (!existsSync(join(pacote, nome))) {
    console.error(`copiar-monaco: ${join(pacote, nome)} não existe — o monaco-editor ${version} mudou de layout?`)
    process.exit(1)
  }
  cpSync(join(pacote, nome), join(WEB, "public", "monaco", nome))
}
