// desktop/vite.config.ts
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
import { defineDosEnderecos, enderecosDoBuild } from './scripts/enderecos.mjs'

/**
 * Barra `electron` e `node:*` no bundle do renderer.
 *
 * O renderer roda no Chromium, com `sandbox: true` e sem integração com Node.
 * Nada disso existe lá. O jeito de cair nessa armadilha é importar um VALOR de
 * um módulo do main — `import { INTERVALO_SYNC } from '../../main/state/config'`
 * — que por sua vez importa `node:fs` e `paths.ts`. Tipos são seguros (somem na
 * compilação); valores arrastam a árvore inteira.
 *
 * O sintoma sem esta guarda é cruel: o `tsc` passa, o `vite build` passa, e o
 * app abre com a JANELA PINTADA E VAZIA — o fundo já foi desenhado pelo
 * `backgroundColor`, e o módulo estoura antes de o React montar. Nenhum erro
 * aparece no terminal, só no DevTools que ninguém abriu.
 *
 * Aqui vira erro de build, apontando quem importou o quê.
 */
function proibirModulosDoMain(): Plugin {
  return {
    name: 'atlans:proibir-modulos-do-main',
    enforce: 'pre',
    resolveId(id, importador) {
      if (id !== 'electron' && !id.startsWith('node:')) return null
      throw new Error(
        `O renderer não pode importar "${id}" (via ${importador ?? 'desconhecido'}).\n`
        + 'Isso acontece ao importar um VALOR de src/main — só `import type` é seguro.\n'
        + 'Mova a constante para src/shared/.',
      )
    },
  }
}

export default defineConfig(({ command }) => ({
  root: 'src/renderer',
  // O servidor e a UI da instalação (scripts/enderecos.mjs): o `vite build`
  // exige os do ambiente; o servidor de desenvolvimento cai nos locais.
  define: defineDosEnderecos(enderecosDoBuild({ dev: command === 'serve' })),
  // Caminho relativo é obrigatório: empacotado, a janela carrega por `file://`,
  // e o `/assets/...` absoluto do padrão do Vite apontaria para a raiz do disco.
  base: './',
  plugins: [proibirModulosDoMain(), tailwindcss(), react()],
  build: {
    outDir: '../../dist/renderer',
    emptyOutDir: true,
    target: 'chrome130',      // Electron 33
    sourcemap: false,
  },
  server: { port: 5273, strictPort: true },
}))
