// desktop/src/main/state/config.test.ts
//
// A escrita do `.env` e uma reimplementacao de
// `executor/_env_utils.py::persist_env_var`. Estes casos travam o
// comportamento que importa: NAO destruir o que o app nao conhece.
//
// O arquivo carrega EXECUTOR_HOST_ALIASES, MINIO_*, LOG_FILE_AGENT,
// EXECUTOR_SYNC_* e o que mais o usuario tenha posto la. Reescrever a partir de
// um dicionario apagaria tudo isso em silencio.
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SERVIDOR } from '../../shared/servidor.js'

let tmp: string
let envFile: string
let certDir: string

// `paths.ts` importa `electron`, que nao existe fora do runtime do Electron.
// O mock cobre so o que este modulo usa.
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
    // dotenv aceita as duas formas; sem tirar, a comparacao com o que o Python
    // enxerga divergiria.
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
    // O split de um arquivo terminado em `\n` deixa um elemento vazio no fim;
    // empurrar a chave depois dele criava uma linha em branco por escrita.
    escrever('A=1\n')
    gravarEnv({ B: '2' })
    gravarEnv({ C: '3' })
    gravarEnv({ D: '4' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe('A=1\nB=2\nC=3\nD=4\n')
  })

  it('preserva linha em branco no meio do arquivo', () => {
    // Separam secoes no `.env.example`; so as do FIM sao removidas.
    escrever('# rede\nA=1\n\n# gis\nB=2\n')
    gravarEnv({ C: '3' })
    expect(fs.readFileSync(envFile, 'utf8')).toBe('# rede\nA=1\n\n# gis\nB=2\nC=3\n')
  })

  it('nao trata chave comentada como existente', () => {
    // Descomentar por engano mudaria o comportamento do executor sem o usuario
    // ter pedido.
    escrever('# EXECUTOR_ID=antigo\n')
    gravarEnv({ EXECUTOR_ID: 'novo' })

    const texto = fs.readFileSync(envFile, 'utf8')
    expect(texto).toContain('# EXECUTOR_ID=antigo')
    expect(texto).toContain('\nEXECUTOR_ID=novo')
  })

  it('termina sempre com quebra de linha', () => {
    // Sem isso a proxima chave gruda na ultima linha: `A=1B=2`.
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
    // O caso de quem apagou a pasta de certificados, ou de um enrollment que
    // falhou depois de gravar o .env.
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
    // `assert_enrolled` do Python exige os dois; divergir aqui faria o app
    // spawnar um executor que sai na hora.
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
    // O caso de segurança do módulo: `server_signing.pub` é a chave Ed25519 do
    // servidor, fixada por TOFU. Apagá-la reabriria a janela que o pinning
    // fecha — o próximo boot aceitaria qualquer chave que respondesse no
    // endereço configurado, e passaria a executar jobs assinados por ela.
    povoar(['cert.pem', 'key.pem', 'server_signing.pub'])
    descartarEnrollment()

    expect(existe('server_signing.pub')).toBe(true)
    expect(existe('cert.pem')).toBe(false)
  })

  it('preserva o trust store da CA interna', () => {
    // Não tem relação com a identidade deste executor; rebaixá-lo só custaria
    // um download a mais no próximo boot.
    povoar(['cert.pem', 'atlans-root.crt', 'atlans-ca-bundle.crt'])
    descartarEnrollment()

    expect(existe('atlans-root.crt')).toBe(true)
    expect(existe('atlans-ca-bundle.crt')).toBe(true)
  })

  it('deixa a configuracao em falta=enrollment, e nao em falta=config', () => {
    // O EXECUTOR_ID sobrevive e vira o valor inicial do formulário: quando o
    // executor foi apenas revogado (não recriado), ele continua valendo.
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
    // O Python compara em maiúsculas; aceitar minúsculo evita divergência com
    // um .env editado à mão.
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
    // `executor/_ambiente.py::ler_int` descarta em SILÊNCIO e usa o default. Se a
    // UI aceitasse o valor, ela mostraria 999 workers e o executor rodaria com
    // 4 — sem nada explicando a diferença.
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
    // `int()` do Python sobre o que o python-dotenv entrega. O `parseInt` lia
    // "8x" como 8, e a tela mostrava 8 workers com o executor rodando 4.
    escrever(`${linha}\n`)
    expect((ler() as unknown as Record<string, number>)[campo]).toBe(esperado)
  })

  it('tempo limite acima de 24 h vale: o executor não impõe teto', () => {
    // A tela tinha teto de 86 400 s que o executor não tem: com 100 000 no
    // `.env`, ela mostrava 3600 e o executor usava 100 000.
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
    // O ponto do travamento: um `.env` editado a mao para outro endereco volta
    // ao servidor correto assim que qualquer ajuste e salvo.
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
    // O padrão do executor (executor/config.py) é `upload`; a tela caía em
    // `bidirectional` e dizia que a pasta recebia o que o Drive publicava.
    escrever('EXECUTOR_SYNC_DIRS=C:/dados\n')
    expect(lerGeoSync()).toMatchObject({ modo: 'upload', conflito: 'remote-wins' })
  })

  it('salvar sem mexer não troca o modo que o executor usa', () => {
    // O bug que a tela mentindo causava: salvar qualquer ajuste do GeoSync
    // (a pasta, o workspace) gravava o `bidirectional` da tela, e o executor
    // passava a baixar do Drive e a seguir as exclusões feitas lá — sem
    // ninguém ter escolhido isso.
    escrever('EXECUTOR_SYNC_DIRS=C:/dados\n')
    gravarGeoSync(lerGeoSync())
    expect(lerEnv().EXECUTOR_SYNC_MODE).toBe('upload')
  })

  it('o modo gravado no .env vale', () => {
    escrever('EXECUTOR_SYNC_MODE=bidirectional\nEXECUTOR_SYNC_CONFLICT_STRATEGY=keep-both\n') // pragma: allowlist secret
    expect(lerGeoSync()).toMatchObject({ modo: 'bidirectional', conflito: 'keep-both' })
  })

  it('comentário no fim da linha não troca o modo (como o dotenv do executor lê)', () => {
    // Não reconhecido, o modo caía no padrão, e salvar o GeoSync gravava
    // `upload` por cima do `bidirectional` que o executor usava.
    escrever('EXECUTOR_SYNC_MODE=bidirectional # editado à mão\nEXECUTOR_SYNC_CONFLICT_STRATEGY="keep-both" # x\n') // pragma: allowlist secret
    expect(lerGeoSync()).toMatchObject({ modo: 'bidirectional', conflito: 'keep-both' })
  })
})

describe('artifactsDirEfetivo', () => {
  it('sem configuração, usa o padrão', () => {
    expect(artifactsDirEfetivo('C:/padrao')).toBe('C:/padrao')
  })

  it('o .env vence sobre o padrão', () => {
    // Sem isto, configurar a pasta em Ajustes gravava o valor e o executor
    // continuava escrevendo no diretório padrão — o usuário mudaria e nada
    // aconteceria.
    escrever('EXECUTOR_ARTIFACTS_DIR=D:/meus-dados\n')
    expect(artifactsDirEfetivo('C:/padrao')).toBe('D:/meus-dados')
  })

  it('valor em branco não vale como configuração', () => {
    escrever('EXECUTOR_ARTIFACTS_DIR=   \n')
    expect(artifactsDirEfetivo('C:/padrao')).toBe('C:/padrao')
  })
})
