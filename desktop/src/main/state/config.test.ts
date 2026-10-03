// desktop/src/main/state/config.test.ts
//
// Writing the `.env` is a reimplementation of
// `executor/_env_utils.py::persist_env_var`. These cases lock in the behavior
// that matters: do NOT destroy what the app does not know about.
//
// The file carries EXECUTOR_HOST_ALIASES, MINIO_*, LOG_FILE_AGENT,
// EXECUTOR_SYNC_* and whatever else the user has put there. Rewriting it from
// a dictionary would silently erase all of that.
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SERVIDOR } from '../../shared/servidor.js'

let tmp: string
let envFile: string
let certDir: string

// `paths.ts` imports `electron`, which does not exist outside the Electron
// runtime. The mock covers only what this module uses.
vi.mock('../paths.js', () => ({
  get ENV_FILE() { return envFile },
  get CERT_DIR() { return certDir },
}))

const {
  artifactsDirEfetivo, descartarEnrollment, gravarEnv, gravarExecucao, gravarGeoSync,
  lerConfiguracao, lerEnv, lerExecucao, lerGeoSync,
} = await import('./config.js')

beforeEach(() => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-cfg-'))
  envFile = path.join(tmp, 'config', '.env')
  certDir = path.join(tmp, 'certs')
  fs.mkdirSync(certDir, { recursive: true })
})

afterEach(() => { fs.rmSync(tmp, { recursive: true, force: true }) })

function escrever(conteudo: string) {
  fs.mkdirSync(path.dirname(envFile), { recursive: true })
  fs.writeFileSync(envFile, conteudo)
}

describe('lerEnv', () => {
  it('devolve vazio quando o arquivo nao existe', () => {
    expect(lerEnv()).toEqual({})
  })

  it('ignora comentarios e linhas em branco', () => {
    escrever('# comentario\n\nA=1\n  \nB=2\n')
    expect(lerEnv()).toEqual({ A: '1', B: '2' })
  })

  it('remove aspas do valor', () => {
    // dotenv accepts both forms; without stripping, the comparison with what
    // Python sees would diverge.
    escrever('A="com espaco"\nB=\'simples\'\n')
    expect(lerEnv()).toEqual({ A: 'com espaco', B: 'simples' })
  })

  it('preserva o = dentro do valor', () => {
    escrever('EXECUTOR_HOST_ALIASES=db=localhost:5433,redis=localhost:6379\n')
    expect(lerEnv().EXECUTOR_HOST_ALIASES).toBe('db=localhost:5433,redis=localhost:6379')
  })

  it('ignora linha sem =', () => {
    escrever('LIXO\nA=1\n')
    expect(lerEnv()).toEqual({ A: '1' })
  })
})

