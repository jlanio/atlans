// desktop/build/antes-de-empacotar.cjs
//
// electron-builder `beforePack` hook: only what came out of `npm run build`
// becomes an installer.
//
// `npm run dev` recompiles dist/main with the local machine's addresses
// (ws://localhost:8000). An `npm run empacotar` after that produced, without
// any error, an installer pointing at localhost. build-main.mjs writes to
// dist/main/build.json which mode the bundle was built in, and here packaging
// stops if it is not the production one (scripts/enderecos.mjs).
//
// `.cjs` for the same reason as sign.cjs: package.json declares "type": "module".
const fs = require('node:fs')
const path = require('node:path')

exports.default = async function beforePack() {
  const { conferirMarcaDoBuild } = await import('../scripts/enderecos.mjs')
  let marca = null
  try {
    marca = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'dist', 'main', 'build.json'), 'utf8'))
  } catch {
    // No marker: no build, or a dist/ from before this check.
  }
  conferirMarcaDoBuild(marca)
}
