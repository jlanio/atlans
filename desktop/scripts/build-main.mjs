// desktop/scripts/build-main.mjs
//
// Empacota o processo principal e o preload com esbuild.
//
// Saem como **.cjs**, e nao ESM, apesar de o package.json ter "type": "module".
// Motivo: o preload roda com `sandbox: true`, e nesse modo o Electron so aceita
// CommonJS — um preload ESM simplesmente nao carrega, e a falha e silenciosa
// (a janela abre com `window.atlas` indefinido). Manter os dois no mesmo
// formato evita a pergunta "por que so um deles e cjs".
//
// `electron` fica como external: e um modulo embutido no runtime, nao um
// pacote a empacotar.
import { build } from 'esbuild'
import fs from 'node:fs'
import path from 'node:path'
import { defineDosEnderecos, enderecosDoBuild, marcaDoBuild } from './enderecos.mjs'
import { DESKTOP, log, ok, step } from './lib.mjs'

const dev = process.argv.includes('--dev')
const saida = path.join(DESKTOP, 'dist')

step('Empacotando main e preload')
fs.mkdirSync(saida, { recursive: true })

const enderecos = enderecosDoBuild({ dev })

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
    // O servidor e a UI da instalação, gravados no executável (enderecos.mjs).
    ...defineDosEnderecos(enderecos),
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

// Preload da janela web (janela-web.ts). Separado do preload do painel de
// proposito: ao conteudo remoto da UI web ele expoe SO a ponte read-only
// window.atlansDesktop (status publico do executor) — nada de ipcRenderer nem
// window.atlas. Ver o cabecalho de preload/web.ts.
await build({
  ...comum,
  entryPoints: [path.join(DESKTOP, 'src/preload/web.ts')],
  outfile: path.join(saida, 'main', 'web-preload.cjs'),
})

// `import.meta.dirname` nao existe em CJS; o esbuild o converte, mas o codigo
// usa o valor para achar os preloads e os icones ao lado do bundle. Confirmar
// que os arquivos ficaram no MESMO diretorio evita um "preload nao encontrado"
// que so apareceria no app empacotado.
for (const arquivo of ['index.cjs', 'preload.cjs', 'web-preload.cjs']) {
  const p = path.join(saida, 'main', arquivo)
  if (!fs.existsSync(p)) throw new Error(`esbuild nao produziu ${p}`)
  log(`  ${arquivo.padEnd(16)} ${(fs.statSync(p).size / 1024).toFixed(0)} KB`)
}

// De que modo este bundle saiu: o empacotamento só aceita o de produção
// (build/antes-de-empacotar.cjs).
fs.writeFileSync(
  path.join(saida, 'main', 'build.json'),
  JSON.stringify(marcaDoBuild({ dev, ...enderecos }), null, 2) + '\n',
)

ok('main e preload prontos em dist/main/')
