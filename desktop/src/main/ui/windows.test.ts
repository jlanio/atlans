// desktop/src/main/ui/windows.test.ts
//
// Regressão de "Abrir painel não faz nada".
//
// O botão vermelho da barra de título ESCONDE a janela em vez de encerrar o app
// — ele vive na bandeja, e fechá-lo no meio de um job seria destrutivo. Depois
// disso, o menu da bandeja chamava `focus()` numa janela escondida, e `focus()`
// não torna nada visível: o item do menu parecia morto, sem erro em lugar
// nenhum.
//
// O bug é de UMA linha ausente, e é exatamente por isso que ele volta se
// ninguém o travar.
import { describe, expect, it, vi } from 'vitest'

vi.mock('electron', () => ({ BrowserWindow: vi.fn(), shell: {} }))
vi.mock('../paths.js', () => ({
  IS_DEV: false,
  ICONE_APP: 'build/icon.ico',
  arquivoDoApp: (...p: string[]) => p.join('/'),
}))

const { trazerParaFrente } = await import('./windows.js')

function janela(estado: { minimizada?: boolean; visivel?: boolean }) {
  return {
    isMinimized: vi.fn(() => estado.minimizada ?? false),
    isVisible: vi.fn(() => estado.visivel ?? true),
    restore: vi.fn(),
    show: vi.fn(),
    focus: vi.fn(),
  }
}

describe('trazerParaFrente', () => {
  it('janela ESCONDIDA é mostrada — o caso do botão vermelho', () => {
    const w = janela({ visivel: false })
    trazerParaFrente(w)

    expect(w.show).toHaveBeenCalledOnce()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('janela minimizada é restaurada', () => {
    const w = janela({ minimizada: true })
    trazerParaFrente(w)

    expect(w.restore).toHaveBeenCalledOnce()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('minimizada E escondida: restaura e mostra', () => {
    // Acontece ao minimizar e depois fechar pelo tray, ou ao restaurar uma
    // sessão do Windows.
    const w = janela({ minimizada: true, visivel: false })
    trazerParaFrente(w)

    expect(w.restore).toHaveBeenCalledOnce()
    expect(w.show).toHaveBeenCalledOnce()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('janela já visível só recebe foco', () => {
    // `show()` numa janela visível é inofensivo, mas `restore()` numa janela
    // não-minimizada pode reposicioná-la — melhor não chamar o que não precisa.
    const w = janela({ visivel: true })
    trazerParaFrente(w)

    expect(w.restore).not.toHaveBeenCalled()
    expect(w.show).not.toHaveBeenCalled()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('foco vem por último, depois de restaurar e mostrar', () => {
    // Focar antes de a janela existir na tela não tem efeito no Windows.
    const ordem: string[] = []
    const w = {
      isMinimized: () => true,
      isVisible: () => false,
      restore: () => { ordem.push('restore') },
      show: () => { ordem.push('show') },
      focus: () => { ordem.push('focus') },
    }
    trazerParaFrente(w)
    expect(ordem).toEqual(['restore', 'show', 'focus'])
  })
})

// ── Link externo e navegação do painel ──────────────────────────────────────
// `shell.openExternal` entrega o destino ao SO: só http(s) e mailto passam, a
// mesma allowlist da janela web. E o painel nunca navega para fora.

describe('protegerNavegacao', () => {
  async function montar() {
    const electron = await import('electron')
    const abrir = vi.fn(async () => undefined)
    ;(electron.shell as { openExternal?: unknown }).openExternal = abrir
    const { protegerNavegacao } = await import('./windows.js')
    let aoAbrir: ((d: { url: string }) => { action: string }) | undefined
    type Ouvinte = (e: { preventDefault: () => void }, url: string) => void
    const ouvintes: Record<string, Ouvinte> = {}
    const conteudo = {
      setWindowOpenHandler: vi.fn((f) => { aoAbrir = f }),
      on: vi.fn((evento: string, f: Ouvinte) => { ouvintes[evento] = f }),
      getURL: vi.fn(() => 'http://localhost:5173/#log'),
    }
    protegerNavegacao(conteudo as never)
    return {
      abrir, aoAbrir: aoAbrir!,
      aoNavegar: ouvintes['will-navigate']!, aoRedirecionar: ouvintes['will-redirect']!,
    }
  }

  it('window.open com https vai ao navegador e a janela nova é negada', async () => {
    const { abrir, aoAbrir } = await montar()
    expect(aoAbrir({ url: 'https://atlans.example.org/docs' })).toEqual({ action: 'deny' })
    expect(abrir).toHaveBeenCalledWith('https://atlans.example.org/docs')
  })

  it.each(['file:///C:/Windows/System32/calc.exe', 'smb://atacante/compartilhamento', 'javascript:alert(1)'])(
    'esquema perigoso (%s) não chega ao SO',
    async (url) => {
      const { abrir, aoAbrir } = await montar()
      expect(aoAbrir({ url })).toEqual({ action: 'deny' })
      expect(abrir).not.toHaveBeenCalled()
    },
  )

  it('navegar o painel para fora é impedido e o destino seguro vai ao navegador', async () => {
    const { abrir, aoNavegar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoNavegar(evento, 'https://exemplo.com/pagina')
    expect(evento.preventDefault).toHaveBeenCalledOnce()
    expect(abrir).toHaveBeenCalledWith('https://exemplo.com/pagina')
  })

  it('navegar para um esquema perigoso é impedido e descartado', async () => {
    const { abrir, aoNavegar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoNavegar(evento, 'file:///etc/passwd')
    expect(evento.preventDefault).toHaveBeenCalledOnce()
    expect(abrir).not.toHaveBeenCalled()
  })

  it('recarregar a própria página passa — é o reload completo do Vite em dev', async () => {
    const { abrir, aoNavegar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoNavegar(evento, 'http://localhost:5173/')
    expect(evento.preventDefault).not.toHaveBeenCalled()
    expect(abrir).not.toHaveBeenCalled()
  })

  it('redirect para outra origem durante uma recarga é barrado', async () => {
    const { abrir, aoRedirecionar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoRedirecionar(evento, 'https://outro.exemplo/')
    expect(evento.preventDefault).toHaveBeenCalledOnce()
    expect(abrir).toHaveBeenCalledWith('https://outro.exemplo/')
  })

  it('mesmaPagina compara esquema, host e caminho — não hash nem query', async () => {
    const { mesmaPagina } = await import('./windows.js')
    expect(mesmaPagina('file:///app/dist/renderer/index.html#log', 'file:///app/dist/renderer/index.html')).toBe(true)
    expect(mesmaPagina('http://localhost:5173/#log', 'http://localhost:5173/?t=1')).toBe(true)
    expect(mesmaPagina('http://localhost:5173/', 'http://localhost:5174/')).toBe(false)
    expect(mesmaPagina('file:///app/dist/renderer/index.html', 'file:///etc/passwd')).toBe(false)
    expect(mesmaPagina('lixo', 'http://localhost:5173/')).toBe(false)
  })
})
