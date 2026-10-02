// desktop/src/renderer/lib/formato.test.ts
//
// As bordas de faixa são onde o arredondamento errado aparece: um valor logo
// abaixo de 60 s ou de 60 min que, arredondado depois da escolha da faixa, vira
// "60.0s" ou "59m 60s".
import { describe, expect, it } from 'vitest'
import { duracao } from './formato.js'

describe('duracao', () => {
  it.each([
    [null, '—'],
    [undefined, '—'],
    [0, '0.0s'],
    [12.34, '12.3s'],
    [59.94, '59.9s'],
    [59.97, '1m 0s'],
    [60, '1m 0s'],
    [61.5, '1m 2s'],
    [119.6, '2m 0s'],
    [3599.4, '59m 59s'],
    [3599.7, '1h 0m'],
    [3660, '1h 1m'],
    [7800, '2h 10m'],
  ])('%s s → %s', (s, esperado) => {
    expect(duracao(s)).toBe(esperado)
  })
})
