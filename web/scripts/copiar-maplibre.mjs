#!/usr/bin/env node
// web/scripts/copiar-maplibre.mjs
//
// Copia o worker do MapLibre (`maplibre-gl-worker.mjs` e o
// `maplibre-gl-shared.mjs` que ele importa) de `node_modules/maplibre-gl/dist`
// para `public/maplibre`. O MapLibreMap aponta o `setWorkerUrl` para lá.
//
// Por quê: o maplibre-gl 6 só sai em ESM e roda o worker a partir de uma URL.
// Com bundler ele não acha o arquivo sozinho: cria o worker com a URL da
// própria página, o worker morre em silêncio e os tiles vetoriais nunca
// carregam. O `new URL(..., import.meta.url)` também não serve, porque o
// Turbopack (e o `next build --webpack`) emite o worker sem o `shared` ao lado,
// e o worker cai no primeiro import. A receita do MapLibre para o Next é esta:
// servir os dois do `public/`, na mesma pasta.
//
// Roda no começo do `npm run build` e do `npm run dev`, como o
// copiar-monaco.mjs (chamado no script, e não por gancho: o web/.npmrc liga
// ignore-scripts, e com ele o npm não roda ganchos pre/post). A pasta de
// destino é gerada: está no .gitignore e no .dockerignore do web.
//
// Uso: node scripts/copiar-maplibre.mjs

import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync } from "node:fs"
import { createRequire } from "node:module"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..")
const require = createRequire(join(WEB, "package.json"))
// O `exports` do maplibre-gl expõe o package.json e a pasta dist.
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

// Todo import relativo dos arquivos copiados tem de estar na lista. Se uma
// versão nova dividir o worker em mais pedaços, o build para aqui, em vez de
// subir um mapa que nunca carrega os tiles.
for (const arquivo of ARQUIVOS) {
  const codigo = readFileSync(join(ORIGEM, arquivo), "utf8")
  for (const [, importado] of codigo.matchAll(/(?:\bfrom|\bimport\s*\(?)\s*["'`]\.\/([^"'`]+)["'`]/g)) {
    if (!ARQUIVOS.includes(importado)) {
      console.error(`copiar-maplibre: ${arquivo} importa ./${importado}, que não é copiado — o maplibre-gl ${version} mudou de layout?`)
      process.exit(1)
    }
  }
}

// A pasta sai inteira antes: nenhum arquivo de uma versão anterior fica para trás.
rmSync(DESTINO, { recursive: true, force: true })
mkdirSync(DESTINO, { recursive: true })
for (const arquivo of ARQUIVOS) copyFileSync(join(ORIGEM, arquivo), join(DESTINO, arquivo))
// A licença do MapLibre (BSD-3-Clause pede o aviso junto do binário) vai ao
// lado do worker servido, como o copiar-monaco.mjs faz com a do Monaco.
if (!existsSync(join(pacote, "LICENSE.txt"))) {
  console.error(`copiar-maplibre: ${join(pacote, "LICENSE.txt")} não existe — o maplibre-gl ${version} mudou de layout?`)
  process.exit(1)
}
copyFileSync(join(pacote, "LICENSE.txt"), join(DESTINO, "LICENSE.txt"))
console.log(`copiar-maplibre: worker do maplibre-gl ${version} copiado para public/maplibre`)
