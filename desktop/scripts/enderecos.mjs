// desktop/scripts/enderecos.mjs
//
// Os dois endereços que o app grava no executável: o host dos executores (o
// SERVIDOR de src/shared/servidor.ts) e a UI web (o UI_URL de src/shared/ui.ts).
//
// Vêm do ambiente do BUILD, e não do código: o mesmo código serve a qualquer
// instalação, e cada build grava os seus. No executável continuam fixos, pelos
// motivos de servidor.ts: trocar de servidor exige outro build.
//
//   ATLANS_DESKTOP_SERVIDOR  wss://agents.<domínio>
//   ATLANS_DESKTOP_UI_URL    https://<domínio>
//
// Build sem eles falha: um instalador com endereço vazio, ou com o de outra
// instalação, é pior que nenhum. Só o desenvolvimento local (`--dev`) e os
// testes têm valores próprios.

/** Desenvolvimento local: a API e o web do `make dev`. */
export const DEV = { servidor: 'ws://localhost:8000', ui: 'http://localhost:3000' }

/** Testes: um domínio de exemplo, que não é de instalação nenhuma. */
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
 * Os endereços deste build. `dev` cai nos de {@link DEV} quando o ambiente não
 * traz os seus, e aceita ws/http; um build de verdade exige wss/https e falha
 * sem eles.
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

/** O `define` do esbuild/vite que troca as duas constantes globais. */
export function defineDosEnderecos({ servidor, ui }) {
  return {
    __ATLANS_SERVIDOR__: JSON.stringify(servidor),
    __ATLANS_UI_URL__: JSON.stringify(ui),
  }
}

/** O que build-main.mjs grava em dist/main/build.json: de que modo o bundle saiu. */
export function marcaDoBuild({ dev = false, servidor, ui }) {
  return { modo: dev ? 'dev' : 'producao', servidor, ui }
}

/**
 * Só o bundle de produção vira instalador (build/antes-de-empacotar.cjs).
 * Depois de um `npm run dev`, o dist/main aponta para a máquina local, e um
 * `npm run empacotar` sozinho gerava, sem erro nenhum, um instalador assim.
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
