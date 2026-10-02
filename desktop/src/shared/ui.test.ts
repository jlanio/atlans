// desktop/src/shared/ui.test.ts
//
// `ehOrigemInterna` é a fronteira que decide o que navega DENTRO da janela web
// e o que vai para o navegador do sistema. É segurança, não conveniência: um
// host que passe por "interno" por engano carregaria conteúdo de terceiros com
// o nosso preload — mínimo, mas próprio — e sob a sessão logada do usuário.
//
// A comparação é por host EXATO e HTTPS por padrão, no mesmo espírito da
// allowlist de servidor em deeplink.ts.
import { describe, expect, it } from 'vitest'
import { UI_HOST, UI_URL, ehExternoSeguro, ehOrigemInterna, hostsInternos } from './ui.js'

describe('hostsInternos', () => {
  it('inclui a UI e a sua API', () => {
    expect(hostsInternos()).toEqual(['atlans.example.org', 'api.atlans.example.org'])
  })

  it('deriva a API do host passado (staging)', () => {
    expect(hostsInternos('staging.atlans.example.org'))
      .toEqual(['staging.atlans.example.org', 'api.staging.atlans.example.org'])
  })

  it('UI_HOST é o host de UI_URL', () => {
    expect(UI_HOST).toBe('atlans.example.org')
    expect(UI_URL).toBe('https://atlans.example.org')
  })
})

describe('ehOrigemInterna', () => {
  it('aceita a própria UI', () => {
    expect(ehOrigemInterna('https://atlans.example.org/')).toBe(true)
    expect(ehOrigemInterna('https://atlans.example.org/workflow/create?x=1#y')).toBe(true)
  })

  it('aceita a API do produto', () => {
    expect(ehOrigemInterna('https://api.atlans.example.org/auth/me')).toBe(true)
  })

  // ── Externo ──────────────────────────────────────────────────────────────

  it('recusa outra origem — vai para o navegador', () => {
    expect(ehOrigemInterna('https://docs.atlans.example.org/')).toBe(false)
    expect(ehOrigemInterna('https://google.com/')).toBe(false)
  })

  it('recusa subdomínio fora da lista', () => {
    // Comparação por host EXATO: um `*.atlans.example.org` deixaria um subdomínio
    // comprometido servir conteúdo dentro da janela logada.
    expect(ehOrigemInterna('https://evil.atlans.example.org/')).toBe(false)
  })

  it('recusa host que apenas TERMINA com o permitido', () => {
    expect(ehOrigemInterna('https://atlans.example.org.mau.com/')).toBe(false)
    expect(ehOrigemInterna('https://notatlans.example.org/')).toBe(false)
  })

  // ── Esquema ──────────────────────────────────────────────────────────────

  it('recusa http:// no host certo por padrão (produção é HTTPS)', () => {
    expect(ehOrigemInterna('http://atlans.example.org/')).toBe(false)
  })

  it('recusa esquemas perigosos', () => {
    expect(ehOrigemInterna('javascript:alert(1)')).toBe(false)
    expect(ehOrigemInterna('file:///etc/passwd')).toBe(false)
    expect(ehOrigemInterna('data:text/html,<h1>x')).toBe(false)
  })

  // ── Override de staging/local ──────────────────────────────────────────────

  it('afrouxa para http só quando o main pede (staging/local)', () => {
    const opts = { hosts: ['localhost'], protocolos: ['https:', 'http:'] as const }
    expect(ehOrigemInterna('http://localhost:3000/', opts)).toBe(true)
    // Mesmo host, mas sem o http liberado → recusa.
    expect(ehOrigemInterna('http://localhost:3000/', { hosts: ['localhost'] })).toBe(false)
  })

  // ── Robustez ───────────────────────────────────────────────────────────────

  it('não lança com entrada arbitrária', () => {
    for (const lixo of ['', '://', 'nao-e-url', '%%%', 'atlans.example.org']) {
      expect(() => ehOrigemInterna(lixo)).not.toThrow()
      expect(ehOrigemInterna(lixo)).toBe(false)
    }
  })
})

describe('ehExternoSeguro', () => {
  it('aceita http, https e mailto', () => {
    expect(ehExternoSeguro('https://docs.atlans.example.org/guia')).toBe(true)
    expect(ehExternoSeguro('http://exemplo.com')).toBe(true)
    expect(ehExternoSeguro('mailto:suporte@atlans.example.org')).toBe(true)
  })

  it('RECUSA esquemas que o SO trataria de forma perigosa', () => {
    // O ponto do achado: openExternal repassa o destino ao SO. `smb:` no Windows
    // vaza hash NTLM; `file:` abre recurso local; `atlans:` dispara o deep link
    // de enrollment do próprio app.
    expect(ehExternoSeguro('smb://atacante.example/share')).toBe(false)
    expect(ehExternoSeguro('file:///etc/passwd')).toBe(false)
    expect(ehExternoSeguro('atlans://enroll?executor_id=x&otp=y')).toBe(false)
    expect(ehExternoSeguro('javascript:alert(1)')).toBe(false)
    expect(ehExternoSeguro('data:text/html,<h1>x')).toBe(false)
  })

  it('não lança com entrada malformada', () => {
    for (const lixo of ['', '://', 'nao-e-url', '%%%']) {
      expect(() => ehExternoSeguro(lixo)).not.toThrow()
      expect(ehExternoSeguro(lixo)).toBe(false)
    }
  })
})
