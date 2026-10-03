// desktop/vitest.config.ts
//
// Separate from vite.config.ts on purpose: that one has `root: 'src/renderer'`
// for the window build, and inheriting that root would make vitest miss the
// main process tests, which is where the tricky logic lives.
import { defineConfig } from 'vitest/config'
import { addressDefines, TEST } from './scripts/enderecos.mjs'

export default defineConfig({
  // The tests run with an example domain in place of the server and UI that
  // the build writes (scripts/enderecos.mjs).
  define: addressDefines(TEST),
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    environment: 'node',
    // Fails if a test leaves a timer or a listener hanging.
    restoreMocks: true,
  },
})
