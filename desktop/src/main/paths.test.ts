import { describe, expect, it, vi } from 'vitest'

// `paths.ts` reads the user's folders from `electron` at the top of the module:
// only what it touches is mocked.
vi.mock('electron', () => ({
  app: {
    setName: vi.fn(),
    isPackaged: false,
    getAppPath: () => '/app',
    getPath: (nome: string) => `/perfil/${nome}`,
    getVersion: () => '9.9.9',
  },
}))

const { envDoExecutor } = await import('./paths.js')

describe('envDoExecutor', () => {
  it('gives the executor the site, besides the executors host', () => {
    // vitest.config.ts: the example installation of scripts/enderecos.mjs.
    const env = envDoExecutor('/artefatos')

    expect(env.EXECUTOR_SERVER_URL).toBe('wss://agents.atlans.example.org')
    expect(env.EXECUTOR_PUBLIC_SERVER_URL).toBe('https://atlans.example.org')
  })
})
