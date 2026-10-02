// desktop/build/antes-de-empacotar.cjs
//
// Hook `beforePack` do electron-builder: só vira instalador o que saiu de
// `npm run build`.
//
// `npm run dev` recompila o dist/main com os endereços da máquina local
// (ws://localhost:8000). Um `npm run empacotar` depois disso gerava, sem erro
// nenhum, um instalador apontando para localhost. O build-main.mjs grava em
// dist/main/build.json de que modo o bundle saiu, e aqui o empacotamento para
// se não for o de produção (scripts/enderecos.mjs).
//
// `.cjs` pelo motivo de sign.cjs: o package.json declara "type": "module".
const fs = require('node:fs')
const path = require('node:path')

exports.default = async function antesDeEmpacotar() {
  const { conferirMarcaDoBuild } = await import('../scripts/enderecos.mjs')
  let marca = null
  try {
    marca = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'dist', 'main', 'build.json'), 'utf8'))
  } catch {
    // Sem marca: nenhum build, ou um dist/ de antes desta conferência.
  }
  conferirMarcaDoBuild(marca)
}
