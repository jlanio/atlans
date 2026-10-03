// desktop/src/main/deeplink.test.ts
//
// `atlans://enroll?…` can be triggered by ANY web page — a link is enough. What
// separates convenience from hijacking is the validation here and the
// confirmation dialog in Onboarding.
//
// The server no longer comes from the link: it is the SERVIDOR constant. A
// `server=` pointing to another host is not ignored, but rather a reason to
// REFUSE the whole link — whoever wrote it declared the intent to divert the
// binding.
import { describe, expect, it, vi } from 'vitest'

// deeplink.ts imports `app` from electron; the functions tested here don't use it.
// Without the mock, the import loads the real package, which requires the binary
// downloaded by postinstall — and desktop/.npmrc turns off install scripts.
vi.mock('electron', () => ({ app: {} }))

import { ehDeepLink, interpretar, urlDosArgumentos } from './deeplink.js'

const OK = 'atlans://enroll?executor_id=abc-123&otp=segredo&server=https://agents.atlans.example.org'

describe('interpretar', () => {
  it('aceita um pedido bem formado', () => {
    expect(interpretar(OK)).toEqual({ executorId: 'abc-123', otp: 'segredo' })
  })

  it('aceita sem `server` — ele nao e mais necessario', () => {
    expect(interpretar('atlans://enroll?executor_id=a&otp=b')).toEqual({
      executorId: 'a', otp: 'b',
    })
  })

  it('aceita wss:// apontando para o servidor do app', () => {
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=wss://agents.atlans.example.org'))
      .toEqual({ executorId: 'a', otp: 'b' })
  })

  it('NAO devolve o servidor — ele nao e decidido pelo link', () => {
    expect(interpretar(OK)).not.toHaveProperty('servidor')
  })

  // ── Host ────────────────────────────────────────────────────────────────────

  it('RECUSA servidor diferente do do app', () => {
    // The central case: some random page telling the app to bind to its
    // server.
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=https://atacante.com')).toBeNull()
  })

  it('RECUSA subdominio', () => {
    // The comparison is by exact host: a `*.atlans.example.org` would let a
    // compromised subdomain, or a misconfigured bucket, serve as an enrollment
    // server.
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=https://evil.atlans.example.org')).toBeNull()
  })

  it('RECUSA o dominio raiz — so `agents.` vale', () => {
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=https://atlans.example.org')).toBeNull()
  })

  it('RECUSA host que apenas TERMINA com o permitido', () => {
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=https://notagents.atlans.example.org')).toBeNull()
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=https://agents.atlans.example.org.mau.com')).toBeNull()
  })

  // ── Esquema ─────────────────────────────────────────────────────────────

  it('RECUSA http:// mesmo no host certo', () => {
    // Right host with the wrong scheme is not a typo: it is a forged link.
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=http://agents.atlans.example.org')).toBeNull()
  })

  it('RECUSA outro protocolo de deep link', () => {
    expect(interpretar('outro://enroll?executor_id=a&otp=b')).toBeNull()
  })

  it('RECUSA acao diferente de enroll', () => {
    expect(interpretar('atlans://executar?executor_id=a&otp=b')).toBeNull()
  })

  // ── Malformado ────────────────────────────────────────────────────────

  it.each([
    ['sem executor_id', 'atlans://enroll?otp=b'],
    ['sem otp', 'atlans://enroll?executor_id=a'],
    ['campos vazios', 'atlans://enroll?executor_id=&otp='],
    ['server nao e URL', 'atlans://enroll?executor_id=a&otp=b&server=nao-e-url'],
    ['nao e URL', 'isto nao e uma url'],
    ['vazio', ''],
  ])('RECUSA: %s', (_nome, url) => {
    expect(interpretar(url)).toBeNull()
  })

  it('nao lanca com entrada arbitraria', () => {
    for (const lixo of ['://', 'atlans://', '%%%', 'atlans://enroll?a=%E0%A4%A']) {
      expect(() => interpretar(lixo)).not.toThrow()
    }
  })
})

describe('ehDeepLink', () => {
  // The web window uses this to tell an `atlans://` clicked inside it (to be
  // forwarded to main) from an ordinary link (goes to the browser). Only the
  // SCHEME: refusing on content is `interpretar`'s job.
  it('reconhece o esquema do app', () => {
    expect(ehDeepLink(OK)).toBe(true)
    expect(ehDeepLink('atlans://enroll?executor_id=a&otp=b')).toBe(true)
  })

  it('reconhece o esquema mesmo em link malformado — quem recusa é o interpretar', () => {
    // The point of the fix: without params, `ehDeepLink` still says "it is a deep
    // link", the window forwards it, and `interpretar` does the silent refusal.
    // If it returned `false` here, the click would fall into the discard path
    // and nothing would happen — the bug.
    expect(ehDeepLink('atlans://enroll?executor_id=&otp=')).toBe(true)
    expect(ehDeepLink('atlans://executar?x=1')).toBe(true)
    expect(interpretar('atlans://enroll?executor_id=&otp=')).toBeNull()
  })

  it('NÃO confunde com link externo comum', () => {
    expect(ehDeepLink('https://atlans.example.org/executores')).toBe(false)
    expect(ehDeepLink('http://exemplo.com')).toBe(false)
    expect(ehDeepLink('mailto:suporte@atlans.example.org')).toBe(false)
    expect(ehDeepLink('outro://enroll?executor_id=a&otp=b')).toBe(false)
  })

  it('devolve false (sem lançar) para entrada que não é URL', () => {
    for (const lixo of ['', 'isto nao e uma url', '://', '%%%']) {
      expect(ehDeepLink(lixo)).toBe(false)
    }
  })
})

describe('urlDosArgumentos', () => {
  it('acha a URL no meio do argv', () => {
    // On Windows the deep link arrives like this, along with Electron's arguments.
    const argv = ['C:\\app\\Atlans Executor.exe', '--flag', OK, '--outro']
    expect(urlDosArgumentos(argv)).toBe(OK)
  })

  it('devolve null quando nao ha deep link', () => {
    expect(urlDosArgumentos(['C:\\app.exe', '--hidden'])).toBeNull()
  })

  it('ignora argumento que apenas contem o esquema', () => {
    expect(urlDosArgumentos(['--url=atlans://enroll?x=1'])).toBeNull()
  })
})
