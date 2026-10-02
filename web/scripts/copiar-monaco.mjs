#!/usr/bin/env node
// web/scripts/copiar-monaco.mjs
//
// Copia `node_modules/monaco-editor/min/vs` para `public/monaco/vs`: o editor de
// código (monaco-code-editor.tsx) passa a carregar o Monaco da própria origem.
//
// Por que servir daqui: o @monaco-editor/loader busca, por padrão, o loader AMD
// e os workers no jsdelivr. Com a CSP bloqueante (next.config.ts) isso é
// `script-src` fora da lista — o editor ficaria no skeleton para sempre — e,
// mesmo sem CSP, é o editor dependente de egress liberado (em rede corporativa
// ele nem abre) e de uma versão que pode não ser a instalada.
//
// Roda no começo do `npm run build` e do `npm run dev` (chamado explicitamente
// no script, não por gancho prebuild/predev: o web/.npmrc liga ignore-scripts,
// e com ele o npm não roda ganchos pre/post). A
// pasta de destino é gerada: está no .gitignore e no .dockerignore do web.
//
// Uso: node scripts/copiar-monaco.mjs

import { cpSync, existsSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { createRequire } from "node:module"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..")
const require = createRequire(join(WEB, "package.json"))
// A raiz do pacote sai da mesma busca por node_modules que o `require` faz, e
// não de `require.resolve("monaco-editor/package.json")`: desde o 0.56 o
// `exports` do monaco-editor mapeia "./*" para "./esm/vs/*.js", e aquele
// caminho virava esm/vs/package.json.js, que não existe.
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
// A versão copiada fica ao lado: sem ela, trocar o monaco-editor no package.json
// e rodar o dev de novo deixaria a cópia velha no lugar.
const MARCA = join(WEB, "public", "monaco", "VERSAO")

if (!existsSync(join(ORIGEM, "loader.js"))) {
  console.error(`copiar-monaco: ${ORIGEM}/loader.js não existe — o monaco-editor ${version} mudou de layout?`)
  process.exit(1)
}

const copiada = existsSync(MARCA) ? readFileSync(MARCA, "utf8").trim() : null
if (copiada === version && existsSync(join(DESTINO, "loader.js"))) {
  console.log(`copiar-monaco: monaco-editor ${version} já em public/monaco/vs`)
} else {
  // A marca sai ANTES e volta só no fim: uma cópia interrompida (Ctrl+C no
  // dev, build morto) deixa a pasta sem marca e a próxima rodada refaz tudo,
  // em vez de dar por completa uma pasta com metade dos arquivos.
  rmSync(MARCA, { force: true })
  rmSync(DESTINO, { recursive: true, force: true })
  cpSync(ORIGEM, DESTINO, { recursive: true })
  writeFileSync(MARCA, `${version}\n`)
  console.log(`copiar-monaco: monaco-editor ${version} copiado para public/monaco/vs`)
}

// A licença do Monaco e os avisos do que ele embute vão junto com o código que
// a instalação serve: o build do web não leva o node_modules.
for (const nome of ["LICENSE", "ThirdPartyNotices.txt"]) {
  if (!existsSync(join(pacote, nome))) {
    console.error(`copiar-monaco: ${join(pacote, nome)} não existe — o monaco-editor ${version} mudou de layout?`)
    process.exit(1)
  }
  cpSync(join(pacote, nome), join(WEB, "public", "monaco", nome))
}
