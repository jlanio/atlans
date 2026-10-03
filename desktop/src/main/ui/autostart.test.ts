// desktop/src/main/ui/autostart.test.ts
//
// Regression of the "checkbox that turns on and flips back by itself".
//
// `app.getLoginItemSettings()` without options compares the command written in
// the registry with `process.execPath` and `args: []`. Since the write appends
// `--hidden`, the read returned `openAtLogin: false` with the entry written and
// CORRECT — and the UI concluded the change had not taken.
//
// Proven on the machine, with the same registry entry in both reads:
//   getLoginItemSettings()                    -> openAtLogin: false
//   getLoginItemSettings({args:['--hidden']}) -> openAtLogin: true
//
// The asymmetry between write and read is invisible in code review, so the
// test is about IT: the arguments used in both must be the same.
import { beforeEach, describe, expect, it, vi } from 'vitest'

interface Chamada { openAtLogin?: boolean; path?: string; args?: string[] }

let escritas: Chamada[] = []
let leituras: Chamada[] = []
/** What `getLoginItemSettings` returns — controlled by the test. */
let resposta = { openAtLogin: false, executableWillLaunchAtLogin: false }

vi.mock('electron', () => ({
  app: {
    setLoginItemSettings: (o: Chamada) => { escritas.push(o) },
    getLoginItemSettings: (o: Chamada = {}) => { leituras.push(o); return resposta },
  },
}))

const { definirAutostart, lerAutostart, ARG_OCULTO } = await import('./autostart.js')

beforeEach(() => {
  escritas = []
  leituras = []
  resposta = { openAtLogin: false, executableWillLaunchAtLogin: false }
})

describe('autostart', () => {
  it('a LEITURA usa os mesmos args da ESCRITA — o bug do checkbox', () => {
    definirAutostart(true)

    expect(escritas).toHaveLength(1)
    expect(leituras).toHaveLength(1)
    // Equality is the point: any divergence makes `openAtLogin` come back false
    // with the correct registry entry.
    expect(leituras[0]!.args).toEqual(escritas[0]!.args)
    expect(leituras[0]!.path).toEqual(escritas[0]!.path)
  })

  it('grava --hidden: sem ele o app abriria a janela a cada logon', () => {
    definirAutostart(true)
    expect(escritas[0]!.args).toContain(ARG_OCULTO)
    expect(escritas[0]!.openAtLogin).toBe(true)
  })

  it('desligar tambem passa path e args', () => {
    definirAutostart(false)
    expect(escritas[0]!.openAtLogin).toBe(false)
    expect(escritas[0]!.args).toContain(ARG_OCULTO)
  })

  it('devolve o estado RELIDO, e nao o pedido', () => {
    // Write blocked by group policy: the registry does not change, and the UI
    // must show "off" even though it asked for "on".
    resposta = { openAtLogin: false, executableWillLaunchAtLogin: false }
    expect(definirAutostart(true).ativo).toBe(false)
  })

  it('distingue "entrada existe" de "vai executar de verdade"', () => {
    // The user disabled the item in Task Manager -> Startup: the entry stays in
    // the registry, but the app does not start. A checked checkbox without a
    // caveat would be a lie.
    resposta = { openAtLogin: true, executableWillLaunchAtLogin: false }
    const e = lerAutostart()
    expect(e.ativo).toBe(true)
    expect(e.efetivo).toBe(false)
  })

  it('expoe o comando que fica no registro', () => {
    // Shown on screen: a logon entry the user cannot inspect is
    // indistinguishable from malware to whoever checks.
    expect(lerAutostart().comando).toContain(ARG_OCULTO)
  })

  it('um erro do registro vira mensagem, e nao excecao', () => {
    // Previously the catch returned `false` and the UI said "off" — the user
    // clicked again, and again, never knowing it had been refused.
    resposta = null as never
    const e = lerAutostart()
    expect(e.ativo).toBe(false)
    expect(e.erro).toBeTruthy()
  })
})
