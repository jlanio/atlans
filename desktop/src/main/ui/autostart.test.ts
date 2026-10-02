// desktop/src/main/ui/autostart.test.ts
//
// Regressão do "checkbox que liga e volta sozinho".
//
// `app.getLoginItemSettings()` sem opções compara o comando gravado no registro
// com `process.execPath` e `args: []`. Como a escrita acrescenta `--hidden`, a
// leitura devolvia `openAtLogin: false` com a entrada gravada e CORRETA — e a
// UI concluía que a alteração não pegou.
//
// Comprovado na máquina, com o mesmo registro nas duas leituras:
//   getLoginItemSettings()                    -> openAtLogin: false
//   getLoginItemSettings({args:['--hidden']}) -> openAtLogin: true
//
// A assimetria entre escrita e leitura é invisível em code review, então o
// teste é sobre ELA: os argumentos usados nas duas precisam ser os mesmos.
import { beforeEach, describe, expect, it, vi } from 'vitest'

interface Chamada { openAtLogin?: boolean; path?: string; args?: string[] }

let escritas: Chamada[] = []
let leituras: Chamada[] = []
/** O que `getLoginItemSettings` devolve — controlado por teste. */
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
    // A igualdade é o ponto: qualquer divergência faz `openAtLogin` voltar
    // false com o registro correto.
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
    // Escrita bloqueada por politica de grupo: o registro nao muda, e a UI
    // precisa mostrar "desligado" mesmo tendo pedido "ligado".
    resposta = { openAtLogin: false, executableWillLaunchAtLogin: false }
    expect(definirAutostart(true).ativo).toBe(false)
  })

  it('distingue "entrada existe" de "vai executar de verdade"', () => {
    // O usuario desativou o item em Gerenciador de Tarefas -> Inicializar: a
    // entrada continua no registro, mas o app nao sobe. Um checkbox marcado
    // sem ressalva seria mentira.
    resposta = { openAtLogin: true, executableWillLaunchAtLogin: false }
    const e = lerAutostart()
    expect(e.ativo).toBe(true)
    expect(e.efetivo).toBe(false)
  })

  it('expoe o comando que fica no registro', () => {
    // Exibido na tela: uma entrada de logon que o usuario nao consegue
    // inspecionar e indistinguivel de malware para quem for conferir.
    expect(lerAutostart().comando).toContain(ARG_OCULTO)
  })

  it('um erro do registro vira mensagem, e nao excecao', () => {
    // Antes o catch devolvia `false` e a UI dizia "desligado" — o usuario
    // clicava de novo, e de novo, sem nunca saber que foi recusado.
    resposta = null as never
    const e = lerAutostart()
    expect(e.ativo).toBe(false)
    expect(e.erro).toBeTruthy()
  })
})