describe('gravarEnv', () => {
  it('cria o arquivo quando nao existe', () => {
    gravarEnv({ EXECUTOR_ID: 'abc' })
    expect(lerEnv()).toEqual({ EXECUTOR_ID: 'abc' })
  })

  it('atualiza no lugar, mantendo a posicao', () => {
    escrever('A=1\nEXECUTOR_ID=velho\nB=2\n')
    gravarEnv({ EXECUTOR_ID: 'novo' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe('A=1\nEXECUTOR_ID=novo\nB=2\n')
  })

  it('preserva comentarios e chaves desconhecidas', () => {
    // O caso que motiva o teste inteiro.
    escrever('# Configuracao do GeoSync\nEXECUTOR_SYNC_DIRS=C:/dados\nMINIO_ENDPOINT=http://x\n')
    gravarEnv({ EXECUTOR_ID: 'abc' })

    const texto = fs.readFileSync(envFile, 'utf8')
    expect(texto).toContain('# Configuracao do GeoSync')
    expect(texto).toContain('EXECUTOR_SYNC_DIRS=C:/dados')
    expect(texto).toContain('MINIO_ENDPOINT=http://x')
    expect(texto).toContain('EXECUTOR_ID=abc')
  })

  it('adiciona chave nova no fim', () => {
    escrever('A=1\n')
    gravarEnv({ B: '2' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe('A=1\nB=2\n')
  })

  it('nao acumula linhas em branco a cada escrita', () => {
    // Splitting a file that ends in `\n` leaves an empty element at the end;
    // pushing the key after it created one blank line per write.
    escrever('A=1\n')
    gravarEnv({ B: '2' })
    gravarEnv({ C: '3' })
    gravarEnv({ D: '4' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe('A=1\nB=2\nC=3\nD=4\n')
  })

  it('preserva linha em branco no meio do arquivo', () => {
    // They separate sections in `.env.example`; only the ones at the END are
    // removed.
    escrever('# rede\nA=1\n\n# gis\nB=2\n')
    gravarEnv({ C: '3' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe('# rede\nA=1\n\n# gis\nB=2\nC=3\n')
  })

  it('nao trata chave comentada como existente', () => {
    // Uncommenting by mistake would change the executor's behavior without the
    // user having asked for it.
    escrever('# EXECUTOR_ID=antigo\n')
    gravarEnv({ EXECUTOR_ID: 'novo' })

    const texto = fs.readFileSync(envFile, 'utf8')
    expect(texto).toContain('# EXECUTOR_ID=antigo')
    expect(texto).toContain('\nEXECUTOR_ID=novo')
  })

  it('termina sempre com quebra de linha', () => {
    // Without this the next key sticks to the last line: `A=1B=2`.
    escrever('A=1')
    gravarEnv({ B: '2' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe('A=1\nB=2\n')
  })

  it('e idempotente', () => {
    gravarEnv({ EXECUTOR_ID: 'abc' })
    const primeiro = fs.readFileSync(envFile, 'utf8')
    gravarEnv({ EXECUTOR_ID: 'abc' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe(primeiro)
  })
})

describe('lerConfiguracao', () => {
  const certificar = () => {
    for (const f of ['cert.pem', 'key.pem']) fs.writeFileSync(path.join(certDir, f), '')
  }

  it('sem nada: falta config', () => {
    const c = lerConfiguracao()
    expect(c.configurado).toBe(false)
    expect(c.falta).toBe('config')
  })

  it('com EXECUTOR_ID mas sem cert: falta enrollment', () => {
    // The case of someone who deleted the certificates folder, or of an
    // enrollment that failed after writing the .env.
    escrever('EXECUTOR_ID=abc\n')
    const c = lerConfiguracao()
    expect(c.configurado).toBe(false)
    expect(c.falta).toBe('enrollment')
    expect(c.executorId).toBe('abc')
  })

  it('com cert mas sem EXECUTOR_ID: falta config', () => {
    certificar()
    expect(lerConfiguracao().falta).toBe('config')
  })

  it('com os dois: configurado', () => {
    escrever('EXECUTOR_ID=abc\n')
    certificar()
    const c = lerConfiguracao()
    expect(c.configurado).toBe(true)
    expect(c.falta).toBeNull()
  })

  it('EXECUTOR_ID em branco nao conta', () => {
    escrever('EXECUTOR_ID=   \n')
    certificar()
    expect(lerConfiguracao().falta).toBe('config')
  })

  it('so cert.pem, sem key.pem, nao basta', () => {
    // Python's `assert_enrolled` requires both; diverging here would make the
    // app spawn an executor that exits immediately.
    escrever('EXECUTOR_ID=abc\n')
    fs.writeFileSync(path.join(certDir, 'cert.pem'), '')
    expect(lerConfiguracao().falta).toBe('enrollment')
  })
})

describe('descartarEnrollment', () => {
  const povoar = (nomes: string[]) => {
    for (const n of nomes) fs.writeFileSync(path.join(certDir, n), 'conteudo')
  }
  const existe = (n: string) => fs.existsSync(path.join(certDir, n))

  it('remove o material de identidade do executor', () => {
    povoar(['cert.pem', 'chain.pem', 'ca.pem', 'key.pem', 'x25519_key.pem'])
    const { removidos } = descartarEnrollment()

    expect(removidos).toHaveLength(5)
    for (const n of ['cert.pem', 'key.pem', 'x25519_key.pem']) expect(existe(n)).toBe(false)
  })

  it('PRESERVA o pin da chave de assinatura do servidor', () => {
    // The module's security case: `server_signing.pub` is the server's Ed25519
    // key, pinned via TOFU. Deleting it would reopen the window that pinning
    // closes — the next boot would accept any key that answered at the
    // configured address, and would start running jobs signed by it.
    povoar(['cert.pem', 'key.pem', 'server_signing.pub'])
    descartarEnrollment()

    expect(existe('server_signing.pub')).toBe(true)
    expect(existe('cert.pem')).toBe(false)
  })

  it('preserva o trust store da CA interna', () => {
    // It has nothing to do with this executor's identity; downgrading it would
    // only cost one extra download on the next boot.
    povoar(['cert.pem', 'atlans-root.crt', 'atlans-ca-bundle.crt'])
    descartarEnrollment()

    expect(existe('atlans-root.crt')).toBe(true)
    expect(existe('atlans-ca-bundle.crt')).toBe(true)
  })

  it('deixa a configuracao em falta=enrollment, e nao em falta=config', () => {
    // The EXECUTOR_ID survives and becomes the form's initial value: when the
    // executor was only revoked (not recreated), it is still valid.
    escrever('EXECUTOR_ID=abc\n')
    povoar(['cert.pem', 'key.pem'])
    descartarEnrollment()

    const c = lerConfiguracao()
    expect(c.configurado).toBe(false)
    expect(c.falta).toBe('enrollment')
    expect(c.executorId).toBe('abc')
  })

  it('e idempotente e nao falha com a pasta vazia', () => {
    expect(descartarEnrollment().removidos).toEqual([])
    povoar(['cert.pem'])
    expect(descartarEnrollment().removidos).toEqual(['cert.pem'])
    expect(descartarEnrollment().removidos).toEqual([])
  })
})

describe('configuração de execução', () => {
  const PADRAO_ART = 'C:/padrao/artifacts'
  const ler = () => lerExecucao(PADRAO_ART)

  it('usa os defaults quando o .env está vazio', () => {
    const c = ler()
    expect(c).toMatchObject({
      workers: 4, filaMax: 50, timeoutS: 3600,
      artifactsDir: PADRAO_ART, nivelLog: 'INFO',
    })
  })

  it('lê os valores do .env', () => {
    escrever('EXECUTOR_MAX_CONCURRENT=8\nEXECUTOR_JOB_TIMEOUT=120\nLOG_LEVEL=debug\n')
    const c = ler()
    expect(c.workers).toBe(8)
    expect(c.timeoutS).toBe(120)
    // Python compares in uppercase; accepting lowercase avoids diverging from a
    // hand-edited .env.
    expect(c.nivelLog).toBe('DEBUG')
  })

  it.each([
    ['EXECUTOR_MAX_CONCURRENT=0', 'workers', 4],
    ['EXECUTOR_MAX_CONCURRENT=999', 'workers', 4],
    ['EXECUTOR_MAX_CONCURRENT=abc', 'workers', 4],
    ['EXECUTOR_MAX_QUEUE_SIZE=0', 'filaMax', 50],
    ['EXECUTOR_MAX_QUEUE_SIZE=99999', 'filaMax', 50],
    ['EXECUTOR_JOB_TIMEOUT=0', 'timeoutS', 3600],
  ])('valor fora da faixa (%s) cai no default, como no Python', (linha, campo, esperado) => {
    // `executor/_ambiente.py::ler_int` SILENTLY discards it and uses the default.
    // If the UI accepted the value, it would show 999 workers and the executor
    // would run with 4 — with nothing explaining the difference.
    escrever(`${linha}\n`)
    expect((ler() as unknown as Record<string, number>)[campo]).toBe(esperado)
  })

  it.each([
    ['EXECUTOR_MAX_CONCURRENT=8x', 'workers', 4],
    ['EXECUTOR_MAX_CONCURRENT=8.5', 'workers', 4],
    ['EXECUTOR_MAX_QUEUE_SIZE=1_000', 'filaMax', 1000],
    ['EXECUTOR_MAX_CONCURRENT= +8 ', 'workers', 8],
    ['EXECUTOR_MAX_CONCURRENT=8 # oito', 'workers', 8],
  ])('lê o número como o executor o lê (%s)', (linha, campo, esperado) => {
    // Python's `int()` over what python-dotenv delivers. `parseInt` read "8x"
    // as 8, and the screen showed 8 workers with the executor running 4.
    escrever(`${linha}\n`)
    expect((ler() as unknown as Record<string, number>)[campo]).toBe(esperado)
  })

  it('tempo limite acima de 24 h vale: o executor não impõe teto', () => {
    // The screen had a ceiling of 86,400 s that the executor does not have: with
    // 100,000 in the `.env`, it showed 3600 and the executor used 100,000.
    escrever('EXECUTOR_JOB_TIMEOUT=100000\n')
    expect(ler().timeoutS).toBe(100000)
  })

  it('salvar sem mexer não troca o tempo limite que o executor usa', () => {
    escrever('EXECUTOR_JOB_TIMEOUT=100000\n')
    gravarExecucao(ler())
    expect(lerEnv().EXECUTOR_JOB_TIMEOUT).toBe('100000')
  })

  it('nível de log desconhecido cai em INFO', () => {
    escrever('LOG_LEVEL=VERBOSO\n')
    expect(ler().nivelLog).toBe('INFO')
  })

  it('grava e relê sem perder nada', () => {
    gravarExecucao({
      workers: 12, filaMax: 200, timeoutS: 60,
      artifactsDir: 'D:/dados', nivelLog: 'WARNING',
    })
    expect(ler()).toMatchObject({
      workers: 12, filaMax: 200, timeoutS: 60,
      artifactsDir: 'D:/dados', nivelLog: 'WARNING',
    })
  })

  it('o servidor gravado e SEMPRE o do app, nunca o que estava no .env', () => {
    // The point of the lock: a `.env` hand-edited to another address goes back
    // to the correct server as soon as any setting is saved.
    escrever('EXECUTOR_SERVER_URL=wss://outro.servidor\n')
    gravarExecucao({
      workers: 4, filaMax: 50, timeoutS: 60, artifactsDir: 'D:/x', nivelLog: 'INFO',
    })
    expect(lerEnv().EXECUTOR_SERVER_URL).toBe(SERVIDOR)
  })

  it('gravar sanitiza valor fora da faixa em vez de persistir lixo', () => {
    gravarExecucao({
      workers: 9999, filaMax: -5, timeoutS: 0,
      artifactsDir: 'D:/x', nivelLog: 'INFO',
    })
    expect(lerEnv().EXECUTOR_MAX_CONCURRENT).toBe('4')
    expect(lerEnv().EXECUTOR_MAX_QUEUE_SIZE).toBe('50')
    expect(lerEnv().EXECUTOR_JOB_TIMEOUT).toBe('3600')
  })

  it('preserva chaves que a tela não conhece', () => {
    escrever('EXECUTOR_HOST_ALIASES=db=localhost:5433\nMINIO_ENDPOINT=http://x\n')
    gravarExecucao({
      workers: 2, filaMax: 10, timeoutS: 60,
      artifactsDir: 'D:/x', nivelLog: 'INFO',
    })
    const env = lerEnv()
    expect(env.EXECUTOR_HOST_ALIASES).toBe('db=localhost:5433')
    expect(env.MINIO_ENDPOINT).toBe('http://x')
  })
})

describe('configuração do GeoSync', () => {
  it('sem EXECUTOR_SYNC_MODE, mostra o modo que o executor usa: upload', () => {
    // The executor's default (executor/config.py) is `upload`; the screen fell
    // back to `bidirectional` and said the folder received what Drive
    // published.
    escrever('EXECUTOR_SYNC_DIRS=C:/dados\n')
    expect(lerGeoSync()).toMatchObject({ modo: 'upload', conflito: 'remote-wins' })
  })

  it('salvar sem mexer não troca o modo que o executor usa', () => {
    // The bug the lying screen caused: saving any GeoSync setting (the folder,
    // the workspace) wrote the screen's `bidirectional`, and the executor
    // started downloading from Drive and following the deletions made there —
    // without anyone having chosen that.
    escrever('EXECUTOR_SYNC_DIRS=C:/dados\n')
    gravarGeoSync(lerGeoSync())
    expect(lerEnv().EXECUTOR_SYNC_MODE).toBe('upload')
  })

  it('o modo gravado no .env vale', () => {
    escrever('EXECUTOR_SYNC_MODE=bidirectional\nEXECUTOR_SYNC_CONFLICT_STRATEGY=keep-both\n') // pragma: allowlist secret
    expect(lerGeoSync()).toMatchObject({ modo: 'bidirectional', conflito: 'keep-both' })
  })

  it('comentário no fim da linha não troca o modo (como o dotenv do executor lê)', () => {
    // Not recognized, the mode fell back to the default, and saving GeoSync
    // wrote `upload` over the `bidirectional` the executor was using.
    escrever('EXECUTOR_SYNC_MODE=bidirectional # editado à mão\nEXECUTOR_SYNC_CONFLICT_STRATEGY="keep-both" # x\n') // pragma: allowlist secret
    expect(lerGeoSync()).toMatchObject({ modo: 'bidirectional', conflito: 'keep-both' })
  })
})

describe('artifactsDirEfetivo', () => {
  it('sem configuração, usa o padrão', () => {
    expect(artifactsDirEfetivo('C:/padrao')).toBe('C:/padrao')
  })

  it('o .env vence sobre o padrão', () => {
    // Without this, setting the folder in Settings wrote the value and the
    // executor kept writing to the default directory — the user would change
    // it and nothing would happen.
    escrever('EXECUTOR_ARTIFACTS_DIR=D:/meus-dados\n')
    expect(artifactsDirEfetivo('C:/padrao')).toBe('D:/meus-dados')
  })

  it('valor em branco não vale como configuração', () => {
    escrever('EXECUTOR_ARTIFACTS_DIR=   \n')
    expect(artifactsDirEfetivo('C:/padrao')).toBe('C:/padrao')
  })
})
