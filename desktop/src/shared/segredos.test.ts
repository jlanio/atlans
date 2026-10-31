// What scripts/payload-stage.mjs keeps out of the installer. A local build
// copies the working tree as it is, gitignored files included — the filter is
// the only thing between a developer's `.env.local` and every user's machine.
import { describe, expect, it } from 'vitest'
import { ehSegredo } from '../../scripts/segredos.mjs'

describe('ehSegredo', () => {
  it.each([
    '.env', '.env.local', '.env.production.local', '.env.bak', '.ENV',
    'key.pem', 'cert.pem', 'server.key', 'cliente.p12', 'cliente.PFX',
    'cert', 'certs', 'executor-certs',
  ])('fica de fora: %s', (nome) => {
    expect(ehSegredo(nome)).toBe(true)
  })

  it.each([
    // The template seed_env_from_example copies on first boot.
    '.env.example',
    'config.py', 'certificados.py', 'certs.py', 'keys.py', 'env_utils.py', 'README.env.md',
  ])('vai para o payload: %s', (nome) => {
    expect(ehSegredo(nome)).toBe(false)
  })
})
