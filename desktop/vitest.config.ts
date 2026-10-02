// desktop/vitest.config.ts
//
// Separado do vite.config.ts de proposito: aquele tem `root: 'src/renderer'`
// para o build da janela, e herdar essa raiz faria o vitest nao enxergar os
// testes do processo principal, que e onde mora a logica com armadilha.
import { defineConfig } from 'vitest/config'
import { defineDosEnderecos, TESTE } from './scripts/enderecos.mjs'

export default defineConfig({
  // Os testes rodam com um domínio de exemplo no lugar do servidor e da UI que
  // o build grava (scripts/enderecos.mjs).
  define: defineDosEnderecos(TESTE),
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    environment: 'node',
    // Falha se um teste esquecer um timer ou um ouvinte pendurado.
    restoreMocks: true,
  },
})
