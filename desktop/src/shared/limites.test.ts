// desktop/src/shared/limites.test.ts
//
// O contrato com o executor: as faixas e os padrões que as telas usam são os de
// `executor/config.py`. O teste lê o fonte Python em vez de confiar num
// comentário "iguais aos do executor" — foi com esse comentário no lugar que as
// cópias divergiram (teto de 24 h no tempo limite que o executor não tem;
// GeoSync mostrando `bidirectional` com o executor em `upload`).
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { INTERVALO_SYNC, PADRAO_SYNC } from './geosync.js'
import { LIMITES, dentroDaFaixa, inteiroDoEnv, type Faixa } from './limites.js'

const SRC = fileURLToPath(new URL('..', import.meta.url))
const CONFIG_PY = fs.readFileSync(
  fileURLToPath(new URL('../../../executor/config.py', import.meta.url)), 'utf8',
)

const numero = (s: string) => Number(s.replace(/_/g, ''))

/** A faixa de `ler_int("NOME", padrao, minimo=..., maximo=...)` em executor/config.py. */
function faixaDoExecutor(nome: string): Faixa {
  const m = new RegExp(
    `ler_int\\(\\s*"${nome}"\\s*,\\s*([\\d_]+)\\s*,\\s*minimo=([\\d_]+)(?:\\s*,\\s*maximo=([\\d_]+))?\\s*\\)`,
  ).exec(CONFIG_PY)
  if (!m) throw new Error(`não achei a leitura de ${nome} em executor/config.py`)
  return { padrao: numero(m[1]!), min: numero(m[2]!), max: m[3] ? numero(m[3]) : null }
}

/** O padrão de `os.getenv("NOME", "padrão")` em executor/config.py. */
function textoDoExecutor(nome: string): string {
  const m = new RegExp(`os\\.getenv\\(\\s*"${nome}"\\s*,\\s*"([^"]*)"\\s*\\)`).exec(CONFIG_PY)
  if (!m) throw new Error(`não achei a leitura de ${nome} em executor/config.py`)
  return m[1]!
}

describe('contrato com executor/config.py', () => {
  it.each([
    ['workers', 'EXECUTOR_MAX_CONCURRENT'],
    ['filaMax', 'EXECUTOR_MAX_QUEUE_SIZE'],
    ['timeoutS', 'EXECUTOR_JOB_TIMEOUT'],
  ] as const)('LIMITES.%s é a faixa de %s', (campo, variavel) => {
    expect(LIMITES[campo]).toEqual(faixaDoExecutor(variavel))
  })

  it('o padrão do GeoSync é o do executor', () => {
    expect(PADRAO_SYNC).toEqual({
      modo: textoDoExecutor('EXECUTOR_SYNC_MODE'),
      conflito: textoDoExecutor('EXECUTOR_SYNC_CONFLICT_STRATEGY'),
    })
  })

  it('o intervalo que o app grava é um que o executor aceita', () => {
    // Fora da faixa, o executor descartaria o valor e usaria o padrão dele.
    expect(dentroDaFaixa(INTERVALO_SYNC, faixaDoExecutor('EXECUTOR_SYNC_INTERVAL'))).toBe(true)
  })
})

describe('inteiroDoEnv — o int() do Python sobre o valor do python-dotenv', () => {
  const faixa: Faixa = { padrao: 4, min: 1, max: 256 }

  it.each([
    ['8', 8], [' 8 ', 8], ['+8', 8], ['0008', 8], ['1_0', 10], ['8 # oito', 8],
    ['8x', 4], ['8.0', 4], ['1e1', 4], ['0x10', 4], ['_8', 4], ['8_', 4], ['1__0', 4],
    ['8#oito', 4], ['', 4], [undefined, 4], ['0', 4], ['257', 4], ['-1', 4],
  ])('%j → %d', (bruto, esperado) => {
    expect(inteiroDoEnv(bruto, faixa)).toBe(esperado)
  })

  it('sem teto, aceita qualquer inteiro a partir do mínimo', () => {
    expect(inteiroDoEnv('100000', { padrao: 3600, min: 1, max: null })).toBe(100000)
  })
})

describe('uma cópia só', () => {
  function fontes(dir: string): string[] {
    return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
      const p = path.join(dir, e.name)
      if (e.isDirectory()) return fontes(p)
      return /\.tsx?$/.test(e.name) && !/\.test\.tsx?$/.test(e.name) ? [p] : []
    })
  }

  it('nenhum outro arquivo do desktop redefine as faixas de execução', () => {
    // Main e renderer tinham cada um a sua tabela, e as duas já tinham o teto
    // de 24 h que o executor não tem.
    const redefinem = fontes(SRC)
      .filter((p) => path.basename(p) !== 'limites.ts')
      .filter((p) => /\b(workers|filaMax|timeoutS):\s*\{\s*(padrao|min|max)\b/.test(fs.readFileSync(p, 'utf8')))
      .map((p) => path.relative(SRC, p))
    expect(redefinem).toEqual([])
  })
})
