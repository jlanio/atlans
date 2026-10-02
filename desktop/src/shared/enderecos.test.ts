// O servidor e a UI que o app grava no executável vêm do build, nunca do código.
import { afterEach, describe, expect, it } from 'vitest'
import {
  DEV, TESTE, conferirMarcaDoBuild, defineDosEnderecos, enderecosDoBuild, marcaDoBuild,
} from '../../scripts/enderecos.mjs'
import { SERVIDOR } from './servidor.js'
import { UI_URL } from './ui.js'

const ORIGINAL = { ...process.env }
afterEach(() => {
  process.env = { ...ORIGINAL }
})

function ambiente(servidor?: string, ui?: string) {
  delete process.env.ATLANS_DESKTOP_SERVIDOR
  delete process.env.ATLANS_DESKTOP_UI_URL
  if (servidor !== undefined) process.env.ATLANS_DESKTOP_SERVIDOR = servidor
  if (ui !== undefined) process.env.ATLANS_DESKTOP_UI_URL = ui
}

describe('endereços do build', () => {
  it('os testes rodam com o domínio de exemplo, não com o de uma instalação', () => {
    expect(SERVIDOR).toBe(TESTE.servidor)
    expect(UI_URL).toBe(TESTE.ui)
  })

  it('um build de verdade sem os endereços falha, em vez de sair com um vazio', () => {
    ambiente()
    expect(() => enderecosDoBuild()).toThrow(/ATLANS_DESKTOP_SERVIDOR e ATLANS_DESKTOP_UI_URL/)
    ambiente('wss://agents.x.org')
    expect(() => enderecosDoBuild()).toThrow(/ATLANS_DESKTOP_UI_URL/)
  })

  it('o build grava os do ambiente, só com esquema e host', () => {
    ambiente(' wss://agents.x.org ', 'https://x.org/')
    expect(enderecosDoBuild()).toEqual({ servidor: 'wss://agents.x.org', ui: 'https://x.org' })
    expect(defineDosEnderecos(enderecosDoBuild())).toEqual({
      __ATLANS_SERVIDOR__: '"wss://agents.x.org"',
      __ATLANS_UI_URL__: '"https://x.org"',
    })
  })

  it('fora do desenvolvimento, só wss e https', () => {
    ambiente('ws://agents.x.org', 'https://x.org')
    expect(() => enderecosDoBuild()).toThrow(/wss:/)
    ambiente('wss://agents.x.org', 'http://x.org')
    expect(() => enderecosDoBuild()).toThrow(/https:/)
  })

  it('caminho, query ou credencial na URL são recusados', () => {
    for (const ui of ['https://x.org/app', 'https://x.org/?a=1', 'https://u:p@x.org', 'nao-e-url']) {
      ambiente('wss://agents.x.org', ui)
      expect(() => enderecosDoBuild(), ui).toThrow()
    }
  })

  it('o desenvolvimento local cai nos endereços locais e aceita ws/http', () => {
    ambiente()
    expect(enderecosDoBuild({ dev: true })).toEqual(DEV)
    ambiente('ws://localhost:9000', 'http://localhost:4000')
    expect(enderecosDoBuild({ dev: true })).toEqual({ servidor: 'ws://localhost:9000', ui: 'http://localhost:4000' })
  })
})

describe('marca do build', () => {
  it('o bundle de produção vira instalador', () => {
    const marca = marcaDoBuild({ dev: false, ...TESTE })
    expect(marca.modo).toBe('producao')
    expect(() => conferirMarcaDoBuild(marca)).not.toThrow()
  })

  it('o bundle do npm run dev não vira instalador', () => {
    const marca = marcaDoBuild({ dev: true, ...DEV })
    expect(() => conferirMarcaDoBuild(marca)).toThrow(/npm run dev.*ws:\/\/localhost:8000.*npm run build/)
  })

  it('sem marca (nenhum build, ou um dist antigo) também não', () => {
    expect(() => conferirMarcaDoBuild(null)).toThrow(/npm run build/)
    expect(() => conferirMarcaDoBuild('producao')).toThrow(/npm run build/)
  })
})
