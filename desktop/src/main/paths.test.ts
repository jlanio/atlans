import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { afterAll, beforeEach, describe, expect, it, vi } from 'vitest'

// A real folder: the migration is file system work. `userData` lives in it, so
// the old names are its siblings, as under %APPDATA%.
const raiz = fs.mkdtempSync(path.join(os.tmpdir(), 'atlans-paths-'))

// `paths.ts` reads the user's folders from `electron` at the top of the module:
// only what it touches is mocked.
vi.mock('electron', () => ({
  app: {
    setName: vi.fn(),
    isPackaged: false,
    getAppPath: () => '/app',
    getPath: (nome: string) => path.join(raiz, nome === 'userData' ? 'AtlansExecutor' : nome),
    getVersion: () => '9.9.9',
  },
}))

const { envDoExecutor, migrateLegacyData, USER_DATA } = await import('./paths.js')

describe('envDoExecutor', () => {
  it('gives the executor the site, besides the executors host', () => {
    // vitest.config.ts: the example installation of scripts/enderecos.mjs.
    const env = envDoExecutor('/artefatos')

    expect(env.EXECUTOR_SERVER_URL).toBe('wss://agents.atlans.example.org')
    expect(env.EXECUTOR_PUBLIC_SERVER_URL).toBe('https://atlans.example.org')
  })
})

describe('migrateLegacyData', () => {
  const escrever = (rel: string, conteudo = 'x') => {
    const alvo = path.join(raiz, rel)
    fs.mkdirSync(path.dirname(alvo), { recursive: true })
    fs.writeFileSync(alvo, conteudo)
  }
  const ler = (rel: string) => fs.readFileSync(path.join(raiz, rel), 'utf8')
  const existe = (rel: string) => fs.existsSync(path.join(raiz, rel))

  /** An old install: config, the mTLS cert, logs and Chromium's own leftovers. */
  const instalacaoAntiga = (nome: string) => {
    escrever(`${nome}/config/.env`, 'EXECUTOR_ID=antigo\n')
    escrever(`${nome}/certs/cert.pem`, 'CERT')
    escrever(`${nome}/certs/key.pem`, 'KEY')
    escrever(`${nome}/logs/agent.log`, 'log')
    escrever(`${nome}/Cache/data_0`, 'cache')
  }

  beforeEach(() => {
    for (const e of fs.readdirSync(raiz)) fs.rmSync(path.join(raiz, e), { recursive: true, force: true })
  })
  afterAll(() => { fs.rmSync(raiz, { recursive: true, force: true }) })

  it('migra mesmo com a pasta nova já criada pelo Chromium', () => {
    // The case that never fired: the single-instance lock and Chromium create
    // userData before `whenReady`, and the old check on the folder itself
    // skipped the migration — the user lost the certificate.
    instalacaoAntiga('AtlasExecutor')
    escrever('AtlansExecutor/lockfile', '')
    escrever('AtlansExecutor/Network/Cookies', '')

    expect(migrateLegacyData()).toBe('AtlasExecutor')
    expect(ler('AtlansExecutor/config/.env')).toBe('EXECUTOR_ID=antigo\n')
    expect(ler('AtlansExecutor/certs/key.pem')).toBe('KEY')
    expect(ler('AtlansExecutor/logs/agent.log')).toBe('log')
    // Chromium's leftovers stay behind; the new folder keeps its own.
    expect(existe('AtlansExecutor/Cache')).toBe(false)
    expect(existe('AtlansExecutor/lockfile')).toBe(true)
  })

  it('migra quando a pasta nova ainda não existe', () => {
    instalacaoAntiga('Atlans Executor')
    expect(migrateLegacyData()).toBe('Atlans Executor')
    expect(path.join(raiz, 'AtlansExecutor')).toBe(USER_DATA)
    expect(ler('AtlansExecutor/certs/cert.pem')).toBe('CERT')
  })

  it('NÃO sobrescreve dados atuais com os antigos', () => {
    instalacaoAntiga('AtlasExecutor')
    escrever('AtlansExecutor/config/.env', 'EXECUTOR_ID=atual\n')

    expect(migrateLegacyData()).toBeNull()
    expect(ler('AtlansExecutor/config/.env')).toBe('EXECUTOR_ID=atual\n')
    expect(existe('AtlansExecutor/certs')).toBe(false)
    expect(existe('AtlasExecutor/certs/cert.pem')).toBe(true)
  })

  it('subpasta que já existe no destino fica onde está', () => {
    // `logs/` may already exist in the new folder; it is not merged nor
    // replaced, and the old one stays where it was.
    instalacaoAntiga('AtlasExecutor')
    escrever('AtlansExecutor/logs/novo.log', 'novo')

    expect(migrateLegacyData()).toBe('AtlasExecutor')
    expect(existe('AtlansExecutor/certs/cert.pem')).toBe(true)
    expect(existe('AtlansExecutor/logs/agent.log')).toBe(false)
    expect(ler('AtlansExecutor/logs/novo.log')).toBe('novo')
    expect(existe('AtlasExecutor/logs/agent.log')).toBe(true)
  })

  it('sem pasta antiga, ou só com resto do Chromium, não faz nada', () => {
    expect(migrateLegacyData()).toBeNull()
    escrever('AtlasExecutor/Cache/data_0', 'cache')
    expect(migrateLegacyData()).toBeNull()
    expect(existe('AtlansExecutor/Cache')).toBe(false)
  })

  it('é idempotente: a segunda chamada não faz nada', () => {
    instalacaoAntiga('AtlasExecutor')
    expect(migrateLegacyData()).toBe('AtlasExecutor')
    instalacaoAntiga('Atlas Executor')
    expect(migrateLegacyData()).toBeNull()
    expect(ler('AtlansExecutor/config/.env')).toBe('EXECUTOR_ID=antigo\n')
  })
})
