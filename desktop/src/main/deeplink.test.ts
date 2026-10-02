// desktop/src/main/deeplink.test.ts
//
// `atlans://enroll?…` e disparavel por QUALQUER pagina web — basta um link. O
// que separa a conveniencia do sequestro e a validacao aqui e o dialogo de
// confirmacao no Onboarding.
//
// O servidor nao vem mais do link: e a constante SERVIDOR. Um `server=` que
// aponte para outro host nao e ignorado, e sim motivo para RECUSAR o link
// inteiro — quem o escreveu declarou a intencao de desviar o vinculo.
import { describe, expect, it, vi } from 'vitest'

// O deeplink.ts importa `app` do electron; as funções testadas aqui não o usam.
// Sem o mock, o import carrega o pacote de verdade, que exige o binário baixado
// pelo postinstall — e o desktop/.npmrc desliga os scripts de instalação.
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
    // O caso central: uma pagina qualquer mandando o app se vincular ao
    // servidor dela.
    expect(interpretar('atlans://enroll?executor_id=a&otp=b&server=https://atacante.com')).toBeNull()
  })

  it('RECUSA subdominio', () => {
    // A comparacao e por host exato: um `*.atlans.example.org` deixaria um subdominio
    // comprometido, ou um bucket mal configurado, servirem de servidor de
    // enrollment.
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
    // Host certo com esquema errado nao e engano de digitacao: e link forjado.
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
  // A janela web usa isto para separar um `atlans://` clicado ali dentro (a
  // encaminhar ao main) de um link comum (vai ao navegador). Só o ESQUEMA: a
  // recusa de conteúdo é do `interpretar`.
  it('reconhece o esquema do app', () => {
    expect(ehDeepLink(OK)).toBe(true)
    expect(ehDeepLink('atlans://enroll?executor_id=a&otp=b')).toBe(true)
  })

  it('reconhece o esquema mesmo em link malformado — quem recusa é o interpretar', () => {
    // O ponto do conserto: sem params, `ehDeepLink` ainda diz "é deep link", a
    // janela encaminha, e o `interpretar` faz a recusa silenciosa. Se retornasse
    // `false` aqui, o clique cairia no descarte e nada aconteceria — o bug.
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
    // No Windows o deep link chega assim, junto dos argumentos do Electron.
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
