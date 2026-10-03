// desktop/src/renderer/lib/formato.test.ts
//
// Range boundaries are where wrong rounding shows up: a value just below 60 s
// or 60 min that, rounded after the range is chosen, becomes "60.0s" or
// "59m 60s".
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
