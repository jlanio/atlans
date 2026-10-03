// desktop/scripts/enderecos.mjs
//
// The two addresses the app bakes into the executable: the executors' host (the
// SERVIDOR of src/shared/servidor.ts) and the web UI (the UI_URL of src/shared/ui.ts).
//
// They come from the BUILD environment, not from the code: the same code serves
// any installation, and each build bakes in its own. In the executable they
// stay fixed, for the reasons in servidor.ts: switching servers requires
// another build.
//
//   ATLANS_DESKTOP_SERVIDOR  wss://agents.<domain>
//   ATLANS_DESKTOP_UI_URL    https://<domain>
//
// A build without them fails: an installer with an empty address, or with
// another installation's, is worse than none. Only local development (`--dev`)
// and the tests have values of their own.

/** Desenvolvimento local: a API e o web do `make dev`. */
export const DEV = { servidor: 'ws://localhost:8000', ui: 'http://localhost:3000' }

/** Tests: an example domain, which belongs to no installation. */
export const TESTE = { servidor: 'wss://agents.atlans.example.org', ui: 'https://atlans.example.org' }

function validar(nome, valor, protocolos) {
  let url
  try {
    url = new URL(valor)
  } catch {
    throw new Error(`${nome}=${JSON.stringify(valor)} não é uma URL.`)
  }
  if (!protocolos.includes(url.protocol)) {
    throw new Error(`${nome} precisa começar com ${protocolos.join(' ou ')} (veio ${url.protocol}).`)
  }
  if (url.pathname !== '/' || url.search || url.hash || url.username || url.password) {
    throw new Error(`${nome} é só esquema e host (com porta, se houver): ${valor}`)
  }
  return url.origin
}

/**
 * This build's addresses. `dev` falls back to those in {@link DEV} when the
 * environment does not bring its own, and accepts ws/http; a real build
 * requires wss/https and fails without them.
 */
export function enderecosDoBuild({ dev = false } = {}) {
  const servidor = process.env.ATLANS_DESKTOP_SERVIDOR?.trim() || (dev ? DEV.servidor : '')
  const ui = process.env.ATLANS_DESKTOP_UI_URL?.trim() || (dev ? DEV.ui : '')
  const faltando = [!servidor && 'ATLANS_DESKTOP_SERVIDOR', !ui && 'ATLANS_DESKTOP_UI_URL'].filter(Boolean)
  if (faltando.length) {
    throw new Error(
      `Faltam ${faltando.join(' e ')} no ambiente do build: o app grava no executável `
      + 'o servidor e a UI da instalação (ver desktop/scripts/enderecos.mjs).',
    )
  }
  return {
    servidor: validar('ATLANS_DESKTOP_SERVIDOR', servidor, dev ? ['wss:', 'ws:'] : ['wss:']),
    ui: validar('ATLANS_DESKTOP_UI_URL', ui, dev ? ['https:', 'http:'] : ['https:']),
  }
}

/** The esbuild/vite `define` that replaces the two global constants. */
export function defineDosEnderecos({ servidor, ui }) {
  return {
    __ATLANS_SERVIDOR__: JSON.stringify(servidor),
    __ATLANS_UI_URL__: JSON.stringify(ui),
  }
}

/** What build-main.mjs writes to dist/main/build.json: which mode the bundle was built in. */
export function marcaDoBuild({ dev = false, servidor, ui }) {
  return { modo: dev ? 'dev' : 'producao', servidor, ui }
}

/**
 * Only the production bundle becomes an installer (build/antes-de-empacotar.cjs).
 * After an `npm run dev`, dist/main points at the local machine, and an
 * `npm run empacotar` on its own produced, without any error, such an installer.
 */
export function conferirMarcaDoBuild(marca) {
  if (!marca || typeof marca !== 'object') {
    throw new Error('dist/main sem a marca do build (dist/main/build.json): rode `npm run build` antes de empacotar.')
  }
  if (marca.modo !== 'producao') {
    throw new Error(
      `dist/main saiu de \`npm run dev\` (servidor ${marca.servidor}): rode \`npm run build\` antes de empacotar.`,
    )
  }
}
